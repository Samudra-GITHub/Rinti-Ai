# Rinti-AI model benchmark (2026-10-21 19:58)

Same production system prompt, temperature 0.7, same cases for every target. Local context window: 8192 tokens. Checks are automated (see `scripts/benchmark.py`).

## Summary

| Target | Failures | Correctness | Instruction | Style | Median 1st token | Median total | Tokens/s | Model memory (GPU) |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | 0/28 | 35/38 | 22/22 | 38/40 | 0.1s | 1.2s | 59 | 3.6 GB (3.6) |
| `ollama:qwen2.5:1.5b` | 0/28 | 31/38 | 21/22 | 39/40 | 0.1s | 0.6s | 120 | 1.4 GB (1.4) |

Cold start (first request after load/connect): `ollama:phi4-mini` 15.0s, `ollama:qwen2.5:1.5b` 5.1s

## Per case

### factual

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 8/8 | 0.63s | 3.68s | 131 |  |
| `ollama:phi4-mini` | yes | 8/8 | 0.1s | 3.67s | 157 |  |
| `ollama:qwen2.5:1.5b` | yes | 8/8 | 0.35s | 1.63s | 116 |  |
| `ollama:qwen2.5:1.5b` | yes | 8/8 | 0.09s | 1.37s | 103 |  |

### detailed

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 6/6 | 0.1s | 13.76s | 599 |  |
| `ollama:phi4-mini` | yes | 6/6 | 0.1s | 13.6s | 591 |  |
| `ollama:qwen2.5:1.5b` | yes | 6/6 | 0.08s | 7.21s | 651 |  |
| `ollama:qwen2.5:1.5b` | yes | 5/6 | 0.08s | 5.68s | 500 | failed: no generic preamble |

### arithmetic

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 3/3 | 0.1s | 0.32s | 9 |  |
| `ollama:phi4-mini` | yes | 3/3 | 0.1s | 0.32s | 9 |  |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.06s | 0.19s | 9 |  |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.07s | 0.17s | 6 |  |

### reasoning

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 3/3 | 0.11s | 0.76s | 24 |  |
| `ollama:phi4-mini` | yes | 3/3 | 0.09s | 0.84s | 24 |  |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.08s | 0.98s | 63 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/3 | 0.08s | 0.16s | 5 | failed: change is $6.50 |

### conversational

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 5/6 | 0.1s | 1.41s | 69 | failed: responds to the feeling |
| `ollama:phi4-mini` | yes | 5/6 | 0.1s | 1.19s | 58 | failed: responds to the feeling |
| `ollama:qwen2.5:1.5b` | yes | 6/6 | 0.09s | 0.5s | 39 |  |
| `ollama:qwen2.5:1.5b` | yes | 6/6 | 0.06s | 0.65s | 60 |  |

### table

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 3/3 | 0.12s | 10.56s | 349 |  |
| `ollama:phi4-mini` | yes | 3/3 | 0.1s | 5.51s | 195 |  |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.08s | 2.09s | 163 |  |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.09s | 4.89s | 251 |  |

### followup

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 2/3 | 0.12s | 0.96s | 42 | failed: ties it to duty/dharma or the Gita |
| `ollama:phi4-mini` | yes | 3/3 | 0.1s | 1.18s | 56 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/3 | 0.09s | 0.24s | 14 | failed: ties it to duty/dharma or the Gita |
| `ollama:qwen2.5:1.5b` | yes | 2/3 | 0.08s | 0.34s | 22 | failed: ties it to duty/dharma or the Gita |

### code

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 2/2 | 0.09s | 3.07s | 107 |  |
| `ollama:phi4-mini` | yes | 2/2 | 0.11s | 2.69s | 90 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/2 | 0.09s | 2.52s | 169 |  |
| `ollama:qwen2.5:1.5b` | yes | 1/2 | 0.08s | 2.47s | 197 | failed: generated function runs and is correct |

### debug

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 3/3 | 0.12s | 3.94s | 151 |  |
| `ollama:phi4-mini` | yes | 3/3 | 0.09s | 3.25s | 146 |  |
| `ollama:qwen2.5:1.5b` | yes | 1/3 | 0.15s | 1.07s | 84 | failed: identifies mutating a list while iterating; offers a fix in a code block |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.09s | 3.32s | 244 |  |

### long

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 2/2 | 0.83s | 0.96s | 5 |  |
| `ollama:phi4-mini` | yes | 2/2 | 0.17s | 0.3s | 5 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/2 | 0.47s | 0.55s | 5 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/2 | 0.12s | 0.19s | 5 |  |

### unknown_fact

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 2/2 | 0.37s | 0.68s | 16 |  |
| `ollama:phi4-mini` | yes | 2/2 | 0.1s | 0.49s | 18 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/2 | 0.16s | 0.46s | 30 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/2 | 0.08s | 0.31s | 22 |  |

### ambiguous

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 3/3 | 0.11s | 0.66s | 28 |  |
| `ollama:phi4-mini` | yes | 3/3 | 0.08s | 0.85s | 40 |  |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.09s | 0.26s | 15 |  |
| `ollama:qwen2.5:1.5b` | yes | 3/3 | 0.11s | 0.26s | 13 |  |

### research_intent

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 2/2 | 0.23s | 0.84s | 15 |  |
| `ollama:phi4-mini` | yes | 2/2 | 0.17s | 1.03s | 26 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/2 | 0.14s | 0.47s | 18 |  |
| `ollama:qwen2.5:1.5b` | yes | 2/2 | 0.12s | 0.53s | 25 |  |

### research_synthesis

| Target | OK | Checks passed | 1st token | Total | Words | Notes |
| --- | --- | --- | --- | --- | --- | --- |
| `ollama:phi4-mini` | yes | 3/4 | 0.43s | 2.77s | 70 | failed: cites sources |
| `ollama:phi4-mini` | yes | 3/4 | 0.13s | 5.74s | 154 | failed: cites sources |
| `ollama:qwen2.5:1.5b` | yes | 3/4 | 0.36s | 5.18s | 235 | failed: cites sources |
| `ollama:qwen2.5:1.5b` | yes | 3/4 | 0.11s | 5.01s | 251 | failed: cites sources |
