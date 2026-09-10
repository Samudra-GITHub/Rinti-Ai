import json

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional, List

import memory.database as db
from auth.dependencies import get_current_user, verify_csrf_header
from config import settings
from core.brain import generate_response, stream_response

router = APIRouter()

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    model: Optional[str] = None

class ChatResponse(BaseModel):
    conversation_id: str
    message: str
    state: str

class MessageItem(BaseModel):
    id: str
    role: str
    content: str
    timestamp: str
    research_session_id: Optional[str] = None

class ConversationSummary(BaseModel):
    id: str
    title: Optional[str] = None
    created_at: str
    updated_at: Optional[str] = None

class RenameConversationRequest(BaseModel):
    title: str


def _owned_conversation_id(requested_id: Optional[str], user_id: str) -> str:
    """Resolves the conversation id to use for this request.

    A client-supplied id is never trusted at face value — it must belong to
    the authenticated user, or the request is rejected outright rather than
    silently falling back to a new conversation (which would look like data
    loss) or silently writing into someone else's conversation.
    """
    if not requested_id:
        return db.create_conversation(user_id)
    owner = db.conversation_owner(requested_id)
    if owner is None:
        # Unknown id from this client — treat it as "start fresh" rather than
        # erroring, since a stale/local id (e.g. after data reset) is a
        # normal, harmless case.
        return db.create_conversation(user_id)
    if owner != user_id:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return requested_id


def _check_chat_quota(user_id: str) -> None:
    usage = db.check_and_increment_usage(user_id, "chat", settings.max_chat_messages_per_day)
    if not usage["allowed"]:
        raise HTTPException(
            status_code=429,
            detail=(
                f"You've reached today's message limit ({usage['limit']} messages). "
                "It resets at midnight UTC. This limit is per-account — it doesn't "
                "affect other users."
            ),
        )


@router.post("/chat", response_model=ChatResponse, dependencies=[Depends(verify_csrf_header)])
async def chat_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")
    _check_chat_quota(current_user["id"])
    try:
        conv_id = _owned_conversation_id(request.conversation_id, current_user["id"])
        reply = generate_response(request.message, conv_id, current_user["id"], model=request.model)

        return ChatResponse(
            conversation_id=conv_id,
            message=reply,
            state="idle"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

async def _quota_exceeded_stream(message: str):
    yield f"event: error\ndata: {json.dumps({'code': 'daily_limit_reached', 'message': message})}\n\n"


@router.post("/chat/stream", dependencies=[Depends(verify_csrf_header)])
async def chat_stream_endpoint(request: ChatRequest, current_user: dict = Depends(get_current_user)):
    if not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty")

    usage = db.check_and_increment_usage(current_user["id"], "chat", settings.max_chat_messages_per_day)
    if not usage["allowed"]:
        message = (
            f"You've reached today's message limit ({usage['limit']} messages). "
            "It resets at midnight UTC. This limit is per-account — it doesn't affect other users."
        )
        return StreamingResponse(
            _quota_exceeded_stream(message),
            media_type="text/event-stream",
            headers={"Cache-Control": "no-cache"},
        )

    conv_id = _owned_conversation_id(request.conversation_id, current_user["id"])
    generator = stream_response(request.message, conv_id, current_user["id"], model=request.model)

    return StreamingResponse(
        generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Conversation-Id": conv_id,
        },
    )

class UsageResponse(BaseModel):
    chat_used: int
    chat_limit: int
    research_used: int
    research_limit: int


@router.get("/usage", response_model=UsageResponse)
async def usage_endpoint(current_user: dict = Depends(get_current_user)):
    usage = db.get_usage_today(current_user["id"])
    return UsageResponse(
        chat_used=usage["chat_used"],
        chat_limit=settings.max_chat_messages_per_day,
        research_used=usage["research_used"],
        research_limit=settings.max_research_queries_per_day,
    )


@router.get("/conversations", response_model=List[ConversationSummary])
async def list_conversations_endpoint(current_user: dict = Depends(get_current_user)):
    try:
        return db.list_conversations(current_user["id"])
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/conversations/{conversation_id}", response_model=List[MessageItem])
async def get_conversation(conversation_id: str, current_user: dict = Depends(get_current_user)):
    try:
        history = db.get_conversation_history(conversation_id, current_user["id"])
        return history or []
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.patch(
    "/conversations/{conversation_id}",
    response_model=ConversationSummary,
    dependencies=[Depends(verify_csrf_header)],
)
async def rename_conversation_endpoint(
    conversation_id: str, request: RenameConversationRequest, current_user: dict = Depends(get_current_user)
):
    if not request.title.strip():
        raise HTTPException(status_code=400, detail="Title cannot be empty")
    success = db.rename_conversation(conversation_id, current_user["id"], request.title.strip())
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    summary = db.get_conversation_summary(conversation_id, current_user["id"])
    if summary is None:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return summary

@router.delete("/conversations/{conversation_id}", dependencies=[Depends(verify_csrf_header)])
async def delete_conversation_endpoint(conversation_id: str, current_user: dict = Depends(get_current_user)):
    success = db.delete_conversation(conversation_id, current_user["id"])
    if not success:
        raise HTTPException(status_code=404, detail="Conversation not found")
    return {"status": "deleted", "id": conversation_id}
