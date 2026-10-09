# 品味特質連線圖 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 連線頁改成像神經網路的星雲圖：兩人各自的 46 個消費訊號連到 18 格品味特質，同一格特質在兩人之間相連，線的粗細與顏色就是推力與加減分；相似度改用原本的向量（不減平均），大字分數全站統一成品味相似度，綜合解讀配上每項特質的俏皮話。

**Architecture:** Python 的 `traits.explain` 算出每個人的向量、每個訊號對每項特質的推力與量測值，`build.py` 只算一次並嵌入配對頁（`matchReportData`）與連線頁（`traitNetworkData`）。新的 `trait-network.js` 是純函式：版面位置、標籤避讓、說明列與綜合解讀的文字、資料檢查；`taste-comparison.html` 只負責把結果畫成 SVG、切換「品味特質｜品項細節」與處理點選。配對頁的門檻改用畫面上的整數百分比，相反名單改成 −10%。

**Tech Stack:** Python 3.10+ 標準函式庫（`unittest`）、原生 JavaScript、Node.js `node:test`

**Spec:** `docs/superpowers/specs/2026-10-09-trait-network-design.md`

## Global Constraints

- Python 只用標準函式庫；`pyproject.toml` 不變。
- 不讀取、不修改 `data/` 底下任何檔案（私人資料）。執行 `python scripts/build_report.py` 會寫入 `data/processed/report-data.js`（公開示範版的輸出），這是允許的；絕不使用 `--private`。
- 根目錄的 `report-data.js` 與 `*.csv` 是私人檔案，絕不加入 Git。每個任務只 `git add` 該任務列出的檔案，不要用 `git add -A` 或 `git add .`。
- 測試只用虛構名稱（「示範」「測試」開頭，或小安、小宇、小林與 40 位虛構用戶）。
- `src/web/` 只改本計畫列出的檔案：`trait-similarity.js`、`match-filter.js`、`match.html`、`taste-profile.js`、`taste-comparison.html`，以及新增的 `trait-network.js`。
- 報告維持單一 HTML 檔、沒有外部資源。
- 程式碼與文字照本計畫逐字輸入。百分比的負號是 U+2212（−），程式裡一律寫成 `String.fromCharCode(0x2212)`，不要換成連字號。
- 改檔一律用編輯工具（Edit／Write）。不要用 shell 的 heredoc、`sed` 或 `echo` 寫入含反斜線（`\`）的程式碼：這個環境的 shell 會把反斜線吃掉一半。
- 編號清單裡的程式碼區塊，為了 Markdown 格式整段多縮排了 3 個空格；貼進檔案時去掉這 3 格，其餘縮排照抄（Python 的縮排有意義）。不在清單裡的程式碼區塊照原樣貼上。
- 在 `feature/taste-traits` 分支工作；不要 push。
- Commit 訊息用英文，結尾一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 指令都在專案根目錄用 Git Bash 執行：
  - 全部 Python 測試：`python -m unittest discover -s tests`
  - 單一檔：`python -m unittest tests.test_traits -v`
  - Node 測試：`node --test tests/*.test.cjs`；單一檔：`node --test tests/trait-network.test.cjs`
- 根目錄的 `invoice-insights.html` 是產生出來的示範報告，`tests/match-page.test.cjs` 會讀它。改到會被嵌入報告的檔案（`src/web/*`、`configs/traits.json`、`src/receipt/build.py`）的任務，最後都要執行 `python scripts/build_report.py`，並把 `invoice-insights.html` 一起 commit。
- Git 在 Windows 上會提示「LF will be replaced by CRLF」，可以忽略。

## 試做結果（已在專案副本逐任務驗證）

- 每個任務結束時的測試數：

  | 任務後 | Python | Node |
  |---|---|---|
  | 開始前 | 55 | 40 |
  | Task 1 | 55 | 40 |
  | Task 2 | 61 | 40 |
  | Task 3 | 59 | 41 |
  | Task 4 | 60 | 41 |
  | Task 5 | 61 | 41 |
  | Task 6 | 61 | 55 |
  | Task 7、8 | 61 | 55 |

- `python scripts/build_report.py` 印出三行，Task 3 起最後一行變成：
  ```text
  2026-03 50 rows; total 7910
  2026-04 53 rows; total 8095
  taste similarity to 40 fictional people: highest 71%, median 14%, lowest -12%
  ```
- 示範配對頁：合拍「14 位品味相似度 +30% 以上，顯示前 5 位。」手搖學生 B（+71%）、A（+71%）、C（+67%）、咖啡上班族 D（+40%）、E（+40%）；同一區是手搖學生 B、A、C、D（+32%）、E（+32%）；相反「6 位品味相似度 −10% 以下，顯示前 5 位。」省錢上班族 D、E（−12%）、C、A、B（−11%）。你的品味特質「偏好好吃飯・偏避開連假・偏香甜」「也有運動、生活小物、3C 的紀錄」。
- 連線頁（點第一張卡片手搖學生 B）：大字 +71，「依 17 項品味特質計算 · 虛構示範」；臭味相投「都偏好好吃飯（加 32 分）— 吃飯這件事，從不將就。」；背道而馳「沒有扣分的特質 — 難得這麼合拍。」；圖上 85 條訊號線、15 條中間的線。點左邊「飲料甜度」，說明列三行：「你：飲料甜度 約 8 分糖，往「香甜」推 0.61」「手搖學生 B：飲料甜度 約 10 分糖，往「香甜」推 0.80」「「清爽 ↔ 香甜」這一格：你偏香甜 0.70、手搖學生 B 偏香甜 0.93，加 21 分 — 糖分補給，雙人同行。」
- 朋友比較預設小安 × 小宇 +80%；背道而馳「小安偏清爽，小宇偏香甜（扣 6 分）— 一個加糖，一個讓糖罐放假。」貼上自己匯出的連結後，大字「—」，品味特質按鈕停用。
- 報告從約 232 KB 變成約 277 KB；`matchReportData` 約 33 KB、`traitNetworkData` 約 10 KB。

## 檔案結構

| 檔案 | 動作 | 責任 |
|---|---|---|
| `src/web/trait-similarity.js` | 修改 | 共用的 `signed`（+71%、−12%、0%） |
| `src/receipt/traits.py` | 修改 | `trait_parts`、`explain`、`population`、`signal_ids`；刪除減平均的 `typical`、`relative`、`population_vectors` |
| `configs/traits.json` | 修改 | 相反門檻 `opposite_score`；每個訊號的 `label`、`unit`；兩端型 `short`；每項特質的 `lines`；`readout` |
| `src/receipt/build.py` | 修改 | 只算一次；原本的向量；推力與訊號值；緊湊 JSON；`traitNetworkData`；連線頁嵌入三個程式 |
| `src/web/match-filter.js` | 修改 | 用整數百分比比門檻；相反門檻；「你的品味特質」新寫法；`phrase` 可帶名字；公開 `words` |
| `src/web/match.html` | 修改 | 「怎麼算的？」改寫；卡片把兩人的品味資料交給連線頁 |
| `src/web/trait-network.js` | 新增 | 版面、標籤、說明列、綜合解讀、資料檢查（純函式） |
| `src/web/taste-profile.js` | 修改 | `fromPair` 不再需要分數，交出品味資料 |
| `src/web/taste-comparison.html` | 修改 | 切換、星雲圖、點選、大字分數、綜合解讀 |
| `tests/test_traits.py`、`tests/test_personas.py`、`tests/test_build_report.py` | 修改 | 對應的 Python 測試 |
| `tests/trait-similarity.test.cjs`、`tests/match-filter.test.cjs`、`tests/match-page.test.cjs`、`tests/taste-profile.test.cjs` | 修改 | 對應的 Node 測試 |
| `tests/trait-network.test.cjs` | 新增 | `trait-network.js` 的測試 |
| `invoice-insights.html` | 重新產生 | 公開示範版 |
| `docs/superpowers/handoffs/2026-10-08-taste-traits-stage1.md` | 修改 | 記錄第②輪（Task 9） |

---

### Task 1: 共用的正負號百分比

**Files:**
- Modify: `src/web/trait-similarity.js`
- Modify: `src/web/match-filter.js`
- Modify: `src/web/match.html`
- Test: `tests/trait-similarity.test.cjs`、`tests/match-filter.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Produces: `TraitSimilarity.signed(score) -> string`（`'+71%'`、`'−12%'`、`'0%'`；整數部分用 `percent`，半數進位）。`MatchFilter` 不再匯出 `signed`。

- [ ] **Step 1: Write the failing test**

在 `tests/trait-similarity.test.cjs` 把第 5 行

```js
const { compare, percent } = require('../src/web/trait-similarity.js');
```

換成

```js
const { compare, percent, signed } = require('../src/web/trait-similarity.js');
```

並在檔案最後加上：

```js

test('signed shows the whole percentage with a plus or a true minus sign', () => {
  const MINUS = String.fromCharCode(0x2212);
  assert.equal(signed(0.7101), '+71%');
  assert.equal(signed(-0.1197), MINUS + '12%');
  assert.equal(signed(0), '0%');
  assert.equal(signed(-0.004), '0%');
  assert.equal(signed(0.625), '+63%');
});
```

在 `tests/match-filter.test.cjs`：第 3 行的 `const { RANGES, signed, pick,` 改成 `const { RANGES, pick,`，並刪掉整個測試 `test('scores read +62%, −42% and 0%, halves rounding up', () => { … });`（連同它後面的空行）。

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/trait-similarity.test.cjs`
Expected: FAIL，`signed is not a function`

- [ ] **Step 3: Write minimal implementation**

`src/web/trait-similarity.js`：把

```js
  // Whole percentage, rounding halves up like percent() in similarity.py.
  const percent = score => Math.floor(score * 100 + 0.5);
  const api = Object.freeze({ compare, percent });
```

換成

```js
  // Whole percentage, rounding halves up like percent() in similarity.py.
  const percent = score => Math.floor(score * 100 + 0.5);
  const MINUS = String.fromCharCode(0x2212);  // the minus sign, not a hyphen
  // +71%, −12% or 0%: the whole percentage with its sign, as every page shows a similarity.
  function signed(score) {
    const whole = percent(score);
    return (whole > 0 ? '+' : whole < 0 ? MINUS : '') + Math.abs(whole) + '%';
  }
  const api = Object.freeze({ compare, percent, signed });
```

`src/web/match-filter.js`：
1. 刪掉這一行：

   ```js
     const MINUS = String.fromCharCode(0x2212);  // the minus sign, not a hyphen
   ```

2. 刪掉整個函式（連同它前面的註解與後面的空行）：

   ```js
     // +62%, −42% or 0%, rounding halves up as percent() does.
     function signed(score) {
       const whole = similarity.percent(score);
       return (whole > 0 ? '+' : whole < 0 ? MINUS : '') + Math.abs(whole) + '%';
     }
   ```

3. 在 `const byName = (a, b) => (a < b ? -1 : a > b ? 1 : 0);` 的下一行加上：

   ```js
     const signed = similarity.signed;
   ```

4. 最後的匯出 `const api = Object.freeze({ RANGES, signed, scored, pick, phrase, reasons, mine, status, view });` 改成 `const api = Object.freeze({ RANGES, scored, pick, phrase, reasons, mine, status, view });`。

`src/web/match.html`：`const signed = MatchFilter.signed;` 改成 `const signed = TraitSimilarity.signed;`。

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/*.test.cjs`
Expected: 40 tests pass

- [ ] **Step 5: Regenerate the report**

Run: `python scripts/build_report.py`
Expected: 最後一行仍是 `taste similarity to 40 fictional people: highest 62%, median 8%, lowest -42%`

Run: `node --test tests/*.test.cjs`
Expected: 40 tests pass

- [ ] **Step 6: Commit**

```bash
git add src/web/trait-similarity.js src/web/match-filter.js src/web/match.html tests/trait-similarity.test.cjs tests/match-filter.test.cjs invoice-insights.html
git commit -m "refactor: share the signed percentage from trait-similarity" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 每個訊號推了多少（`explain` 與 `population`）

這個任務只新增功能，示範結果不變；舊的 `typical`、`relative`、`population_vectors` 留到 Task 3 才刪。

**Files:**
- Modify: `src/receipt/traits.py`
- Test: `tests/test_traits.py`

**Interfaces:**
- Consumes: `signals.measure(rows, period, context)`、既有的 `push`、`reaches`
- Produces:
  - `traits.trait_parts(trait, measured) -> (value | None, list[float | None])`：推力對齊該特質 `signals` 的順序；特質為 `None` 時推力全是 `None`；量測不到的訊號推力是 `None`；兩端型總和為 0 時回傳 `(0.0, 未除分母的推力)`
  - `traits.trait_value(trait, measured)`：等於 `trait_parts(...)[0]`，數值和原本完全相同
  - `traits.explain(rows, period, context) -> None | {"vector": list, "pushes": list[list], "signals": dict}`：資料不足（沒有月份或有效品項少於 `min_items`）時 `None`
  - `traits.build_vector(rows, period, context)`：等於 `explain(...)["vector"]`，資料不足時 `None`
  - `traits.population(people, period, context) -> dict[str, dict | None]`：依名字回傳每個人的 `explain`；名字重複拋出 `ValueError`

- [ ] **Step 1: Write the failing tests**

`tests/test_traits.py`：把開頭的 import 區

```python
"""Taste traits on small fictional purchase sets, one behaviour at a time."""
import unittest
from datetime import date
from pathlib import Path

from src.receipt.signals import calendar_days, category_counts
from src.receipt.traits import between, build_vector, load_context, population_vectors, relative, trait_value, typical
```

換成

```python
"""Taste traits on small fictional purchase sets, one behaviour at a time."""
import json
import unittest
from datetime import date
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.personas import build_friends, build_personas
from src.receipt.signals import calendar_days, category_counts
from src.receipt.traits import (between, build_vector, dated, explain, load_context, population, population_vectors, relative,
                                trait_parts, trait_value, typical)
```

並在 `class CategoryCountTests(unittest.TestCase):` 的前面加上：

```python
class ExplainTests(unittest.TestCase):
    def test_each_trait_is_the_sum_of_its_signal_pushes(self):
        catalog = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
        rows, period = dated(build_demo(catalog))
        people = [*build_personas(CONTEXT["calendar"]), *build_friends(CONTEXT["calendar"]), {"name": "我", "rows": rows}]
        for name, person in population(people, period, CONTEXT).items():
            for trait, value, pushes in zip(TRAITS, person["vector"], person["pushes"]):
                with self.subTest(name=name, trait=trait["id"]):
                    self.assertEqual(len(pushes), len(trait["signals"]))
                    if value is None:
                        self.assertEqual(pushes, [None] * len(pushes))
                    else:
                        self.assertAlmostEqual(sum(push for push in pushes if push is not None), value, delta=1e-9)

    def test_a_thin_trait_pushes_nothing_and_an_unmeasured_signal_pushes_none(self):
        person = explain(bought(lunches()), PERIOD, CONTEXT)
        self.assertIsNone(person["vector"][INDEX["holiday"]])
        self.assertEqual(person["pushes"][INDEX["holiday"]], [None])
        # Twenty lunches and no drinks: the share of premium drinks cannot be measured.
        self.assertIsNone(person["signals"]["premium_drink_share"])
        self.assertEqual(person["pushes"][INDEX["spend"]], [-0.625, 0.0, None])
        self.assertEqual(set(person["signals"]), {signal["id"] for trait in TRAITS for signal in trait["signals"]})

    def test_one_signal_pushes_two_traits(self):
        person = explain(bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME)), PERIOD, CONTEXT)
        for trait_id, sign in (("meals", -1), ("motive", 1)):
            ids = [signal["id"] for signal in TRAITS[INDEX[trait_id]]["signals"]]
            self.assertGreater(sign * person["pushes"][INDEX[trait_id]][ids.index("weekday_quick_share")], 0, trait_id)

    def test_level_traits_are_only_pushed_up(self):
        person = explain(bought(lunches(), (WORKDAYS[20:24], "測試貓飼料", 8, 400, "測試寵物店", HOME)), PERIOD, CONTEXT)
        for trait, pushes in zip(TRAITS, person["pushes"]):
            if trait["kind"] == "level":
                self.assertTrue(all(push is None or push >= 0 for push in pushes), trait["id"])
        self.assertGreater(person["vector"][INDEX["pets_cat"]], 0)

    def test_pushes_that_cancel_out_leave_the_trait_at_zero(self):
        motive = TRAITS[INDEX["motive"]]
        measured = {"counts": {"store_food_items": 8}, "constants": {},
                    "signals": {"store_clearance_share": 0.2, "weekday_quick_share": 0.3}}
        self.assertEqual(trait_parts(motive, measured), (0.0, [-0.25, 0.25]))

    def test_too_little_data_explains_nothing_and_names_must_be_unique(self):
        self.assertIsNone(explain([], [], CONTEXT))
        self.assertIsNone(explain(bought(lunches(19)), PERIOD, CONTEXT))
        people = [{"name": "測試甲", "rows": bought(lunches())}, {"name": "測試乙", "rows": bought(lunches(19))}]
        explained = population(people, PERIOD, CONTEXT)
        self.assertEqual(list(explained), ["測試甲", "測試乙"])
        self.assertEqual(explained["測試甲"]["vector"], build_vector(people[0]["rows"], PERIOD, CONTEXT))
        self.assertIsNone(explained["測試乙"])
        with self.assertRaises(ValueError):
            population([*people, {"name": "測試甲", "rows": []}], PERIOD, CONTEXT)


```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_traits -v`
Expected: FAIL，`ImportError: cannot import name 'explain'`

- [ ] **Step 3: Write minimal implementation**

`src/receipt/traits.py`：把整個 `def trait_value(trait, measured):` 到 `def build_vector(...)` 結束（`return [trait_value(trait, measured) for trait in settings["traits"]]` 那一行）為止，換成：

```python
def trait_parts(trait, measured):
    """A trait and how far each of its signals pushed it, in the trait's signal order.

    Signals that cannot be measured push nothing (None) and hand their weight to the rest; a trait
    without enough data is None, and so is every push.
    """
    signals, counts, constants = measured["signals"], measured["counts"], measured["constants"]
    nothing = (None, [None] * len(trait["signals"]))
    if any(counts[name] < minimum for name, minimum in trait.get("requires", {}).items()):
        return nothing
    raw = [None if signals[signal["id"]] is None else signal["weight"] * push(signals[signal["id"]], signal, constants)
           for signal in trait["signals"]]
    available = [signal for signal, value in zip(trait["signals"], raw) if value is not None]
    if not available:
        return nothing
    total = sum(value for value in raw if value is not None)
    if trait["kind"] == "level":
        scale = sum(signal["weight"] for signal in available)
    elif total == 0:
        return 0.0, raw
    else:
        # Divide by what the available signals could reach on this side, so both ends stay reachable.
        direction = 1 if total > 0 else -1
        scale = sum(signal["weight"] for signal in available if reaches(signal, direction))
    return total / scale, [None if value is None else value / scale for value in raw]


def trait_value(trait, measured):
    """A trait from its signals; signals that cannot be measured hand their weight to the rest."""
    return trait_parts(trait, measured)[0]


def explain(rows, period, context):
    """One person's taste: the vector, each signal's push on each trait, and the measured signals.

    None when the person has too little data at all.
    """
    if not period:
        return None
    settings = context["traits"]
    measured = measure(rows, period, context)
    if measured["counts"]["items"] < settings["min_items"]:
        return None
    parts = [trait_parts(trait, measured) for trait in settings["traits"]]
    return {"vector": [value for value, _ in parts], "pushes": [pushes for _, pushes in parts],
            "signals": measured["signals"]}


def build_vector(rows, period, context):
    """One value per trait (None where data is thin), or None when the person has too little data at all."""
    explained = explain(rows, period, context)
    return None if explained is None else explained["vector"]


def population(people, period, context):
    """Everyone's explained taste by name, None for those with too little data; names must be unique."""
    names = [person["name"] for person in people]
    if len(set(names)) != len(names):
        raise ValueError("Every person needs a unique name")
    return {person["name"]: explain(person["rows"], period, context) for person in people}
```

（`similarity_model`、`typical`、`relative`、`population_vectors` 這一步都不動。）

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests`
Expected: 61 tests OK

Run: `python scripts/build_report.py && git status --short`
Expected: 最後一行仍是 `highest 62%, median 8%, lowest -42%`；`git status` 只有 `src/receipt/traits.py`、`tests/test_traits.py` 與未追蹤的 `report-data.js`（`invoice-insights.html` 不變）

- [ ] **Step 5: Commit**

```bash
git add src/receipt/traits.py tests/test_traits.py
git commit -m "feat: explain how far each signal pushes each taste trait" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 3: 配對改用原本的向量，相反門檻 −10%

**Files:**
- Modify: `src/receipt/traits.py`
- Modify: `configs/traits.json`
- Modify: `src/receipt/build.py`
- Modify: `src/web/match-filter.js`
- Modify: `src/web/match.html`
- Test: `tests/test_traits.py`、`tests/test_personas.py`、`tests/test_build_report.py`、`tests/match-filter.test.cjs`、`tests/match-page.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 2 的 `traits.explain`、`traits.population`；Task 1 的 `TraitSimilarity.signed`
- Produces:
  - `traits.json` 的 `"match": {"min_score": 0.3, "opposite_score": 0.1, "top": 5}`；`matchReportData.settings` 因此多了 `opposite_score`
  - `build.vector_of(explained) -> list | None`
  - `build.build_matches(rows, months, people, tastes, me, context, regions, is_demo)`：`tastes` 是 `population(...)` 的結果、`me` 是「我」的 `explain`
  - `build.taste_summary(me, people, tastes, context) -> list[float]`（由低到高，「我」資料不足時是空的）
  - `matchReportData.traits[]`：有 `group` 的特質帶上 `group`
  - `MatchFilter.pick` 用 `percent` 比門檻：合拍 `percent(score) >= percent(min_score)`，相反 `percent(score) <= percent(-opposite_score)`；排序仍用未四捨五入的分數
  - `MatchFilter.mine(...)`：`lean` 不再有「跟一般人比：」字首，都不明顯時是「品味特質還不明顯」

- [ ] **Step 1: Write the failing tests**

`tests/test_traits.py`：
1. import 區改成：

   ```python
   from src.receipt.traits import between, build_vector, dated, explain, load_context, population, trait_parts, trait_value
   ```

2. `self.assertEqual(CONTEXT["traits"]["match"], {"min_score": 0.3, "top": 5})` 改成：

   ```python
           self.assertEqual(CONTEXT["traits"]["match"], {"min_score": 0.3, "opposite_score": 0.1, "top": 5})
   ```

3. 刪掉整個 `class TypicalTests(unittest.TestCase):`（兩個測試，直到 `if __name__ == "__main__":` 之前）。

`tests/test_personas.py`：
1. `from src.receipt.traits import build_vector, dated, load_context, population_vectors, relative, similarity_model` 改成：

   ```python
   from src.receipt.traits import dated, explain, load_context, population, similarity_model
   ```

2. `setUpClass` 裡的

   ```python
           vectors = population_vectors(cls.people, list(PERIOD), CONTEXT, extra=cls.friends)
           cls.raw, cls.vectors = vectors["raw"], vectors["relative"]
           rows, period = dated(build_demo(CATALOG))
           cls.me = relative(build_vector(rows, period, CONTEXT), vectors["centers"])
   ```

   換成

   ```python
           tastes = population([*cls.people, *cls.friends], list(PERIOD), CONTEXT)
           cls.vectors = {name: taste["vector"] for name, taste in tastes.items()}
           rows, period = dated(build_demo(CATALOG))
           cls.me = explain(rows, period, CONTEXT)["vector"]
   ```

3. 其他地方的 `self.raw` 都改成 `self.vectors`（共四處）：
   - `self.assertTrue(all(self.raw[name] is not None for name in self.raw))` 改成 `self.assertTrue(all(vector is not None for vector in self.vectors.values()))`
   - `value = self.raw[name][INDEX[trait]]` 改成 `value = self.vectors[name][INDEX[trait]]`
   - `self.assertGreaterEqual(self.raw[name][INDEX["pets_dog"]], 0.5, name)` 改成 `self.assertGreaterEqual(self.vectors[name][INDEX["pets_dog"]], 0.5, name)`
   - `self.assertGreaterEqual(self.raw[name][INDEX["pets_cat"]], 0.5, name)` 改成 `self.assertGreaterEqual(self.vectors[name][INDEX["pets_cat"]], 0.5, name)`
4. 把

   ```python
       def test_clearance_shoppers_and_rice_ball_eaters_both_live_at_the_convenience_store_but_differ(self):
   ```

   改成

   ```python
       def test_clearance_shoppers_and_rice_ball_eaters_both_live_at_the_convenience_store_but_do_not_match(self):
   ```

   並把它裡面的 `self.assertLess(self.score(name, other), 0, (name, other))` 改成：

   ```python
                   self.assertLess(self.score(name, other), CONTEXT["traits"]["match"]["min_score"], (name, other))
   ```

5. `test_me_has_a_clear_match_and_a_clear_opposite` 裡的 `self.assertLessEqual(scored[0][0], -0.3)` 改成：

   ```python
           self.assertLessEqual(scored[0][0], -CONTEXT["traits"]["match"]["opposite_score"])
   ```

`tests/test_build_report.py`：`self.assertEqual(payload["settings"], {"min_score": 0.3, "top": 5, "min_items": 20})` 改成：

```python
            self.assertEqual(payload["settings"], {"min_score": 0.3, "opposite_score": 0.1, "top": 5, "min_items": 20})
```

`tests/match-filter.test.cjs`：
1. `const settings = { min_score: 0.3, top: 5, min_items: 20 };` 改成 `const settings = { min_score: 0.3, opposite_score: 0.1, top: 5, min_items: 20 };`
2. 把整個測試 `test('the opposite list mirrors it at −30% or less, most opposite first', () => { … });` 換成：

   ```js
   test('the opposite list keeps people at −10% or less, most opposite first', () => {
     const entries = [entry('A', -0.1), entry('B', -0.5), entry('C', -0.09), entry('D', 0.8), entry('E', -0.5)];
     const result = pick(entries, settings, true, null);
     assert.equal(result.eligible, 3);
     assert.deepEqual(names(result.shown), ['B', 'E', 'A']);
   });

   test('the bar is the printed whole percentage: +30% is in and +29% is out, likewise −10% and −9%', () => {
     const entries = [entry('A', 0.2966), entry('B', 0.2949), entry('C', -0.0951), entry('D', -0.0949)];
     assert.deepEqual(names(pick(entries, settings, false, null).shown), ['A']);
     assert.deepEqual(names(pick(entries, settings, true, null).shown), ['C']);
   });
   ```

3. 測試 `my traits list up to three leanings past 0.2, then the habits on record` 裡：
   - `{ lean: '跟一般人比：偏香甜・偏待在生活圈・偏喜歡嘗鮮', habits: '也有養貓的紀錄' }` 改成 `{ lean: '偏香甜・偏待在生活圈・偏喜歡嘗鮮', habits: '也有養貓的紀錄' }`
   - `{ lean: '跟一般人差不多', habits: '' }` 改成 `{ lean: '品味特質還不明顯', habits: '' }`
4. 測試 `the page lists matches, and opposites only when asked` 裡：
   - `{ lean: '跟一般人比：偏享受・偏香甜・偏常出遊', habits: '也有養貓的紀錄' }` 改成 `{ lean: '偏享受・偏香甜・偏常出遊', habits: '也有養貓的紀錄' }`
   - `'1 位品味相似度 ' + MINUS + '30% 以下。'` 改成 `'1 位品味相似度 ' + MINUS + '10% 以下。'`
5. 測試 `the page explains an empty distance, missing home districts, nobody close and thin data` 裡：
   - `'這個距離內沒有品味相似度 ' + MINUS + '30% 以下的人，試試放寬距離。'` 改成 `'這個距離內沒有品味相似度 ' + MINUS + '10% 以下的人，試試放寬距離。'`
   - `'目前沒有和你明顯相反的人（' + MINUS + '30% 以下）。'` 改成 `'目前沒有和你明顯相反的人（' + MINUS + '10% 以下）。'`

`tests/match-page.test.cjs`：把從 `test('the demo lists the three sweet-toothed students and two holiday travellers', () => {` 到檔案結尾的三個測試，換成：

```js
test('the demo lists the three sweet-toothed students and two coffee lovers', () => {
  const shown = view(data, { range: null, opposite: false });
  assert.equal(shown.match.status, '14 位品味相似度 +30% 以上，顯示前 5 位。');
  assert.deepEqual(summary(shown.match.cards), [['手搖學生 B', '+71%'], ['手搖學生 A', '+71%'], ['手搖學生 C', '+67%'],
    ['咖啡上班族 D', '+40%'], ['咖啡上班族 E', '+40%']]);
  const [first, , , fourth] = shown.match.cards;
  assert.deepEqual([first.alike, first.unlike, first.place], ['都偏好好吃飯', null, '高雄市苓雅區']);
  assert.deepEqual([fourth.alike, fourth.unlike, fourth.place], ['都偏好好吃飯', '你偏省錢，對方偏享受', '臺北市信義區']);
  assert.deepEqual(shown.mine, { lean: '偏好好吃飯・偏避開連假・偏香甜', habits: '也有運動、生活小物、3C 的紀錄' });
  assert.equal(shown.note, '你的生活圈：高雄市苓雅區、高雄市新興區');
});

test('within the same district all five students remain', () => {
  const shown = view(data, { range: 0, opposite: false });
  assert.equal(shown.match.status, '5 位品味相似度 +30% 以上。');
  assert.deepEqual(summary(shown.match.cards), [['手搖學生 B', '+71%'], ['手搖學生 A', '+71%'], ['手搖學生 C', '+67%'],
    ['手搖學生 D', '+32%'], ['手搖學生 E', '+32%']]);
  assert.equal(shown.match.cards[3].unlike, '你偏香甜，對方偏清爽');
});

test('the opposite list is the thrifty office workers', () => {
  const shown = view(data, { range: null, opposite: true });
  assert.equal(shown.opposite.status, '6 位品味相似度 ' + MINUS + '10% 以下，顯示前 5 位。');
  assert.deepEqual(summary(shown.opposite.cards), [['省錢上班族 D', MINUS + '12%'], ['省錢上班族 E', MINUS + '12%'],
    ['省錢上班族 C', MINUS + '11%'], ['省錢上班族 A', MINUS + '11%'], ['省錢上班族 B', MINUS + '11%']]);
  assert.ok(shown.opposite.cards.every(card => card.alike === '都偏省錢' && card.unlike === '你偏香甜，對方偏清爽'));
  // They pass 同一區 through their second home district, so the card shows that one.
  assert.ok(shown.opposite.cards.every(card => card.place === '高雄市苓雅區'));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s tests`
Expected: FAIL（`test_traits` 的設定、`test_personas` 讀不到 `opposite_score`、`test_build_report` 的 `settings`）

Run: `node --test tests/match-filter.test.cjs`
Expected: FAIL（相反門檻與「你的品味特質」的文字）

- [ ] **Step 3: Write minimal implementation**

`src/receipt/traits.py`：刪掉檔案最後的 `typical`、`relative`、`population_vectors` 三個函式（從 `def typical(vectors, settings):` 到檔案結尾），讓 `similarity_model` 成為最後一個函式。

`configs/traits.json`：第 4 行改成：

```json
  "match": {"min_score": 0.3, "opposite_score": 0.1, "top": 5},
```

`src/receipt/build.py`：
1. import 區：

   ```python
   from .personas import PERIOD, build_friends, build_personas
   ```

   改成

   ```python
   from .personas import PERIOD, build_personas
   ```

   並把 `from .traits import build_vector, dated, load_context, population_vectors, relative, similarity_model` 改成：

   ```python
   from .traits import dated, explain, load_context, population, similarity_model
   ```

2. `trait_words` 換成：

   ```python
   def trait_words(settings):
       """How the match page names each trait: its two ends, or the short word for a habit, and its group if any."""
       words = []
       for trait in settings["traits"]:
           entry = {"id": trait["id"], "name": trait["name"], "kind": trait["kind"]}
           entry.update({"ends": trait["ends"]} if trait["kind"] == "two_sided" else {"habit": trait["habit"]})
           if "group" in trait:
               entry["group"] = trait["group"]
           words.append(entry)
       return words
   ```

3. 把整個 `def build_matches(months, population, context, regions, is_demo):` 與 `def taste_summary(months, population, friends, context):` 換成：

   ```python
   def vector_of(explained):
       """The taste vector of an explain() result, or None when the person had too little data."""
       return None if explained is None else explained["vector"]


   def build_matches(rows, months, people, tastes, me, context, regions, is_demo):
       """Everyone's taste vector for the match page to score in the browser."""
       settings = context["traits"]
       mine = areas_of(rows, context)
       entries = []
       for person in people:
           areas = areas_of(person["rows"], context)
           entries.append({"name": person["name"], "vector": vector_of(tastes[person["name"]]),
                           "distance": distance(mine, areas, regions), "place": closest_area(mine, areas, regions),
                           "counts": category_counts(person["rows"])})
       return {
           "isDemo": is_demo, "population": len(entries),
           "personaMonths": [f"{year}-{month:02}" for year, month in PERIOD],
           "model": similarity_model(settings), "traits": trait_words(settings),
           "settings": {**settings["match"], "min_items": settings["min_items"]},
           "me": {"vector": vector_of(me), "months": sorted(months), "areas": mine, "counts": category_counts(rows)},
           "people": entries,
       }


   def taste_summary(me, people, tastes, context):
       """My similarity to each fictional person, lowest first; empty when I have too little data."""
       if me is None:
           return []
       model = similarity_model(context["traits"])
       scores = [compare(me["vector"], vector_of(tastes[person["name"]]), model)["score"] for person in people]
       return sorted(score for score in scores if score is not None)
   ```

4. `main()` 裡的

   ```python
       context = load_context(ROOT)
       population = build_personas(context["calendar"])
       matches = build_matches(months, population, context, load_regions(ROOT), not args.private)
   ```

   換成

   ```python
       context = load_context(ROOT)
       people = build_personas(context["calendar"])
       # Everyone's taste is worked out once, here, and shared by the match page and the summary below.
       tastes = population(people, list(PERIOD), context)
       rows, period = dated(months)
       me = explain(rows, period, context)
       matches = build_matches(rows, months, people, tastes, me, context, load_regions(ROOT), not args.private)
   ```

5. `main()` 最後的

   ```python
       me, scores = taste_summary(months, population, build_friends(context["calendar"]), context)
       if me is None or not scores:
   ```

   換成

   ```python
       scores = taste_summary(me, people, tastes, context)
       if not scores:
   ```

`src/web/match-filter.js`：
1. 把

   ```js
     // People past the threshold on one side, then within the chosen distance; strongest first, ties by name.
     function pick(entries, settings, opposite, range) {
       const eligible = entries.filter(entry => (opposite ? entry.score <= -settings.min_score : entry.score >= settings.min_score));
   ```

   換成

   ```js
     // The bar on one side, as the whole percentage the page prints: +30% for matches, −10% for opposites.
     const bar = (settings, opposite) => (opposite ? -settings.opposite_score : settings.min_score);

     // People past the bar on one side, then within the chosen distance; strongest first, ties by name.
     // The bar is checked on the printed whole percentage, so a card reading +30% is always on the list.
     function pick(entries, settings, opposite, range) {
       const line = similarity.percent(bar(settings, opposite));
       const eligible = entries.filter(entry => (opposite ? similarity.percent(entry.score) <= line : similarity.percent(entry.score) >= line));
   ```

2. `// My three most distinctive two-sided traits (at least 0.2 from the average) and the habits on record.` 改成 `// My three strongest two-sided leanings (at least 0.2 either way) and the habits on record.`
3. 把

   ```js
       if (!leaning.length && !habits.length) return { lean: '跟一般人差不多', habits: '' };
       return { lean: leaning.length ? '跟一般人比：' + leaning.join('・') : '', habits: habits.length ? words('也有', habits.join('、'), '的紀錄') : '' };
   ```

   換成

   ```js
       if (!leaning.length && !habits.length) return { lean: '品味特質還不明顯', habits: '' };
       return { lean: leaning.join('・'), habits: habits.length ? words('也有', habits.join('、'), '的紀錄') : '' };
   ```

4. `status` 裡的 `const line = signed(opposite ? -settings.min_score : settings.min_score) + (opposite ? ' 以下' : ' 以上');` 改成：

   ```js
       const line = signed(bar(settings, opposite)) + (opposite ? ' 以下' : ' 以上');
   ```

`src/web/match.html`：把

```js
  const signed = TraitSimilarity.signed;
  $('method').append(
    make('p', '每個人的發票先整理成 17 項品味特質（18 格），例如「省錢 ↔ 享受」「清爽 ↔ 香甜」「運動投入」。兩端型特質減去 '
      + data.population + ' 位虛構用戶的平均，表示跟一般人比偏哪一邊。'),
```

換成

```js
  const signed = TraitSimilarity.signed;
  // Traits that share a group, such as cats and dogs, count as one.
  const traitCount = new Set(data.traits.map(trait => trait.group ?? trait.id)).size;
  $('method').append(
    make('p', '每個人的發票先整理成 ' + traitCount + ' 項品味特質（' + data.traits.length
      + ' 格），例如「省錢 ↔ 享受」「清爽 ↔ 香甜」「運動投入」。兩端型特質看偏向哪一端，程度型特質看有多投入。'),
```

並把 `+ signed(-settings.min_score) + ' 以下的人。'),` 改成 `+ signed(-settings.opposite_score) + ' 以下的人。'),`。

- [ ] **Step 4: Run tests and regenerate the report**

Run: `python -m unittest discover -s tests`
Expected: 59 tests OK

Run: `python scripts/build_report.py`
Expected: 最後一行 `taste similarity to 40 fictional people: highest 71%, median 14%, lowest -12%`

Run: `node --test tests/*.test.cjs`
Expected: 41 tests pass

- [ ] **Step 5: Commit**

```bash
git add src/receipt/traits.py configs/traits.json src/receipt/build.py src/web/match-filter.js src/web/match.html tests/test_traits.py tests/test_personas.py tests/test_build_report.py tests/match-filter.test.cjs tests/match-page.test.cjs invoice-insights.html
git commit -m "feat: match on raw taste vectors with a -10% opposite bar" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 推力與訊號值嵌入配對資料、緊湊 JSON

**Files:**
- Modify: `src/receipt/traits.py`
- Modify: `src/receipt/build.py`
- Test: `tests/test_traits.py`、`tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 3 的 `build_matches`、`vector_of`
- Produces:
  - `traits.signal_ids(settings) -> list[str]`：46 個訊號各一次，依第一次出現在特質裡的順序
  - `build.rounded(value)`：遞迴四捨五入到小數 4 位，`-0.0` 變成 `0.0`
  - `build.drawing_of(explained, order) -> {"pushes": ..., "signals": [...]}`：`signals` 依 `order` 排成陣列；`explained` 是 `None` 時兩者都是 `None`
  - `matchReportData` 的 `me` 與每個 `people[]` 多了 `pushes`、`signals`
  - `script_constant` 一律輸出緊湊 JSON

- [ ] **Step 1: Write the failing tests**

`tests/test_traits.py`：import 區改成

```python
from src.receipt.traits import (between, build_vector, dated, explain, load_context, population, signal_ids, trait_parts,
                                trait_value)
```

並在 `ExplainTests` 的 `def test_too_little_data_explains_nothing_and_names_must_be_unique(self):` 前面加上：

```python
    def test_signals_are_listed_once_in_the_order_they_first_appear(self):
        ids = signal_ids(CONTEXT["traits"])
        self.assertEqual(len(ids), 46)
        self.assertEqual(len(set(ids)), 46)
        self.assertEqual(ids[:7], ["meal_cost", "clearance_share", "premium_drink_share", "store_meal_share",
                                   "weekday_quick_share", "shop_meal_share", "store_clearance_share"])

```

`tests/test_build_report.py`（第一個測試 `test_default_build_ignores_private_sources_and_preserves_private_html`）：
1. `self.assertIn('"isDemo": true', html)` 改成 `self.assertIn('"isDemo":true', html)`
2. `self.assertIn('"district": "高雄市苓雅區"', html)` 改成 `self.assertIn('"district":"高雄市苓雅區"', html)`
3. 把

   ```python
               payload = json.loads(re.search(r"const matchReportData = (.*?);\n</script>", match_page, re.S).group(1))
               self.assertTrue(payload["isDemo"])
   ```

   換成

   ```python
               text = re.search(r"const matchReportData = (.*?);\n</script>", match_page, re.S).group(1)
               # Compact JSON: no indentation and no space after a colon.
               self.assertNotIn("\n", text)
               self.assertNotIn('": ', text)
               # Rounded pushes of nothing are written as 0.0, never -0.0.
               self.assertIsNone(re.search(r"-0\.0(?!\d)", text))
               payload = json.loads(text)
               self.assertTrue(payload["isDemo"])
   ```

4. 把

   ```python
               self.assertEqual(set(payload["me"]), {"vector", "months", "areas", "counts"})
               self.assertEqual(len(payload["people"]), 40)
               for person in payload["people"]:
                   self.assertEqual(set(person), {"name", "vector", "distance", "place", "counts"})
                   self.assertEqual((len(person["vector"]), len(person["counts"])), (18, 10))
   ```

   換成

   ```python
               self.assertEqual(set(payload["me"]), {"vector", "pushes", "signals", "months", "areas", "counts"})
               self.assertEqual(len(payload["people"]), 40)
               traits = json.loads((ROOT / "configs" / "traits.json").read_text(encoding="utf-8"))["traits"]
               for person in [payload["me"], *payload["people"]]:
                   self.assertEqual([len(pushes) for pushes in person["pushes"]], [len(trait["signals"]) for trait in traits])
                   self.assertEqual(len(person["signals"]), 46)
               for person in payload["people"]:
                   self.assertEqual(set(person), {"name", "vector", "pushes", "signals", "distance", "place", "counts"})
                   self.assertEqual((len(person["vector"]), len(person["counts"])), (18, 10))
   ```

第二個測試 `test_build_from_another_directory_is_self_contained_and_repeatable`：
1. `self.assertIn('"amount": 30', html)` 改成 `self.assertIn('"amount":30', html)`
2. 把

   ```python
               self.assertIsNone(payload["me"]["vector"])
               self.assertEqual(set(payload["me"]), {"vector", "months", "areas", "counts"})
   ```

   換成

   ```python
               self.assertEqual([payload["me"][key] for key in ("vector", "pushes", "signals")], [None, None, None])
               self.assertEqual(set(payload["me"]), {"vector", "pushes", "signals", "months", "areas", "counts"})
   ```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_traits tests.test_build_report -v`
Expected: FAIL，`cannot import name 'signal_ids'`；`test_build_report` 也失敗（還沒有緊湊格式與新欄位）

- [ ] **Step 3: Write minimal implementation**

`src/receipt/traits.py`：在 `def similarity_model(settings):` 前面加上：

```python
def signal_ids(settings):
    """Every signal once, in the order it first appears among the traits; embedded signal lists follow it."""
    ids = []
    for trait in settings["traits"]:
        ids += [signal["id"] for signal in trait["signals"] if signal["id"] not in ids]
    return ids


```

`src/receipt/build.py`：
1. `from .traits import dated, explain, load_context, population, similarity_model` 改成：

   ```python
   from .traits import dated, explain, load_context, population, signal_ids, similarity_model
   ```

2. `script_constant` 的前兩行

   ```python
       # A product name must not be able to introduce an HTML script element.
       payload = json.dumps(value, ensure_ascii=False, indent=2).replace("<", "\\u003c")
   ```

   改成（只改註解與 `indent=2` 那個參數，`replace` 不動）：

   ```python
       # Compact JSON keeps the single-file report small; a product name must not be able to introduce a script element.
       payload = json.dumps(value, ensure_ascii=False, separators=(",", ":")).replace("<", "\\u003c")
   ```

3. 在 `vector_of` 後面加上：

   ```python


   def rounded(value):
       """Four decimals, through lists and dicts: pushes and signals only draw lines and fill sentences."""
       if isinstance(value, dict):
           return {key: rounded(item) for key, item in value.items()}
       if isinstance(value, list):
           return [rounded(item) for item in value]
       # Adding 0.0 turns -0.0 into 0.0, so a push of nothing never prints as negative.
       return round(value, 4) + 0.0 if isinstance(value, float) else value


   def drawing_of(explained, order):
       """What the network graph draws for one person: each signal's push on each trait, and the measured signals
       listed in signal_ids() order so their names are not repeated for everyone."""
       if explained is None:
           return {"pushes": None, "signals": None}
       return {"pushes": rounded(explained["pushes"]), "signals": [rounded(explained["signals"][key]) for key in order]}
   ```

4. `build_matches` 裡：

   ```python
       settings = context["traits"]
       mine = areas_of(rows, context)
   ```

   改成

   ```python
       settings = context["traits"]
       order = signal_ids(settings)
       mine = areas_of(rows, context)
   ```

   `entries.append({"name": person["name"], "vector": vector_of(tastes[person["name"]]),` 的下一行加上 `**drawing_of(tastes[person["name"]], order),`（縮排與上下兩行對齊），也就是：

   ```python
           entries.append({"name": person["name"], "vector": vector_of(tastes[person["name"]]),
                           **drawing_of(tastes[person["name"]], order),
                           "distance": distance(mine, areas, regions), "place": closest_area(mine, areas, regions),
                           "counts": category_counts(person["rows"])})
   ```

   並把 `"me": {"vector": vector_of(me), "months": sorted(months), "areas": mine, "counts": category_counts(rows)},` 換成：

   ```python
           "me": {"vector": vector_of(me), **drawing_of(me, order), "months": sorted(months), "areas": mine,
                  "counts": category_counts(rows)},
   ```

- [ ] **Step 4: Run tests and regenerate the report**

Run: `python scripts/build_report.py`
Expected: 最後一行不變（`highest 71%, median 14%, lowest -12%`）

Run: `python -m unittest discover -s tests`
Expected: 60 tests OK

Run: `node --test tests/*.test.cjs`
Expected: 41 tests pass

- [ ] **Step 5: Commit**

```bash
git add src/receipt/traits.py src/receipt/build.py tests/test_traits.py tests/test_build_report.py invoice-insights.html
git commit -m "feat: embed each signal's push and measured value for the network graph" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 訊號名稱、俏皮話與連線頁的品味資料

**Files:**
- Modify: `configs/traits.json`
- Modify: `src/receipt/build.py`
- Modify: `src/web/taste-comparison.html`
- Test: `tests/test_traits.py`、`tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 4 的 `signal_ids`、`drawing_of`、`vector_of`；Task 3 的 `trait_words`
- Produces:
  - `traits.json`：每個訊號的 `label`、`unit`（`share`、`sugar`、`money`、`money_month`、`times_month`、`items_month`、`kinds`）；兩端型的 `short`；每項特質的 `lines`（兩端型 `{"both": [左, 右], "split": …}`，程度型 `{"both": …}`）；頂層 `readout`
  - `build.trait_network_data(settings, tastes, friends) -> dict`：`{"model", "traits", "signals", "readout", "friends"}`。`traits[]` 是 `trait_words` 加上 `short`（兩端型）、`lines`、`signals`（訊號 id 陣列）；`signals[]` 依 `signal_ids` 順序，每筆 `{"id", "label", "unit"}`；`friends` 是 `{名字: {"vector", "pushes", "signals"}}`
  - 連線頁嵌入常數 `traitNetworkData`（佔位 `<script src="trait-network-data.js"></script>`）
  - `main()` 的 `tastes` 包含 40 位虛構用戶與小安、小宇、小林

- [ ] **Step 1: Write the failing tests**

`tests/test_traits.py`：在 `class CalendarTests(unittest.TestCase):` 前面加上：

```python
class WordingTests(unittest.TestCase):
    def test_every_signal_has_a_label_and_a_unit_and_every_trait_its_lines(self):
        units = {"share", "sugar", "money", "money_month", "times_month", "items_month", "kinds"}
        seen = {}
        for trait in TRAITS:
            for signal in trait["signals"]:
                with self.subTest(signal=signal["id"]):
                    self.assertIn(signal["unit"], units)
                    self.assertLessEqual(len(signal["label"]), 6)
                    # A signal shared by two traits reads the same in both.
                    self.assertEqual(seen.setdefault(signal["id"], (signal["label"], signal["unit"])), (signal["label"], signal["unit"]))
            with self.subTest(trait=trait["id"]):
                if trait["kind"] == "two_sided":
                    self.assertTrue(trait["short"])
                    self.assertEqual(len(trait["lines"]["both"]), 2)
                    self.assertTrue(trait["lines"]["split"])
                else:
                    self.assertIsInstance(trait["lines"]["both"], str)
        labels = [label for label, _ in seen.values()]
        self.assertEqual(len(labels), len(set(labels)))
        self.assertEqual(CONTEXT["traits"]["readout"], {"no_alike": "共同話題還在找。", "no_unlike": "難得這麼合拍。"})


```

`tests/test_build_report.py`：在第一個測試的 `self.assertIn("receipt-taste/categories-v1", comparison)` 下一行加上：

```python
            self.assertIn('data-source="trait-network-data.js"', comparison)
            network = json.loads(re.search(r"const traitNetworkData = (.*?);\n</script>", comparison, re.S).group(1))
            self.assertEqual(set(network), {"model", "traits", "signals", "readout", "friends"})
            self.assertEqual(len(network["traits"]), 18)
            self.assertEqual(len(network["signals"]), 46)
            self.assertEqual(set(network["signals"][0]), {"id", "label", "unit"})
            self.assertEqual(network["traits"][4]["lines"]["split"], "一個加糖，一個讓糖罐放假。")
            self.assertEqual(list(network["friends"]), ["小安", "小宇", "小林"])
            for friend in network["friends"].values():
                self.assertEqual(set(friend), {"vector", "pushes", "signals"})
                self.assertEqual((len(friend["vector"]), len(friend["signals"])), (18, 46))
            self.assertNotIn("示範", json.dumps(network, ensure_ascii=False))
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_traits tests.test_build_report -v`
Expected: FAIL，`KeyError: 'unit'`；`test_build_report` 找不到 `trait-network-data.js`

- [ ] **Step 3: Write minimal implementation**

`configs/traits.json`：整個檔案換成：

```json
{
  "min_items": 20,
  "similarity": {"shrink": 0.25, "min_shared_two_sided": 5},
  "match": {"min_score": 0.3, "opposite_score": 0.1, "top": 5},
  "readout": {"no_alike": "共同話題還在找。", "no_unlike": "難得這麼合拍。"},
  "traits": [
    {"id": "spend", "name": "省錢 ↔ 享受", "ends": ["省錢", "享受"], "short": "花費", "kind": "two_sided", "weight": 1,
     "requires": {"food_items": 10},
     "lines": {"both": ["精打細算，錢包同盟。", "對自己好，從不打折。"], "split": "一個看價錢，一個看心情。"},
     "signals": [
       {"id": "meal_cost", "weight": 0.5, "scale": [100, 200, 300], "label": "每餐花費", "unit": "money"},
       {"id": "clearance_share", "weight": 0.3, "toward": -1, "full": 0.3, "label": "即期食品", "unit": "share"},
       {"id": "premium_drink_share", "weight": 0.2, "toward": 1, "full": 0.5, "label": "百元飲料", "unit": "share"}
     ]},
    {"id": "meals", "name": "快速解決 ↔ 好好吃飯", "ends": ["快速解決", "好好吃飯"], "short": "吃飯", "kind": "two_sided", "weight": 1,
     "requires": {"meal_items": 8},
     "lines": {"both": ["五分鐘吃完，效率一百分。", "吃飯這件事，從不將就。"], "split": "一個在趕路，一個在等上菜。"},
     "signals": [
       {"id": "store_meal_share", "weight": 0.4, "toward": -1, "full": 0.8, "label": "超商正餐", "unit": "share"},
       {"id": "weekday_quick_share", "weight": 0.3, "toward": -1, "full": 0.6, "label": "平日固定速食", "unit": "share"},
       {"id": "shop_meal_share", "weight": 0.3, "toward": 1, "full": 0.8, "label": "餐廳正餐", "unit": "share"}
     ]},
    {"id": "motive", "name": "超商：省錢 ↔ 省時", "ends": ["為了省錢", "為了省時"], "short": "超商動機", "kind": "two_sided", "weight": 1,
     "requires": {"store_food_items": 8},
     "lines": {"both": ["即期區的老朋友。", "超商是續命補給站。"], "split": "同一家超商，不同的理由。"},
     "signals": [
       {"id": "store_clearance_share", "weight": 0.5, "toward": -1, "full": 0.4, "label": "超商即期", "unit": "share"},
       {"id": "weekday_quick_share", "weight": 0.5, "toward": 1, "full": 0.6, "label": "平日固定速食", "unit": "share"}
     ]},
    {"id": "cooking", "name": "外食 ↔ 自己煮", "ends": ["外食", "自己煮"], "short": "下廚", "kind": "two_sided", "weight": 1,
     "requires": {"food_items": 10},
     "lines": {"both": ["廚房是裝飾，外食是日常。", "冰箱滿滿，鍋鏟不閒。"], "split": "一個在家開伙，一個在外覓食。"},
     "signals": [
       {"id": "fresh_share", "weight": 0.5, "toward": 1, "full": 0.4, "label": "生鮮食材", "unit": "share"},
       {"id": "ready_meal_share", "weight": 0.3, "toward": -1, "full": 0.6, "label": "現成餐點", "unit": "share"},
       {"id": "kitchen_per_month", "weight": 0.2, "toward": 1, "full": 2, "label": "廚房用品", "unit": "items_month"}
     ]},
    {"id": "sweet", "name": "清爽 ↔ 香甜", "ends": ["清爽", "香甜"], "short": "甜度", "kind": "two_sided", "weight": 1,
     "requires": {"known_sugar_drinks": 3},
     "lines": {"both": ["無糖派，清爽到底。", "糖分補給，雙人同行。"], "split": "一個加糖，一個讓糖罐放假。"},
     "signals": [
       {"id": "sugar_mean", "weight": 0.8, "scale": [0, 0.3, 1], "label": "飲料甜度", "unit": "sugar"},
       {"id": "dessert_share", "weight": 0.2, "toward": 1, "full": 0.3, "label": "甜點", "unit": "share"}
     ]},
    {"id": "routine", "name": "固定習慣 ↔ 喜歡嘗鮮", "ends": ["固定習慣", "喜歡嘗鮮"], "short": "新鮮感", "kind": "two_sided", "weight": 1,
     "requires": {"items": 20},
     "lines": {"both": ["老地方、老樣子，最安心。", "新店開幕，都想搶第一。"], "split": "一個點老樣子，一個點新口味。"},
     "signals": [
       {"id": "repeat_rate", "weight": 0.4, "scale": [0.7, 0.45, 0.2], "label": "重複購買", "unit": "share"},
       {"id": "shop_focus", "weight": 0.3, "scale": [0.8, 0.55, 0.3], "label": "常去店家", "unit": "share"},
       {"id": "new_shop_share", "weight": 0.3, "scale": [0.2, 0.4, 0.6], "label": "新店家", "unit": "share"}
     ]},
    {"id": "sport", "name": "運動投入", "habit": "運動", "kind": "level", "weight": 1,
     "lines": {"both": "流汗也有伴。"},
     "signals": [
       {"id": "sport_visits", "weight": 0.6, "toward": 1, "full": 8, "label": "運動消費", "unit": "times_month"},
       {"id": "sport_supplies", "weight": 0.25, "toward": 1, "full": 4, "label": "運動補給", "unit": "items_month"},
       {"id": "sport_gear", "weight": 0.15, "toward": 1, "full": 1, "label": "運動裝備", "unit": "items_month"}
     ]},
    {"id": "driving", "name": "自己開車騎車", "habit": "開車騎車", "kind": "level", "weight": 1,
     "lines": {"both": "油錢停車費，都不陌生。"},
     "signals": [
       {"id": "fuel_visits", "weight": 0.6, "toward": 1, "full": 4, "label": "加油", "unit": "times_month"},
       {"id": "parking_visits", "weight": 0.25, "toward": 1, "full": 4, "label": "停車", "unit": "times_month"},
       {"id": "car_care", "weight": 0.15, "toward": 1, "full": 1, "label": "汽機車保養", "unit": "items_month"}
     ]},
    {"id": "travel", "name": "待在生活圈 ↔ 常出遊", "ends": ["待在生活圈", "常出遊"], "short": "出遊", "kind": "two_sided", "weight": 1,
     "requires": {"district_invoices": 10},
     "lines": {"both": ["家附近就是全世界。", "行李箱常備，說走就走。"], "split": "一個守著巷口，一個奔向遠方。"},
     "signals": [
       {"id": "away_share", "weight": 0.5, "scale": [0, 0.1, 0.3], "label": "外地消費", "unit": "share"},
       {"id": "stays", "weight": 0.3, "toward": 1, "full": 1, "label": "住宿", "unit": "times_month"},
       {"id": "long_trips", "weight": 0.2, "toward": 1, "full": 2, "label": "長途交通", "unit": "times_month"}
     ]},
    {"id": "stock", "name": "囤貨 ↔ 少量即買", "ends": ["囤貨", "少量即買"], "short": "囤貨", "kind": "two_sided", "weight": 1,
     "requires": {"daily_items": 3},
     "lines": {"both": ["量販推車，一推就滿。", "用完再買，櫃子清爽。"], "split": "一個整箱扛，一個買一包。"},
     "signals": [
       {"id": "convenience_share", "weight": 0.5, "scale": [0, 0.5, 1], "label": "超商買日用品", "unit": "share"},
       {"id": "bulk_share", "weight": 0.3, "toward": -1, "full": 0.5, "label": "大包裝", "unit": "share"},
       {"id": "small_daily_visits", "weight": 0.2, "toward": 1, "full": 4, "label": "小額日用品", "unit": "times_month"}
     ]},
    {"id": "lifestyle", "name": "生活質感小物", "habit": "生活小物", "kind": "level", "weight": 1,
     "lines": {"both": "生活要有點小確幸。"},
     "signals": [
       {"id": "home_items", "weight": 0.4, "toward": 1, "full": 2, "label": "居家小物", "unit": "items_month"},
       {"id": "stationery_items", "weight": 0.3, "toward": 1, "full": 2, "label": "文具", "unit": "items_month"},
       {"id": "select_visits", "weight": 0.3, "toward": 1, "full": 2, "label": "選物店", "unit": "times_month"}
     ]},
    {"id": "tech", "name": "3C 投入", "habit": "3C", "kind": "level", "weight": 1,
     "lines": {"both": "新規格一出，雙雙心動。"},
     "signals": [
       {"id": "tech_items", "weight": 0.4, "toward": 1, "full": 3, "label": "3C 件數", "unit": "items_month"},
       {"id": "tech_spend", "weight": 0.4, "toward": 1, "full": 3000, "label": "3C 花費", "unit": "money_month"},
       {"id": "tech_visits", "weight": 0.2, "toward": 1, "full": 2, "label": "3C 門市", "unit": "times_month"}
     ]},
    {"id": "days", "name": "上班日型 ↔ 休假日型", "ends": ["上班日型", "休假日型"], "short": "假日", "kind": "two_sided", "weight": 1,
     "requires": {"invoices": 10},
     "lines": {"both": ["上班日的錢包最忙。", "平日存著，假日再花。"], "split": "花錢的日子剛好錯開。"},
     "signals": [
       {"id": "offday_invoice_share", "weight": 0.6, "scale": [0, "offday_share", "offday_double"], "label": "假日消費次數", "unit": "share"},
       {"id": "offday_amount_share", "weight": 0.4, "scale": [0, "offday_share", "offday_double"], "label": "假日消費金額", "unit": "share"}
     ]},
    {"id": "holiday", "name": "避開連假 ↔ 連假出遊", "ends": ["避開連假", "連假出遊"], "short": "連假", "kind": "two_sided", "weight": 1,
     "requires": {"trip_days": 2, "long_holidays": 1},
     "lines": {"both": ["連假人擠人？不去。", "連假一到，人就不見。"], "split": "一個連假出門，一個連假顧家。"},
     "signals": [
       {"id": "holiday_trip_share", "weight": 1, "scale": [0, "long_holiday_share", 1], "label": "連假出遊", "unit": "share"}
     ]},
    {"id": "fun", "name": "娛樂體驗", "habit": "娛樂", "kind": "level", "weight": 1,
     "lines": {"both": "看展看戲，都不缺席。"},
     "signals": [
       {"id": "fun_visits", "weight": 0.7, "toward": 1, "full": 4, "label": "娛樂消費", "unit": "times_month"},
       {"id": "fun_kinds", "weight": 0.3, "toward": 1, "full": 4, "label": "娛樂種類", "unit": "kinds"}
     ]},
    {"id": "pets_cat", "name": "有養寵物（貓）", "habit": "養貓", "group": "有養寵物", "kind": "level", "weight": 1,
     "lines": {"both": "都有主子要伺候。"},
     "signals": [
       {"id": "pet_food_cat", "weight": 0.6, "toward": 1, "full": 2, "label": "貓食", "unit": "items_month"},
       {"id": "pet_supply_cat", "weight": 0.25, "toward": 1, "full": 1, "label": "貓用品", "unit": "items_month"},
       {"id": "pet_visits_cat", "weight": 0.15, "toward": 1, "full": 1, "label": "寵物店（貓）", "unit": "times_month"}
     ]},
    {"id": "pets_dog", "name": "有養寵物（狗）", "habit": "養狗", "group": "有養寵物", "kind": "level", "weight": 1,
     "lines": {"both": "散步路線可以一起走。"},
     "signals": [
       {"id": "pet_food_dog", "weight": 0.6, "toward": 1, "full": 2, "label": "狗食", "unit": "items_month"},
       {"id": "pet_supply_dog", "weight": 0.25, "toward": 1, "full": 1, "label": "狗用品", "unit": "items_month"},
       {"id": "pet_visits_dog", "weight": 0.15, "toward": 1, "full": 1, "label": "寵物店（狗）", "unit": "times_month"}
     ]},
    {"id": "alcohol", "name": "小酌", "habit": "小酌", "kind": "level", "weight": 1,
     "lines": {"both": "下班後，來一杯。"},
     "signals": [
       {"id": "alcohol_items", "weight": 0.7, "toward": 1, "full": 8, "label": "酒類", "unit": "items_month"},
       {"id": "bar_visits", "weight": 0.3, "toward": 1, "full": 4, "label": "酒吧", "unit": "times_month"}
     ]}
  ]
}
```

`src/receipt/build.py`：
1. `from .personas import PERIOD, build_personas` 改成 `from .personas import PERIOD, build_friends, build_personas`
2. 在 `def taste_summary(me, people, tastes, context):` 前面加上：

   ```python
   def trait_network_data(settings, tastes, friends):
       """What the connection page needs to draw the network graph by itself: the model, every trait with its
       words, lines and signal ids, every signal's label and unit, the readout fallbacks, and the three demo friends."""
       order = signal_ids(settings)
       labels = {}
       traits = trait_words(settings)
       for entry, trait in zip(traits, settings["traits"]):
           if "short" in trait:
               entry["short"] = trait["short"]
           entry["lines"] = trait["lines"]
           entry["signals"] = [signal["id"] for signal in trait["signals"]]
           for signal in trait["signals"]:
               labels.setdefault(signal["id"], {"id": signal["id"], "label": signal["label"], "unit": signal["unit"]})
       return {
           "model": similarity_model(settings), "traits": traits, "signals": [labels[key] for key in order],
           "readout": settings["readout"],
           "friends": {friend["name"]: {"vector": vector_of(tastes[friend["name"]]), **drawing_of(tastes[friend["name"]], order)}
                       for friend in friends},
       }


   ```

3. `main()` 裡的

   ```python
       comparison = (WEB / "taste-comparison.html").read_text(encoding="utf-8")
       comparison = embed_scripts(comparison, {"taste-profile.js": scripts["taste-profile.js"]})
       html = embed_page(html, "taste-page-source", comparison)
       context = load_context(ROOT)
       people = build_personas(context["calendar"])
       # Everyone's taste is worked out once, here, and shared by the match page and the summary below.
       tastes = population(people, list(PERIOD), context)
   ```

   換成

   ```python
       context = load_context(ROOT)
       people = build_personas(context["calendar"])
       friends = build_friends(context["calendar"])
       # Everyone's taste is worked out once, here, and shared by both pages and the summary below.
       tastes = population([*people, *friends], list(PERIOD), context)
       comparison = embed_scripts((WEB / "taste-comparison.html").read_text(encoding="utf-8"), {
           "taste-profile.js": scripts["taste-profile.js"],
           "trait-network-data.js": script_constant("traitNetworkData", trait_network_data(context["traits"], tastes, friends))})
       html = embed_page(html, "taste-page-source", comparison)
   ```

`src/web/taste-comparison.html`：`<script src="taste-profile.js"></script>` 的下一行加上：

```html
<script src="trait-network-data.js"></script>
```

- [ ] **Step 4: Run tests and regenerate the report**

Run: `python scripts/build_report.py`
Expected: 最後一行不變

Run: `python -m unittest discover -s tests`
Expected: 61 tests OK

Run: `node --test tests/*.test.cjs`
Expected: 41 tests pass

- [ ] **Step 5: Commit**

```bash
git add configs/traits.json src/receipt/build.py src/web/taste-comparison.html tests/test_traits.py tests/test_build_report.py invoice-insights.html
git commit -m "feat: name every signal and give the connection page its network data" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---
### Task 6: 版面與文字的純函式（`trait-network.js`）

**Files:**
- Create: `src/web/trait-network.js`
- Modify: `src/web/match-filter.js`
- Create: `tests/trait-network.test.cjs`
- Test: `tests/match-filter.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: `TraitSimilarity.compare`、`TraitSimilarity.percent`；`MatchFilter.phrase`、`MatchFilter.words`
- Produces（`TraitNetwork`，瀏覽器是全域、Node 是 `require`）：
  - `SHAPES.desktop`、`SHAPES.mobile`：畫布大小、兩把扇子的中心、距離、點大小、字級
  - `validate(person, data) -> {vector, pushes, signals}`（複本），不合格拋出「品味資料不正確，請回配對清單重新選擇。」
  - `layout(data, left, right, mobile) -> {width, height, font, sides, links, cells, result}`：`sides[k].traits[i]` 有 `index, value, angle, distance, hollow, label, r, x, y, labelShown, labelX, labelY, labelAnchor`；`sides[k].signals[j]` 有 `id, order, value, x, y`；`links[]` 是 `{side, signal, trait, push, d}`；`cells[]` 是 `{trait, part, d}`；`result` 是 `TraitSimilarity.compare` 的結果
  - `traitLabel(trait, value)`、`labelRect(text, font, x, y, anchor)`、`formatSignal(value, unit)`、`traitText(trait, value)`
  - `signalSentence(data, person, name, id)`、`cellSentence(data, index, left, right, names, part)`、`readout(data, left, right, names, result) -> {alike, unlike}`、`traitCount(traits)`
  - `MatchFilter.phrase(trait, mine, theirs, names = ['你', '對方'])`；`MatchFilter.words` 公開

`data` 就是 Task 5 的 `traitNetworkData` 格式（`model`、`traits`、`signals`、`readout`）；`person` 是 `{vector, pushes, signals}`。

- [ ] **Step 1: Write the failing tests**

建立 `tests/trait-network.test.cjs`：

```js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const TN = require('../src/web/trait-network.js');
const { percent } = require('../src/web/trait-similarity.js');

// Four traits and six signals are enough to exercise every rule; "quick" feeds two traits, like weekday_quick_share.
const traits = [
  { id: 'sweet', name: '清爽 ↔ 香甜', kind: 'two_sided', ends: ['清爽', '香甜'], short: '甜度', signals: ['sugar_mean', 'dessert_share'],
    lines: { both: ['無糖派，清爽到底。', '糖分補給，雙人同行。'], split: '一個加糖，一個讓糖罐放假。' } },
  { id: 'meals', name: '快速解決 ↔ 好好吃飯', kind: 'two_sided', ends: ['快速解決', '好好吃飯'], short: '吃飯', signals: ['quick', 'shop_meal'],
    lines: { both: ['五分鐘吃完，效率一百分。', '吃飯這件事，從不將就。'], split: '一個在趕路，一個在等上菜。' } },
  { id: 'motive', name: '超商：省錢 ↔ 省時', kind: 'two_sided', ends: ['為了省錢', '為了省時'], short: '超商動機', signals: ['clearance', 'quick'],
    lines: { both: ['即期區的老朋友。', '超商是續命補給站。'], split: '同一家超商，不同的理由。' } },
  { id: 'sport', name: '運動投入', kind: 'level', habit: '運動', signals: ['sport_visits'], lines: { both: '流汗也有伴。' } },
];
const data = {
  model: { cells: traits.map(trait => ({ id: trait.id, kind: trait.kind, weight: 1 })), shrink: 0.25, min_shared_two_sided: 2 },
  traits,
  signals: [{ id: 'sugar_mean', label: '飲料甜度', unit: 'sugar' }, { id: 'dessert_share', label: '甜點', unit: 'share' },
    { id: 'quick', label: '平日固定速食', unit: 'share' }, { id: 'shop_meal', label: '餐廳正餐', unit: 'share' },
    { id: 'clearance', label: '超商即期', unit: 'share' }, { id: 'sport_visits', label: '運動消費', unit: 'times_month' }],
  readout: { no_alike: '共同話題還在找。', no_unlike: '難得這麼合拍。' },
};
const me = { vector: [0.7, 1, null, 0.375], pushes: [[0.61, 0.09], [0, 1], [null, null], [0.375]], signals: [0.8333, 0.1429, 0, 1, null, 5] };
const them = { vector: [0.94, 0.82, 0.5, 0.2], pushes: [[0.8, 0.14], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, 0.2, 0.36, 1, 0.1, 2] };
const light = { ...them, vector: [-0.58, 0.82, 0.5, 0], pushes: [[-0.5, -0.08], [-0.18, 1], [-0.1, 0.6], [0]] };
const shownRects = side => side.traits.filter(trait => trait.labelShown)
  .map(trait => TN.labelRect(trait.label, TN.SHAPES.desktop.font, trait.labelX, trait.labelY, trait.labelAnchor));
const overlap = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

test('validate keeps well-formed taste data and refuses anything else', () => {
  const copy = TN.validate(me, data);
  assert.deepEqual(copy, me);
  assert.notEqual(copy.vector, me.vector);
  const broken = [
    null, { ...me, vector: me.vector.slice(1) }, { ...me, vector: [1.2, 1, null, 0.3] }, { ...me, vector: [0.7, 1, null, -0.1] },
    { ...me, vector: [NaN, 1, null, 0.3] }, { ...me, pushes: [[0.61], [0, 1], [null, null], [0.375]] },
    { ...me, pushes: [[0.61, 'x'], [0, 1], [null, null], [0.375]] }, { ...me, signals: me.signals.slice(1) },
    { ...me, signals: [Infinity, 0, 0, 1, null, 5] },
  ];
  for (const person of broken) assert.throws(() => TN.validate(person, data), /品味資料不正確/);
});

test('the layout is the same every time, left fan on the left and the first trait on top', () => {
  const graph = TN.layout(data, me, them, false);
  assert.deepEqual(TN.layout(data, me, them, false), graph);
  const [a, b] = graph.sides;
  assert.ok(a.traits.every(trait => trait.x < 430) && b.traits.every(trait => trait.x > 770));
  assert.ok(a.traits[0].y < a.traits[3].y);
  for (const side of graph.sides) side.traits.slice(1).forEach((trait, k) => assert.ok(trait.angle < side.traits[k].angle));
  assert.deepEqual([graph.width, graph.height], [1200, 640]);
});

test('a stronger trait sits further out and is bigger; a trait without data is a small hollow dot near the centre', () => {
  const [a, b] = TN.layout(data, me, them, false).sides;
  const { near, far, none, dot } = TN.SHAPES.desktop;
  assert.equal(a.traits[1].distance, far);
  assert.equal(b.traits[3].distance, near + (far - near) * 0.2);
  assert.ok(a.traits[1].r > a.traits[3].r);
  assert.deepEqual([a.traits[2].hollow, a.traits[2].distance, a.traits[2].r], [true, none, dot[0]]);
  assert.equal(b.traits[2].hollow, false);
});

test('a signal feeding two traits is one dot with a line to each, and missing pushes draw no line', () => {
  const graph = TN.layout(data, me, them, false);
  for (const side of graph.sides) assert.equal(side.signals.filter(signal => signal.id === 'quick').length, 1);
  const quick = side => graph.links.filter(link => link.side === side && link.signal === 'quick').map(link => link.trait);
  assert.deepEqual(quick('b'), [1, 2]);
  assert.deepEqual(quick('a'), [1]);
  assert.equal(graph.links.filter(link => link.side === 'a').length, 5);
  assert.ok(graph.links.every(link => /^M[\d.]+ [\d.]+ Q[\d.]+ [\d.]+ [\d.]+ [\d.]+$/.test(link.d)));
});

test('the middle lines are the cells both people have, and they add up to the score', () => {
  const graph = TN.layout(data, me, them, false);
  assert.deepEqual(graph.cells.map(cell => cell.trait), [0, 1, 3]);
  const total = graph.cells.reduce((sum, cell) => sum + cell.part, 0);
  assert.ok(Math.abs(total - graph.result.score) < 1e-12);
  assert.equal(percent(graph.result.score), 83);
});

test('phones stack the fans, the left person on top', () => {
  const graph = TN.layout(data, me, them, true);
  const [a, b] = graph.sides;
  assert.deepEqual([graph.width, graph.height], [600, 820]);
  assert.ok(a.traits.every(trait => trait.y < 290) && b.traits.every(trait => trait.y > 530));
  assert.ok(a.traits[0].x < a.traits[3].x);
});

test('one more trait spreads every direction again, without any code change', () => {
  const extra = { id: 'fun', name: '娛樂體驗', kind: 'level', habit: '娛樂', signals: ['fun_visits'], lines: { both: '看展看戲，都不缺席。' } };
  const bigger = { ...data, traits: [...traits, extra], signals: [...data.signals, { id: 'fun_visits', label: '娛樂消費', unit: 'times_month' }],
    model: { ...data.model, cells: [...data.model.cells, { id: 'fun', kind: 'level', weight: 1 }] } };
  const grow = person => ({ vector: [...person.vector, 0.5], pushes: [...person.pushes, [0.5]], signals: [...person.signals, 2] });
  const before = TN.layout(data, me, them, false).sides[0].traits, after = TN.layout(bigger, grow(me), grow(them), false).sides[0].traits;
  assert.equal(after.length, 5);
  // Neighbours move closer together and the fan still opens the same 78° either way.
  assert.ok(after[0].angle - after[1].angle < before[0].angle - before[1].angle);
  assert.ok(Math.abs(after[0].angle + after[4].angle) < 1e-12 && after[0].angle < 78 * Math.PI / 180);
  after.slice(1).forEach((trait, k) => assert.ok(trait.angle < after[k].angle));
});

test('labels never cover each other, and the strongest trait always keeps its label', () => {
  // Twenty habits at zero crowd the centre of the fan; only the one at 1.0 stands out.
  const crowd = Array.from({ length: 20 }, (_, k) => ({ id: 't' + k, name: '測試' + k, kind: 'level', habit: '測試習慣' + k,
    signals: ['s' + k], lines: { both: '測試。' } }));
  const busy = { ...data, traits: crowd, signals: crowd.map((_, k) => ({ id: 's' + k, label: '訊號' + k, unit: 'share' })),
    model: { ...data.model, cells: crowd.map(trait => ({ id: trait.id, kind: 'level', weight: 1 })), min_shared_two_sided: 0 } };
  const person = { vector: crowd.map((_, k) => (k === 7 ? 1 : 0)), pushes: crowd.map((_, k) => [k === 7 ? 1 : 0]), signals: crowd.map(() => 0) };
  const [a] = TN.layout(busy, person, person, false).sides;
  assert.equal(a.traits[7].labelShown, true);
  assert.ok(a.traits.some(trait => !trait.labelShown));
  const rects = shownRects(a);
  rects.forEach((rect, k) => rects.slice(k + 1).forEach(other => assert.ok(!overlap(rect, other))));
});

test('labels name the end a trait leans to, else its short name or habit', () => {
  assert.equal(TN.traitLabel(traits[0], 0.7), '香甜');
  assert.equal(TN.traitLabel(traits[0], -0.2), '清爽');
  assert.equal(TN.traitLabel(traits[0], 0), '甜度');
  assert.equal(TN.traitLabel(traits[2], null), '超商動機');
  assert.equal(TN.traitLabel(traits[3], 0), '運動');
});

test('each unit reads naturally in the detail line', () => {
  assert.equal(TN.formatSignal(0.381, 'share'), '38%');
  assert.equal(TN.formatSignal(0.8333, 'sugar'), '約 8 分糖');
  assert.equal(TN.formatSignal(125, 'money'), '每餐約 NT$125');
  assert.equal(TN.formatSignal(1200, 'money_month'), '每月約 NT$1,200');
  assert.equal(TN.formatSignal(2.5, 'times_month'), '每月 2.5 次');
  assert.equal(TN.formatSignal(3, 'times_month'), '每月 3 次');
  assert.equal(TN.formatSignal(0.333, 'items_month'), '每月 0.3 件');
  assert.equal(TN.formatSignal(3, 'kinds'), '3 種');
  assert.throws(() => TN.formatSignal(1, 'stars'));
  assert.equal(TN.traitText(traits[0], 0.7), '偏香甜 0.70');
  assert.equal(TN.traitText(traits[0], -0.58), '偏清爽 0.58');
  assert.equal(TN.traitText(traits[0], 0), '0.00');
  assert.equal(TN.traitText(traits[3], 0.375), '0.38');
  assert.equal(TN.traitText(traits[2], null), '資料不足');
});

test('a signal sentence says its value and how far it pushed each trait it feeds', () => {
  assert.equal(TN.signalSentence(data, me, '你', 'sugar_mean'), '你：飲料甜度 約 8 分糖，往「香甜」推 0.61');
  assert.equal(TN.signalSentence(data, them, '對方', 'quick'), '對方：平日固定速食 36%，往「快速解決」推 0.18；往「為了省時」推 0.60');
  assert.equal(TN.signalSentence(data, me, '你', 'quick'), '你：平日固定速食 0%，沒有推動「快速解決 ↔ 好好吃飯」；「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, me, '你', 'clearance'), '你：超商即期，「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, them, '手搖學生 A', 'sport_visits'), '手搖學生 A：運動消費 每月 2 次，往「運動」推 0.20');
  const unmeasured = { ...them, pushes: [[0.8, null], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, null, 0.36, 1, 0.1, 2] };
  assert.equal(TN.signalSentence(data, unmeasured, '對方', 'dessert_share'), '對方：甜點，沒有紀錄');
});

test('a cell sentence gives both values, the points it added or took, and its line', () => {
  const alike = TN.layout(data, me, them, false).result, apart = TN.layout(data, me, light, false).result;
  assert.equal(TN.cellSentence(data, 0, me, them, ['你', '對方'], alike.parts[0]),
    '「清爽 ↔ 香甜」這一格：你偏香甜 0.70、對方偏香甜 0.94，加 ' + percent(alike.parts[0]) + ' 分 — 糖分補給，雙人同行。');
  assert.equal(TN.cellSentence(data, 0, me, light, ['小安', '小宇'], apart.parts[0]),
    '「清爽 ↔ 香甜」這一格：小安偏香甜 0.70、小宇偏清爽 0.58，扣 ' + -percent(apart.parts[0]) + ' 分 — 一個加糖，一個讓糖罐放假。');
  assert.equal(TN.cellSentence(data, 2, me, them, ['你', '對方'], null), '「超商：省錢 ↔ 省時」這一格：你資料不足，這一格不計分');
  assert.equal(TN.cellSentence(data, 2, me, me, ['你', '手搖學生 A'], null), '「超商：省錢 ↔ 省時」這一格：你和手搖學生 A 資料不足，這一格不計分');
  assert.equal(TN.cellSentence(data, 3, me, light, ['你', '對方'], 0), '「運動投入」這一格：你 0.38、對方 0.00，不加也不扣');
  assert.equal(TN.cellSentence(data, 0, me, them, ['你', '對方'], null), '「清爽 ↔ 香甜」這一格：兩人共同的特質太少，無法計分');
});

test('the readout names the cell that adds most and the one that takes most away', () => {
  const alike = TN.layout(data, me, them, false).result;
  assert.deepEqual(TN.readout(data, me, them, ['你', '對方'], alike), {
    alike: '都偏好好吃飯（加 ' + percent(alike.parts[1]) + ' 分）— 吃飯這件事，從不將就。',
    unlike: '沒有扣分的特質 — 難得這麼合拍。' });
  const apart = TN.layout(data, me, light, false).result;
  assert.equal(TN.readout(data, me, light, ['小安', '小宇'], apart).unlike,
    '小安偏香甜，小宇偏清爽（扣 ' + -percent(apart.parts[0]) + ' 分）— 一個加糖，一個讓糖罐放假。');
  const habitOnly = { ...data, model: { ...data.model, min_shared_two_sided: 0 } };
  const sporty = { vector: [null, null, null, 0.5], pushes: [[null, null], [null, null], [null, null], [0.5]], signals: [null, null, null, null, null, 4] };
  const both = TN.layout(habitOnly, sporty, sporty, false).result;
  assert.equal(TN.readout(habitOnly, sporty, sporty, ['你', '對方'], both).alike, '都有運動的紀錄（加 ' + percent(both.parts[3]) + ' 分）— 流汗也有伴。');
  assert.deepEqual(TN.readout(data, me, them, ['你', '對方'], { comparable: false, score: null, parts: null }),
    { alike: '沒有加分的特質 — 共同話題還在找。', unlike: '沒有扣分的特質 — 難得這麼合拍。' });
});

test('cats and dogs count as one trait', () => {
  assert.equal(TN.traitCount([{ id: 'a' }, { id: 'b', group: 'pets' }, { id: 'c', group: 'pets' }]), 2);
});
```

`tests/match-filter.test.cjs`：在 `assert.equal(phrase({ kind: 'level', habit: '3C' }, 0.3, 0.5), '都有 3C 的紀錄');` 的下一行加上：

```js
  // The connection page names both people instead of 你 and 對方, spacing a Latin letter from the Chinese after it.
  assert.equal(phrase(traits[2], 0.61, -0.19, ['小安', '手搖學生 A']), '小安偏常出遊，手搖學生 A 偏待在生活圈');
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/trait-network.test.cjs tests/match-filter.test.cjs`
Expected: FAIL，`Cannot find module '../src/web/trait-network.js'`；`match-filter` 的卡片測試也失敗（名字還是「你／對方」）

- [ ] **Step 3: Write minimal implementation**

建立 `src/web/trait-network.js`：

```js
/* Where the taste network draws every dot and line, and what its sentences say; the page only turns this into SVG. */
(function (root) {
  'use strict';
  const node = typeof module !== 'undefined' && module.exports;
  const similarity = node ? require('./trait-similarity.js') : root.TraitSimilarity;
  const cards = node ? require('./match-filter.js') : root.MatchFilter;

  // Desktop puts the two fans side by side; phones stack them, the left person on top. All sizes are SVG units.
  const SHAPES = Object.freeze({
    desktop: Object.freeze({ width: 1200, height: 640, centers: [[430, 325], [770, 325]], stretch: [1, 0.86],
      near: 110, far: 270, none: 72, ring: 312, stagger: 14, dot: [3.5, 9], font: 13 }),
    mobile: Object.freeze({ width: 600, height: 820, centers: [[300, 290], [300, 530]], stretch: [1, 0.9],
      near: 70, far: 190, none: 46, ring: 228, stagger: 12, dot: [5, 11], font: 18 }),
  });
  const FAN = 78 * Math.PI / 180;      // each fan opens 78° either side of straight out
  const SPREAD = 0.045;                // radians between neighbouring signals of one trait
  const LABEL_STEPS = 3;               // a crowded label moves outwards this many times before it hides
  const PAD = 3;                       // the gap kept around every label

  // Every check a person's taste data must pass before the graph trusts it.
  function validate(person, data) {
    const fail = () => { throw new Error('品味資料不正確，請回配對清單重新選擇。'); };
    const finite = value => typeof value === 'number' && Number.isFinite(value);
    if (!person || typeof person !== 'object') fail();
    const { vector, pushes, signals } = person;
    if (!Array.isArray(vector) || vector.length !== data.traits.length) fail();
    vector.forEach((value, index) => {
      const low = data.traits[index].kind === 'level' ? 0 : -1;
      if (value !== null && (!finite(value) || value < low || value > 1)) fail();
    });
    if (!Array.isArray(pushes) || pushes.length !== data.traits.length) fail();
    pushes.forEach((list, index) => {
      if (!Array.isArray(list) || list.length !== data.traits[index].signals.length
        || list.some(value => value !== null && !finite(value))) fail();
    });
    if (!Array.isArray(signals) || signals.length !== data.signals.length
      || signals.some(value => value !== null && !finite(value))) fail();
    return { vector: [...vector], pushes: pushes.map(list => [...list]), signals: [...signals] };
  }

  // The label a trait wears: the end it leans to, or its short name or habit word.
  function traitLabel(trait, value) {
    if (trait.kind === 'level') return trait.habit;
    if (value === null || value === 0) return trait.short;
    return trait.ends[value > 0 ? 1 : 0];
  }

  // Roughly how wide a label is: a full em for Chinese, a little over half for Latin letters and digits.
  const textWidth = (text, font) => Array.from(text).reduce((sum, letter) => sum + (letter.charCodeAt(0) > 0x2e80 ? 1 : 0.6), 0) * font;

  // The box a label covers, with a small gap around it, for text anchored at (x, y).
  function labelRect(text, font, x, y, anchor) {
    const width = textWidth(text, font), left = anchor === 'end' ? x - width : x;
    return { left: left - PAD, right: left + width + PAD, top: y - font - PAD, bottom: y + PAD };
  }

  const overlaps = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

  // A point d away from a fan's centre at angle e (positive e is the first trait's side), in SVG coordinates.
  function place(shape, side, d, e) {
    const [cx, cy] = shape.centers[side === 'a' ? 0 : 1];
    const [sx, sy] = shape.stretch;
    const out = d * Math.cos(e), across = d * Math.sin(e);
    if (shape === SHAPES.mobile) return { x: cx - across * sx, y: side === 'a' ? cy - out * sy : cy + out * sy };
    return { x: side === 'a' ? cx - out * sx : cx + out * sx, y: cy - across * sy };
  }

  // Each trait's fixed angle: spread evenly in configuration order, the first at the top (on the left on phones).
  const angle = (index, count) => FAN - 2 * FAN * (index + 0.5) / count;

  // Labels go in strongest first; one that would cover a dot or another label moves outwards, then hides.
  function placeLabels(traits, shape, side) {
    const taken = traits.map(trait => ({ left: trait.x - trait.r, right: trait.x + trait.r, top: trait.y - trait.r, bottom: trait.y + trait.r }));
    const strength = trait => (trait.value === null ? -1 : Math.abs(trait.value));
    for (const trait of [...traits].sort((a, b) => strength(b) - strength(a) || a.index - b.index)) {
      trait.labelShown = false;
      for (let step = 0; step <= LABEL_STEPS && !trait.labelShown; step++) {
        const at = place(shape, side, trait.distance + step * shape.font * 1.2, trait.angle);
        let box;
        if (shape === SHAPES.mobile) box = { x: at.x + trait.r + 4, y: at.y + shape.font * 0.35, anchor: 'start' };
        else if (side === 'a') box = { x: at.x - trait.r - 4, y: at.y - 6, anchor: 'end' };
        else box = { x: at.x + trait.r + 4, y: at.y - 6, anchor: 'start' };
        const rect = labelRect(trait.label, shape.font, box.x, box.y, box.anchor);
        if (taken.some(other => overlaps(rect, other))) continue;
        taken.push(rect);
        Object.assign(trait, { labelShown: true, labelX: box.x, labelY: box.y, labelAnchor: box.anchor });
      }
    }
  }

  const fixed = number => number.toFixed(1);

  // Every dot and line of the graph for two people, from the trait order in data and each person's values.
  function layout(data, left, right, mobile) {
    const shape = mobile ? SHAPES.mobile : SHAPES.desktop;
    const count = data.traits.length;
    // A signal sits beside the first trait that lists it; later traits only get another line.
    const home = new Map();
    data.traits.forEach((trait, index) => trait.signals.forEach(id => { if (!home.has(id)) home.set(id, index); }));
    const sides = [['a', left], ['b', right]].map(([side, person]) => {
      const traits = data.traits.map((trait, index) => {
        const value = person.vector[index], e = angle(index, count);
        const distance = value === null ? shape.none : shape.near + (shape.far - shape.near) * Math.abs(value);
        return { index, value, angle: e, distance, hollow: value === null, label: traitLabel(trait, value),
          r: shape.dot[0] + (value === null ? 0 : shape.dot[1] * Math.abs(value)), ...place(shape, side, distance, e) };
      });
      placeLabels(traits, shape, side);
      const signals = data.signals.map((signal, order) => {
        const index = home.get(signal.id);
        const own = data.traits[index].signals.filter(id => home.get(id) === index), slot = own.indexOf(signal.id);
        const e = angle(index, count) + SPREAD * (slot - (own.length - 1) / 2);
        return { id: signal.id, order, value: person.signals[order], ...place(shape, side, shape.ring + shape.stagger * ((index + slot) % 3), e) };
      });
      return { side, traits, signals };
    });
    const links = [];
    sides.forEach((side, k) => {
      const person = k === 0 ? left : right;
      data.traits.forEach((trait, index) => trait.signals.forEach((id, slot) => {
        const push = person.pushes[index][slot];
        if (push === null) return;
        const from = side.signals.find(signal => signal.id === id), to = side.traits[index];
        const bend = side.side === 'a' ? 0.18 : -0.18;
        const mx = (from.x + to.x) / 2 + (to.y - from.y) * bend, my = (from.y + to.y) / 2 - (to.x - from.x) * bend;
        links.push({ side: side.side, signal: id, trait: index, push,
          d: `M${fixed(from.x)} ${fixed(from.y)} Q${fixed(mx)} ${fixed(my)} ${fixed(to.x)} ${fixed(to.y)}` });
      }));
    });
    const result = similarity.compare(left.vector, right.vector, data.model);
    const cells = [];
    data.traits.forEach((trait, index) => {
      const part = result.parts ? result.parts[index] : null;
      if (part === null) return;
      const a = sides[0].traits[index], b = sides[1].traits[index];
      const middle = mobile ? (a.y + b.y) / 2 : (a.x + b.x) / 2;
      const d = mobile
        ? `M${fixed(a.x)} ${fixed(a.y)} C${fixed(a.x)} ${fixed(middle)} ${fixed(b.x)} ${fixed(middle)} ${fixed(b.x)} ${fixed(b.y)}`
        : `M${fixed(a.x)} ${fixed(a.y)} C${fixed(middle)} ${fixed(a.y)} ${fixed(middle)} ${fixed(b.y)} ${fixed(b.x)} ${fixed(b.y)}`;
      cells.push({ trait: index, part, d });
    });
    return { width: shape.width, height: shape.height, font: shape.font, sides, links, cells, result };
  }

  // A measured signal as the detail line reads it.
  function formatSignal(value, unit) {
    const one = number => String(Number(number.toFixed(1)));
    const money = number => 'NT$' + Math.round(number).toLocaleString('en-US');
    switch (unit) {
      case 'share': return Math.round(value * 100) + '%';
      case 'sugar': return '約 ' + Math.round(value * 10) + ' 分糖';
      case 'money': return '每餐約 ' + money(value);
      case 'money_month': return '每月約 ' + money(value);
      case 'times_month': return '每月 ' + one(value) + ' 次';
      case 'items_month': return '每月 ' + one(value) + ' 件';
      case 'kinds': return value + ' 種';
      default: throw new Error('Unknown unit: ' + unit);
    }
  }

  // A trait's value with its direction: 偏香甜 0.70, 0.38 for a habit, or 資料不足.
  function traitText(trait, value) {
    if (value === null) return '資料不足';
    if (trait.kind === 'level' || value === 0) return Math.abs(value).toFixed(2);
    return '偏' + trait.ends[value > 0 ? 1 : 0] + ' ' + Math.abs(value).toFixed(2);
  }

  // Which line fits a cell: both on one end, one on each end, or a habit both have.
  function line(trait, mine, theirs) {
    if (trait.kind === 'level') return trait.lines.both;
    return mine * theirs > 0 ? trait.lines.both[mine > 0 ? 1 : 0] : trait.lines.split;
  }

  const points = part => Math.abs(similarity.percent(part));

  // What one person's signal did: its value, and how far it pushed each trait it feeds.
  function signalSentence(data, person, name, id) {
    const order = data.signals.findIndex(signal => signal.id === id);
    const signal = data.signals[order], value = person.signals[order];
    const effects = [];
    data.traits.forEach((trait, index) => {
      const slot = trait.signals.indexOf(id);
      if (slot < 0) return;
      const push = person.pushes[index][slot];
      if (person.vector[index] === null) effects.push('「' + trait.name + '」資料不足');
      else if (push === null) effects.push('沒有紀錄');
      else if (push === 0) effects.push('沒有推動「' + trait.name + '」');
      else effects.push('往「' + (trait.kind === 'level' ? trait.habit : trait.ends[push > 0 ? 1 : 0]) + '」推 ' + Math.abs(push).toFixed(2));
    });
    const shown = value === null ? '' : ' ' + formatSignal(value, signal.unit);
    return name + '：' + signal.label + shown + '，' + effects.join('；');
  }

  // One cell of the score: both values and what it added or took away, with its line.
  function cellSentence(data, index, left, right, names, part) {
    const trait = data.traits[index], head = '「' + trait.name + '」這一格：';
    const missing = names.filter((name, k) => [left, right][k].vector[index] === null);
    if (missing.length) return head + cards.words(missing.join('和'), '資料不足，這一格不計分');
    if (part === null) return head + '兩人共同的特質太少，無法計分';
    const values = cards.words(names[0], traitText(trait, left.vector[index])) + '、' + cards.words(names[1], traitText(trait, right.vector[index]));
    if (part === 0) return head + values + '，不加也不扣';
    return head + values + '，' + (part > 0 ? '加 ' : '扣 ') + points(part) + ' 分 — ' + line(trait, left.vector[index], right.vector[index]);
  }

  // 臭味相投 and 背道而馳: the cell that adds the most and the one that takes the most away.
  function readout(data, left, right, names, result) {
    let best = null, worst = null;
    (result.parts || []).forEach((part, index) => {
      if (part === null) return;
      if (part > 0 && (best === null || part > result.parts[best])) best = index;
      if (part < 0 && (worst === null || part < result.parts[worst])) worst = index;
    });
    const say = (index, verb) => {
      const trait = data.traits[index], mine = left.vector[index], theirs = right.vector[index];
      return cards.phrase(trait, mine, theirs, names) + '（' + verb + ' ' + points(result.parts[index]) + ' 分）— ' + line(trait, mine, theirs);
    };
    return {
      alike: best === null ? '沒有加分的特質 — ' + data.readout.no_alike : say(best, '加'),
      unlike: worst === null ? '沒有扣分的特質 — ' + data.readout.no_unlike : say(worst, '扣'),
    };
  }

  // How many traits the page talks about: cats and dogs share one group, so 18 cells read as 17 traits.
  const traitCount = traits => new Set(traits.map(trait => trait.group ?? trait.id)).size;

  const api = Object.freeze({ SHAPES, validate, traitLabel, labelRect, layout, formatSignal, traitText, signalSentence,
    cellSentence, readout, traitCount });
  if (node) module.exports = api; else root.TraitNetwork = api;
})(globalThis);
```

`src/web/match-filter.js`：把

```js
  // How one cell reads on a card: a habit both have, both on one side, or opposite sides.
  function phrase(trait, mine, theirs) {
    if (trait.kind === 'level') return words('都有', trait.habit, '的紀錄');
    if (mine * theirs > 0) return '都偏' + end(trait, mine);
    return '你偏' + end(trait, mine) + '，對方偏' + end(trait, theirs);
  }
```

換成

```js
  // How one cell reads: a habit both have, both on one side, or opposite sides; cards call the two 你 and 對方.
  function phrase(trait, mine, theirs, names = ['你', '對方']) {
    if (trait.kind === 'level') return words('都有', trait.habit, '的紀錄');
    if (mine * theirs > 0) return '都偏' + end(trait, mine);
    return words(names[0], '偏' + end(trait, mine)) + '，' + words(names[1], '偏' + end(trait, theirs));
  }
```

並把匯出改成 `const api = Object.freeze({ RANGES, scored, pick, words, phrase, reasons, mine, status, view });`。

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/*.test.cjs`
Expected: 55 tests pass

- [ ] **Step 5: Regenerate the report**

Run: `python scripts/build_report.py && python -m unittest discover -s tests && node --test tests/*.test.cjs`
Expected: 最後一行不變；61 tests OK；55 tests pass

- [ ] **Step 6: Commit**

```bash
git add src/web/trait-network.js src/web/match-filter.js tests/trait-network.test.cjs tests/match-filter.test.cjs invoice-insights.html
git commit -m "feat: lay out the taste network and word its sentences" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 連線頁畫出星雲圖，大字分數統一

這個任務改動多，但都在連線頁。點選與滑過留到 Task 8；這個任務結束時，圖已經畫得出來，說明列只顯示預設的一句。

**Files:**
- Modify: `src/web/taste-comparison.html`
- Modify: `src/web/match.html`
- Modify: `src/web/taste-profile.js`
- Modify: `src/receipt/build.py`
- Test: `tests/taste-profile.test.cjs`、`tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 6 的 `TraitNetwork.*`；Task 5 的 `traitNetworkData`；Task 4 的 `matchReportData.me/people[].pushes/signals`
- Produces:
  - 配對頁傳給連線頁的 `pair`：`{left, right}`，各帶 `name, demo, months, counts, traits: {vector, pushes, signals}`；不再有 `score`
  - `TasteProfile.fromPair(pair) -> {left, right, traits: [左, 右]}`（`traits` 原樣交出，可能是 `null`）
  - 連線頁的全域：`network`（`traitNetworkData` 或 `null`）、`chosenView`、`traitGraph`；函式 `traitsOf`、`traitPair`、`allDemo`、`pairNames`、`currentView`、`prepareView`、`renderSummary(result, both)`、`drawTraits(svg, mobile, both)`
  - 連線頁嵌入 `trait-similarity.js`、`match-filter.js`、`trait-network.js`

- [ ] **Step 1: Write the failing tests**

`tests/taste-profile.test.cjs`：把整個 `test('a match pair carries a whole-number score from -100 to 100 and two valid profiles',()=>{ … });` 換成：

```js
test('a match pair carries two valid profiles and hands their taste traits on untouched',()=>{
 const side=(name,demo)=>({name,demo,months:['2026-03','2026-04'],counts:[3,2,0,0,0,0,0,0,0,0],traits:{vector:[0.5]}});
 const pair=taste.fromPair({left:side('你',false),right:side('手搖學生 A',true)});
 assert.equal(pair.left.name,'你');assert.equal(pair.right.schema,taste.schema);
 assert.equal('traits' in pair.left,false);assert.equal('score' in pair,false);
 assert.deepEqual(pair.traits,[{vector:[0.5]},{vector:[0.5]}]);
 assert.deepEqual(taste.fromPair({left:{...side('你',false),traits:undefined},right:side('A',true)}).traits,[null,{vector:[0.5]}]);
 for(const invalid of [null,{left:side('你',false)},{left:side('你',false),right:{...side('A',true),counts:[1]}}])assert.throws(()=>taste.fromPair(invalid));
});
```

`tests/test_build_report.py`：把 Task 5 加的 `self.assertIn('data-source="trait-network-data.js"', comparison)` 換成：

```python
            for name in ("trait-similarity.js", "match-filter.js", "trait-network.js", "trait-network-data.js"):
                self.assertIn(f'data-source="{name}"', comparison)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/taste-profile.test.cjs`
Expected: FAIL（`fromPair` 還要求分數）

Run: `python -m unittest tests.test_build_report -v`
Expected: FAIL（連線頁還沒有嵌入 `trait-similarity.js`）

- [ ] **Step 3: taste-profile.js、match.html、build.py**

`src/web/taste-profile.js`：把

```js
 function fromPair(pair){
  if(!pair||!Number.isSafeInteger(pair.score)||pair.score<-100||pair.score>100)throw new Error('配對資料不正確，請回配對清單重新選擇。');
  return {score:pair.score,left:validate({schema,...pair.left}),right:validate({schema,...pair.right})};
 }
```

換成

```js
 function fromPair(pair){
  if(!pair||!pair.left||!pair.right)throw new Error('配對資料不正確，請回配對清單重新選擇。');
  // Taste traits pass through untouched; the connection page checks them against its own trait data.
  return {left:validate({schema,...pair.left}),right:validate({schema,...pair.right}),traits:[pair.left.traits??null,pair.right.traits??null]};
 }
```

`src/web/match.html`：把

```js
  function pairFor(card) {
    return {
      score: card.percent,
      left: { name: '你', demo: data.isDemo, months: data.me.months, counts: data.me.counts },
      right: { name: card.name, demo: true, months: data.personaMonths, counts: card.person.counts },
    };
  }
```

換成

```js
  // The connection page draws the network from both people's taste and works out the score itself.
  const taste = person => ({ vector: person.vector, pushes: person.pushes, signals: person.signals });
  function pairFor(card) {
    return {
      left: { name: '你', demo: data.isDemo, months: data.me.months, counts: data.me.counts, traits: taste(data.me) },
      right: { name: card.name, demo: true, months: data.personaMonths, counts: card.person.counts, traits: taste(card.person) },
    };
  }
```

`src/receipt/build.py`（`main()`）：把

```python
    comparison = embed_scripts((WEB / "taste-comparison.html").read_text(encoding="utf-8"), {
        "taste-profile.js": scripts["taste-profile.js"],
        "trait-network-data.js": script_constant("traitNetworkData", trait_network_data(context["traits"], tastes, friends))})
```

換成

```python
    shared = {name: (WEB / name).read_text(encoding="utf-8") for name in ("trait-similarity.js", "match-filter.js")}
    comparison = embed_scripts((WEB / "taste-comparison.html").read_text(encoding="utf-8"), {
        "taste-profile.js": scripts["taste-profile.js"], **shared,
        "trait-network.js": (WEB / "trait-network.js").read_text(encoding="utf-8"),
        "trait-network-data.js": script_constant("traitNetworkData", trait_network_data(context["traits"], tastes, friends))})
```

並把

```python
    match_page = embed_scripts((WEB / "match.html").read_text(encoding="utf-8"), {
        "trait-similarity.js": (WEB / "trait-similarity.js").read_text(encoding="utf-8"),
        "match-filter.js": (WEB / "match-filter.js").read_text(encoding="utf-8"),
        "match-data.js": script_constant("matchReportData", matches)})
```

換成

```python
    match_page = embed_scripts((WEB / "match.html").read_text(encoding="utf-8"), {
        **shared, "match-data.js": script_constant("matchReportData", matches)})
```

- [ ] **Step 4: taste-comparison.html 的版面與樣式**

`src/web/taste-comparison.html` 的每一處都是「找到這段，換成那段」，找的文字在檔案裡只出現一次。

1. 樣式：在 `</style>` 的前面（也就是 `</style>\n</head>` 之前）加上兩行：

   ```css
   .views{display:inline-flex;border:1px solid var(--line);border-radius:999px;overflow:hidden}.view-button{background:none;border:0;padding:7px 15px;font-size:12px;color:var(--muted);min-height:36px}.view-button[aria-pressed="true"]{background:#2b2626;color:var(--ink)}.view-button:disabled{opacity:.4;cursor:not-allowed}.views-note{font-size:11px;color:var(--muted)}.toolbar-left{display:flex;align-items:center;gap:16px;flex-wrap:wrap}
   .t-label{fill:var(--ink);paint-order:stroke;stroke:#101010;stroke-width:3px;stroke-linejoin:round;pointer-events:none}.t-trait,.t-signal{stroke-width:1.4}.t-link,.t-cell{fill:none;stroke-linecap:round;transition:opacity .15s}.detail-text{white-space:pre-line}
   ```

2. `<div class="overall-label">綜合品味相似指數</div>` 換成 `<div class="overall-label">品味相似度</div>`
3. `<div class="toolbar"><div class="controls">` 換成：

   ```html
   <div class="toolbar"><div class="toolbar-left"><div class="views" role="group" aria-label="選擇要看的圖"><button type="button" class="view-button" data-view="traits" aria-pressed="true">品味特質</button><button type="button" class="view-button" data-view="items" aria-pressed="false">品項細節</button></div><span class="views-note" id="views-note" hidden>這份連結還沒有品味特質</span><div class="controls">
   ```

4. `</select></label></div><div class="scope" id="scope"` 換成 `</select></label></div></div><div class="scope" id="scope"`
5. `<div class="legend"><span class="legend-item"><span class="size-key"` 換成 `<div class="legend" id="item-legend"><span class="legend-item"><span class="size-key"`
6. `<span class="legend-hint">點選查看關聯，點空白處取消</span></div>` 換成（兩行）：

   ```html
   <span class="legend-hint">點選查看關聯，點空白處取消</span></div>
   <div class="legend" id="trait-legend" hidden><span class="legend-item">訊號線：實線往右端推、虛線往左端推</span><span class="legend-item positive-label">中間：綠線加分、橘虛線扣分</span><span class="legend-item">越粗影響越大</span><span class="legend-item">空心：資料不足</span><span class="legend-hint">點選查看連線，點空白處取消</span></div>
   ```

7. `<details class="method"><summary>資料來源與相似百分比怎麼算？</summary>` 換成：

   ```html
   <details class="method"><summary>資料來源與相似百分比怎麼算？</summary><div id="trait-method" hidden><p id="trait-method-text"></p></div>
   ```

8. 把

   ```html
   <script src="taste-profile.js"></script>
   <script src="trait-network-data.js"></script>
   ```

   換成

   ```html
   <script src="taste-profile.js"></script>
   <script src="trait-similarity.js"></script>
   <script src="match-filter.js"></script>
   <script src="trait-network.js"></script>
   <script src="trait-network-data.js"></script>
   ```

- [ ] **Step 5: taste-comparison.html 的程式**

1. 朋友帶上品味資料。把

   ```js
   const $=id=>document.getElementById(id);const svgNS='http://www.w3.org/2000/svg';let items=demoItems,categoryMode=false,category='all',leftKey='an',rightKey='yu',nodes=[],edges=[],selected=null;
   for(const person of Object.values(profiles)){
    person.demoCounts=[...person.counts];person.categoryCounts=TasteProfile.categories.map(name=>demoItems.reduce((n,item,i)=>n+(item.c===name?person.counts[i]:0),0));
   }
   ```

   換成

   ```js
   const $=id=>document.getElementById(id);const svgNS='http://www.w3.org/2000/svg';let items=demoItems,categoryMode=false,category='all',leftKey='an',rightKey='yu',nodes=[],edges=[],selected=null;
   // The network data exists only inside the built report; opened on its own, the page shows item details only.
   const network=typeof traitNetworkData==='undefined'?null:traitNetworkData;let chosenView='traits',traitGraph=null;
   for(const person of Object.values(profiles)){
    person.demoCounts=[...person.counts];person.categoryCounts=TasteProfile.categories.map(name=>demoItems.reduce((n,item,i)=>n+(item.c===name?person.counts[i]:0),0));
    person.traits=network&&network.friends[person.name]?TraitNetwork.validate(network.friends[person.name],network):null;
   }
   ```

2. 配對的兩人帶上品味資料。把

   ```js
   // Opened from the match list: the sides are fixed to you and that match, and the big number is the match score.
   let pair=null;
   if(hostFrame==='connection-frame'){
    try{pair=TasteProfile.fromPair(pageHost.ReceiptPages.connection());}catch(error){pageHost.ReceiptPages.showMatches();}
    if(pair){
     profiles.me={name:pair.left.name,payload:pair.left};profiles.match={name:pair.right.name,payload:pair.right};leftKey='me';rightKey='match';
   ```

   換成

   ```js
   // Opened from the match list: the sides are fixed to you and that match, each with the taste traits it was matched on.
   let pair=null;
   if(hostFrame==='connection-frame'){
    try{pair=TasteProfile.fromPair(pageHost.ReceiptPages.connection());pair.traits=pair.traits.map(person=>TraitNetwork.validate(person,network));}catch(error){pair=null;pageHost.ReceiptPages.showMatches();}
    if(pair){
     profiles.me={name:pair.left.name,payload:pair.left,traits:pair.traits[0]};profiles.match={name:pair.right.name,payload:pair.right,traits:pair.traits[1]};leftKey='me';rightKey='match';
   ```

3. 在 `prepareMode()` 裡刪掉這一行：

   ```js
    document.querySelector('.overall-label').textContent=pair?'品味相似度':categoryMode?'消費類型相似度':'綜合品味相似指數';
   ```

4. 刪掉舊的品項分數與解讀：整個 `function renderCategorySummary(overall){ … }`（14 行）、`function cosine(a,b){…}` 這一行、`function indexPercent(score){…}` 這一行，以及 `function aggregate(person,side,indices){…}` 與 `function similarity(indices){…}` 這兩行。
5. 把從 `function summaryJoke(pair,best){` 開始、到 `function updateImport(side,message='',error=false){` 之前的整段（`summaryJoke` 與舊的 `renderSummary`）換成：

   ```js
   function traitsOf(side){const key=keyFor(side);return key===null?null:profiles[key].traits||null;}
   function traitPair(){const a=traitsOf('a'),b=traitsOf('b');return a&&b?[a,b]:null;}
   function allDemo(){const loaded=loadedSides();return loaded.length>0&&loaded.every(side=>isDemoProfile(keyFor(side)));}
   // Cards call the two 你 and 對方; friends are called by name.
   function pairNames(){return pair?['你','對方']:[profiles[leftKey].name,profiles[rightKey].name];}
   function currentView(){return traitPair()?chosenView:'items';}
   function prepareView(){
    const available=Boolean(traitPair()),traits=currentView()==='traits';
    for(const button of document.querySelectorAll('[data-view]')){button.setAttribute('aria-pressed',String(button.dataset.view===currentView()));if(button.dataset.view==='traits')button.disabled=!available;}
    $('views-note').hidden=available||!hasBoth();
    $('item-legend').hidden=traits;$('trait-legend').hidden=!traits;document.querySelector('.legend-explain').hidden=traits;document.querySelector('.controls').hidden=traits;
    $('trait-method').hidden=!traits;
    if(traits){$('category-method').hidden=true;$('demo-method').hidden=true;document.querySelector('.subtitle').textContent='每個點是一個消費訊號或品味特質。看看你們的品味，怎麼連起來。';}
   }
   // The readout always explains the big number, the taste similarity, whichever graph is showing.
   function renderSummary(result,both){
    const cases=document.querySelectorAll('.summary-case'),show=on=>{cases.forEach(node=>node.hidden=!on);$('summary-note').hidden=!on||!allDemo();};
    if(!hasBoth()){show(false);const side=loadedSides()[0];$('summary').textContent=side?`已載入${profiles[keyFor(side)].name}，再匯入朋友的連結就能比較。`:'貼上兩人的連結，看看品味有多像。';return;}
    if(!both){show(false);$('summary').textContent=`已載入${profiles[leftKey].name}和${profiles[rightKey].name}。品味特質要兩邊都有才能比較，下面可以看消費類別的比較。`;return;}
    if(!result.comparable){show(false);$('summary').textContent=`${profiles[leftKey].name} × ${profiles[rightKey].name} · 兩人共同的特質太少，還不能比較。`;return;}
    show(true);
    $('summary').textContent=leftKey===rightKey?`${profiles[leftKey].name} × 自己 · 這輪是自己對答案。`:`${profiles[leftKey].name} × ${profiles[rightKey].name} · 合拍的、各有主張的，都在這裡。`;
    const lines=TraitNetwork.readout(network,both[0],both[1],pairNames(),result);
    $('summary-best').textContent=lines.alike;$('summary-worst').textContent=lines.unlike;$('summary-note').textContent='虛構示範 · 分數不代表關係契合度。';
   }
   // The taste network: signals fan out from each person's traits, and the middle lines are the score's cells.
   function drawTraits(svg,mobile,both){
    const graph=TraitNetwork.layout(network,both[0],both[1],mobile),shape=TraitNetwork.SHAPES[mobile?'mobile':'desktop'],color={a:'#ff9aa7',b:'#9bbcff'};
    svg.setAttribute('viewBox',`0 0 ${graph.width} ${graph.height}`);
    const names=el('g',{'aria-hidden':'true'});
    for(const side of ['a','b']){
     const [cx]=shape.centers[side==='a'?0:1],x=mobile?cx:cx+(side==='a'?-130:130),y=mobile?(side==='a'?28:graph.height-14):30;
     names.append(el('text',{x,y,'text-anchor':'middle',class:'person-name'},chartName(keyFor(side),mobile)+(pair?(side==='a'?'':' · 配對對象'):' · '+(side==='a'?'你':'朋友'))));
    }
    const lines=el('g'),middles=el('g'),dots=el('g'),labels=el('g'),view={graph,links:[],cells:[],signals:[],traits:[]};
    for(const link of graph.links){const zero=link.push===0,base=zero?.3:.85;const path=el('path',{d:link.d,class:'t-link',stroke:color[link.side],'stroke-width':zero?.6:(.8+6*Math.abs(link.push)).toFixed(2),'stroke-dasharray':link.push<0?'5 4':'none',opacity:base});lines.append(path);view.links.push({...link,el:path,base});}
    for(const cell of graph.cells){const zero=cell.part===0,base=zero?.45:.9;const path=el('path',{d:cell.d,class:'t-cell',stroke:cell.part>0?'#5eeac7':cell.part<0?'#ffb65c':'#77736c','stroke-width':zero?.6:(.8+20*Math.abs(cell.part)).toFixed(2),'stroke-dasharray':cell.part<0?'7 5':'none',opacity:base});middles.append(path);view.cells.push({...cell,el:path,base});}
    for(const side of graph.sides){
     for(const signal of side.signals){const dot=el('circle',{cx:signal.x.toFixed(1),cy:signal.y.toFixed(1),r:mobile?4:3,class:'t-signal',fill:signal.value===null?'#101010':color[side.side],stroke:color[side.side]});dots.append(dot);view.signals.push({...signal,side:side.side,el:dot});}
     for(const trait of side.traits){
      const dot=el('circle',{cx:trait.x.toFixed(1),cy:trait.y.toFixed(1),r:trait.r.toFixed(1),class:'t-trait',fill:trait.hollow?'#101010':color[side.side],stroke:color[side.side]});dots.append(dot);
      const label=trait.labelShown?el('text',{x:trait.labelX.toFixed(1),y:trait.labelY.toFixed(1),'text-anchor':trait.labelAnchor,class:'t-label','font-size':graph.font},trait.label):null;if(label)labels.append(label);
      view.traits.push({...trait,side:side.side,el:dot,labelEl:label});
     }
    }
    svg.append(names,lines,middles,dots,labels);traitGraph=view;clearSelection();
   }
   ```

6. `clearSelection` 開頭的 `function clearSelection(){selected=null;for(const edge of edges){` 換成：

   ```js
   function clearSelection(){selected=null;if(traitGraph){for(const item of [...traitGraph.links,...traitGraph.cells])item.el.style.opacity=String(item.base);for(const item of [...traitGraph.signals,...traitGraph.traits]){item.el.style.opacity='1';if(item.labelEl)item.labelEl.style.opacity='1';}$('detail').textContent='點一個訊號或特質，看看它怎麼一路連到分數。';return;}for(const edge of edges){
   ```

7. `draw()` 的開頭（從 `function draw(){` 到 `renderSummary(overall);` 這一行為止，共 8 行）：

   ```js
   function draw(){
    prepareMode();
    const mobile=matchMedia('(max-width:640px)').matches,svg=$('network'),indices=items.map((_,i)=>i).filter(i=>category==='all'||(category==='dumplings'?items[i].dumpling:category==='sweetness'?items[i].sweetness:items[i].c===category)).filter(i=>!loadedSides().length||loadedSides().some(side=>profiles[keyFor(side)].counts[i]>0));svg.replaceChildren();const chartWidth=mobile?600:1200,chartHeight=mobile&&loadedSides().length&&indices.length>4?160+indices.length*76:570;svg.setAttribute('viewBox',`0 0 ${chartWidth} ${chartHeight}`);nodes=[];edges=[];selected=null;
    const overall=similarity(items.map((_,i)=>i));$('overall-score').textContent=overall===null?'—':indexPercent(overall);$('score-unit').hidden=overall===null;$('overall-score').parentElement.classList.toggle('waiting',overall===null);$('overall-note').textContent=hasBoth()?(categoryMode?'全類別評估 · 分類偏好摘要':'全類別評估 · 虛構示範'):loadedSides().length?'等待另一人匯入':'先匯入偏好資料';
    if(pair){$('overall-score').textContent=(pair.score>0?'+':pair.score<0?String.fromCharCode(0x2212):'')+Math.abs(pair.score);$('overall-note').textContent='消費類型相似度 '+indexPercent(overall)+'%（下圖）';}
    const scopeScore=similarity(indices),count=loadedSides().length;
    $('scope').textContent=(category==='all'?'全類別':category==='dumplings'?'同店不同餡':category==='sweetness'?'半糖與無糖':category)+' · '+(!count?'尚未匯入資料':!indices.length?'目前無資料':loadedSides().reduce((n,side)=>n+indices.filter(i=>profiles[keyFor(side)].counts[i]>0).length,0)+(categoryMode?' 個類別點 · ':' 個品項點 · ')+(scopeScore===null?(hasBoth()?'此範圍有一側無資料':'尚待另一人匯入'):categoryMode&&category!=='all'?'綜合分數仍計算全部類別':'範圍相似 '+indexPercent(scopeScore)+'%'));
    renderSummary(overall);
   ```

   換成：

   ```js
   function draw(){
    prepareMode();prepareView();
    const mobile=matchMedia('(max-width:640px)').matches,svg=$('network');svg.replaceChildren();nodes=[];edges=[];selected=null;traitGraph=null;
    // One big number everywhere: the taste similarity of the two people's trait vectors.
    const both=traitPair(),result=both?TraitSimilarity.compare(both[0].vector,both[1].vector,network.model):null,scored=Boolean(result&&result.comparable);
    $('overall-score').textContent=scored?TraitSimilarity.signed(result.score).slice(0,-1):'—';$('score-unit').hidden=!scored;$('overall-score').parentElement.classList.toggle('waiting',!scored);
    $('overall-note').textContent=scored?'依 '+TraitNetwork.traitCount(network.traits)+' 項品味特質計算'+(allDemo()?' · 虛構示範':''):hasBoth()?(both?'兩人共同的特質太少，無法計算品味相似度':'舊版連結沒有品味特質，無法計算品味相似度'):loadedSides().length?'等待另一人匯入':'先匯入偏好資料';
    renderSummary(result,both);
    if(currentView()==='traits'){$('scope').textContent=TraitNetwork.traitCount(network.traits)+' 項品味特質 · '+network.signals.length+' 個訊號';drawTraits(svg,mobile,both);return;}
    const indices=items.map((_,i)=>i).filter(i=>category==='all'||(category==='dumplings'?items[i].dumpling:category==='sweetness'?items[i].sweetness:items[i].c===category)).filter(i=>!loadedSides().length||loadedSides().some(side=>profiles[keyFor(side)].counts[i]>0));const chartWidth=mobile?600:1200,chartHeight=mobile&&loadedSides().length&&indices.length>4?160+indices.length*76:570;svg.setAttribute('viewBox',`0 0 ${chartWidth} ${chartHeight}`);
    const count=loadedSides().length;
    $('scope').textContent=(category==='all'?'全類別':category==='dumplings'?'同店不同餡':category==='sweetness'?'半糖與無糖':category)+' · '+(!count?'尚未匯入資料':!indices.length?'目前無資料':loadedSides().reduce((n,side)=>n+indices.filter(i=>profiles[keyFor(side)].counts[i]>0).length,0)+(categoryMode?' 個類別點':' 個品項點'));
   ```

   （`draw()` 後面從 ` if(!indices.length){svg.append(` 開始的品項圖程式不動。）

8. 把 `$('category').addEventListener('change',event=>{category=event.target.value;draw();});` 換成（兩行）：

   ```js
   $('category').addEventListener('change',event=>{category=event.target.value;draw();});document.querySelectorAll('[data-view]').forEach(button=>button.addEventListener('click',()=>{chosenView=button.dataset.view;draw();}));
   if(network)$('trait-method-text').textContent='品味相似度是 '+TraitNetwork.traitCount(network.traits)+' 項品味特質（'+network.traits.length+' 格）的餘弦相似度，範圍 '+TraitSimilarity.signed(-1)+'～'+TraitSimilarity.signed(1)+'。每項特質由幾個消費訊號加權而成，訊號線越粗，代表這個訊號推得越多；中間每條線是那一格對分數的加減，全部加起來就是品味相似度。';
   ```

   注意：第一行原本後面還接著 `$('reset').addEventListener(...)` 等程式，只替換這一段，後面的保持原樣。
9. `if(['dumplings','sweetness'].includes(requestedCase)){category=requestedCase;$('category').value=category;}` 換成：

   ```js
   if(['dumplings','sweetness'].includes(requestedCase)){category=requestedCase;$('category').value=category;chosenView='items';}
   ```

- [ ] **Step 6: Run tests and regenerate the report**

Run: `python scripts/build_report.py && python -m unittest discover -s tests && node --test tests/*.test.cjs`
Expected: 最後一行不變；61 tests OK；55 tests pass

Run: `grep -c "similarity(\|indexPercent\|cosine(\|summaryJoke\|renderCategorySummary" src/web/taste-comparison.html`
Expected: `0`

- [ ] **Step 7: Commit**

```bash
git add src/web/taste-comparison.html src/web/match.html src/web/taste-profile.js src/receipt/build.py tests/taste-profile.test.cjs tests/test_build_report.py invoice-insights.html
git commit -m "feat: draw the taste network on the connection page with one taste score" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 點選、滑過與鍵盤

**Files:**
- Modify: `src/web/taste-comparison.html`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 7 的 `drawTraits`、`traitGraph`、`clearSelection`；Task 6 的 `TraitNetwork.signalSentence`、`cellSentence`、`traitText`、`formatSignal`、`SHAPES`
- Produces：連線頁的 `sideNames`、`tipText`、`hideHover`、`hoverable`、`pin`、`clearPins`、`lightTraits`、`selectSignal`、`selectTrait`；`drawTraits` 改成可點選的版本（訊號點、特質點、中間的線都是 `role="button"`、`tabindex="0"` 的 `<g>`）

- [ ] **Step 1: 樣式**

把 Task 7 加的 `.t-link,.t-cell{fill:none;stroke-linecap:round;transition:opacity .15s}` 換成：

```css
.t-link,.t-cell{fill:none;stroke-linecap:round;transition:opacity .15s}.t-hit{cursor:pointer;outline:none;transition:opacity .15s}.t-hit:focus-visible .t-signal,.t-hit:focus-visible .t-trait{stroke:#fff;stroke-width:2.5}.t-cell-hit{fill:none;stroke:transparent;stroke-width:14}.t-tip{fill:var(--ink);paint-order:stroke;stroke:#101010;stroke-width:3px;stroke-linejoin:round;pointer-events:none}
```

- [ ] **Step 2: 可點選的圖與選取**

把從 `// The taste network: signals fan out from each person's traits, and the middle lines are the score's cells.` 開始、到 `function updateImport(side,message='',error=false){` 之前的整段（Task 7 的 `drawTraits`）換成：

```js
// The taste network: signals fan out from each person's traits, and the middle lines are the score's cells.
function drawTraits(svg,mobile,both){
 const graph=TraitNetwork.layout(network,both[0],both[1],mobile),shape=TraitNetwork.SHAPES[mobile?'mobile':'desktop'],color={a:'#ff9aa7',b:'#9bbcff'},who=sideNames();
 svg.setAttribute('viewBox',`0 0 ${graph.width} ${graph.height}`);
 const names=el('g',{'aria-hidden':'true'});
 for(const side of ['a','b']){
  const [cx]=shape.centers[side==='a'?0:1],x=mobile?cx:cx+(side==='a'?-130:130),y=mobile?(side==='a'?28:graph.height-14):30;
  names.append(el('text',{x,y,'text-anchor':'middle',class:'person-name'},chartName(keyFor(side),mobile)+(pair?(side==='a'?'':' · 配對對象'):' · '+(side==='a'?'你':'朋友'))));
 }
 const lines=el('g'),middles=el('g'),dots=el('g'),labels=el('g'),tips=el('g'),view={graph,links:[],cells:[],signals:[],traits:[],tips,pinned:[],hover:null};
 for(const link of graph.links){const zero=link.push===0,base=zero?.3:.85;const path=el('path',{d:link.d,class:'t-link',stroke:color[link.side],'stroke-width':zero?.6:(.8+6*Math.abs(link.push)).toFixed(2),'stroke-dasharray':link.push<0?'5 4':'none',opacity:base});lines.append(path);view.links.push({...link,el:path,base});}
 for(const cell of graph.cells){
  const zero=cell.part===0,base=zero?.45:.9,trait=network.traits[cell.trait];
  const path=el('path',{d:cell.d,class:'t-cell',stroke:cell.part>0?'#5eeac7':cell.part<0?'#ffb65c':'#77736c','stroke-width':zero?.6:(.8+20*Math.abs(cell.part)).toFixed(2),'stroke-dasharray':cell.part<0?'7 5':'none',opacity:base});
  const hit=el('g',{class:'t-hit',tabindex:'0',role:'button','aria-label':`「${trait.name}」這一格，${cell.part>0?'加':cell.part<0?'扣':'不加也不扣'}${cell.part?' '+Math.abs(TraitSimilarity.percent(cell.part))+' 分':''}，查看連線`});
  hit.append(el('path',{d:cell.d,class:'t-cell-hit'}),el('title',{},trait.name));bind(hit,()=>selectTrait(cell.trait));
  middles.append(path,hit);view.cells.push({...cell,el:path,base});
 }
 for(const side of graph.sides){
  const name=who[side.side==='a'?0:1];
  for(const signal of side.signals){
   const meta=network.signals[signal.order],value=signal.value===null?'':'（'+TraitNetwork.formatSignal(signal.value,meta.unit)+'）',item={...signal,side:side.side};
   const group=el('g',{class:'t-hit',tabindex:'0',role:'button','aria-label':`${name}的${meta.label}${value}，查看連線`});
   group.append(el('circle',{cx:signal.x.toFixed(1),cy:signal.y.toFixed(1),r:mobile?12:8,fill:'transparent'}),el('circle',{cx:signal.x.toFixed(1),cy:signal.y.toFixed(1),r:mobile?4:3,class:'t-signal',fill:signal.value===null?'#101010':color[side.side],stroke:color[side.side]}),el('title',{},meta.label+value));
   bind(group,()=>selectSignal(signal.id));hoverable(group,item,meta.label);
   dots.append(group);view.signals.push({...item,el:group});
  }
  for(const trait of side.traits){
   const data=network.traits[trait.index],item={...trait,side:side.side};
   const group=el('g',{class:'t-hit',tabindex:'0',role:'button','aria-label':`${name}，${data.name}：${TraitNetwork.traitText(data,trait.value)}，查看這一格`});
   group.append(el('circle',{cx:trait.x.toFixed(1),cy:trait.y.toFixed(1),r:Math.max(trait.r+5,10).toFixed(1),fill:'transparent'}),el('circle',{cx:trait.x.toFixed(1),cy:trait.y.toFixed(1),r:trait.r.toFixed(1),class:'t-trait',fill:trait.hollow?'#101010':color[side.side],stroke:color[side.side]}),el('title',{},data.name));
   bind(group,()=>selectTrait(trait.index));if(!trait.labelShown)hoverable(group,item,trait.label);
   const label=trait.labelShown?el('text',{x:trait.labelX.toFixed(1),y:trait.labelY.toFixed(1),'text-anchor':trait.labelAnchor,class:'t-label','font-size':graph.font},trait.label):null;if(label)labels.append(label);
   dots.append(group);view.traits.push({...item,el:group,labelEl:label});
  }
 }
 svg.append(names,lines,middles,dots,labels,tips);traitGraph=view;clearSelection();
}
// The detail sentences name both people; cards and the readout say 你 and 對方 instead.
function sideNames(){return [profiles[leftKey].name,profiles[rightKey].name];}
// A name next to a dot: a signal's name, or a trait label that had no room.
function tipText(item,text){
 const font=traitGraph.graph.font,mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width,gap=item.r===undefined?8:item.r+4;
 let x,y,anchor;
 if(mobile){x=item.x+gap;y=item.y+font*.35;anchor='start';}
 else{x=item.side==='a'?item.x-gap:item.x+gap;y=item.r===undefined?item.y+4:item.y-6;anchor=item.side==='a'?'end':'start';}
 return el('text',{x:x.toFixed(1),y:y.toFixed(1),'text-anchor':anchor,class:'t-tip','font-size':font},text);
}
function hideHover(){if(traitGraph&&traitGraph.hover){traitGraph.hover.remove();traitGraph.hover=null;}}
function hoverable(group,item,text){
 const show=()=>{hideHover();traitGraph.hover=tipText(item,text);traitGraph.tips.append(traitGraph.hover);};
 group.addEventListener('mouseenter',show);group.addEventListener('focus',show);group.addEventListener('mouseleave',hideHover);group.addEventListener('blur',hideHover);
}
function pin(item,text){const tip=tipText(item,text);traitGraph.tips.append(tip);traitGraph.pinned.push(tip);}
function clearPins(){if(!traitGraph)return;for(const tip of traitGraph.pinned)tip.remove();traitGraph.pinned=[];}
// Light the chosen traits and their signals; a chosen signal shows at full strength and the traits' other signals at half.
function lightTraits(indexes,focus){
 const lit=new Set(indexes),feeds=new Set(traitGraph.links.filter(link=>lit.has(link.trait)).map(link=>link.signal));
 for(const link of traitGraph.links)link.el.style.opacity=!lit.has(link.trait)?'.06':focus===null||link.signal===focus?'1':'.45';
 for(const cell of traitGraph.cells)cell.el.style.opacity=lit.has(cell.trait)?'1':'.06';
 for(const signal of traitGraph.signals)signal.el.style.opacity=signal.id===focus||(focus===null&&feeds.has(signal.id))?'1':feeds.has(signal.id)?'.5':'.15';
 for(const trait of traitGraph.traits){const on=lit.has(trait.index);trait.el.style.opacity=on?'1':'.2';if(trait.labelEl)trait.labelEl.style.opacity=on?'1':'.2';}
}
function selectSignal(id){
 clearPins();selected='signal:'+id;
 const feeds=network.traits.map((trait,index)=>(trait.signals.includes(id)?index:-1)).filter(index=>index>=0);
 lightTraits(feeds,id);
 const label=network.signals.find(signal=>signal.id===id).label,[left,right]=traitPair(),names=sideNames(),parts=traitGraph.graph.result.parts;
 for(const signal of traitGraph.signals)if(signal.id===id)pin(signal,label);
 $('detail').textContent=[TraitNetwork.signalSentence(network,left,names[0],id),TraitNetwork.signalSentence(network,right,names[1],id),
  ...feeds.map(index=>TraitNetwork.cellSentence(network,index,left,right,names,parts?parts[index]:null))].join('\n');
}
function selectTrait(index){
 clearPins();selected='trait:'+index;lightTraits([index],null);
 for(const trait of traitGraph.traits)if(trait.index===index&&!trait.labelShown)pin(trait,trait.label);
 const [left,right]=traitPair(),parts=traitGraph.graph.result.parts;
 $('detail').textContent=TraitNetwork.cellSentence(network,index,left,right,sideNames(),parts?parts[index]:null);
}
```

並把 `function clearSelection(){selected=null;if(traitGraph){for(const item` 換成 `function clearSelection(){selected=null;if(traitGraph){clearPins();hideHover();for(const item`。

- [ ] **Step 3: Regenerate and run every test**

Run: `python scripts/build_report.py && python -m unittest discover -s tests && node --test tests/*.test.cjs`
Expected: 最後一行不變；61 tests OK；55 tests pass

- [ ] **Step 4: Commit**

```bash
git add src/web/taste-comparison.html invoice-insights.html
git commit -m "feat: light up a signal's path through the taste network" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 最終驗證與交接（由主控執行，不交給子代理）

- [ ] **Step 1: 全部測試**

Run: `python -m unittest discover -s tests`
Expected: 61 tests OK

Run: `node --test tests/*.test.cjs`
Expected: 55 tests pass

- [ ] **Step 2: 產生結果可重現、只動到預期的檔案**

Run: `python scripts/build_report.py && git status --short`
Expected: 輸出同「試做結果」的三行；`git status` 只看到未追蹤的 `report-data.js`，`invoice-insights.html` 沒有變動。

- [ ] **Step 3: 瀏覽器檢查**

主控用無頭 Chrome（DevTools 協定）實際操作 `invoice-insights.html`，逐項截圖確認：

- 配對頁：名單與「試做結果」相同；「你的品味特質」是「偏好好吃飯・偏避開連假・偏香甜」；打開「也看看跟你相反的人」出現省錢上班族 D、E、C、A、B。
- 點手搖學生 B：品味特質圖、大字 +71、綜合解讀；點左邊「飲料甜度」與「快速解決 ↔ 好好吃飯」那一格，說明列與「試做結果」相同；Esc 取消；切到品項細節是 10 類圖、大字不變；返回配對清單後開關與距離仍保留。
- 點省錢上班族 D：大字是負的，中間有橘色虛線。
- 朋友比較：小安 × 小宇 +80%；品項細節的兩個案例；匯出自己的品味連結再貼到右側，大字「—」、品味特質停用。
- 視窗寬 375：上下排的版面，標籤沒有互相蓋住。
- 消費回顧（3 月 50 筆、4 月 53 筆）照常。

- [ ] **Step 4: 更新交接文件**

`docs/superpowers/handoffs/2026-10-08-taste-traits-stage1.md`：
- 標題改成「品味特質：交接（第一段、第二段第①②輪）」，開頭的分支狀態補上第②輪。
- 「目前進度與下一步」表格：第②輪標成「完成」，第③輪標成「**下一步**」；「新對話怎麼接」改成「開始第二段第③輪」，先讀文末的「第二段第②輪」。
- 文末新增「第二段第②輪：神經網路連線圖（2026-10-09 完成）」：規格、計畫、commit 範圍、測試數、示範結果、與規格不同的地方（若有），以及「第③輪要記得」：新版連結要帶 `vector`、`pushes`、`signals`，匯入時用 `TraitNetwork.validate`；匯出按鈕；真實資料校準三格中間點。
- 「第②輪要先做」四項標成已完成（只算一次、共用正負號百分比、±1 截斷因不減平均而不再存在、緊湊格式）。

```bash
git add docs/superpowers/handoffs/2026-10-08-taste-traits-stage1.md
git commit -m "docs: record round 2 of stage 2 in the handoff note" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 5: 回報使用者**

回報 Task 1～8 的 commit、測試結果與截圖。不要 push、不要合併：第二段三輪都完成後才一起合併。
