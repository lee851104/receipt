# Model A Implementation Plan

> Execute inline with executing-plans and test-driven-development; review the complete change before delivery.

**Goal:** Train and use a reproducible, local TF-IDF plus logistic regression classifier on human-confirmed names.

**Architecture:** Separate data validation/preparation, shared evaluation, and a model CLI. Fit TF-IDF inside each training fold. Save a final model trained on all confirmed items separately from out-of-fold predictions.

**Tech Stack:** Python 3.12, scikit-learn, NumPy, SciPy, joblib; CPU only.

**Spec:** ../../docs/category-models-brief.md and the user's approved labels and request to implement A.

## Constraints and rulings

- Only this experimental directory changes; private source data remains untouched.
- Human-confirmed JSONL is authoritative. Also provide CSV/catalog preparation for future data.
- Ruling: Current singleton classes cannot support 70/15/15 splits. Use fixed three-fold development CV for classes with at least three independent groups; retain rare groups in training only. Do not claim a full ten-class test score. B/C may reuse saved assignments once implemented; the final held-out benchmark waits for more data.
- Ruling: Preserve confirmed context-dependent names; expose their separate validation metrics. No descriptions, merchant, amount, or IDs become model inputs.
- Ruling: Existing checkout has unrelated work and ignored private sources. Make additive changes in this isolated experiment directory; do not change branches, commit, push, or modify the main application.
- Use a dedicated virtual environment and pinned dependencies. Models, input data, split files and row-level results are ignored by Git.
- No parameter search; C=1, balanced class weights, character 1–3 grams, sublinear TF, seed 42.

## Review focus

- Unreviewed records, invalid labels, duplicate IDs and conflicting normalized names must fail safely without printing private names.
- Related variants must not cross a validation boundary; rare classes must not receive invented evaluation scores.
- Vocabulary must be fit on training data only; all evaluated records receive exactly one held-out prediction.
- Saved models must reproduce probabilities and preserve class order, including classes absent from training.
- External evaluation must expose overlap with training names and never label it independent test performance.

## Tasks

- [x] 1. Write failing data and evaluation tests; implement loaders, CSV conversion and reproducible grouped folds.
- [x] 2. Write failing model/CLI tests; implement training, saved artifacts, prediction and external evaluation.
- [x] 3. Run tests, train the current reviewed data, independently verify outputs and run existing project suites.
- [x] 4. Write usage/results documentation and complete a fresh code review.

## Execution ledger

- Baseline: existing Python suite passes (77 tests). Existing root environment has scikit-learn 1.9.1.
- The old private pilot is not reused as authoritative labels; the newly reviewed JSONL is the source.
- Tasks 1–2: observed ten expected missing-implementation failures, then ten passing tests. Added the CSV external-evaluation test, observed the missing-command failure, implemented it; twelve tests pass in the dedicated environment.
- Dependency installation initially blocked by network permissions; approved scoped pip installation completed. No private data sent to a model service.
- Real run: 57 confirmed items; 49 held-out predictions, 8 rare training-only items; four-class development Macro-F1 0.6239448052 and accuracy 35/49. Final model trained on all 57 items. Known related names are grouped in an ignored prepared copy, not by altering original labels.
- Verification: independent confusion-matrix/F1 recomputation passed; all held-out IDs appear exactly once; group boundaries and all ten persisted classes verified; original CSV and reviewed-source SHA256 hashes unchanged.
- Existing suites: Python 77/77 and Node 82/82 pass. Dedicated environment `pip check` passes.
- Fresh reviewer: no important findings; independently ran all 12 synthetic tests successfully. No source-data inspection or edits by reviewer.
- Delivery: implementation, labeling notes and aggregate results remain in this experiment directory. Private dataset snapshot, model and row-level outputs remain ignored. No commits, push, branch switch or application integration.
