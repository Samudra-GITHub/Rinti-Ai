"""Tests for provider routing, fallback policy, context budgeting and the admin gate.

They use fake providers, so they need neither Ollama nor any API key. The most
important guarantee covered here: in strict local-only mode no request ever
reaches a cloud provider, whatever fails.
"""

import asyncio
import os
import sys


import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import inference, routing  # noqa: E402
from core.context import estimate_tokens, fit_messages  # noqa: E402
from core.routing import InferenceConfig, classify_task, plan_route  # noqa: E402
from providers import registry  # noqa: E402
from providers.base import (  # noqa: E402
    GenParams,
    LLMProvider,
    ModelInfo,
    ModelUnavailable,
    PolicyViolation,
    ProviderError,
    ProviderHealth,
    ProviderUnavailable,
    StreamEvent,
)


class FakeProvider(LLMProvider):
    def __init__(self, name, kind, models=(), configured=True, script=None):
        self.name = name
        self.label = name
        self.kind = kind
        self._models = list(models)
        self._configured = configured
        self.script = script or ["hello", " world"]  # items: str (text) or Exception
        self.calls = 0
        self.default_model = models[0] if models else "cloud-model"

    def is_configured(self):
        return self._configured

    def context_limit(self, model):
        return 4096

    async def stream(self, messages, model, params: GenParams):
        self.calls += 1
        for item in self.script:
            if isinstance(item, Exception):
                raise item
            yield StreamEvent("text", text=item)

    def complete(self, messages, model, params):
        self.calls += 1
        for item in self.script:
            if isinstance(item, Exception):
                raise item
        return "".join(i for i in self.script if isinstance(i, str))

    def health(self):
        return ProviderHealth(True, "ok", [ModelInfo(m, self.name) for m in self._models])

    def installed_model_ids(self):
        return list(self._models)


def make_config(mode="local", escalation=False):
    return InferenceConfig(
        mode=mode,
        local_model="local-general",
        coding_model="local-coder",
        fast_model="local-general",
        cloud_provider="groq",
        cloud_model="cloud-model",
        escalation=escalation,
    )


@pytest.fixture
def world(monkeypatch):
    """Fake local + cloud providers wired into the registry and routing config."""
    local = FakeProvider("ollama", "local", models=["local-general", "local-coder"])
    cloud = FakeProvider("groq", "cloud", models=["cloud-model"])
    monkeypatch.setattr(registry, "_registry", {"ollama": local, "groq": cloud})
    state = {"cfg": make_config()}
    monkeypatch.setattr(routing, "load_config", lambda force=False: state["cfg"])

    class World:
        pass

    w = World()
    w.local, w.cloud, w.state = local, cloud, state
    w.set_mode = lambda mode, escalation=False: state.update(cfg=make_config(mode, escalation))
    return w


def collect(route, messages=None):
    async def run():
        events = []
        async for event in inference.stream_chat(route, messages or [{"role": "user", "content": "hi"}]):
            events.append(event)
        return events

    return asyncio.run(run())


# --- context budgeting ---------------------------------------------------------

def test_fit_messages_keeps_system_and_newest_and_drops_oldest():
    system = {"role": "system", "content": "s" * 300}
    turns = []
    for i in range(50):
        turns.append({"role": "user", "content": f"q{i} " + "x" * 300})
        turns.append({"role": "assistant", "content": f"a{i} " + "y" * 300})
    turns.append({"role": "user", "content": "latest"})
    fitted, dropped = fit_messages([system] + turns, 2048, 512)
    assert fitted[0] == system
    assert fitted[-1]["content"] == "latest"
    assert dropped > 0
    assert sum(estimate_tokens(m["content"]) for m in fitted) <= 2048 - 512
    assert fitted[1]["role"] == "user"  # never starts on a dangling assistant reply


def test_fit_messages_truncates_a_single_oversized_message():
    fitted, _ = fit_messages(
        [{"role": "system", "content": "s"}, {"role": "user", "content": "z" * 100_000}], 2048, 512
    )
    assert estimate_tokens(fitted[-1]["content"]) <= 2048


# --- task classification --------------------------------------------------------

@pytest.mark.parametrize(
    "text,expected",
    [
        ("What is the Mahabharata?", "general"),
        ("What's 17 multiplied by 24?", "general"),
        ("Help me write an email to my manager", "general"),
        ("Explain the code of Hammurabi", "general"),
        ("Why does my Python loop skip items when I remove from the list?", "coding"),
        ("```js\nconst a = 1;\n```\nwhy undefined?", "coding"),
        ("Write a function in Python that removes duplicates", "coding"),
        ("Debug my SQL query that returns duplicates", "coding"),
        ("Fix this: Traceback (most recent call last):", "coding"),
    ],
)
def test_classify_task(text, expected):
    assert classify_task(text) == expected


# --- routing ----------------------------------------------------------------------

def test_local_mode_routes_locally_and_never_plans_a_cloud_fallback(world):
    route = plan_route("What is the Mahabharata?")
    assert route.primary.provider == "ollama" and route.primary.model == "local-general"
    assert route.fallback is None


def test_coding_requests_use_the_coding_model(world):
    assert plan_route("Debug my SQL query that returns duplicates").primary.model == "local-coder"


def test_auto_mode_plans_cloud_fallback(world):
    world.set_mode("auto")
    route = plan_route("What is the Mahabharata?")
    assert route.primary.provider == "ollama"
    assert route.fallback and route.fallback.provider == "groq"


def test_cloud_mode_goes_to_the_cloud(world):
    world.set_mode("cloud")
    route = plan_route("hello")
    assert route.primary.provider == "groq" and route.fallback is None


def test_escalation_only_in_auto_mode_and_only_when_enabled(world):
    demanding = "Prove that the square root of 2 is irrational."
    world.set_mode("auto", escalation=False)
    assert plan_route(demanding).primary.provider == "ollama"
    world.set_mode("auto", escalation=True)
    assert plan_route(demanding).primary.provider == "groq"
    world.set_mode("local", escalation=True)
    assert plan_route(demanding).primary.provider == "ollama"


def test_explicit_cloud_model_is_refused_in_local_only_mode(world):
    with pytest.raises(PolicyViolation):
        plan_route("hello", "cloud-model")


def test_explicit_local_model_and_unknown_model(world):
    assert plan_route("hello", "local-coder").primary.model == "local-coder"
    with pytest.raises(ModelUnavailable):
        plan_route("hello", "no-such-model")


def test_cloud_mode_without_a_key_explains_itself(world):
    world.cloud._configured = False
    world.set_mode("cloud")
    with pytest.raises(ProviderUnavailable):
        plan_route("hello")


# --- fallback policy ------------------------------------------------------------------

def test_local_only_failure_never_reaches_the_cloud(world):
    world.local.script = [ProviderUnavailable("down")]
    route = plan_route("hello")
    with pytest.raises(ProviderError):
        collect(route)
    assert world.cloud.calls == 0


def test_auto_mode_falls_back_when_local_fails_before_any_text(world):
    world.set_mode("auto")
    world.local.script = [ProviderUnavailable("down")]
    events = collect(plan_route("hello"))
    texts = "".join(e.text for e in events if e.kind == "text")
    assert texts == "hello world"
    assert world.cloud.calls == 1
    providers_used = [e.usage["provider"] for e in events if e.kind == "meta"]
    assert providers_used == ["ollama", "groq"]


def test_no_fallback_after_text_was_already_streamed(world):
    world.set_mode("auto")
    world.local.script = ["partial", ProviderUnavailable("dropped")]
    with pytest.raises(ProviderError):
        collect(plan_route("hello"))
    assert world.cloud.calls == 0


def test_complete_sync_respects_local_only(world):
    world.local.script = [ProviderUnavailable("down")]
    with pytest.raises(ProviderError):
        inference.complete_sync([{"role": "user", "content": "hi"}], user_text="hi")
    assert world.cloud.calls == 0


def test_complete_sync_falls_back_in_auto_mode(world):
    world.set_mode("auto")
    world.local.script = [ProviderUnavailable("down")]
    result = inference.complete_sync([{"role": "user", "content": "hi"}], user_text="hi")
    assert result.provider == "groq" and result.text == "hello world"


# --- admin gate -----------------------------------------------------------------------

class _Client:
    def __init__(self, host):
        self.host = host


class _Request:
    def __init__(self, host, headers=None):
        self.client = _Client(host)
        self.headers = headers or {}


def test_admin_gate(monkeypatch):
    from fastapi import HTTPException

    from api import inference as api_inference
    from config import settings

    monkeypatch.setattr(settings, "admin_token", "")
    api_inference.require_admin(_Request("127.0.0.1"), None)  # loopback is allowed
    with pytest.raises(HTTPException):
        api_inference.require_admin(_Request("203.0.113.9"), None)  # remote is refused
    with pytest.raises(HTTPException):
        api_inference.require_admin(_Request("127.0.0.1", {"x-forwarded-for": "203.0.113.9"}), None)  # proxied

    monkeypatch.setattr(settings, "admin_token", "secret-token")
    with pytest.raises(HTTPException):
        api_inference.require_admin(_Request("127.0.0.1"), None)  # token mode: loopback alone isn't enough
    with pytest.raises(HTTPException):
        api_inference.require_admin(_Request("127.0.0.1"), "wrong")
    api_inference.require_admin(_Request("203.0.113.9"), "secret-token")
