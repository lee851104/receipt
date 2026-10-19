# Receipt attribute experiment Implementation Plan

> For agentic workers: use superpowers:executing-plans task-by-task. This is an isolated experimental spike expressly authorized in chat; do not commit or integrate it.

**Goal:** Copy March CSV, download three local Chinese instruction models, compare typed item attributes, leave a reproducible Claude handoff.
**Architecture:** Standard-library Python + portable llama.cpp CPU server, pinned Q4_K_M GGUF. No project dependency changes. One immutable raw copy, deterministic per-row IDs and merchant+item deduplication, typed saved predictions.
**Tech Stack:** Python 3.12 standard library, llama.cpp b11557 CPU x64, Qwen2.5 0.5B / 1.5B / 3B Instruct GGUF.
**Spec:** User request in this chat, 2026-10-12: separate folder, copy March CSV, download/run candidate models, do not affect Claude/main project. Previous messages specify 16 attribute fields plus basic flags needed for future integration.

## Global Constraints
- All writes under experiments/receipt-attributes; private data and runtime ignored by nested .gitignore.
- Actual source is 0301-0331.csv (0301-0330.csv does not exist); copy bytes unchanged.
- Preserve distinction between unknown and false. Preserve original row count, amounts and traceability.
- No cloud inference. Model output cannot write files or execute instructions; input treated as data.
- CPU only, 2 threads, sequential models and IDLE child priority.
- Do not claim validated accuracy without user-reviewed ground truth or coverage of every attribute.

## Review Focus
- Same name at different merchants must not collide.
- Unknown fields and malformed output must be rejected, not filled as confident negatives.
- No raw invoice IDs/addresses/carrier identifiers in inference prompts.
- Data amounts / row mapping survive annotation.
- Missing real examples for attributes must remain an explicit coverage gap.

## Tasks
- [x] Snapshot protected files, copy CSV and pin/download/checksum runtime and models.
- [x] Test item grouping, typed validation and stable round-trip linkage, implement local preparation.
- [x] Run deterministic schema-constrained local inference for all three models, save raw outputs/timings/failures.
- [x] Compare with assistant-drafted partial reference labels, mark unknown/uncovered fields, leave editable human review file.
- [x] Write README/RESULTS/integration contract, verify original files and CSV unchanged, run lab tests.

## Rulings / execution ledger
- User explicitly asked to download and run now; no further design approval requested. Folder isolation replaces a worktree because the user wants Claude to find this experiment in this checkout.
- Selected generative models because embedding-only models do not directly produce 16 typed attributes without another classifier.
- GPU is NVIDIA 940MX 2 GB: CPU quantized models avoid contending for GPU and modern CUDA incompatibility.
- The first positional-array prompt produced mostly nulls. Kept that round in results/archive and reran all models with prompt-named-v2.txt. Runtime schema supports boolean/null; format difficulty is a hypothesis, not a proven cause.
- Named protocol explicitly uses yes=true, unknown=null, omitted boolean=false. The validator rejects duplicate/contradictory labels; this is distinct from filling missing fields in malformed output.
- Review fixes: archive the entire previous model directory on rerun; count missing requested positives as false negatives; pin assistant reference to the exact CSV SHA256.
- Prompt adjustments used this March sample, so it is a development set, not an independent holdout. Human-reviewed evaluation and broader attribute coverage remain future work.
- Final named run: valid groups 25/28, 28/28, 28/28; exact draft matches 0/28, 9/28, 6/28 for 0.5B / 1.5B / 3B. No production model selected. Full results and limits are in RESULTS.md.
