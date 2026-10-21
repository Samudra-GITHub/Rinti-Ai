"""Hardware-aware recommendations, licence classification and the guarantees
around them: unsuitable models are explained (never silently replaced by a cloud
model), Auto only uses the cloud when its fallback is enabled, and hosted
deployments say that they describe the server.

All machines here are made up; none of these tests claim a model was run on them.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core import hardware, inference, local_fit, model_catalog as catalog, routing  # noqa: E402
from core.hardware import Gpu, Hardware  # noqa: E402
from core.routing import plan_route  # noqa: E402
from providers import registry  # noqa: E402
from providers.base import ModelUnavailable  # noqa: E402

from tests.test_inference import FakeProvider, make_config  # noqa: E402


def machine(ram, vram=None, available=None, apple=False):
    gpu = None
    if vram is not None:
        gpu = Gpu("Test GPU", vram, vram, "apple-silicon" if apple else "nvidia-smi")
    return Hardware("linux", 8, ram, available if available is not None else ram * 0.6, gpu)


QWEN7 = dict(weights_gb=4.7, params_b=7.6, kv=57344)


# --- fit levels -------------------------------------------------------------------

def test_big_gpu_runs_7b_on_the_gpu():
    r = catalog.assess(machine(32, 12), kv_per_token=QWEN7["kv"], weights_gb=4.7, params_b=7.6, ctx=8192)
    assert r["level"] == "gpu" and r["fits"]


def test_six_gb_gpu_splits_the_7b_between_gpu_and_cpu():
    # Matches what was measured on a 6 GB RTX 4050 (4.1 of 5.4 GB on the GPU).
    r = catalog.assess(machine(24, 6), kv_per_token=QWEN7["kv"], weights_gb=4.7, params_b=7.6, ctx=8192)
    assert r["level"] == "partial" and r["fits"]


def test_cpu_only_machine_does_not_get_a_7b_model():
    r = catalog.assess(machine(16), kv_per_token=QWEN7["kv"], weights_gb=4.7, params_b=7.6, ctx=8192)
    assert r["level"] == "no" and "too slow" in " ".join(r["reasons"])


def test_7b_on_a_small_gpu_is_not_called_workable():
    # Only a 6 GB split was tested; on 4 GB most of the model would run on the CPU.
    r = catalog.assess(machine(16, 4), kv_per_token=QWEN7["kv"], weights_gb=4.7, params_b=7.6, ctx=8192)
    assert r["level"] == "no" and "mostly run on the CPU" in " ".join(r["reasons"])
    assert catalog.recommend(machine(16, 4), [], False)["recommended"]["model"] == "phi4-mini"


def test_apple_silicon_is_labelled_an_estimate():
    r = catalog.assess(machine(16, 10.5, apple=True), kv_per_token=QWEN7["kv"], weights_gb=4.7, params_b=7.6, ctx=8192)
    assert "hasn't been tested" in " ".join(r["reasons"])


def test_machine_without_enough_memory_is_refused_with_numbers():
    r = catalog.assess(machine(4), kv_per_token=QWEN7["kv"], weights_gb=4.7, params_b=7.6, ctx=8192)
    assert r["level"] == "no" and "4" in r["reasons"][0] and not r["fits"]


def test_low_free_memory_is_called_out():
    r = catalog.assess(machine(16, 6, available=3), kv_per_token=QWEN7["kv"], weights_gb=4.7, params_b=7.6, ctx=4096)
    assert any("free right now" in x for x in r["reasons"])


def test_context_shrinks_before_the_model_gets_worse():
    # 5 GB card: a 2.5 GB model with a heavy cache stays fully on the GPU at 4096
    # tokens but would spill to the CPU at 8192, so the window is lowered.
    hw = machine(16, 5)
    assert catalog.assess(hw, 2.5, 3.8, 131072, 8192)["level"] == "partial"
    chosen = catalog.best_context(hw, 2.5, 3.8, 131072, 8192)
    assert chosen == 4096
    assert catalog.assess(hw, 2.5, 3.8, 131072, chosen)["level"] == "gpu"


# --- recommendations --------------------------------------------------------------

@pytest.mark.parametrize(
    "hw,expected",
    [
        (machine(32, 12), "qwen2.5:7b"),
        (machine(24, 6), "qwen2.5:7b"),
        (machine(16), "phi4-mini"),  # CPU only: smaller model
        (machine(8), "phi4-mini"),
        (machine(4), "qwen2.5:1.5b"),
    ],
)
def test_recommendation_follows_the_hardware(hw, expected):
    assert catalog.recommend(hw, [], commercial_only=False)["recommended"]["model"] == expected


def test_nothing_suitable_says_so_and_points_to_the_cloud():
    rec = catalog.recommend(machine(2), [], commercial_only=False)
    assert rec["recommended"] is None
    assert "cloud" in rec["summary"].lower()


def test_installed_flag_changes_the_install_hint():
    rec = catalog.recommend(machine(24, 6), ["qwen2.5:7b"], False)
    assert rec["recommended"]["installed"] and "ollama pull" not in rec["summary"]
    rec = catalog.recommend(machine(24, 6), [], False)
    assert "`ollama pull qwen2.5:7b`." in rec["summary"]


def test_commercial_deployments_never_get_a_restricted_model(monkeypatch):
    restricted = catalog.CatalogModel(
        "big-restricted", "Big", 7.0, 4.0, 50000, "custom", "Custom", "", "no", "none", "x"
    )
    monkeypatch.setattr(catalog, "VERIFIED_MODELS", [restricted] + catalog.VERIFIED_MODELS)
    assert catalog.recommend(machine(32, 12), [], False)["recommended"]["model"] == "big-restricted"
    assert catalog.recommend(machine(32, 12), [], True)["recommended"]["model"] == "qwen2.5:7b"


def test_every_recommendable_model_has_a_checked_permissive_licence():
    for model in catalog.VERIFIED_MODELS:
        assert model.commercial == "yes" and model.license_id in ("apache-2.0", "mit")
        assert model.license_url.startswith("https://")


# --- licences ---------------------------------------------------------------------

@pytest.mark.parametrize(
    "text,lic,commercial",
    [
        ("Apache License\nVersion 2.0, January 2004", "apache-2.0", "yes"),
        ("MIT License\n\nPermission is hereby granted, free of charge, to any person", "mit", "yes"),
        ("Qwen RESEARCH LICENSE AGREEMENT Release Date", "qwen-research", "no"),
        ("Gemma Terms of Use Last modified", "gemma", "review"),
        ("LLAMA 3.2 COMMUNITY LICENSE AGREEMENT", "llama-community", "review"),
        ("Some bespoke terms", "custom", "review"),
        ("", "unknown", "review"),
        (None, "unknown", "review"),
    ],
)
def test_license_classification_is_conservative(text, lic, commercial):
    result = catalog.classify_license(text)
    assert result["id"] == lic and result["commercial"] == commercial


def test_kv_cache_size_is_computed_from_model_info():
    info = {
        "qwen2.block_count": 28,
        "qwen2.attention.head_count": 28,
        "qwen2.attention.head_count_kv": 4,
        "qwen2.embedding_length": 3584,
    }
    assert catalog.kv_bytes_per_token(info) == 57344
    assert catalog.kv_bytes_per_token({}, fallback=1) == 1


# --- deployment -------------------------------------------------------------------

def test_hosted_deployment_says_it_describes_the_server(monkeypatch):
    for name in ("VERCEL", "AWS_LAMBDA_FUNCTION_NAME", "K_SERVICE", "RENDER", "FLY_APP_NAME", "RAILWAY_ENVIRONMENT"):
        monkeypatch.delenv(name, raising=False)
    assert hardware.deployment()["hosted"] is False
    monkeypatch.setenv("VERCEL", "1")
    d = hardware.deployment()
    assert d["hosted"] and d["serverless"] and "not your computer" in d["note"]


def test_detection_works_on_this_machine_and_leaks_no_identity():
    hw = hardware.detect(force=True)
    assert hw.ram_total_gb > 0 and hw.cpu_threads >= 1
    assert set(hw.to_dict()) == {"os", "cpu_threads", "ram_total_gb", "ram_available_gb", "gpu", "notes"}


# --- routing guarantees -----------------------------------------------------------

@pytest.fixture
def world(monkeypatch):
    local = FakeProvider("ollama", "local", models=["local-general", "local-coder", "small-ok"])
    cloud = FakeProvider("groq", "cloud", models=["cloud-model"])
    monkeypatch.setattr(registry, "_registry", {"ollama": local, "groq": cloud})
    state = {"cfg": make_config()}
    monkeypatch.setattr(routing, "load_config", lambda force=False: state["cfg"])

    verdicts = {"local-general": {"fits": False, "level": "no", "reasons": ["It needs about 9.0 GB."], "context": 8192}}
    monkeypatch.setattr(
        local_fit, "assess_model", lambda model_id: verdicts.get(model_id, {"fits": True, "level": "gpu", "reasons": []})
    )

    class W:
        pass

    w = W()
    w.local, w.cloud, w.state = local, cloud, state
    return w


def test_local_mode_explains_an_unsuitable_model_and_never_uses_the_cloud(world):
    with pytest.raises(ModelUnavailable) as err:
        plan_route("What is the Mahabharata?")
    message = str(err.value)
    assert "too large" in message and "Nothing was sent to the cloud" in message
    assert "Cloud mode" in message  # an explicit alternative the user can choose
    assert world.cloud.calls == 0


def test_auto_without_cloud_fallback_has_no_cloud_route_and_explains(world):
    cfg = make_config("auto")
    world.state["cfg"] = type(cfg)(**{**cfg.__dict__, "cloud_fallback": False})
    # local-general doesn't fit and no catalogue model is installed to swap in
    with pytest.raises(ModelUnavailable):
        plan_route("hello")
    assert world.cloud.calls == 0


def test_auto_with_fallback_disabled_never_plans_a_cloud_fallback(world):
    cfg = make_config("auto")
    world.state["cfg"] = type(cfg)(**{**cfg.__dict__, "local_model": "small-ok", "coding_model": "small-ok", "cloud_fallback": False})
    route = plan_route("hello")
    assert route.primary.provider == "ollama" and route.fallback is None


def test_auto_with_fallback_enabled_keeps_cloud_as_fallback_only(world):
    cfg = make_config("auto")
    world.state["cfg"] = type(cfg)(**{**cfg.__dict__, "local_model": "small-ok", "coding_model": "small-ok", "cloud_fallback": True})
    route = plan_route("hello")
    assert route.primary.provider == "ollama" and route.fallback and route.fallback.provider == "groq"


def test_escalation_needs_the_fallback_to_be_enabled(world):
    cfg = make_config("auto", escalation=True)
    base = {**cfg.__dict__, "local_model": "small-ok", "coding_model": "small-ok"}
    world.state["cfg"] = type(cfg)(**{**base, "cloud_fallback": False})
    assert plan_route("Prove that the square root of 2 is irrational.").primary.provider == "ollama"
    world.state["cfg"] = type(cfg)(**{**base, "cloud_fallback": True})
    assert plan_route("Prove that the square root of 2 is irrational.").primary.provider == "groq"


def test_hardware_check_can_be_turned_off(world, monkeypatch):
    from config import settings

    monkeypatch.setattr(settings, "hardware_check", False)
    assert plan_route("hello").primary.model == "local-general"


# --- API: who sees the hardware ----------------------------------------------------

def _client(monkeypatch, hosted, admin_token=""):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api import inference as api_inference
    from auth.dependencies import get_current_user
    from config import settings

    monkeypatch.setattr(settings, "admin_token", admin_token)
    hw = machine(24, 6).to_dict()
    overview = {
        "hardware": hw,
        "deployment": {"hosted": hosted, "serverless": hosted, "note": "n"},
        "models": [],
        "recommendation": {"recommended": None, "candidates": [], "summary": "s", "commercial_only": False},
        "commercial_only": False,
    }
    monkeypatch.setattr(api_inference.local_fit, "overview", lambda: overview)
    monkeypatch.setattr(api_inference.routing, "status_snapshot", lambda: {"local_model": "m", "coding_model": "m", "mode": "local", "cloud_fallback": False})
    monkeypatch.setattr(api_inference, "cloud_providers", lambda: {})
    monkeypatch.setattr(api_inference, "providers", lambda: {"ollama": FakeProvider("ollama", "local", models=["m"])})
    app = FastAPI()
    app.include_router(api_inference.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "u"}
    return TestClient(app)


def test_hosted_backend_hides_its_hardware_from_visitors(monkeypatch):
    body = _client(monkeypatch, hosted=True).get("/api/inference/status").json()
    assert body["can_configure"] is False and body["hardware"] is None
    assert body["deployment"]["hosted"] is True


def test_hosted_backend_shows_hardware_to_an_admin(monkeypatch):
    client = _client(monkeypatch, hosted=True, admin_token="s3cret-token")
    body = client.get("/api/inference/status", headers={"X-Rinti-Admin": "s3cret-token"}).json()
    assert body["can_configure"] is True and body["hardware"]["ram_total_gb"] == 24


def test_self_hosted_backend_shows_hardware(monkeypatch):
    body = _client(monkeypatch, hosted=False).get("/api/inference/status").json()
    assert body["hardware"]["gpu"]["vram_total_gb"] == 6


def test_settings_changes_still_refused_for_remote_clients(monkeypatch):
    client = _client(monkeypatch, hosted=True)
    r = client.patch("/api/inference/config", json={"mode": "local"}, headers={"X-Rinti-Client": "1"})
    assert r.status_code == 403


# --- review fixes -----------------------------------------------------------------

class Recording(FakeProvider):
    """Remembers which model and JSON mode each blocking call used."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.seen = []

    def complete(self, messages, model, params):
        self.seen.append((model, params.json_mode))
        return "{}"


def _recording_world(monkeypatch, cfg_changes=None, mode="local"):
    local = Recording("ollama", "local", models=["local-general", "phi4-mini"])
    cloud = Recording("groq", "cloud", models=["cloud-model"])
    monkeypatch.setattr(registry, "_registry", {"ollama": local, "groq": cloud})
    cfg = make_config(mode)
    cfg = type(cfg)(**{**cfg.__dict__, **(cfg_changes or {})})
    monkeypatch.setattr(routing, "load_config", lambda force=False: cfg)
    return local, cloud


def test_classification_keeps_the_model_chosen_for_this_hardware(monkeypatch):
    from config import settings

    local, _ = _recording_world(monkeypatch, {"cloud_fallback": False}, mode="auto")
    monkeypatch.setattr(settings, "fast_model", "")
    monkeypatch.setattr(hardware, "detect", lambda force=False: machine(8))
    # local-general doesn't fit an 8 GB CPU-only machine; phi4-mini does and is installed
    monkeypatch.setattr(
        local_fit,
        "assess_model",
        lambda m: {"fits": m != "local-general", "level": "cpu", "reasons": [], "context": 4096},
    )
    inference.complete_sync([{"role": "user", "content": "hi"}], purpose="classify", json_mode=True)
    assert [m for m, _ in local.seen] == ["phi4-mini"]


def test_an_explicit_fast_model_is_used_for_classification(monkeypatch):
    from config import settings

    local, _ = _recording_world(monkeypatch, {"local_model": "phi4-mini", "coding_model": "phi4-mini"})
    monkeypatch.setattr(settings, "fast_model", "local-general")
    monkeypatch.setattr(local_fit, "assess_model", lambda m: None)
    inference.complete_sync([{"role": "user", "content": "hi"}], purpose="classify")
    assert [m for m, _ in local.seen] == ["local-general"]


def test_synthesis_json_mode_reaches_local_models_but_not_the_cloud(monkeypatch):
    local, cloud = _recording_world(monkeypatch, {"local_model": "phi4-mini", "coding_model": "phi4-mini"})
    monkeypatch.setattr(local_fit, "assess_model", lambda m: None)
    inference.complete_sync([{"role": "user", "content": "q"}], json_mode=True, json_mode_cloud=False)
    assert local.seen == [("phi4-mini", True)]

    local.seen.clear()
    monkeypatch.setattr(routing, "load_config", lambda force=False: type(make_config())(**{**make_config("cloud").__dict__}))
    inference.complete_sync([{"role": "user", "content": "q"}], json_mode=True, json_mode_cloud=False)
    assert cloud.seen == [("cloud-model", False)]  # the original Groq request: no response_format


def test_legacy_model_name_still_selects_the_cloud_model():
    """Run in a fresh interpreter so reloading settings can't leak into other tests."""
    import subprocess

    code = "from config import settings; print(settings.cloud_model)"
    base = {k: v for k, v in os.environ.items() if k not in ("MODEL_NAME", "RINTI_CLOUD_MODEL")}
    cwd = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    def run(extra):
        return subprocess.run(
            [sys.executable, "-c", code], capture_output=True, text=True, cwd=cwd, env={**base, **extra}, timeout=60
        ).stdout.strip()

    assert run({"MODEL_NAME": "legacy/model-x"}) == "legacy/model-x"
    assert run({"MODEL_NAME": "legacy/model-x", "RINTI_CLOUD_MODEL": "new/model-y"}) == "new/model-y"


def _chat_client(monkeypatch, route):
    from fastapi import FastAPI
    from fastapi.testclient import TestClient

    from api import chat as api_chat
    from auth.dependencies import get_current_user

    calls = []
    monkeypatch.setattr(api_chat, "plan_route", lambda text, model=None: route)
    monkeypatch.setattr(
        api_chat.db, "check_and_increment_usage", lambda *a, **k: calls.append(a) or {"allowed": False, "limit": 1}
    )

    async def fake_stream(*args, **kwargs):
        yield "event: done\ndata: {}\n\n"

    monkeypatch.setattr(api_chat, "stream_response", fake_stream)
    monkeypatch.setattr(api_chat, "_owned_conversation_id", lambda requested, user: "c1")
    app = FastAPI()
    app.include_router(api_chat.router, prefix="/api")
    app.dependency_overrides[get_current_user] = lambda: {"id": "u"}
    return TestClient(app), calls


def test_a_planned_cloud_fallback_counts_against_the_daily_cap(monkeypatch):
    local_route = routing.Route(routing.Target("ollama", "m"), routing.Target("groq", "g"), "r", "general", "auto")
    client, calls = _chat_client(monkeypatch, local_route)
    monkeypatch.setattr(registry, "_registry", {"ollama": FakeProvider("ollama", "local"), "groq": FakeProvider("groq", "cloud")})
    client.post("/api/chat/stream", json={"message": "hi"}, headers={"X-Rinti-Client": "1"})
    assert len(calls) == 1


def test_purely_local_replies_do_not_use_the_cloud_cap(monkeypatch):
    local_route = routing.Route(routing.Target("ollama", "m"), None, "r", "general", "local")
    client, calls = _chat_client(monkeypatch, local_route)
    monkeypatch.setattr(registry, "_registry", {"ollama": FakeProvider("ollama", "local"), "groq": FakeProvider("groq", "cloud")})
    client.post("/api/chat/stream", json={"message": "hi"}, headers={"X-Rinti-Client": "1"})
    assert calls == []


# --- admin gate on a hosted backend ------------------------------------------------

class _Req:
    def __init__(self, host, headers=None):
        from types import SimpleNamespace

        self.client = SimpleNamespace(host=host)
        self.headers = headers or {}


def test_hosted_backend_ignores_loopback_and_needs_the_token(monkeypatch):
    from fastapi import HTTPException

    from api import inference as api_inference
    from config import settings

    monkeypatch.setattr(settings, "admin_token", "")
    monkeypatch.setenv("VERCEL", "1")
    with pytest.raises(HTTPException):
        api_inference.require_admin(_Req("127.0.0.1"), None)  # looks local, but the proxy can't be trusted

    monkeypatch.setattr(settings, "admin_token", "tok-123")
    api_inference.require_admin(_Req("203.0.113.9"), "tok-123")  # the token is what authorises
    with pytest.raises(HTTPException):
        api_inference.require_admin(_Req("127.0.0.1"), "wrong")


def test_cloud_mode_does_not_probe_ollama(monkeypatch):
    from api import health as api_health

    cloud = Recording("groq", "cloud", models=["cloud-model"])

    class Boom(FakeProvider):
        def health(self):
            raise AssertionError("Ollama must not be contacted in cloud mode")

    monkeypatch.setattr(registry, "_registry", {"ollama": Boom("ollama", "local"), "groq": cloud})
    cfg = make_config("cloud")
    monkeypatch.setattr(routing, "load_config", lambda force=False: cfg)
    result = api_health._check_inference()
    assert result["mode"] == "cloud" and result["local"] == {"checked": False}


def test_auto_without_fallback_refuses_an_explicitly_chosen_cloud_model(world):
    from providers.base import PolicyViolation

    cfg = make_config("auto")
    world.state["cfg"] = type(cfg)(**{**cfg.__dict__, "local_model": "small-ok", "coding_model": "small-ok", "cloud_fallback": False})
    with pytest.raises(PolicyViolation):
        plan_route("hello", "cloud-model")
    world.state["cfg"] = type(cfg)(**{**cfg.__dict__, "local_model": "small-ok", "coding_model": "small-ok", "cloud_fallback": True})
    assert plan_route("hello", "cloud-model").primary.provider == "groq"
