import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Any, Dict, List, Optional
import uuid

import memory.database as db
from auth.dependencies import get_current_user, verify_csrf_header
from config import settings
from research import storage
from research.config import research_available
from research.engine import ResearchEngine
from research.intent import detect_intent
from research.models import ResearchMode

router = APIRouter()


class ResearchRequest(BaseModel):
    query: str
    conversation_id: Optional[str] = None
    mode: Optional[str] = None  # "QUICK" | "STANDARD"


class IntentRequest(BaseModel):
    query: str


class IntentResponse(BaseModel):
    intent: str
    needs_research: bool
    requires_freshness: bool
    reason: str


class ResearchStatusResponse(BaseModel):
    available: bool
    provider: Optional[str] = None
    modes: List[str] = []


@router.get("/research/status", response_model=ResearchStatusResponse)
async def research_status_endpoint(current_user: dict = Depends(get_current_user)):
    """Whether research can run. Never exposes the key itself — only availability."""
    available = research_available()
    return ResearchStatusResponse(
        available=available,
        provider="tavily" if available else None,
        modes=[m.value for m in ResearchMode] if available else [],
    )


@router.post("/research/intent", response_model=IntentResponse, dependencies=[Depends(verify_csrf_header)])
async def research_intent_endpoint(request: IntentRequest, current_user: dict = Depends(get_current_user)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")
    decision = detect_intent(request.query)
    return IntentResponse(
        intent=decision.intent.value,
        needs_research=decision.needs_research,
        requires_freshness=decision.requires_freshness,
        reason=decision.reason,
    )


@router.post("/research/stream", dependencies=[Depends(verify_csrf_header)])
async def research_stream_endpoint(request: ResearchRequest, current_user: dict = Depends(get_current_user)):
    if not request.query.strip():
        raise HTTPException(status_code=400, detail="Query cannot be empty")

    try:
        mode = ResearchMode(request.mode) if request.mode else ResearchMode.QUICK
    except ValueError:
        mode = ResearchMode.QUICK

    user_id = current_user["id"]

    usage = db.check_and_increment_usage(user_id, "research", settings.max_research_queries_per_day)
    if not usage["allowed"]:
        message = (
            f"You've reached today's research limit ({usage['limit']} queries). "
            "It resets at midnight UTC. This limit is per-account — it doesn't affect other users."
        )

        async def quota_stream():
            yield f"event: error\ndata: {json.dumps({'code': 'daily_limit_reached', 'message': message})}\n\n"

        return StreamingResponse(
            quota_stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"}
        )

    # A client-supplied conversation_id is only honored if it's actually owned
    # by this user — never trusted at face value (matches /api/chat/stream).
    if request.conversation_id:
        owner = db.conversation_owner(request.conversation_id)
        if owner is not None and owner != user_id:
            raise HTTPException(status_code=404, detail="Conversation not found")
        conversation_id = request.conversation_id if owner == user_id else db.create_conversation(user_id)
    else:
        conversation_id = db.create_conversation(user_id)

    session_id = f"rs_{uuid.uuid4().hex[:12]}"

    async def generator():
        final_result = None
        try:
            engine = ResearchEngine()
            async for frame, result in engine.run(
                request.query, mode=mode, session_id=session_id
            ):
                final_result = result
                yield frame
        finally:
            if final_result is not None:
                # Persist the turn into the normal conversation history so research
                # answers survive refresh exactly like ordinary chat messages do.
                try:
                    if final_result.answer:
                        db.save_message(conversation_id, "user", request.query)
                        db.save_message(
                            conversation_id, "assistant", final_result.answer,
                            research_session_id=session_id,
                        )
                    storage.save_session(
                        final_result,
                        conversation_id=conversation_id,
                        user_id=user_id,
                        status="partial" if final_result.partial else "completed",
                    )
                except Exception as exc:
                    print(f"[research persistence error] {type(exc).__name__}")

    return StreamingResponse(
        generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Conversation-Id": conversation_id,
            "X-Research-Session-Id": session_id,
        },
    )


@router.get("/research/{session_id}")
async def get_research_session(session_id: str, current_user: dict = Depends(get_current_user)) -> Dict[str, Any]:
    session = storage.get_session(session_id, current_user["id"])
    if session is None:
        raise HTTPException(status_code=404, detail="Research session not found")
    return session
