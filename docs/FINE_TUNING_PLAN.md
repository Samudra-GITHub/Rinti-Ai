# Optional plan: fine-tuning a local model for Rinti-AI

**Status: not started, on purpose.** Nothing here should be run until the
conditions in "When to start" are met. Training a foundation model from scratch
is out of scope for this hardware; the realistic option is adapting an existing
open model with a small LoRA/QLoRA adapter.

## When to start

Fine-tuning is worth the effort only if the *measured* gaps below remain after
prompt and routing work (see `docs/benchmarks/`). From the current benchmark of
`qwen2.5:7b`:

| Gap | Evidence | Target |
| --- | --- | --- |
| Research answers often omit `[n]` citations | `research_synthesis` "cites sources" failed 2 of 2 runs locally; the cloud model passed | at least 90% of synthesis runs cite real sources |
| Verbosity on simple questions | partly fixed by the prompt; verify it holds across more cases | style checks at 95% or better |
| Occasional factual errors about Indian epics | benchmark checks are keyword-level; add a held-out factual set before judging | to be defined with a larger test set |

If a gap can be closed by editing the prompt, the retrieval, or the model
choice, do that instead. A fine-tune that does not beat the base model on the
held-out set is discarded.

## What is feasible on an RTX 4050 (6 GB) with 24 GB RAM

- **QLoRA (4-bit base + small adapter)** on a 3B to 4B model with short
  sequences (1,024 to 2,048 tokens), batch size 1, gradient checkpointing:
  plausible, slow (hours for a few thousand examples).
- **7B QLoRA** does not comfortably fit 6 GB of VRAM. Rent a GPU with 16 to
  24 GB for a few hours instead (typically a few US dollars), train there, and
  bring the adapter back.
- Full fine-tuning of any of these models is not feasible locally.

## Licensing (check before training)

- Base model license decides what you may do with the result. From the model
  files that were on this machine (`qwen3:4b` and `gemma3:4b` have since been
  removed; see `docs/LOCAL_INFERENCE.md`): `qwen2.5:7b`, `qwen2.5-coder:7b`,
  `qwen2.5:1.5b` and `qwen3:4b` are **Apache-2.0** and `phi4-mini` is **MIT**
  (both permissive). `qwen2.5-coder:3b` (since removed) is under the **Qwen Research
  License** (not for commercial use). `gemma3:4b` uses **Google's Gemma Terms
  of Use** (use restrictions apply). Prefer Apache-2.0 bases.
- Training data must be yours to use: your own text, data you generated and are
  allowed to reuse, or datasets whose license permits it. Read the terms of any
  model whose outputs you use for synthetic data. Do not train on private
  conversations of other people without their consent.

## Data

1. **Quality over quantity.** 1,000 to 3,000 carefully reviewed examples beat
   a large noisy set for style and format behavior.
2. **Sources**, in order of preference: (a) examples written or edited by you in
   Rinti's voice; (b) your own conversations, after removing personal data and
   keeping only the ones you rate as good; (c) synthetic examples from a
   stronger model, filtered by the same automated checks as the benchmark,
   subject to that model's license and terms.
3. **For the citation gap**, build examples from the real research pipeline:
   (question, numbered evidence, correct structured answer with valid `[n]`
   markers). The existing validators in `backend/research/claims.py` can
   reject bad examples automatically.
4. **Never train on the benchmark cases.** Keep a held-out set that the
   training data cannot overlap with (deduplicate by normalized text).

## Procedure

1. Freeze the baseline: run `scripts/benchmark.py` on the base model and save
   the JSON.
2. Curate and deduplicate the dataset; split train / validation / held-out.
3. Train a LoRA or QLoRA adapter (for example with Unsloth, TRL or Axolotl),
   small rank (8 to 16), 1 to 3 epochs, watching validation loss to avoid
   overfitting.
4. Merge the adapter and export to GGUF (`Q4_K_M`), then register it with
   Ollama (`ollama create rinti-7b -f Modelfile`).
5. Re-run the benchmark with the new model as a target and compare to the
   baseline on every category, including regressions on cases that used to pass.
6. Adopt it only if it beats the base model on the held-out set and does not
   regress correctness. Otherwise keep the base model.

## Cost and effort

Dataset curation is the main cost (days of review, not GPU hours). Training is
hours on rented hardware. Maintenance matters too: each new base model release
means re-running the process, so keep the dataset and scripts versioned.
