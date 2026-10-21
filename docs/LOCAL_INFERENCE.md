# Local-first inference for Rinti-AI

Rinti-AI can answer from a model running on your own computer (through
[Ollama](https://ollama.com)) instead of a paid or rate-limited cloud API. The
cloud (Groq by default) remains available as an option. This page covers what
was built, which model was chosen and why, how to run it, and what it costs.

## Quick start (Windows)

```powershell
# 1. Ollama must be running and have the model (done once)
ollama serve                    # skip if the Ollama app is already running
ollama pull qwen2.5:7b

# 2. Backend (from the backend folder)
.venv\Scripts\activate
uvicorn main:app --port 8000

# 3. Frontend (from the frontend folder)
npm run dev                     # http://localhost:3000
```

`backend/.env` (see `backend/.env.example` for everything):

```ini
RINTI_DEFAULT_PROVIDER=ollama     # groq (cloud, the original) | ollama (local)
RINTI_CLOUD_FALLBACK=false        # Auto mode: may the cloud answer if local fails?
RINTI_COMMERCIAL_USE=false        # true = only suggest permissively licensed models
RINTI_OLLAMA_BASE_URL=http://127.0.0.1:11434
RINTI_DEFAULT_MODEL=qwen2.5:7b
RINTI_LOCAL_NUM_CTX=8192
OPENAI_API_KEY=                   # optional now; only needed for cloud use
```

To go back to Groq at any time: set `RINTI_DEFAULT_PROVIDER=groq` (or choose
**Cloud** under Settings > Where Rinti runs) and keep `OPENAI_API_KEY` set. The
default when the variable is absent is `groq`, so the hosted deployment behaves
exactly as before until it is configured otherwise.

## Architecture

```
frontend (Next.js)  ->  /api/chat/stream  ->  api/chat.py
                                                 |  plan_route()      core/routing.py
                                                 v
                                       core/brain.py  (prompt, memory, history, saving)
                                                 |  stream_chat()     core/inference.py
                                                 v                    (context budget, limits, fallback)
                                      providers/  (LLMProvider interface)
                                       |- ollama.py         native /api/chat, local
                                       |- openai_compat.py  Groq or any OpenAI-compatible API
                                       '- registry.py       built from settings
```

- **`providers/`**: one interface (`stream`, `complete`, `health`,
  `context_limit`) and stable, user-safe error types (unavailable, model
  missing, rate limited, auth, timeout, busy, policy). Business logic never
  imports a vendor SDK. Extra OpenAI-compatible providers can be declared with
  `RINTI_EXTRA_PROVIDERS` (keys are read from environment variables named in
  that JSON, never stored in it).
- **`core/routing.py`**: transparent, rule-based routing with a human-readable
  reason on every decision. No classifier model.
- **`core/context.py`**: keeps the system prompt and the newest turns that fit
  the model's window; drops the oldest first; shortens a single oversized
  message instead of failing.
- **`core/hardware.py`, `core/model_catalog.py`, `core/local_fit.py`**: what the
  backend's computer can run, the verified model list with licences, and the
  glue that applies both to the models Ollama has installed (see "Hardware-aware
  setup" below).
- **`core/inference.py`**: the single entry point. Applies the context budget,
  concurrency limits and timeouts, streams, and falls back only when policy
  allows and only before any text was produced. It never logs message content.
- Research (intent, planning, synthesis) goes through the same facade, so
  strict local-only mode covers it too. Web search itself still uses Tavily.
- The personality and response policy (`core/personality.py`) is unchanged in
  structure and shared by every provider.

### Modes

| Mode | Behaviour |
| --- | --- |
| `local` | Use the configured local model, only if it suits this computer. Everything stays on the computer hosting Rinti. If the model is missing, Ollama is down or the model is too large, the user gets an explanation and a list of options. **Nothing is ever sent to a cloud provider.** Explicitly requesting a cloud model is refused (HTTP 403). |
| `auto` | Pick the best local setup for this computer: the configured model if it fits, otherwise the best installed model from the verified list that does. The cloud is used **only if "Allow cloud fallback" is on** (`RINTI_CLOUD_FALLBACK`, changeable in Settings), and then only when the local model fails before producing text. With the fallback off, Auto never leaves the machine. |
| `cloud` | The original behaviour: Groq only. |

Nothing switches mode on its own. A weak machine produces an explanation and
buttons the user presses; it never turns a Local request into a cloud request.

Routing rules in local/auto: programming requests use the coding model
(`RINTI_CODING_MODEL`, defaulting to the everyday model); everything else uses
`RINTI_DEFAULT_MODEL`; a model picked in the model menu always wins (subject to
the mode). Each reply reports which provider and model produced it; the chat
shows it under the message ("on this device - qwen2.5:7b").

### Security and privacy

- API keys never reach the browser; `/api/models` and `/api/inference/status`
  expose only model names and health.
- Inference settings can be changed only from the machine running Rinti
  (loopback, and not through a proxy) or with `RINTI_ADMIN_TOKEN` in an
  `X-Rinti-Admin` header. On a hosted deployment (Vercel and similar, or
  `ENVIRONMENT=production`) loopback is never trusted, because every request
  arrives through the platform's proxy: without the token nobody can change
  settings, and a hosted backend hides its server hardware from everyone else.
- The cloud is only reachable when the mode allows it: in Cloud mode, or in Auto
  with the fallback enabled. In Local mode, or Auto with the fallback off,
  explicitly choosing a cloud model is refused (HTTP 403) and the model menu
  doesn't offer one.
- Cloud replies and any planned cloud fallback count against the per-user daily
  message cap, so a failing local model can't be used to bypass it.
- There is deliberately **no** endpoint to download, delete or run models.
  Install models on the host with the Ollama CLI.
- Local concurrency is capped (`RINTI_LOCAL_MAX_CONCURRENCY`, default 1);
  requests queue up to `RINTI_QUEUE_TIMEOUT` seconds, then get a "busy"
  message. Total request time is capped by `RINTI_REQUEST_TIMEOUT`.
- Secrets stay in `backend/.env` (ignored by Git). `backend/.env.example` is the
  committed template.

## Hardware-aware setup

Not every computer can run every model, so Rinti inspects the machine and says
what suits it.

**What is detected** (`core/hardware.py`, standard library plus `nvidia-smi`):
total and free memory, CPU thread count, and an NVIDIA GPU with its video memory
if the driver is present. Apple Silicon is reported as unified memory. AMD and
Intel graphics are **not** detected (the machine is then treated as CPU-only).
No hostname, user name or serial number is collected.

**Whose hardware.** Detection runs in the backend process, so it describes the
computer that runs the backend and the Ollama it talks to. It never describes a
browser visitor's laptop, and the browser never talks to Ollama (it only calls
`/api/*`). On a hosted backend (Vercel and similar, detected from their
environment variables) the settings page says so, hides the server's hardware
from anyone who can't configure it, and the default stays cloud, because a
hosted backend cannot reach a model on someone's laptop.

**How a model is judged** (`core/model_catalog.py`). Memory needed = file size +
KV cache for the context window (read from the model file) + 0.35 GB overhead.

| Result | Meaning |
| --- | --- |
| `gpu` | Fits in 75% of video memory: fast |
| `partial` | Too big for the GPU, fits RAM: split between GPU and CPU, moderate speed (what a 6 GB card does with the 7B) |
| `cpu` | No usable GPU, models up to 4B parameters only: slow |
| `no` | Larger than memory allows, or a 7B model on a CPU: refused with an explanation |

The context window is the configured value (`RINTI_LOCAL_NUM_CTX`, default 8192)
lowered, if needed, so the model doesn't spill from GPU to CPU. It is never raised.

**Calibration.** The 75% video-memory share and the 0.35 GB overhead come from
real loads at an 8192-token window on the RTX 4050 6 GB machine (the only GPU
tested):

| Model | File | Estimate | Measured total | On the GPU |
| --- | --- | --- | --- | --- |
| `qwen2.5:7b` | 4.68 GB | 5.47 GB | 5.41 GB | 4.10 GB (76%) |
| `qwen2.5-coder:7b` | 4.68 GB | 5.47 GB | 5.41 GB | 4.10 GB (76%) |
| `phi4-mini` | 2.49 GB | 3.84 GB | 3.64 GB | 3.64 GB (100%) |
| `qwen2.5-coder:3b` (removed) | 1.93 GB | 2.56 GB | 2.41 GB | 2.41 GB (100%) |
| `qwen2.5:1.5b` | 0.99 GB | 1.55 GB | 1.37 GB | 1.37 GB (100%) |
| `qwen3:4b` (removed) | 2.50 GB | 3.97 GB | 3.88 GB | 3.88 GB (100%) |
| `gemma3:4b` (removed) | 3.35 GB | 4.76 GB | 2.89 GB | 2.89 GB (100%) |

The estimate errs high for these models (Gemma is over-estimated because of its
sliding-window attention). It says "should fit", not "was tested on your machine".

**When it doesn't suit.** In Local mode a model that can't fit is refused with
the numbers, "Nothing was sent to the cloud", and options (use an installed
model that fits, or `ollama pull` a suggested one, or switch to Cloud yourself).
`RINTI_HARDWARE_CHECK=false` turns the refusal off. In Settings the same
explanation appears as a banner with explicit buttons.

## Model catalogue and licences

Only the models below are ever **suggested**. Any other installed model is
listed with the licence text read from its own file and is never suggested
automatically. Licences were checked on 2026-10-21 against the publisher's
Hugging Face page (`license` field) and the licence text shipped in the model
file Ollama downloaded. This is not legal advice; read the licence before a
commercial launch.

| Model | Download | Licence | Commercial use | Evidence checked |
| --- | --- | --- | --- | --- |
| `qwen2.5:7b` | 4.7 GB | Apache-2.0 | Yes | HF page + model file |
| `phi4-mini` (3.8B) | 2.5 GB | MIT | Yes | HF page + model file |
| `qwen2.5:1.5b` | 0.99 GB | Apache-2.0 | Yes | HF page + model file |
| `qwen2.5-coder:7b` (comparison) | 4.7 GB | Apache-2.0 | Yes | model file |
| `qwen2.5-coder:3b` (removed) | 1.9 GB | Qwen Research License | **No**: non-commercial; commercial use needs a separate licence (clauses read in the Qwen2.5-3B licence, which has the same agreement title) | model file + HF licence text |
| `qwen2.5:3b` (not used) | 1.9 GB | Qwen Research License | **No** | HF page + licence text |
| `gemma3:4b` (removed) | 3.4 GB | Gemma Terms of Use | Review: custom terms and use policy, not assessed | model file |
| `qwen3:4b` (removed) | 2.5 GB | Apache-2.0 | Yes (but unusable here, see the benchmarks) | model file |

With `RINTI_COMMERCIAL_USE=true` only models classified Apache-2.0 or MIT are
suggested, and the settings page warns about an installed model with any other
licence. A model with an unrecognised licence is always classed "review".

### Which model for which computer

| Computer | Suggested | Evidence |
| --- | --- | --- |
| NVIDIA GPU with 5.5 GB or more of video memory (and about 8 GB+ RAM) | `qwen2.5:7b` | Tested on one RTX 4050 6 GB. Below 5.5 GB the 7B is not offered, because most of it would run on the CPU |
| CPU only, or a smaller GPU | `phi4-mini` | CPU-only tested on one laptop CPU; smaller GPUs not tested |
| Very little memory (about 4 GB) | `qwen2.5:1.5b`, basic chat only | Quality measured; low-memory machine not tested |
| Less than that | Cloud | Nothing in the verified list fits |

Benchmark results on this machine (14 cases x 2 runs, same prompt, GPU):

| Model | Failed runs | Correctness | Instruction | Style | Median first token | Median full answer | Tokens/s |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen2.5:7b` | 0 / 28 | 37/38 | 22/22 | 40/40 | 0.3 s | 6.8 s | 12 to 25 |
| `phi4-mini` | 0 / 28 | 35/38 | 22/22 | 38/40 | 0.1 s | 1.2 s | 59 |
| `qwen2.5:1.5b` | 0 / 28 | 31/38 | 21/22 | 39/40 | 0.1 s | 0.6 s | 120 |

`phi4-mini` omitted `[n]` citations in research synthesis and missed two
phrasing checks. `qwen2.5:1.5b` got a change calculation wrong, wrote incorrect
code in 1 of 2 runs and missed the debugging answer in both. Treat it as basic
chat only. Raw responses: `docs/benchmarks/benchmark-20261021-195809-small-models.*`.

**CPU-only measurements** (13th-gen Core i5-13450HX, 10 cores / 16 threads,
GPU disabled with `num_gpu=0`, 8192 window, Rinti's roughly 1,650-token system
prompt):

| Model | Generation | First token, fresh conversation | Memory |
| --- | --- | --- | --- |
| `qwen2.5:1.5b` | 33.9 tokens/s | 13.8 s | 1.4 GB |
| `phi4-mini` | 13.6 tokens/s | 30.3 s | 3.7 GB |
| `qwen2.5:7b` | 7.5 tokens/s | 58.6 s | 5.5 GB |

The wait is the system prompt being processed. Repeating an identical prompt
brought the first token to 0.1 to 0.2 s, but real follow-up turns (whose memory
notes can change) were not timed on a CPU. A weaker CPU will be slower than this
one. That is why a 7B model is not offered on CPU-only machines.

`gemma3:4b`, `qwen3:4b` and `qwen2.5-coder:3b` were pulled only for the
comparison. None is referenced by any code, test, configuration, template or
saved setting, so all three were removed from this machine; their results remain
in `docs/benchmarks/` as historical records. To reproduce those runs,
`ollama pull` them again.

## The model

**Default: `qwen2.5:7b`** (Q4_K_M, Apache-2.0 license, 4.7 GB on disk).

Fits a 6 GB card: with an 8192-token window it needs 5.4 GB, of which 4.1 GB
sits on the GPU and the rest on the CPU; it generates about 14 to 25 tokens per
second on this machine (the figure varies with load) with first tokens in about
0.2 s once loaded (about 6 to 10 s to load from cold). Shrinking the window to
3072 changed speed by under 15%, so the larger window was kept.

Candidates were benchmarked on the same cases, prompt and settings (13 cases x
2 runs each; automated checks including *executing* the generated code):

| Target | Failed runs | Correctness | Instruction | Style | Median first token | Median full answer | GPU/RAM |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `qwen2.5:7b` (chosen), final prompt, 14 cases | 0 / 28 | 37/38 | 22/22 | 40/40 | 0.3 s | 6.8 s | 5.4 GB (4.1 on GPU) |
| `qwen2.5-coder:7b`, previous prompt, 13 cases | 0 / 26 | 33/36 | 22/22 | 37/38 | 0.2 s | 6.2 s | 5.4 GB (4.1 on GPU) |
| Groq `openai/gpt-oss-120b`, final prompt, 14 cases | 2 / 28 (rate limited) | 34/36 | 21/21 | 36/38 | 7.0 s* | 7.1 s* | cloud |

\* Median latency in that run was inflated by the SDK retrying rate-limited
requests; in another run the median full answer was 2.7 s. Cloud latency is
fast when the account is not being throttled and erratic when it is.

Earlier round (before the response policy was tightened with length guidance),
same method: `gemma3:4b` 35/36, 22/22, **30/38** style (answers 2 to 3x too long,
485 words to an ambiguous "Fix it."); `qwen2.5-coder:3b` 33/36, 18/22 (fast,
32 tok/s, lowest quality, and a Qwen *Research* license that forbids commercial
use); `qwen3:4b` 10 of 26 runs failed (its hidden reasoning used the whole
token budget; about 31 s to first visible token). Full tables and every raw
response are in `docs/benchmarks/`.

What this does and does not show:

- The local 7B handled every case without a failed run and followed the style
  policy, at a cost of seconds per answer instead of the cloud's sub-second to
  few-second answers. The cloud model was strong when it answered (its few
  failed checks were mostly keyword-matching quirks in the automated checks, not
  clear errors), but across the three benchmark sessions Groq rejected 11 of 80
  requests (14%) with rate limits. That bursty pattern is exactly what a local
  default avoids.
- The correctness checks are keyword-level and the suite is small. They do not
  measure depth of knowledge. A 7B model knows less and makes more factual
  mistakes than a 120B model; do not expect cloud-model intelligence.
- Weak spot found: in research synthesis the local model sometimes returns a
  well-formed answer **without `[n]` citations** (failed 1 of 2 runs in the
  final benchmark, 2 of 2 earlier). For research that must be cited, use Auto or
  Cloud mode, or accept lighter citation coverage.
- `qwen2.5-coder:7b` scored the same as the general 7B, including on the two
  coding cases, so a split model setup is **not justified by this data**. It is
  supported (`RINTI_CODING_MODEL`, or Settings > Coding model) but off by
  default: swapping two 7B models in 6 GB of VRAM costs about 6 to 10 s of load
  time whenever a conversation alternates between coding and general questions.
- `qwen2.5-coder:3b` was not adopted for quality and licensing reasons (and has
  since been removed from this machine). No
  separate classifier model is used: routing is rule-based, and the optional
  `RINTI_FAST_MODEL` only matters if you choose a smaller model for research
  classification.

### Prompt tuning measured

Two measured fixes went into the shared response policy (`core/personality.py`):

The first local runs were wordy on simple questions (about 190 words for "What
is the Mahabharata?", and "Fix it." sometimes produced a long guess). Adding two
sentences of concrete guidance to `core/personality.py` (one short paragraph for
a "what is X" question; ask one short question when a request is too vague)
cut failed checks on the targeted six cases (same model) from 4 of 50 (two runs)
to 1 of 75 (three runs). The sample is small, but the change was in the intended
direction on exactly the weak spots. These are general rules, not answers to
test questions.

The second fix targeted fabrication: asked "What is my pet's name?" with no
stored memory, the 7B invented a name in 2 of 5 runs. An explicit rule to say it
doesn't know about unrecorded personal facts brought that to 0 of 8 invented
answers (benchmark case `unknown_fact`).

## Running the benchmark

```powershell
cd backend
python scripts\benchmark.py --list
python scripts\benchmark.py --targets ollama:qwen2.5:7b,groq:openai/gpt-oss-120b --runs 2
```

Results go to `docs/benchmarks/` (Markdown summary plus JSON with every raw
response). It measures correctness, instruction following, style, time to first
token, total time, tokens per second, model memory, failures, and verifies the
provider by calling it directly. Add `--cold` to include model load time. Cloud
targets need `OPENAI_API_KEY`; they will count rate-limited requests as failures.

Tests (no Ollama or API key needed; they use fake providers):

```powershell
cd backend
python -m pip install -r requirements-dev.txt
python -m pytest
```

## Cost and independence, honestly

| | Local (Ollama) | Cloud (Groq etc.) |
| --- | --- | --- |
| Per-token charge | None | Free tier with limits, then usage charges |
| Rate limits | None (limited by hardware: one reply at a time by default) | Yes; 6 of 26 benchmark requests were refused |
| What you pay | Electricity, hardware wear, and your machine's time | API usage, if you exceed the free tier |
| Availability | Only while the host computer and Ollama are running and reachable | Whenever the provider is up |
| Privacy | Conversations stay on the machine in local-only mode | Conversations are sent to the vendor |
| Speed | About 14 to 25 tokens/s, slower with long prompts | Hundreds of tokens/s |
| Intelligence | A 7B model: good for everyday chat, weaker on hard reasoning and facts | A 120B model: noticeably stronger |

Things this does **not** give you:

- Unlimited throughput. One laptop GPU serves one reply at a time; extra
  requests wait or are told the system is busy.
- A free public service. The hosted site on Vercel cannot reach a model on your
  laptop. Serving local models publicly would need a separate always-on GPU
  server, with its own cost, security and capacity decisions. Until then the
  hosted deployment keeps using the cloud provider.
- Cloud-level quality. Use Auto mode with `RINTI_CLOUD_ESCALATION=true` if you
  want the cloud for the hardest prompts; that sends those prompts to the vendor.

The optional path to improve the local model further is in
`docs/FINE_TUNING_PLAN.md`. It is a plan only; nothing has been trained.

## Hosted deployment notes (Vercel)

- The hosted backend is a Vercel Python Function. It cannot reach Ollama on a
  laptop or home PC, so leave `RINTI_DEFAULT_PROVIDER` unset there (= `groq`,
  Cloud mode). Setting it to `ollama` on Vercel would make every chat return a
  clear "Ollama isn't reachable" error; it never silently uses the cloud.
- No new environment variable is required. `RINTI_ADMIN_TOKEN` is optional: left
  unset, nobody can change inference settings on the hosted site, and chat is
  unaffected. The existing `MODEL_NAME` still selects the cloud model unless
  `RINTI_CLOUD_MODEL` is set.
- On start-up the backend runs `init_db()`, which creates the new `app_config`
  table if missing. On Postgres it first takes a transaction-level advisory lock,
  so simultaneous cold starts take turns instead of racing on the first creation.
- **Check before relying on Preview deployments:** the backend picks its database
  only from `DATABASE_URL`. Vercel scopes each environment variable to
  Production, Preview and/or Development, and a variable added with all three
  ticked is shared. If `DATABASE_URL` is set for Preview with the production
  connection string, Preview deployments read and write production data. Give
  Preview its own database (for example a Neon branch). Leaving `DATABASE_URL`
  unset for Preview would not fall back to production, but the backend would then
  try to use a SQLite file on Vercel's read-only filesystem and most likely fail
  to start (not verified). The repository cannot show which is configured.

## Not tested (do not assume)

- Only one machine has run these models: Windows 11, RTX 4050 Laptop 6 GB,
  24 GB RAM. Every other hardware claim is an estimate from that calibration.
- No AMD or Intel GPU, no Apple Silicon, no GPU under 6 GB, no machine under
  16 GB RAM, and no CPU other than the i5-13450HX was tested.
- The memory-detection code for Linux and macOS exists but was not run on those
  systems. In the tests and manual checks, "simulated machines" change only the
  detected RAM and GPU; the models, Ollama and model files were real.
- A real Vercel deployment was not exercised; hosted behaviour was checked by
  running the backend with the `VERCEL` environment variable set.
- A 4 GB GPU is assumed to split a model like the 6 GB card does; not measured.

## Known limitations

- Voice transcription still uses the cloud client (`voice/stt.py`); the voice
  router is not mounted in this app, so it is unaffected.
- Web research needs a Tavily key regardless of inference mode. It could not be
  run live in the local test environment (no key there); the planning and
  synthesis steps were tested with the local model on fixed evidence.
- The routing classifier is a small rule set; a request like "how do I install
  git" is treated as general (which the general model handles fine).
- Older context is dropped, not summarized, when a conversation outgrows the
  model's window.
