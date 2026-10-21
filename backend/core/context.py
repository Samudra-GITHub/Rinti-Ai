"""Context-window budgeting.

A model has a fixed context window (prompt + reply). Sending a long history to
a small local model either overflows it (Ollama silently truncates from the
start, which can cut the system prompt) or wastes time on prompt processing.
`fit_messages` keeps the system prompt and the newest turns that fit, and
drops the oldest turns first.

Token counts are estimated from characters because the providers use
different tokenizers; the estimate is deliberately a little pessimistic.
"""

from __future__ import annotations

import math
from typing import List, Tuple

from providers.base import Message

_CHARS_PER_TOKEN = 3.3
_PER_MESSAGE_OVERHEAD = 6  # role markers and separators


def estimate_tokens(text: str) -> int:
    return math.ceil(len(text) / _CHARS_PER_TOKEN) + _PER_MESSAGE_OVERHEAD


def _truncate_middle(text: str, max_tokens: int) -> str:
    """Keeps the start and end of an over-long message (the instruction is often at the end)."""
    max_chars = max(int(max_tokens * _CHARS_PER_TOKEN) - 20, 200)
    if len(text) <= max_chars:
        return text
    head = max_chars // 2
    tail = max_chars - head
    return f"{text[:head]}\n[…]\n{text[-tail:]}"


def fit_messages(messages: List[Message], context_tokens: int, reserve_tokens: int) -> Tuple[List[Message], int]:
    """Returns (messages that fit, number of older turns dropped).

    `context_tokens` is the model's window; `reserve_tokens` is held back for
    the reply. The system message (if first) is always kept.
    """
    system = [m for m in messages[:1] if m["role"] == "system"]
    turns = messages[len(system):]

    budget = max(context_tokens - reserve_tokens - sum(estimate_tokens(m["content"]) for m in system), 256)

    kept: List[Message] = []
    used = 0
    for index in range(len(turns) - 1, -1, -1):
        message = turns[index]
        cost = estimate_tokens(message["content"])
        if not kept and cost > budget:
            # Even the newest message alone is too big: shorten it rather than fail.
            message = {**message, "content": _truncate_middle(message["content"], budget)}
            cost = estimate_tokens(message["content"])
        if used + cost > budget:
            break
        kept.append(message)
        used += cost

    kept.reverse()
    # A reply must follow a user turn; never start the window on a dangling assistant message.
    while len(kept) > 1 and kept[0]["role"] == "assistant":
        kept.pop(0)
    dropped = len(turns) - len(kept)
    return system + kept, dropped
