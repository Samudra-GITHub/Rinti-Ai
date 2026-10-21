# Rinti-AI model benchmark (2026-10-21 12:53)

Same production system prompt, temperature 0.7, same cases for every target. Local context window: 8192 tokens. Checks are automated (see `scripts/benchmark.py`).

## Summary

| Target | Failures | Correctness | Instruction | Style | Median 1st token | Median total | Tokens/s | Model memory (GPU) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | 0/26 | 34/36 | 22/22 | 38/38 | 0.2s | 6.3s | 14 | 5.4 GB (4.1) |
| `ollama:qwen2.5-coder:7b` | 0/26 | 33/36 | 22/22 | 37/38 | 0.2s | 6.2s | 13 | 5.4 GB (4.1) |
| `groq:openai/gpt-oss-120b` | 6/26 | 29/29 | 16/16 | 32/32 | 1.7s | 2.7s | 471 | cloud |

Cold start (first request after load/connect): `ollama:qwen2.5:7b` 1.2s, `ollama:qwen2.5-coder:7b` 11.2s, `groq:openai/gpt-oss-120b` 2.5s

## Per case

### factual

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 8/8 | 0.34s | 13.59s | 144 |  |
| `ollama:qwen2.5:7b` | yes | 8/8 | 0.1s | 7.7s | 92 |  |
| `ollama:qwen2.5-coder:7b` | yes | 8/8 | 2.53s | 16.84s | 143 |  |
| `ollama:qwen2.5-coder:7b` | yes | 8/8 | 0.14s | 9.39s | 97 |  |
| `groq:openai/gpt-oss-120b` | yes | 8/8 | 0.62s | 0.9s | 76 |  |
| `groq:openai/gpt-oss-120b` | yes | 8/8 | 0.79s | 1.05s | 80 |  |

### detailed

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.39s | 39.99s | 470 |  |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.11s | 44.74s | 466 |  |
| `ollama:qwen2.5-coder:7b` | yes | 6/6 | 0.66s | 119.53s | 1054 |  |
| `ollama:qwen2.5-coder:7b` | yes | 4/6 | 0.13s | 71.07s | 647 | failed: covers karma or detachment; not wall of bullets (bullets <= 12) |
| `groq:openai/gpt-oss-120b` | yes | 6/6 | 1.47s | 2.75s | 414 |  |
| `groq:openai/gpt-oss-120b` | yes | 6/6 | 1.33s | 2.58s | 431 |  |

### arithmetic

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.35s | 1.18s | 6 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.11s | 0.93s | 6 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.48s | 1.45s | 6 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.14s | 1.12s | 6 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 3.39s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 4.86s | 4.93s | 5 |  |

### reasoning

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.21s | 5.58s | 47 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.13s | 7.02s | 60 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.29s | 4.96s | 31 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/3 | 0.14s | 1.21s | 5 | failed: change is $6.50 |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 5.48s | 5.48s | 5 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 0.66s | 0.71s | 13 |  |

### conversational

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.38s | 3.59s | 38 |  |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.13s | 3.36s | 42 |  |
| `ollama:qwen2.5-coder:7b` | yes | 6/6 | 0.47s | 3.18s | 32 |  |
| `ollama:qwen2.5-coder:7b` | yes | 6/6 | 0.14s | 5.05s | 58 |  |
| `groq:openai/gpt-oss-120b` | yes | 6/6 | 0.69s | 0.83s | 54 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 12.41s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |

### table

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.52s | 21.28s | 167 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.12s | 20.47s | 149 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.67s | 23.75s | 155 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.13s | 40.02s | 290 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 2.96s | 3.79s | 201 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 5.38s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |

### followup

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/3 | 0.29s | 4.63s | 52 | failed: ties it to duty/dharma or the Gita |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.17s | 3.65s | 39 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/3 | 0.31s | 5.1s | 45 | failed: ties it to duty/dharma or the Gita |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.14s | 7.25s | 62 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 4.66s | 4.8s | 45 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 0.86s | 0.93s | 31 |  |

### code

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.64s | 15.39s | 125 |  |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.13s | 11.57s | 107 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.75s | 19.07s | 151 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.15s | 23.47s | 194 |  |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 12.82s | 13.17s | 90 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 14.41s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |

### debug

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.26s | 26.65s | 225 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.13s | 21.51s | 187 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.27s | 23.23s | 201 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.13s | 11.6s | 120 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 0.66s | 1.15s | 148 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 4.38s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |

### long

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/2 | 3.22s | 3.98s | 5 |  |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.18s | 2.34s | 17 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 4.21s | 5.19s | 5 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.19s | 0.88s | 5 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 15.33s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 1.22s | 1.24s | 5 |  |

### ambiguous

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.52s | 2.21s | 21 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.13s | 2.29s | 25 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.59s | 1.41s | 10 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.14s | 2.96s | 32 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 0.9s | 0.92s | 9 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 1.89s | 1.92s | 10 |  |

### research_intent

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.53s | 2.51s | 11 |  |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.14s | 2.13s | 11 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.5s | 3.05s | 17 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.23s | 3.57s | 23 |  |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 9.0s | 9.0s | 15 |  |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 15.12s | 15.12s | 14 |  |

### research_synthesis

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 4/4 | 2.21s | 22.45s | 114 |  |
| `ollama:qwen2.5:7b` | yes | 3/4 | 0.16s | 32.33s | 197 | failed: cites sources |
| `ollama:qwen2.5-coder:7b` | yes | 4/4 | 2.74s | 30.53s | 175 |  |
| `ollama:qwen2.5-coder:7b` | yes | 4/4 | 0.19s | 28.9s | 177 |  |
| `groq:openai/gpt-oss-120b` | yes | 4/4 | 12.97s | 12.97s | 215 |  |
| `groq:openai/gpt-oss-120b` | yes | 4/4 | 13.92s | 13.93s | 157 |  |
