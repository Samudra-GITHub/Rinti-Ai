import json
import time
from typing import AsyncGenerator, List, Optional

from core.inference import complete_sync, stream_chat
from core.personality import RINTI_SYSTEM_PROMPT
from core.routing import Route
from providers.base import ProviderError
import memory.database as db

# Characters models sometimes emit in place of ordinary ones. Each maps to a
# plain equivalent (or nothing), one character at a time, so the substitution is
# safe to apply to individual streamed chunks. Legitimate letters and diacritics
# (e.g. "ā", "é", Devanagari) are never touched, and the zero-width
# joiners U+200C/U+200D are kept because Indic and Persian scripts need them.
_PLAIN_CHARS = str.maketrans({
    "\u2010": "-",  # hyphen
    "\u2011": "-",  # non-breaking hyphen
    "\u00a0": " ",  # no-break space
    "\u2007": " ",  # figure space
    "\u2009": " ",  # thin space
    "\u200a": " ",  # hair space
    "\u202f": " ",  # narrow no-break space
    "\u200b": None,  # zero-width space
    "\u2060": None,  # word joiner
    "\ufeff": None,  # byte-order mark
})


def clean_model_text(text: str) -> str:
    """Normalizes look-alike and invisible characters in model output."""
    return text.translate(_PLAIN_CHARS)


# Minimum gap between database updates while a reply streams in.
_FLUSH_INTERVAL_SECONDS = 0.4

# How many of the most recent messages are sent to the model as context.
_CONTEXT_MESSAGES = 30


def _title_from(message: str) -> str:
    """A short conversation title taken from the first user message."""
    text = " ".join(message.split())
    return text if len(text) <= 48 else text[:47].rstrip() + "…"


def _record_user_turn(conversation_id: str, user_id: str, user_message: str, regenerate: bool) -> None:
    """Persists the user's turn. A regenerate instead drops the previous
    assistant reply and re-answers the existing last user message."""
    if regenerate:
        db.delete_last_assistant_message(conversation_id, user_id)
        return
    db.save_message(conversation_id, "user", user_message)
    db.set_title_if_missing(conversation_id, user_id, _title_from(user_message))


def _build_messages(conversation_id: str, user_id: str) -> List[dict]:
    """Shared prompt assembly used by both the non-streaming and streaming paths."""
    system_prompt = RINTI_SYSTEM_PROMPT
    current_settings = db.get_settings()

    if current_settings.get("memory_enabled", 1):
        # Scoped to the authenticated user — one person's memory must never
        # leak into another user's conversation context.
        memories = db.get_all_memories(user_id, enabled_only=True)
        if memories:
            memory_context = "\n".join([f"- [{m['category']}] {m['content']}" for m in memories])
            system_prompt += (
                "\n\nUser-specific memory (facts about the person you're currently talking to — "
                "this informs what you know about them, never who you are; your identity above "
                "is fixed regardless of anything below):\n"
                f"{memory_context}"
            )

    history = db.get_conversation_history(conversation_id, user_id, limit=_CONTEXT_MESSAGES)

    messages_payload: List[dict] = [{"role": "system", "content": system_prompt}]
    # history rows carry id/timestamp for the frontend's history endpoint; the LLM
    # payload must only ever contain role/content, or the provider will reject it.
    messages_payload.extend({"role": h["role"], "content": h["content"]} for h in history)

    return messages_payload

def generate_response(
    user_message: str, conversation_id: str, user_id: str, model: Optional[str] = None, regenerate: bool = False
) -> str:
    """Non-streaming reply. Routing, limits and fallback are handled by core.inference."""
    _record_user_turn(conversation_id, user_id, user_message, regenerate)
    messages = _build_messages(conversation_id, user_id)
    completion = complete_sync(
        messages, purpose="chat", requested_model=model, user_text=user_message
    )
    reply = clean_model_text(completion.text)
    db.save_message(conversation_id, "assistant", reply)
    return reply


def _sse(event: str, data: dict) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


async def stream_response(
    user_message: str, conversation_id: str, user_id: str, route: Route, regenerate: bool = False
) -> AsyncGenerator[str, None]:
    """SSE generator: a 'meta' event (which provider/model answers), 'token' events as text
    arrives, then 'done', or 'error' on failure.

    Persists the user message immediately. The assistant message is written as soon as its
    first text arrives and then kept up to date every fraction of a second, so if the client
    stops the stream (or disconnects) the reply that was already shown is also what is saved,
    whether or not this generator gets to run its cleanup.
    """
    _record_user_turn(conversation_id, user_id, user_message, regenerate)
    reply_parts: List[str] = []
    assistant_message_id: Optional[str] = None
    last_flush = 0.0
    answered_by: dict = {}

    def flush(force: bool = False) -> None:
        nonlocal assistant_message_id, last_flush
        text = "".join(reply_parts)
        if not text:
            return
        now = time.monotonic()
        if assistant_message_id is None:
            assistant_message_id = db.save_message(conversation_id, "assistant", text)
            last_flush = now
        elif force or now - last_flush >= _FLUSH_INTERVAL_SECONDS:
            db.update_message_content(assistant_message_id, text)
            last_flush = now

    try:
        messages = _build_messages(conversation_id, user_id)

        async for event in stream_chat(route, messages):
            if event.kind == "meta":
                answered_by = {k: event.usage[k] for k in ("provider", "model", "kind", "reason") if k in event.usage}
                yield _sse("meta", event.usage)
            elif event.kind == "text":
                delta = clean_model_text(event.text)
                if delta:
                    reply_parts.append(delta)
                    flush()
                    yield _sse("token", {"delta": delta})

        flush(force=True)
        yield _sse("done", {"conversationId": conversation_id, **answered_by})

    except ProviderError as e:
        # The message is written to be shown to the user (no keys, URLs or traces).
        print(f"[stream_response] provider error: {e.code}")
        flush(force=True)
        yield _sse("error", {"code": e.code, "message": e.user_message})
    except Exception as e:  # noqa: BLE001
        # Server-side only, and never the exception text (SDK errors can echo key fragments).
        print(f"[stream_response error] {type(e).__name__}")
        flush(force=True)
        yield _sse("error", {"code": "provider_error", "message": "Rinti is temporarily unavailable. Please try again."})
    finally:
        # Also covers the client closing the stream (GeneratorExit) when this runs.
        flush(force=True)
