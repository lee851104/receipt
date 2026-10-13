# Four-metric model selection Implementation Plan

User explicitly delegates execution and model choice, 2026-10-12; proceed without another approval gate. Use native execution and independent review. All writes remain inside this lab, no production integration or cloud inference.

- [x] Add hand-calculated tests and a scorer for 16 typed attributes: field Accuracy, positive-label micro Precision/Recall/F1, per-field and macro F1. Boolean unknown gold is masked; prediction abstentions remain errors in field Accuracy and missed positives in Recall. Enumerated sugar/fun/species count each concrete value as a positive label; null is unspecified, not a concrete class. Report support and abstentions separately.
- [x] Freeze synthetic diagnostic cases with positive/negative coverage of every attribute before inference. Keep real March development data separate. Both are assistant-labelled, not human ground truth; synthetic data does not prove real-world generalization.
- [x] Download pinned Qwen3-4B-Instruct-2507 Q4_K_M; reuse the existing three models, runtime, prompt-named-v2, decoder and local CPU limits. Save each run in results/followup, preserving the first experiment.
- [x] Run all four models on the synthetic diagnostic set and Qwen3 on March data; reuse frozen earlier March outputs for the three unchanged configurations. If evidence supports a prompt/protocol bug, investigate with a controlled probe before changing candidates.
- [x] Select by positive-label macro F1 on covered synthetic fields, check March performance and failures, report limitations. Development metric gate (not deployment approval): both sets micro F1 >=0.90, synthetic macro F1 >=0.85, no malformed output; these are engineering gates chosen by the assistant, not user-provided guarantees.
- [x] Verify data joins and unchanged source, test scorer, perform independent review, update RESULTS/README/CLAUDE with final choice and four metrics. No automatic production deployment even if scores pass because no human-reviewed holdout exists.

Files: metrics.py and test_metrics.py (metric correctness); benchmark_cases.json (frozen synthetic fixtures); run_followup.py (isolated orchestration); download_extra.py (pinned new asset); followup_report.py (reproducible reports).

## Execution rulings

- Added a separately reported positive-only bulk rule, before Qwen3 inference and before viewing its predictions. This derives from the existing specification (quantity>=3, explicit multipack words), never from reference IDs or answers. Pure-model rankings remain unchanged; combined system scores are reported separately. It cannot fill failed model items or overwrite an unsupported unknown with false.
- Review found the follow-up wrapper ignored failed batch return values. Fixed exit-code propagation and added a CLI regression test. The already-running process uses the earlier loaded wrapper, so saved failures/ID coverage are authoritative for this run.
- Existing source files remain untouched; user asked to keep the experiment discoverable in this checkout, so there is no separate worktree, commit or production deployment.
- Final evidence found Qwen3 guessed five unspecified sweetness values in March despite the original prompt's explicit-only policy. Added a narrow presence guard, not new inference settings: missing explicit sweetness text forces sugar=null. This was added AFTER viewing errors; combined scores are therefore post-hoc development replays, not independent validation. Raw and bulk-only scores remain preserved. Labels, model weights, prompt, and inference outputs were not changed.

## Completed evidence

Selected Qwen3 4B with bulk and explicit-sweetness guards for offline review assistance. Raw synthetic macro F1: 83.25%; raw real micro F1: 44.44%. Post-hoc guarded replay: synthetic micro F1 90.91% / macro F1 89.99%, real micro F1 94.12%. Production readiness remains false. All 35 source rows rejoin without changed original fields; CSV and selected model SHA verified. Experiment 22, main Python 77, final JavaScript 82 tests passed. Independent metric and guard reviews found no blockers. Main concurrent changes were preserved. See RESULTS.md, SELECTED_MODEL.json and private/followup-verification.json.
