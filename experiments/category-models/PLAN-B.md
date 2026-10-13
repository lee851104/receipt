# Model B Implementation Plan

> Execute inline using writing-plans, executing-plans and test-driven-development. Complete a fresh review before delivery.

**Goal:** Compare frozen Chinese embeddings plus logistic regression with A on exactly the same reviewed items and saved folds.

**Spec:** ../../docs/category-models-brief.md and the user's request to implement B.

**Architecture:** Download the pinned public BGE-small Chinese safetensors model separately from private-data execution. Use a local CPU-only frozen encoder (CLS pooling, L2 normalization, no retrieval prefix). Cache embeddings with input/model fingerprints; fit logistic regression only on each training fold. Save the all-item final classifier with encoder provenance.

## Decisions and constraints

- Preserve A's code, saved artifacts, data and splits; B requires A's saved `splits.json` and validates its dataset fingerprint and partition integrity.
- Use `BAAI/bge-small-zh-v1.5`, revision `7999e1d3359715c523056ef9478215996d62a620` (official Hugging Face metadata verified 2026-10-13).
- Freeze encoder parameters. CLS pooling, L2-normalized FP32 vectors, max length 512, batch 16, CPU, one compute thread. No fine-tuning, no task instruction prefix, no API inference.
- Same LR settings as A: C=1, balanced class weights, max_iter=2000, seed from saved splits. No tuning.
- A/B development scores cover only categories with held-out support. Report no full ten-class or independent test claim.
- Cache keys include normalized ordered names, model file hashes, pooling/tokenization settings and dependency versions. Labels never enter the encoder.
- Benchmark full uncached embedding-plus-classification of 1,000 names, separately from classifier-only time. Include encoder weights in deployed size.
- Additional dependencies stay in the experimental virtual environment. Public model downloads and package installs may use network; encoding private names must be offline.
- Model, cache and per-item outputs stay ignored. Do not modify original labels, CSVs or the main application; no commit/push.

## Review focus

- Reject stale/tampered folds and input-order mismatches before training.
- Never silently reuse embeddings for different names/model revisions or corrupt array contents.
- Verify frozen/eval/inference mode, padding-independent CLS and normalized vector dimensions using a tiny real local BERT fixture.
- Preserve 0–9 probability ordering across save/load; reject incompatible encoders.
- Include full encoder latency/size and use exactly A's validation IDs/baseline.

## Tasks

- [x] Write failing tests for split verification, cache invalidation, frozen encoding and persisted predictions.
- [x] Implement download, local encoder/cache and B train/predict/evaluate CLI.
- [x] Download dependencies/weights, run B on the reviewed corpus and independently verify exact A/B split parity.
- [x] Document results/costs, run relevant suites, complete fresh review.

## Ledger

- Existing A data, splits and implementation are now committed by the user; working tree has only unrelated `.claude/` untracked content.
- This is the already-approved B experiment, so implementation proceeds without another design approval round.
- Tests first failed for missing B modules; initial implementation passed the original seven cases. Review found truncated-cache exceptions and potential input overwrite through a mistaken cache path. Both were reproduced with failing regression tests and fixed before the private-data run. Final experiment suite: 21 passing, including nine B tests; root Python 77 and frontend 82 passing; pip check clean.
- Fresh reviewer rechecked fixes with no remaining substantive findings. No commit/push or changes to the main app.
- Real run: `outputs/embedding-20261013/`, 34/49 correct, four-class macro-F1 0.6570751373382953. Exact saved splits and all 49 ID/fold/actual/baseline tuples match A. Original labels and prepared data match recorded hashes. No hyperparameter tuning.
- CPU benchmark: full uncached 1,000-name prediction 12.756266 seconds, deployed encoder plus LR files 96,430,421 bytes. See RESULTS-B.md for interpretation and limitations.
