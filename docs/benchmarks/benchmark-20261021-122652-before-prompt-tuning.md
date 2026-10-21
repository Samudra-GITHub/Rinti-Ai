# Rinti-AI model benchmark (2026-10-21 12:26)

Same production system prompt, temperature 0.7, same cases for every target. Local context window: 8192 tokens. Checks are automated (see `scripts/benchmark.py`).

## Summary

| Target | Failures | Correctness | Instruction | Style | Median 1st token | Median total | Tokens/s | Model memory (GPU) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | 0/26 | 34/36 | 20/22 | 36/38 | 0.2s | 9.3s | 14 | 5.4 GB (4.1) |
| `ollama:gemma3:4b` | 0/26 | 35/36 | 22/22 | 30/38 | 0.3s | 25.4s | 22 | 2.9 GB (2.9) |
| `ollama:qwen2.5-coder:7b` | 0/26 | 34/36 | 22/22 | 36/38 | 0.2s | 6.2s | 15 | 5.4 GB (4.1) |
| `ollama:qwen2.5-coder:3b` | 0/26 | 33/36 | 18/22 | 35/38 | 0.1s | 4.7s | 32 | 2.4 GB (2.4) |
| `ollama:qwen3:4b` | 10/26 | 17/18 | 12/12 | 38/38 | 31.0s | 37.7s | 151 | 3.9 GB (3.9) |
| `groq:openai/gpt-oss-120b` | 3/26 | 33/33 | 20/20 | 34/35 | 9.1s | 9.6s | 530 | cloud |

Cold start (first request after load/connect): `ollama:qwen2.5:7b` 9.3s, `ollama:gemma3:4b` 7.4s, `ollama:qwen2.5-coder:7b` 10.8s, `ollama:qwen2.5-coder:3b` 5.9s, `ollama:qwen3:4b` 5.7s, `groq:openai/gpt-oss-120b` 2.4s

## Per case

### factual

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 7/8 | 1.66s | 19.13s | 202 | failed: concise (<= 170 words) |
| `ollama:qwen2.5:7b` | yes | 7/8 | 0.11s | 17.2s | 181 | failed: concise (<= 170 words) |
| `ollama:gemma3:4b` | yes | 6/8 | 1.8s | 25.4s | 370 | failed: concise (<= 170 words); at most 2 bold phrases |
| `ollama:gemma3:4b` | yes | 6/8 | 0.28s | 27.21s | 408 | failed: concise (<= 170 words); at most 2 bold phrases |
| `ollama:qwen2.5-coder:7b` | yes | 7/8 | 2.69s | 18.74s | 186 | failed: concise (<= 170 words) |
| `ollama:qwen2.5-coder:7b` | yes | 8/8 | 0.12s | 8.61s | 94 |  |
| `ollama:qwen2.5-coder:3b` | yes | 6/8 | 1.41s | 26.95s | 432 | failed: concise (<= 170 words); at most 2 bold phrases |
| `ollama:qwen2.5-coder:3b` | yes | 7/8 | 0.1s | 10.99s | 207 | failed: concise (<= 170 words) |
| `ollama:qwen3:4b` | yes | 7/8 | 63.29s | 65.36s | 26 | failed: mentions the Pandavas/Kauravas or Kurukshetra |
| `ollama:qwen3:4b` | yes | 8/8 | 31.49s | 38.92s | 110 |  |
| `groq:openai/gpt-oss-120b` | yes | 8/8 | 0.78s | 1.08s | 96 |  |
| `groq:openai/gpt-oss-120b` | yes | 8/8 | 0.7s | 1.1s | 127 |  |

### detailed

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.59s | 69.95s | 719 |  |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.12s | 81.14s | 749 |  |
| `ollama:gemma3:4b` | yes | 5/6 | 1.02s | 83.56s | 715 | failed: not wall of bullets (bullets <= 12) |
| `ollama:gemma3:4b` | yes | 5/6 | 0.32s | 57.68s | 771 | failed: not wall of bullets (bullets <= 12) |
| `ollama:qwen2.5-coder:7b` | yes | 5/6 | 0.55s | 63.01s | 647 | failed: not wall of bullets (bullets <= 12) |
| `ollama:qwen2.5-coder:7b` | yes | 6/6 | 0.11s | 55.68s | 561 |  |
| `ollama:qwen2.5-coder:3b` | yes | 6/6 | 0.08s | 24.45s | 493 |  |
| `ollama:qwen2.5-coder:3b` | yes | 6/6 | 0.09s | 17.18s | 412 |  |
| `ollama:qwen3:4b` | yes | 6/6 | 35.69s | 74.51s | 483 |  |
| `ollama:qwen3:4b` | yes | 6/6 | 40.6s | 79.15s | 465 |  |
| `groq:openai/gpt-oss-120b` | yes | 6/6 | 1.09s | 2.45s | 479 |  |
| `groq:openai/gpt-oss-120b` | yes | 6/6 | 1.44s | 3.04s | 484 |  |

### arithmetic

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.39s | 3.38s | 25 |  |
| `ollama:qwen2.5:7b` | yes | 2/3 | 0.12s | 4.68s | 40 | failed: direct (<= 25 words) |
| `ollama:gemma3:4b` | yes | 3/3 | 0.85s | 1.26s | 6 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.16s | 0.53s | 6 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.43s | 1.21s | 6 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.11s | 0.89s | 6 |  |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.12s | 0.38s | 6 |  |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.09s | 0.35s | 6 |  |
| `ollama:qwen3:4b` | yes | 3/3 | 25.01s | 27.57s | 23 |  |
| `ollama:qwen3:4b` | yes | 3/3 | 26.81s | 27.76s | 6 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 16.38s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 2.81s | 2.81s | 1 |  |

### reasoning

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.3s | 9.04s | 73 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.13s | 9.64s | 67 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.25s | 3.28s | 37 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.17s | 3.47s | 36 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.26s | 4.49s | 35 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/3 | 0.11s | 0.79s | 5 | failed: change is $6.50 |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.1s | 3.65s | 66 |  |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.09s | 1.73s | 28 |  |
| `ollama:qwen3:4b` | yes | 3/3 | 27.35s | 30.17s | 17 |  |
| `ollama:qwen3:4b` | yes | 3/3 | 57.38s | 61.2s | 18 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 6.99s | 7.01s | 5 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 11.39s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |

### conversational

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.38s | 5.2s | 63 |  |
| `ollama:qwen2.5:7b` | yes | 6/6 | 0.12s | 4.63s | 53 |  |
| `ollama:gemma3:4b` | yes | 6/6 | 0.27s | 5.46s | 93 |  |
| `ollama:gemma3:4b` | yes | 6/6 | 0.19s | 5.6s | 93 |  |
| `ollama:qwen2.5-coder:7b` | yes | 6/6 | 0.4s | 7.23s | 81 |  |
| `ollama:qwen2.5-coder:7b` | yes | 6/6 | 0.11s | 3.09s | 37 |  |
| `ollama:qwen2.5-coder:3b` | yes | 6/6 | 0.1s | 0.67s | 20 |  |
| `ollama:qwen2.5-coder:3b` | yes | 6/6 | 0.08s | 1.01s | 25 |  |
| `ollama:qwen3:4b` | yes | 6/6 | 30.54s | 36.43s | 63 |  |
| `ollama:qwen3:4b` | yes | 6/6 | 48.2s | 57.04s | 87 |  |
| `groq:openai/gpt-oss-120b` | yes | 5/6 | 5.99s | 6.21s | 84 | failed: responds to the feeling |
| `groq:openai/gpt-oss-120b` | yes | 6/6 | 12.89s | 13.01s | 45 |  |

### table

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.58s | 24.47s | 165 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.12s | 21.43s | 155 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.28s | 25.47s | 362 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.28s | 33.9s | 420 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.58s | 37.33s | 295 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.11s | 27.36s | 256 |  |
| `ollama:qwen2.5-coder:3b` | yes | 2/3 | 0.12s | 13.05s | 258 | failed: contains a table |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.09s | 15.93s | 298 |  |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 64.47s | - | empty response |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 59.02s | - | empty response |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 12.21s | 12.98s | 174 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 12.13s | 12.89s | 189 |  |

### followup

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.3s | 5.14s | 56 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.11s | 3.88s | 45 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.32s | 2.83s | 63 |  |
| `ollama:gemma3:4b` | yes | 2/3 | 0.2s | 2.41s | 44 | failed: ties it to duty/dharma or the Gita |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.2s | 4.64s | 35 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.11s | 4.24s | 51 |  |
| `ollama:qwen2.5-coder:3b` | yes | 2/3 | 0.13s | 1.08s | 15 | failed: ties it to duty/dharma or the Gita |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.09s | 1.5s | 35 |  |
| `ollama:qwen3:4b` | yes | 3/3 | 52.61s | 58.49s | 48 |  |
| `ollama:qwen3:4b` | yes | 3/3 | 28.87s | 35.34s | 52 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 9.87s | 9.97s | 42 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 14.05s | 14.18s | 48 |  |

### code

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.63s | 22.37s | 194 |  |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.15s | 15.23s | 131 |  |
| `ollama:gemma3:4b` | yes | 2/2 | 0.31s | 31.66s | 439 |  |
| `ollama:gemma3:4b` | yes | 2/2 | 0.29s | 37.18s | 424 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.58s | 15.7s | 138 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.14s | 22.62s | 222 |  |
| `ollama:qwen2.5-coder:3b` | yes | 2/2 | 0.12s | 8.69s | 179 |  |
| `ollama:qwen2.5-coder:3b` | yes | 2/2 | 0.11s | 11.57s | 242 |  |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 96.61s | - | empty response |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 98.67s | - | empty response |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 10.69s | 10.82s | 34 |  |
| `groq:openai/gpt-oss-120b` | NO | 0/0 | -s | 13.38s | - | rate_limited: Groq (cloud) is rate limiting requests right now. Try again shortly. |

### debug

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.28s | 33.29s | 265 |  |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.11s | 24.58s | 207 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.32s | 28.89s | 359 |  |
| `ollama:gemma3:4b` | yes | 3/3 | 0.32s | 35.09s | 414 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.3s | 19.11s | 195 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.12s | 30.4s | 283 |  |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.1s | 7.0s | 182 |  |
| `ollama:qwen2.5-coder:3b` | yes | 3/3 | 0.1s | 13.99s | 249 |  |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 79.44s | - | empty response |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 66.58s | - | empty response |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 5.79s | 6.32s | 151 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 9.05s | 9.63s | 187 |  |

### long

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/2 | 4.77s | 7.0s | 27 |  |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.15s | 2.03s | 16 |  |
| `ollama:gemma3:4b` | yes | 2/2 | 2.21s | 2.54s | 5 |  |
| `ollama:gemma3:4b` | yes | 2/2 | 0.24s | 0.47s | 5 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 4.53s | 5.23s | 5 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.15s | 1.05s | 9 |  |
| `ollama:qwen2.5-coder:3b` | yes | 1/2 | 1.91s | 5.78s | 85 | failed: short answer (<= 40 words) |
| `ollama:qwen2.5-coder:3b` | yes | 2/2 | 0.14s | 0.4s | 7 |  |
| `ollama:qwen3:4b` | yes | 2/2 | 42.16s | 43.12s | 9 |  |
| `ollama:qwen3:4b` | yes | 2/2 | 20.24s | 21.29s | 14 |  |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 31.15s | 31.17s | 5 |  |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 21.28s | 21.3s | 5 |  |

### ambiguous

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/3 | 0.47s | 2.31s | 22 | failed: asks for the missing information |
| `ollama:qwen2.5:7b` | yes | 3/3 | 0.12s | 1.64s | 19 |  |
| `ollama:gemma3:4b` | yes | 2/3 | 0.74s | 32.3s | 446 | failed: short (<= 60 words) |
| `ollama:gemma3:4b` | yes | 2/3 | 0.3s | 39.63s | 524 | failed: short (<= 60 words) |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.47s | 2.5s | 26 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/3 | 0.11s | 2.51s | 28 |  |
| `ollama:qwen2.5-coder:3b` | yes | 2/3 | 0.21s | 0.69s | 8 | failed: asks for the missing information |
| `ollama:qwen2.5-coder:3b` | yes | 2/3 | 0.08s | 1.52s | 33 | failed: asks for the missing information |
| `ollama:qwen3:4b` | yes | 3/3 | 23.69s | 24.0s | 3 |  |
| `ollama:qwen3:4b` | yes | 3/3 | 17.51s | 20.2s | 42 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 0.71s | 0.73s | 8 |  |
| `groq:openai/gpt-oss-120b` | yes | 3/3 | 15.73s | 15.75s | 9 |  |

### research_intent

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.7s | 2.81s | 11 |  |
| `ollama:qwen2.5:7b` | yes | 2/2 | 0.13s | 2.06s | 11 |  |
| `ollama:gemma3:4b` | yes | 2/2 | 0.43s | 2.65s | 22 |  |
| `ollama:gemma3:4b` | yes | 2/2 | 0.28s | 2.24s | 19 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.44s | 3.62s | 21 |  |
| `ollama:qwen2.5-coder:7b` | yes | 2/2 | 0.14s | 3.3s | 25 |  |
| `ollama:qwen2.5-coder:3b` | yes | 2/2 | 0.19s | 1.38s | 17 |  |
| `ollama:qwen2.5-coder:3b` | yes | 2/2 | 0.09s | 1.17s | 16 |  |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 9.86s | - | empty response |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 9.91s | - | empty response |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 0.91s | 0.91s | 10 |  |
| `groq:openai/gpt-oss-120b` | yes | 2/2 | 1.0s | 1.01s | 18 |  |

### research_synthesis

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:qwen2.5:7b` | yes | 3/4 | 3.08s | 25.34s | 160 | failed: cites sources |
| `ollama:qwen2.5:7b` | yes | 3/4 | 0.15s | 25.55s | 174 | failed: cites sources |
| `ollama:gemma3:4b` | yes | 4/4 | 1.59s | 36.67s | 264 |  |
| `ollama:gemma3:4b` | yes | 4/4 | 0.37s | 26.72s | 283 |  |
| `ollama:qwen2.5-coder:7b` | yes | 4/4 | 2.73s | 31.57s | 199 |  |
| `ollama:qwen2.5-coder:7b` | yes | 3/4 | 0.17s | 29.8s | 211 | failed: cites sources |
| `ollama:qwen2.5-coder:3b` | yes | 3/4 | 0.94s | 12.02s | 152 | failed: cites sources |
| `ollama:qwen2.5-coder:3b` | yes | 3/4 | 0.12s | 12.59s | 130 | failed: cites sources |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 85.93s | - | empty response |
| `ollama:qwen3:4b` | NO | 0/0 | -s | 77.65s | - | empty response |
| `groq:openai/gpt-oss-120b` | yes | 4/4 | 25.68s | 25.68s | 242 |  |
| `groq:openai/gpt-oss-120b` | yes | 4/4 | 26.18s | 26.19s | 129 |  |
