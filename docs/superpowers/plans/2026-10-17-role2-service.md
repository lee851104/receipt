# Role 2 service integration Implementation Plan

> For agentic workers: Use executing-plans; perform TDD and one final independent review.
Goal: finish authorized role2 adapter, local deployment acceptance, aggregate report and concepts without opening sealed test.
Architecture: merge committed role1/models into role2, implement load(model_dir)->callable; preserve server settings as sole model path source. Missing or broken model => unavailable. No experimental sys.path imports in service.
Spec: overview sections5/6/13.10 and item-classification/model-evaluation; latest user selects existing next25-v3 and Protected distribution.
Tech Stack: Python3.12, CPU torch/transformers, existing FastAPI.
## Global Constraints
- role2 linked worktree only; baseline5ba971b. Main/role4/live DB untouched; merge role1 dependency in this branch only.
- No sealed test access, hash, copies or evaluation; no private names to tools. Synthetic fixtures for all inference/HTTP acceptance.
- No public weight release: previous public requirement superseded by Protected policy. Local complete model installation from trusted bundle; document authenticated remote distribution separately, do not fake clean-machine/Docker proof.
- No GPU/shared dependency modifications; fresh dedicated service venv. Keep fake lightweight.
## Review Focus
- Missing dependency/file, corrupted safetensors, wrong labels/max length/manifest path traversal must not produce a random classifier.
- Input order, >batch, empty input, concurrent calls, invalid probabilities; exceptions/logs do not echo names.
- Startup loads once, offline mode no remote code; backend config not read from unrelated global env.
- Main role1 behavior retained for attrs, thresholds, background failure and health.
- Historical aggregate data only, no new test opening; task completion distinguishes local integration and main merge.
## Task 1: Adapter and API integration
- [x] Fictional failing tests for manifest, loading, batching/order, lock, bad input/logits and missing dependency; backend success/failure and shared contract.
- [x] Implement src/ml/category.py; connect category_backend locally; CPU dependency file.
- [x] Run new tests and full main suite; commit.
Interfaces: load(Path)->callable names:list[str] -> list[dict(category:int,probs:list[float])].
## Task 2: Isolated CPU acceptance
- [x] Create new service venv from declared requirements; use existing weights only.
- [x] Add synthetic-only acceptance tool: audit guard sealed test; exact source/export equivalence, check_classify, 1000 sequential CPU names, offline inference, API health/login/classify/upload/jobs/profile plus unavailable case on temp DB.
- [x] Reproduce install into fresh local directory with only inference files and verify startup; document no remote or clean physical machine claim.
- [x] Commit scripts/results; record actual measurements.
Interfaces: accepts explicit model dir and private output; no dataset arguments or outputs containing names.
## Task 3: Documents and closeout
- [x] Replace stale classification.md with numeric whitelist from already computed report, class matrices and exclusions, preserve distinction from selected untested candidate; no new scoring.
- [x] Concepts logistic regression fictional numeric example; selected-model install guide/model card; tasks update3.3/3.6/3.7/3.8 and3.9 policy amendment with precise boundary.
- [x] Final independent review, meaningful checks, and closeout commit; shared handoff is the final delivery step recorded in the common log.
## Ledger
- Ruling: existing specification and user's explicit instruction authorize bounded implementation directly; no redundant design approval.
- Ruling: importing role1 commits preserves authoritative backend; only category wiring modified on role2, main remains untouched.
- Preflight: adapter load return callable is consumed by category_backend and acceptance; existing full-model manifest is consumed directly, no format migration.

## Execution evidence
- Task1 complete: merge adbb535; adapter1789e96; missing-module RED, contract23pass, full457pass after restoring legacy log sentence.
- Task2 complete: installer missing-module RED then2pass; fresh CPU venv full459pass; real HTTP/synthetic acceptance result-v1.json, model reference maxdiff0, 1000=12.9486s, single=.0335s, test/private JSONL attempts0, external connect0. No GPU.
- Task3 implementation complete: numeric-only historical matrices rebuilt and 3-doc privacy audit57 references gives0; concepts and deployment guide written; task3.9 remains unchecked for authenticated remote and physical new-machine/Docker acceptance.
- Ruling: local Windows newvenv plus local model delivery is fully verified; no Docker executable, no authorized credential/public model publication. Do not claim these external acceptance items complete.
- Dependencies: initial uv first-index failed on old idna in CPU index; explicit unsafe-best-match across PyPI/official CPU resolved. Linux requirements resolution also passed, not execution.

## Final closeout evidence
- Stage2 commit5c5d396. Independent Codex review adbb535..5c5d396: no confirmed Critical/Important; 25 targeted tests pass. Claude formal review still pending.
- Minor reference shape gap fixed with RED/PASS unit coverage; final full460pass (30.132s), synthetic HTTP result-v2 pass: maxdiff0, CPU1000=13.1849s, warm single=.0306s; private/external attempts0.
- Added existing366-label report numeric-only tables/matrices; all12 subset matrices checked count/diagonal/accuracy consistency, no dataset or test opening. Three-doc privacy audit uses approved audit_synthetic.py,57 references,0 matches; not all-source audit.
- OpenSpec strict and whitespace checks passed. Task3.9 external environment work remains open; no Docker executable, remote authenticated model delivery and new physical machine unverified. All checked tasks above are this bounded local plan, not full project integration closure.
