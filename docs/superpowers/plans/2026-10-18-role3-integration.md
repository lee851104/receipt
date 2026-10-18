# Role 3 integration, role 1 side (to-do B) Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** With role 3's reviewed branch (6065c8c) merged into `role-1/role3-integration`, make qwen the demo's attribute model, build the Qwen adapter from `Settings`, and give the Docker demo the 300 demo users with their purchases and profiles.

**Architecture:** `src/api/backends.py` builds one `AttributeDescriber` from `Settings.llama_server_url` (one source for the address, checked when the app loads). `src/api/container.py` calls role 3's `seed_demo_population` in demo mode on every start (it skips a complete population), and the image carries the reviewed synthetic cache. Compose and `.env.example` default to `ATTRIBUTES_MODEL=qwen`; `Settings`' own default stays `fake`.

**Tech Stack:** Python 3.12, FastAPI, SQLModel/SQLite, unittest, Docker/compose, GitHub Actions.

**Spec:** `docs/team/overview.md` 13.10 ("合併當天的清單", items 1, 4, 5, 6, 7) and 13.11 (role 3's reply); `openspec/changes/add-matching-system/specs/item-attributes/spec.md`, `specs/service-runtime/spec.md` ("無 GPU 模式"); handoff record `CLAUDE-R1-B-START-20261018-121316-0f9a`.

## Global Constraints

- Python: `.venv/Scripts/python.exe -X utf8 -m unittest ...` from the repository root; Node: `node --test "tests/*.test.cjs"`; OpenSpec: `OPENSPEC_TELEMETRY=0 /c/Users/User/AppData/Roaming/npm/openspec validate add-matching-system --strict`.
- Never read `data/`, `rawdata/`, root `*.csv` or `.env`. Test names are fictional (role 3's start with 示範). No test may reach a real llama-server, Hugging Face or the network: stub `AttributeDescriber._request` or use a port nothing listens on only where the call never connects.
- Never print or log `LLAMA_SERVER_URL` / `DOCKER_LLAMA_SERVER_URL` values (they may hold credentials); error text names the variable only.
- Do not edit role 3's files: `src/api/seed.py`, `src/ml/attributes.py`, `tests/test_role3_seed.py`, `tests/test_ml_attributes.py`, `tests/test_synthetic_attribute_cache.py`, `datasets/synthetic/*`.
- `Settings.attributes_model` default stays `"fake"`; only `docker-compose.yml` and `.env.example` change to qwen. An existing `.env` is never edited.
- `git add` named files only, never `-A`; never stage `AGENTS.md`, `CLAUDE.md`, `CODEX_CLAUDE_HANDOFF.md`. Each commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. No push.
- Match the surrounding code: plain-English docstrings that say why, one-line errors starting `error: ` at the entry points, `log.warning` lines without newlines.

## Review Focus

1. A Docker volume made by an older image already holds the 40 demo users with no purchases: the container must still fill in all 300 with profiles (the old code only seeded an empty database). Task 3 test `test_a_database_with_people_in_it_is_still_seeded_in_demo_mode`.
2. A seed that refuses inside the container (a changed cache answer, an unfinished demo job, a clash) must leave the server starting, with one log line. Task 3 test `test_a_seed_that_refuses_is_one_log_line_and_the_start_goes_on`.
3. `LLAMA_SERVER_URL` holding a user name and password, a path, or a remote host must stop qwen at load with a message that does not echo the URL; `http://[::1]:8080` and `http://localhost:8080` must still start. Task 2 test `test_qwen_with_an_address_that_is_not_local_stops_without_showing_it`.
4. The key the service reads (`Backends.attributes_version`) must equal the key the seed writes (`src.ml.attributes.MODEL_VERSION`), or demo users show every name as pending. Task 2 test `test_the_real_module_keys_the_cache_the_way_the_seed_writes_it`.
5. The CI runner seeds 300 people before the server answers: the compose check must wait long enough and must prove profiles, not only the user list. Task 3 workflow step and `test_ci_checks_the_demo_has_its_profiles_in_cache_only_mode`.

---

### Task 1: qwen is the demo default, and the missing-module check still bites

**Files:**
- Modify: `tests/test_api_main.py:28-38`
- Modify: `docker-compose.yml:1-4` (comment), `:13` (`ATTRIBUTES_MODEL`)
- Modify: `.env.example:11-12`
- Modify: `tests/test_docker_files.py:46-48`

**Interfaces:** Produces nothing other tasks call.

- [ ] **Step 1: Write the failing tests**

In `tests/test_api_main.py`, give `start()` a keyword-only `missing_attributes=False`; when true the subprocess runs `import sys; sys.modules["src.ml.attributes"] = None; ` + `IMPORT`. The qwen sub-case of `test_a_model_that_is_not_there_yet_stops_it_in_one_line` calls `start(ATTRIBUTES_MODEL="qwen", missing_attributes=True)` and keeps its assertions (exit 1, one stderr line, starts with `error: ATTRIBUTES_MODEL=qwen needs src/ml/attributes.py`); update the comment (role 3's file is merged now, the subprocess hides it). Add:

```python
def test_qwen_starts_now_that_role_3s_module_is_merged(self):
    result = start(ATTRIBUTES_MODEL="qwen", LLAMA_SERVER_URL="http://127.0.0.1:8080")
    self.assertEqual((result.returncode, result.stdout.strip()), (0, "FastAPI"), result.stderr)
```

In `tests/test_docker_files.py` rename the compose test to `test_compose_passes_the_attribute_model_choice_with_qwen_as_default` asserting `"ATTRIBUTES_MODEL: ${ATTRIBUTES_MODEL:-qwen}"` is in the text. Add `test_the_example_settings_make_qwen_the_demo_attribute_model`: the `.env.example` line list contains `"ATTRIBUTES_MODEL=qwen"` and `"LLAMA_SERVER_URL=http://127.0.0.1:8080"`.

- [ ] **Step 2: Run them, expect the two file tests to fail**

Run: `.venv/Scripts/python.exe -X utf8 -m unittest tests.test_api_main tests.test_docker_files -v`
Expected: the compose and `.env.example` tests FAIL; the test_api_main tests PASS (the old failure is gone).

- [ ] **Step 3: Change the defaults**

`docker-compose.yml`: `ATTRIBUTES_MODEL: ${ATTRIBUTES_MODEL:-qwen}`; rewrite the header comment's qwen sentence: qwen reads the demo users' reviewed answers from the cache and asks the computer's llama-server (through `DOCKER_LLAMA_SERVER_URL`) about new names; without one the health check says `cache_only`. `.env.example`: `ATTRIBUTES_MODEL=qwen`, comment `fake | qwen. qwen (the default here) reads the demo users' reviewed answers from the cache; with no llama-server answering, /api/health says cache_only and new names wait as 待分析. fake never reads them.` Above `LLAMA_SERVER_URL` add: `# qwen accepts only http:// on localhost, 127.0.0.1, [::1] or host.docker.internal, with no path.`

- [ ] **Step 4: Run the tests, expect all to pass**

Run: `.venv/Scripts/python.exe -X utf8 -m unittest tests.test_api_main tests.test_docker_files -v` → OK.

- [ ] **Step 5: Commit**

```bash
git add tests/test_api_main.py tests/test_docker_files.py docker-compose.yml .env.example
git commit -m "feat: make qwen the demo's attribute model now that role 3's module is merged"
```

### Task 2: the backend builds the Qwen adapter from Settings

**Files:**
- Modify: `src/api/backends.py:79-98` (`attribute_backend`)
- Modify: `tests/test_api_backends.py:140-195` (`QwenBackendTests`)
- Modify: `tests/test_api_main.py` (one sub-case)

**Interfaces:**
- Consumes: role 3's `src.ml.attributes.AttributeDescriber(server_url, ...)` (raises `ValueError` for a non-local URL), its `.model_version` and `.describe_items(names, ask_model=True)`; `src.ml.attributes.MODEL_VERSION`.
- Produces: `attribute_backend(settings) -> (name, cache_key, describe_items)` unchanged in shape; for qwen `cache_key == describer.model_version` and `describe_items` is that describer's bound `describe_items`.

- [ ] **Step 1: Write the failing tests** (in `QwenBackendTests`)

`stand_in()` gains `module.AttributeDescriber`: a small class recording `server_url`, with `model_version = "qwen-test:v1"` and `describe_items(self, names, ask_model=True)` returning `[None] * len(names)`; it raises `ValueError("LLAMA_SERVER_URL must be a local HTTP server")` when the host is not local (reuse `urlsplit` like role 3).
- `test_with_the_module_qwen_answers_through_it_and_keys_the_cache_by_its_version`: `attributes_version == "qwen-test:v1"`, the describer was built with `server_url == settings.llama_server_url`, `check_describe(self, backends.describe_items)` passes.
- `test_qwen_with_an_address_that_is_not_local_stops_without_showing_it`: real module; for `http://example.com:8080`, `http://user:secret@127.0.0.1:8080`, `http://127.0.0.1:8080/v1` → `assertRaisesRegex(ValueError, "ATTRIBUTES_MODEL=qwen needs LLAMA_SERVER_URL")`, the message has no `secret`, `example.com` or `/v1`, and no newline. For `http://localhost:8080` and `http://[::1]:8080` `load_backends` succeeds.
- `test_the_real_module_keys_the_cache_the_way_the_seed_writes_it`: real module, `Settings(jwt_secret=SECRET, attributes_model="qwen")`; `attributes_version == src.ml.attributes.MODEL_VERSION`. Then with `mock.patch.object(attributes.AttributeDescriber, "_request", return_value=ANSWER)` where `ANSWER = {"choices": [{"finish_reason": "stop", "message": {"content": json.dumps({"items": [{"id": "i0", "yes": [], "unknown": [], "sugar": None, "fun": None, "species": None}]})}}]}`, `check_describe(self, backends.describe_items)` returns three non-None answers (overview 13.10 item 5).
- In `tests/test_api_main.py` add the sub-case `({"ATTRIBUTES_MODEL": "qwen", "LLAMA_SERVER_URL": "http://example.com:8080"}, "error: ATTRIBUTES_MODEL=qwen needs LLAMA_SERVER_URL")` to `test_a_model_that_is_not_there_yet_stops_it_in_one_line` (rename it `test_a_model_that_cannot_run_stops_it_in_one_line`).

- [ ] **Step 2: Run them, expect failures**

Run: `.venv/Scripts/python.exe -X utf8 -m unittest tests.test_api_backends tests.test_api_main -v`
Expected: the stand-in, not-local and key tests FAIL (the backend still returns the module-level `describe_items`).

- [ ] **Step 3: Implement in `attribute_backend`**

After the import, `describer = attributes.AttributeDescriber(server_url=settings.llama_server_url)`; on `ValueError` raise `ValueError("ATTRIBUTES_MODEL=qwen needs LLAMA_SERVER_URL (DOCKER_LLAMA_SERVER_URL in Docker) to be http:// on localhost, 127.0.0.1, [::1] or host.docker.internal, with no path or password")` `from None` (never the URL). Return `"qwen", describer.model_version, describer.describe_items`. Rewrite the docstring: Settings is the address's only source, checked when the app loads; the key is the describer's version, which with batch size 1 is `MODEL_VERSION`, the key role 3's seed writes.

- [ ] **Step 4: Run, expect pass**

Run: `.venv/Scripts/python.exe -X utf8 -m unittest tests.test_api_backends tests.test_api_main tests.test_api_health tests.test_api_items -v` → OK. (Drop a module from the list if it does not exist.)

- [ ] **Step 5: Commit**

```bash
git add src/api/backends.py tests/test_api_backends.py tests/test_api_main.py
git commit -m "feat: build the Qwen adapter from the settings and stop on an address it would refuse"
```

### Task 3: the Docker demo gets the 300 demo users with their profiles

**Files:**
- Modify: `src/api/container.py:94-121` (`seed_if_empty` → `seed_demo`, `main`)
- Modify: `Dockerfile` (one COPY line after `COPY src ./src`)
- Modify: `.github/workflows/ci.yml` (compose step)
- Modify: `tests/test_container.py:181-260`, `tests/test_docker_files.py`

**Interfaces:**
- Consumes: role 3's `src.api.seed.seed_demo_population(engine, people, context, *, cache_path=None) -> dict` with keys `users, profiles, cache_items, items, added_users, skipped` (raises `ValueError` on a refusal); `build_personas(calendar, total=300)`; `load_context(ROOT)`.
- Produces: `container.seed_demo(engine, demo_mode) -> dict | None` (the seed's summary; `None` when demo mode is off or the seed refused).

- [ ] **Step 1: Write the failing tests**

Replace `SeedTests` (mock `src.api.seed.seed_demo_population` to record its arguments and return `{"users": 300, "added_users": 300, "skipped": False}` unless a test says otherwise):
- `test_demo_mode_seeds_the_300_demo_users_with_the_current_context`: called once with this engine, a list of 300 people, and the context from `load_context(ROOT)` (same `calendar`); returns the summary.
- `test_a_database_with_people_in_it_is_still_seeded_in_demo_mode`: after adding a real `User`, still called once.
- `test_demo_mode_off_seeds_nothing`: returns `None`, not called.
- `test_a_seed_that_refuses_is_one_log_line_and_the_start_goes_on`: side effect `ValueError("first line\nsecond line")`; returns `None`; `assertLogs("src.api.container", "WARNING")` holds one record without `\n` containing `first line second line`.
In `MainTests` patch `seed_demo` instead of `seed_if_empty`; the recorder returns the summary dict; event list unchanged.
In `tests/test_docker_files.py`: the expected COPY list gains `["datasets/synthetic/attribute-cache.jsonl", "./datasets/synthetic/attribute-cache.jsonl"]` after `["src", "./src"]`; add `test_ci_checks_the_demo_has_its_profiles_in_cache_only_mode` requiring each of `cache_only`, `/api/auth/demo-login`, `/api/me/profile`, `pending_attributes` and `== 300` in `ci.yml`, and `seq 1 90` (the longer wait).

- [ ] **Step 2: Run, expect failures**

Run: `.venv/Scripts/python.exe -X utf8 -m unittest tests.test_container tests.test_docker_files -v` → FAIL (`seed_demo` missing, COPY list, CI text).

- [ ] **Step 3: Implement**

`seed_demo(engine, demo_mode)`: in demo mode only, import inside the function (as now), `context = load_context(ROOT)`, return `seed_demo_population(engine, build_personas(context["calendar"], total=300), context)`; on any `Exception` log `log.warning("demo users not updated: %s", " ".join(str(error).split()))` and return `None`. Docstring: runs on every start because the seed skips a complete population and repairs a stale one (new `MODEL_VERSION`, an older image's 40 bare demo users); a refusal must not keep the server from starting, as in `launch.main`. `main()`: `summary = seed_demo(...)`; when it is a dict, `log.info("demo users: %d in all, %d added%s", summary["users"], summary["added_users"], " (already complete)" if summary["skipped"] else "")`. Update the module docstring's "the demo users on an empty database".
`Dockerfile`: `COPY datasets/synthetic/attribute-cache.jsonl ./datasets/synthetic/attribute-cache.jsonl` with a comment: the reviewed fictional answers the demo seed loads (no real names).
`ci.yml` compose step: wait up to 90 attempts (the first start seeds 300 people before serving); then one `python3` stdlib check (urllib) that `/api/health` has `demo_mode` true and `models.attributes == "cache_only"`, `/api/auth/demo-users` lists 300, `POST /api/auth/demo-login` with the first `user_id` gives a token, and `/api/me/profile` with it is `ready` with `pending_attributes == 0`; on failure print `docker compose logs` and exit 1. Keep `timeout-minutes: 15`.

- [ ] **Step 4: Run, expect pass; then one real container seed**

Run: `.venv/Scripts/python.exe -X utf8 -m unittest tests.test_container tests.test_docker_files -v` → OK.
Then, with a Windows path (MSYS paths in `DATABASE_URL` are not converted), call the real thing on a scratch database outside the repository: `container.seed_demo(make_engine("sqlite:///C:/<scratch>/c.db"), True)` twice → first `added_users == 300`, second `skipped is True`; delete that scratch file afterwards.

- [ ] **Step 5: Commit**

```bash
git add src/api/container.py Dockerfile .github/workflows/ci.yml tests/test_container.py tests/test_docker_files.py
git commit -m "feat: seed the Docker demo with the 300 demo users and their profiles on every start"
```

### Task 4: documents

**Files:**
- Modify: `README.md:131-135` (Docker section), `docs/team/overview.md` (new 13.13 at the top of section 13; :30, :112, :222, :335, :341, :728; mark 13.10's checklist items 1, 4–7 done with a pointer to 13.13), `openspec/changes/add-matching-system/design.md:153`, `:210`, `openspec/changes/add-matching-system/tasks.md` (2.15 note, 2.12 note)

- [ ] **Step 1: Write the changes**

Say, dated 10/18: role 3's branch is merged on `role-1/role3-integration` (not main); compose and `.env.example` default to qwen, Settings' default stays fake, an existing `.env` keeps its value (set `ATTRIBUTES_MODEL=qwen` there to see the demo users' attributes; with fake the demo users show their names as 待分析); qwen without llama-server is `cache_only`; the address comes only from `LLAMA_SERVER_URL` (`DOCKER_LLAMA_SERVER_URL` in Docker) and a non-local one stops the server in one line; the container seeds the 300 demo users on every start in demo mode, skipping a complete population, and a refusal is one log line; the image carries `datasets/synthetic/attribute-cache.jsonl`; after a `MODEL_VERSION` change the next start (container) or the next start.bat run reseeds. 13.13 lists what is still open: CI green after a push (2.11, 2.12), bert (role 2), true Qwen run with a GPU, start.bat on a GPU-less PC (2.10), overview numbering 13.11 shared by roles 2 and 3. Keep 2.15 unticked (bert is not wired).

- [ ] **Step 2: Verify**

Run: `OPENSPEC_TELEMETRY=0 /c/Users/User/AppData/Roaming/npm/openspec validate add-matching-system --strict` → valid; `git diff --check` → nothing.

- [ ] **Step 3: Commit**

```bash
git add README.md docs/team/overview.md openspec/changes/add-matching-system/design.md openspec/changes/add-matching-system/tasks.md
git commit -m "docs: record qwen as the demo default, the settings-built adapter and the 300-person Docker demo"
```

### Final check (after all tasks)

Run the whole suite: `.venv/Scripts/python.exe -X utf8 -W error -m unittest discover -s tests` → OK with 0 failures (role 3's merge brought it to 506 with one known failure; that failure is fixed in Task 1); `node --test "tests/*.test.cjs"` → 82 pass; OpenSpec strict valid; `git diff --check 783dfd4 HEAD`.
