# Benchmark results

Produced by `backend/scripts/benchmark.py` (see `docs/LOCAL_INFERENCE.md`).
Each run records every raw response in the `.json` file next to its summary.

| File | What it is |
| --- | --- |
| `benchmark-20261021-122652-before-prompt-tuning.*` | Six targets (five local models plus Groq), two runs each, with the first version of the response policy. Includes `qwen3:4b` (reasoning tokens exhausted its budget) and `gemma3:4b`. |
| `benchmark-20261021-125306-after-length-guidance.*` | `qwen2.5:7b`, `qwen2.5-coder:7b` and Groq after the response policy gained concrete length guidance (13 cases, 2 runs). The only run that includes `qwen2.5-coder:7b` after tuning. |
| `benchmark-20261021-130752-final.*` | The shipped configuration: `qwen2.5:7b` and Groq on the final prompt (14 cases including "unknown personal fact", 2 runs). |
| `benchmark-20261021-195809-small-models.*` | The two smaller catalogue models, `phi4-mini` and `qwen2.5:1.5b`, on the same 14 cases (2 runs each, final prompt). Basis for the lower hardware tiers. |

**These are historical records.** Models that appear in the older files and are no longer installed
(`gemma3:4b`, `qwen3:4b`, `qwen2.5-coder:3b`) were removed after the comparison; nothing in the
application depends on them. Re-pull a model with `ollama pull` to reproduce its numbers.

Timings depend on what else the machine is doing; cloud failures are rate-limit
rejections and vary with how recently the account was used.
