# 品味特質與向量 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 從發票明細算出 17 項品味特質（18 格向量），以虛構用戶的平均為中間點，用餘弦相似度比較兩個人；重做虛構用戶與「我」的示範資料，讓「即期族 vs 飯糰族」呈現負相關，並在產生報告時印出相似度分布。

**Architecture:** `attributes.py` 把每筆明細標上品項屬性與店家通路；`signals.py` 依日曆把一個人的明細換算成訊號；`traits.py` 依 `configs/traits.json` 把訊號加權成特質向量，並以 40 位虛構用戶的平均換算成相對向量；`similarity.py`（與瀏覽器版 `trait-similarity.js` 共用測試案例）算出 −1～+1 的分數與每格貢獻。這一段不改任何網頁畫面，舊配對頁照常運作。

**Tech Stack:** Python 3.10+ 標準函式庫（`unittest`）、原生 JavaScript、Node.js `node:test`

**Spec:** `docs/superpowers/specs/2026-10-07-taste-traits-design.md`

## Global Constraints

- Python 只用標準函式庫；`pyproject.toml` 不變。
- 不讀取、不修改 `data/` 底下任何檔案（私人資料）。唯一例外是 Task 6 Step 3 的冒煙測試：只在記憶體中執行、只印數量。
- 根目錄的 `report-data.js` 是未追蹤的私人檔案，絕不加入 Git。每個任務只 `git add` 該任務列出的檔案，不要用 `git add -A` 或 `git add .`。
- 測試與設定只用虛構店名與品名（以「示範」或「測試」開頭）。行政區只用：高雄市苓雅區、高雄市新興區、高雄市前鎮區、高雄市左營區、臺北市信義區、臺北市內湖區、新北市板橋區、桃園市中壢區、新竹市東區、新竹縣竹北市、宜蘭縣宜蘭市、屏東縣恆春鎮、屏東縣東港鎮。
- 這一段不改網頁畫面：`src/web/` 底下既有的 HTML、CSS、JavaScript 都不動；只新增 `src/web/trait-similarity.js`（第二段才會載入它）。
- 不改 `src/receipt/tags.py`、`src/receipt/matching.py`、`configs/tags.json`；它們在第二段才移除。
- 報告維持單一 HTML 檔、沒有外部資源。
- 設定值、示範資料與程式碼照本計畫逐字輸入。`personas.py` 的亂數使用順序、`demo.py` 的資料與 `configs/traits.json` 的基準都會影響校準結果；任何一處不同，Task 4 的測試就可能失敗。
- 在 `feature/taste-traits` 分支工作（已存在，規格已 commit）。
- Commit 訊息用英文，結尾一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 指令都在專案根目錄 `D:\@spin\receipt` 用 Git Bash 執行：
  - 全部 Python 測試：`python -m unittest discover -s tests -v`
  - 單一檔：`python -m unittest tests.test_traits -v`
  - Node 測試：`node --test tests/*.test.cjs`
- Node 測試讀取根目錄已產生的 `invoice-insights.html`。Task 4 改了示範資料後要執行 `python scripts/build_report.py` 重新產生，並把它一起 commit。
- Git 在 Windows 上會提示「LF will be replaced by CRLF」，可以忽略。

## 校準結果（試做驗證，供參考）

以下結果來自本計畫的程式碼與資料，已在專案副本中跑過全部測試（Python 74 個、Node 35 個全部通過）：

- 「我」和 40 位虛構用戶：最像 +62%（手搖學生 A、B），中位數 +8%，最不像 −42%（省錢上班族）。產生報告印出 `taste similarity to 40 fictional people: highest 62%, median 8%, lowest -42%`。
- 囤貨的省錢上班族（A～C）和每位忙碌工程師：−18%～−16%；在超商少量買日用品的 D、E 和工程師：+17%～+21%。
- 同類型平均 +54%～+94%，不同類型平均約 −7%。
- 小安 vs 小宇 +51%（清爽 ↔ 香甜一格 −0.175），小安 vs 小林 +22%。
- 一般人的中間點（兩端型）：省錢 ↔ 享受 −0.22、快速解決 ↔ 好好吃飯 +0.50、超商：省錢 ↔ 省時 0.00、外食 ↔ 自己煮 −0.51、清爽 ↔ 香甜 −0.42、固定習慣 ↔ 喜歡嘗鮮 −0.77、待在生活圈 ↔ 常出遊 −0.81、囤貨 ↔ 少量即買 +0.05、上班日型 ↔ 休假日型 +0.13、避開連假 ↔ 連假出遊 +0.20。
- 消費回顧不變：3 月 50 筆、7,910 元；4 月 53 筆、8,095 元。舊配對頁有 5 位候選人。

## 檔案結構

| 檔案 | 動作 | 責任 |
|---|---|---|
| `src/receipt/similarity.py` | 新增 | 兩個向量 → 相似度與每格貢獻；百分比進位 |
| `src/web/trait-similarity.js` | 新增 | 同上的瀏覽器版 |
| `tests/fixtures/similarity-cases.json` | 新增 | Python 與 Node 共用的手算測試案例 |
| `configs/attributes.json` | 新增 | 品名關鍵字、店名關鍵字、非實體賣方 |
| `configs/brands.json` | 修改 | 每個品牌的通路類型；補 4 個示範品牌 |
| `src/receipt/attributes.py` | 新增 | 一筆明細 → 品項屬性；店家 → 通路 |
| `configs/traits.json` | 新增 | 17 項特質（18 格）的訊號、權重、基準、門檻；相似度設定 |
| `configs/calendar-2026.json` | 新增 | 2026 年 3～4 月的國定假日與補假 |
| `src/receipt/signals.py` | 新增 | 日曆；一個人的明細 → 訊號、資料量、日曆常數 |
| `src/receipt/traits.py` | 新增 | 設定載入；訊號 → 特質向量；一般人的中間點與相對向量 |
| `src/receipt/personas.py` | 改寫 | 40 位虛構用戶與小安、小宇、小林 |
| `src/receipt/demo.py` | 修改 | 「我」的示範資料輪流多家店與多種品項 |
| `configs/item-categories.json` | 修改 | 「我」的 23 個示範品名 |
| `src/receipt/build.py` | 修改 | 虛構用戶只建一次；印出品味相似度分布 |
| `README.md` | 修改 | 示範品名數量 |
| `tests/test_similarity.py`、`tests/trait-similarity.test.cjs` | 新增 | 相似度 |
| `tests/test_attributes.py` | 新增 | 品項屬性與通路 |
| `tests/test_traits.py` | 新增 | 設定、日曆、基準換算、每個特質的範例 |
| `tests/test_personas.py` | 改寫 | 示範資料說出的故事 |
| `tests/test_build_report.py` | 修改 | 產生報告印出的分布 |
| `invoice-insights.html` | 重新產生 | 公開示範版 |

---

### Task 1: 相似度（Python 與瀏覽器共用測試案例）

**Files:**
- Create: `src/receipt/similarity.py`
- Create: `src/web/trait-similarity.js`
- Create: `tests/fixtures/similarity-cases.json`
- Test: `tests/test_similarity.py`、`tests/trait-similarity.test.cjs`

**Interfaces:**
- Consumes: 無（純計算）
- Produces:
  - 模型格式 `model = {"cells": [{"id": str, "kind": "two_sided" | "level", "weight": number}, ...], "shrink": float, "min_shared_two_sided": int}`
  - Python `compare(mine, theirs, model) -> {"comparable": bool, "score": float | None, "parts": list[float | None] | None}`；`mine`、`theirs` 是與 `cells` 等長的 `list[float | None]`，或整份為 `None`
  - Python `percent(score) -> int`（0.5 一律進位）
  - JavaScript `TraitSimilarity.compare(mine, theirs, model)`、`TraitSimilarity.percent(score)`，Node 以 `require('../src/web/trait-similarity.js')` 取得同樣的兩個函式

- [ ] **Step 1: 建立共用測試案例**

預期值由公式直接手算，不是由實作產生。建立 `tests/fixtures/similarity-cases.json`：

```json
{
  "model": {"cells": [{"id": "a", "kind": "two_sided", "weight": 1}, {"id": "b", "kind": "two_sided", "weight": 1}, {"id": "c", "kind": "two_sided", "weight": 1}, {"id": "d", "kind": "two_sided", "weight": 1}, {"id": "e", "kind": "two_sided", "weight": 1}, {"id": "f", "kind": "two_sided", "weight": 1}, {"id": "g", "kind": "level", "weight": 1}], "shrink": 0.25, "min_shared_two_sided": 5},
  "cases": [
    {"name": "identical vectors score just under +1",
     "mine": [0.6, -0.4, 0.2, 0.8, -0.2, 0.5, 0.3], "theirs": [0.6, -0.4, 0.2, 0.8, -0.2, 0.5, 0.3],
     "comparable": true, "score": 0.863387978142,
     "parts": [0.196721311475, 0.087431693989, 0.021857923497, 0.349726775956, 0.021857923497, 0.136612021858, 0.049180327869]},
    {"name": "opposite vectors score just above -1",
     "mine": [0.6, -0.4, 0.2, 0.8, -0.2, 0.5, 0.0], "theirs": [-0.6, 0.4, -0.2, -0.8, 0.2, -0.5, 0.0],
     "comparable": true, "score": -0.85632183908,
     "parts": [-0.206896551724, -0.091954022989, -0.022988505747, -0.367816091954, -0.022988505747, -0.14367816092, 0.0]},
    {"name": "a cell either side lacks is skipped",
     "mine": [0.6, null, 0.2, 0.8, -0.2, 0.5, 0.3], "theirs": [0.5, 0.9, 0.1, 0.7, -0.1, 0.4, 0.0],
     "comparable": true, "score": 0.789674749961,
     "parts": [0.215365840898, null, 0.014357722727, 0.402016236344, 0.014357722727, 0.143577227266, 0.0]},
    {"name": "fewer than five shared two-sided cells cannot be compared",
     "mine": [0.6, null, null, 0.8, -0.2, 0.5, 0.3], "theirs": [0.6, -0.4, 0.2, 0.8, -0.2, 0.5, 0.3],
     "comparable": false, "score": null,
     "parts": null},
    {"name": "faint profiles shrink toward zero",
     "mine": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.0], "theirs": [0.1, 0.1, 0.1, 0.1, 0.1, 0.1, 0.0],
     "comparable": true, "score": 0.193548387097,
     "parts": [0.032258064516, 0.032258064516, 0.032258064516, 0.032258064516, 0.032258064516, 0.032258064516, 0.0]},
    {"name": "a missing vector cannot be compared",
     "mine": null, "theirs": [0.6, -0.4, 0.2, 0.8, -0.2, 0.5, 0.3],
     "comparable": false, "score": null,
     "parts": null},
    {"name": "a heavier cell counts more", "model": {"cells": [{"id": "a", "kind": "two_sided", "weight": 2}, {"id": "b", "kind": "two_sided", "weight": 1}, {"id": "c", "kind": "two_sided", "weight": 1}, {"id": "d", "kind": "two_sided", "weight": 1}, {"id": "e", "kind": "two_sided", "weight": 1}, {"id": "f", "kind": "two_sided", "weight": 1}, {"id": "g", "kind": "level", "weight": 1}], "shrink": 0.25, "min_shared_two_sided": 5},
     "mine": [0.6, -0.4, 0.2, 0.8, -0.2, 0.5, 0.3], "theirs": [0.9, 0.1, -0.3, 0.4, 0.0, -0.6, 0.2],
     "comparable": true, "score": 0.450461838556,
     "parts": [0.458961118528, -0.016998559945, -0.025497839918, 0.135988479564, -0.0, -0.127489199591, 0.025497839918]}
  ]
}
```

- [ ] **Step 2: Write the failing tests**

建立 `tests/test_similarity.py`：

```python
"""Similarity on hand-made vectors; tests/fixtures/similarity-cases.json is shared with the browser version."""
import json
import unittest
from pathlib import Path

from src.receipt.similarity import compare, percent

FIXTURE = json.loads((Path(__file__).resolve().parent / "fixtures" / "similarity-cases.json").read_text(encoding="utf-8"))


class SimilarityTests(unittest.TestCase):
    def test_shared_cases(self):
        for case in FIXTURE["cases"]:
            with self.subTest(case["name"]):
                result = compare(case["mine"], case["theirs"], case.get("model", FIXTURE["model"]))
                self.assertEqual(result["comparable"], case["comparable"])
                if not case["comparable"]:
                    self.assertIsNone(result["score"])
                    self.assertIsNone(result["parts"])
                    continue
                self.assertAlmostEqual(result["score"], case["score"], places=9)
                for got, expected in zip(result["parts"], case["parts"]):
                    if expected is None:
                        self.assertIsNone(got)
                    else:
                        self.assertAlmostEqual(got, expected, places=9)

    def test_parts_add_up_to_the_score(self):
        case = FIXTURE["cases"][2]
        result = compare(case["mine"], case["theirs"], FIXTURE["model"])
        self.assertAlmostEqual(sum(part for part in result["parts"] if part is not None), result["score"])

    def test_percent_rounds_halves_up_like_the_browser(self):
        self.assertEqual(percent(0.625), 63)
        self.assertEqual(percent(-0.355), -35)
        self.assertEqual(percent(0.1234), 12)


if __name__ == "__main__":
    unittest.main()
```

建立 `tests/trait-similarity.test.cjs`：

```javascript
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { compare, percent } = require('../src/web/trait-similarity.js');

const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'similarity-cases.json'), 'utf8'));

for (const item of fixture.cases) {
  test(item.name, () => {
    const result = compare(item.mine, item.theirs, item.model ?? fixture.model);
    assert.equal(result.comparable, item.comparable);
    if (!item.comparable) {
      assert.equal(result.score, null);
      assert.equal(result.parts, null);
      return;
    }
    assert.ok(Math.abs(result.score - item.score) < 1e-9, `${result.score} vs ${item.score}`);
    result.parts.forEach((part, index) => {
      if (item.parts[index] === null) assert.equal(part, null);
      else assert.ok(Math.abs(part - item.parts[index]) < 1e-9, `cell ${index}: ${part} vs ${item.parts[index]}`);
    });
  });
}

test('percent rounds halves up, as the Python side does', () => {
  assert.equal(percent(0.625), 63);
  assert.equal(percent(-0.355), -35);
  assert.equal(percent(0.1234), 12);
});
```

- [ ] **Step 3: Run tests to verify they fail**

Run: `python -m unittest tests.test_similarity -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.similarity'`

Run: `node --test tests/trait-similarity.test.cjs`
Expected: FAIL，`Cannot find module '../src/web/trait-similarity.js'`

- [ ] **Step 4: Implement**

建立 `src/receipt/similarity.py`：

```python
"""Compare two taste vectors: a cosine that is shrunk toward zero when either profile is faint.

src/web/trait-similarity.js mirrors this file; both run tests/fixtures/similarity-cases.json.
"""
import math

NOT_COMPARABLE = {"comparable": False, "score": None, "parts": None}


def compare(mine, theirs, model):
    """Score from -1 to +1 and each cell's share of it; cells either side lacks are skipped, not penalised."""
    if mine is None or theirs is None:
        return dict(NOT_COMPARABLE)
    cells = model["cells"]
    shared = [index for index, (a, b) in enumerate(zip(mine, theirs)) if a is not None and b is not None]
    if sum(1 for index in shared if cells[index]["kind"] == "two_sided") < model["min_shared_two_sided"]:
        return dict(NOT_COMPARABLE)

    def norm(values):
        return math.sqrt(sum(cells[index]["weight"] * values[index] ** 2 for index in shared))

    denominator = norm(mine) * norm(theirs) + model["shrink"]
    parts = [None] * len(cells)
    for index in shared:
        parts[index] = cells[index]["weight"] * mine[index] * theirs[index] / denominator
    return {"comparable": True, "score": sum(parts[index] for index in shared), "parts": parts}


def percent(score):
    """Whole percentage, rounding halves up exactly as Math.round does in the browser."""
    return math.floor(score * 100 + 0.5)
```

建立 `src/web/trait-similarity.js`：

```javascript
/* Taste-vector similarity, mirrored from src/receipt/similarity.py; both run tests/fixtures/similarity-cases.json. */
(function (root) {
  'use strict';
  const NOT_COMPARABLE = Object.freeze({ comparable: false, score: null, parts: null });
  function compare(mine, theirs, model) {
    if (!mine || !theirs) return { ...NOT_COMPARABLE };
    const cells = model.cells;
    const shared = mine.map((value, index) => index).filter(index => mine[index] !== null && theirs[index] !== null);
    if (shared.filter(index => cells[index].kind === 'two_sided').length < model.min_shared_two_sided) return { ...NOT_COMPARABLE };
    const norm = values => Math.sqrt(shared.reduce((sum, index) => sum + cells[index].weight * values[index] ** 2, 0));
    const denominator = norm(mine) * norm(theirs) + model.shrink;
    const parts = mine.map(() => null);
    for (const index of shared) parts[index] = cells[index].weight * mine[index] * theirs[index] / denominator;
    return { comparable: true, score: shared.reduce((sum, index) => sum + parts[index], 0), parts };
  }
  // Whole percentage, rounding halves up like percent() in similarity.py.
  const percent = score => Math.floor(score * 100 + 0.5);
  const api = Object.freeze({ compare, percent });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.TraitSimilarity = api;
})(globalThis);
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_similarity -v`
Expected: 3 tests OK

Run: `node --test tests/trait-similarity.test.cjs`
Expected: 8 tests pass

- [ ] **Step 6: Commit**

```bash
git add src/receipt/similarity.py src/web/trait-similarity.js tests/fixtures/similarity-cases.json tests/test_similarity.py tests/trait-similarity.test.cjs
git commit -m "feat: compare taste vectors the same way in Python and the browser" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 店家通路與品項屬性

**Files:**
- Create: `configs/attributes.json`
- Modify: `configs/brands.json`（整檔換成下方內容：每個品牌加 `channel`，最後補 4 個示範品牌）
- Create: `src/receipt/attributes.py`
- Test: `tests/test_attributes.py`

**Interfaces:**
- Consumes: `src/receipt/address.py` 的 `normalize_place(text)`（去空白、「台」改「臺」）
- Produces（`src/receipt/attributes.py`）:
  - 分類常數 `MEAL, DRINK, DESSERT, FRESH, SPORT, DAILY, TECH = 0, 1, 2, 3, 4, 8, 9`、`FOOD`、`GOODS`、`GENERAL = "一般店家"`
  - `fold(text) -> str`、`has(text, words) -> bool`
  - `channel_of(merchant, brands, vocabulary) -> str`（`brands` 是 `brands.json` 的清單，`vocabulary` 是 `attributes.json` 的內容）
  - `describe(row, channel, vocabulary) -> dict`，鍵為 `food, clearance, sugar, quick, cooking, kitchen, sport_supply, sport_gear, car_care, bulk, home, stationery, fun, pet_food, pet_supply, species, alcohol`；`row` 至少要有 `name, category, merchant, quantity`
  - `brands.json` 每筆為 `{"brand": str, "keywords": [str], "channel": str}`

- [ ] **Step 1: Write the failing test**

建立 `tests/test_attributes.py`：

```python
"""Item and shop attributes read from fictional names."""
import json
import unittest
from pathlib import Path

from src.receipt.attributes import channel_of, describe

ROOT = Path(__file__).resolve().parents[1]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
WORDS = json.loads((ROOT / "configs" / "attributes.json").read_text(encoding="utf-8"))


def line(name, category, merchant="測試小店", quantity=1):
    row = {"name": name, "category": category, "merchant": merchant, "quantity": quantity}
    return describe(row, channel_of(merchant, BRANDS, WORDS), WORDS)


class AttributeTests(unittest.TestCase):
    def test_every_brand_names_a_channel(self):
        channels = {"超商", "量販", "超市", "咖啡", "手搖", "餐飲", "3C", "選物", "寵物", "娛樂", "長途交通", "加油", "停車",
                    "住宿", "酒吧", "運動", "一般店家"}
        self.assertTrue(all(entry["channel"] in channels for entry in BRANDS))
        self.assertTrue(all(entry["channel"] in channels for entry in WORDS["seller_channels"]))

    def test_brand_list_decides_before_seller_words(self):
        self.assertEqual(channel_of("統一超商股份有限公司高雄示範分公司", BRANDS, WORDS), "超商")
        self.assertEqual(channel_of("台灣中油股份有限公司", BRANDS, WORDS), "加油")
        # 示範客運 is a listed city shuttle, although 客運 alone means a long-distance bus.
        self.assertEqual(channel_of("示範客運", BRANDS, WORDS), "一般店家")
        self.assertEqual(channel_of("測試客運股份有限公司", BRANDS, WORDS), "長途交通")
        self.assertEqual(channel_of("測試動物醫院", BRANDS, WORDS), "寵物")
        self.assertEqual(channel_of("測試 bar", BRANDS, WORDS), "酒吧")
        self.assertEqual(channel_of("測試小店", BRANDS, WORDS), "一般店家")

    def test_sugar_comes_from_words_then_drink_kind_then_tea_shop(self):
        self.assertEqual(line("測試半糖綠茶", 1)["sugar"], 0.5)
        self.assertEqual(line("測試無糖拿鐵", 1)["sugar"], 0)
        self.assertEqual(line("測試鮮奶", 1)["sugar"], 0.2)
        self.assertEqual(line("測試冰美式", 1)["sugar"], 0)
        self.assertEqual(line("測試珍珠鮮奶", 1)["sugar"], 1)
        self.assertEqual(line("測試青茶", 1, merchant="示範茶屋")["sugar"], 1)
        self.assertIsNone(line("測試手沖咖啡", 1)["sugar"])
        self.assertIsNone(line("測試半糖布丁", 2)["sugar"])

    def test_fruit_is_not_cooking_and_rice_wine_is_not_alcohol(self):
        self.assertTrue(line("測試高麗菜", 3)["cooking"])
        self.assertFalse(line("測試香蕉", 3)["cooking"])
        self.assertTrue(line("測試料理米酒", 3)["kitchen"])
        self.assertFalse(line("測試料理米酒", 3)["alcohol"])
        self.assertFalse(line("測試無糖綠茶", 1)["kitchen"])
        self.assertTrue(line("測試生啤酒", 1)["alcohol"])
        self.assertFalse(line("測試酒釀湯圓", 2)["alcohol"])

    def test_pet_items_carry_their_species(self):
        self.assertEqual((line("測試貓砂", 8)["pet_supply"], line("測試貓砂", 8)["species"]), (True, "cat"))
        self.assertEqual((line("測試犬用飼料", 8)["pet_food"], line("測試犬用飼料", 8)["species"]), (True, "dog"))
        self.assertEqual((line("測試寵物罐頭", 8)["pet_food"], line("測試寵物罐頭", 8)["species"]), (True, None))

    def test_quick_meals_bulk_fun_and_home_goods(self):
        self.assertTrue(line("測試鮪魚飯糰", 0)["quick"])
        self.assertFalse(line("測試鮪魚飯糰", 2)["quick"])
        self.assertTrue(line("測試即期便當", 0)["clearance"])
        self.assertTrue(line("測試衛生紙箱", 8)["bulk"])
        self.assertTrue(line("測試洗碗精3入", 8)["bulk"])
        self.assertTrue(line("測試洗碗精", 8, quantity=3)["bulk"])
        self.assertFalse(line("測試洗碗精", 8)["bulk"])
        self.assertEqual(line("測試爆米花", 2, merchant="測試影城")["fun"], "電影")
        self.assertEqual(line("測試展覽門票", 5)["fun"], "展演")
        self.assertTrue(line("測試香氛蠟燭", 8)["home"])
        self.assertFalse(line("測試大杯紅茶", 1)["home"])
        self.assertTrue(line("測試手帳", 8)["stationery"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_attributes -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.attributes'`

- [ ] **Step 3: Add the vocabulary and shop channels**

建立 `configs/attributes.json`：

```json
{
  "remote_sellers": ["富邦媒體", "網路家庭", "蝦皮", "酷澎", "博客來", "富胖達", "優食", "中華電信", "台灣大哥大", "遠傳電信", "台灣電力", "台灣自來水"],
  "seller_channels": [
    {"channel": "加油", "keywords": ["加油站"]},
    {"channel": "停車", "keywords": ["停車場"]},
    {"channel": "寵物", "keywords": ["動物醫院", "寵物"]},
    {"channel": "酒吧", "keywords": ["居酒屋", "酒吧", "Bar", "餐酒館"]},
    {"channel": "住宿", "keywords": ["民宿", "旅店", "旅宿", "飯店", "露營區"]},
    {"channel": "娛樂", "keywords": ["影城", "KTV", "遊樂園", "密室", "售票"]},
    {"channel": "長途交通", "keywords": ["高鐵", "客運", "航空"]},
    {"channel": "手搖", "keywords": ["茶飲", "茶坊", "茶舖", "飲料店"]}
  ],
  "clearance": ["即期", "i珍食", "友善食光"],
  "sugar_words": [["無糖", 0], ["微糖", 0.3], ["半糖", 0.5], ["少糖", 0.7], ["全糖", 1], ["正常甜", 1]],
  "sugar_defaults": [
    {"sugar": 1, "keywords": ["奶茶", "珍珠", "果茶", "汽水", "可樂", "多多"]},
    {"sugar": 0, "keywords": ["美式", "黑咖啡", "純茶", "礦泉水", "氣泡水"]},
    {"sugar": 0.2, "keywords": ["鮮奶", "拿鐵"]}
  ],
  "quick": ["飯糰", "三明治", "微波"],
  "fruit": ["水果", "蘋果", "香蕉", "芭樂", "柳丁", "橘子", "葡萄", "草莓", "西瓜", "鳳梨", "芒果", "奇異果"],
  "kitchen": ["醬油", "食用油", "橄欖油", "沙拉油", "鹽", "砂糖", "調味", "白米", "糙米", "米酒", "料理酒"],
  "sport_supply": ["高蛋白", "乳清", "能量棒"],
  "sport_gear": ["運動服", "運動鞋", "瑜珈墊", "球拍", "護膝"],
  "car_care": ["洗車", "汽車保養", "機車保養", "輪胎", "機油"],
  "bulk": ["箱", "組", "家庭號", "量販包"],
  "home": ["香氛", "蠟燭", "擴香", "精油", "花束", "植栽", "杯", "盤"],
  "stationery": ["手帳", "筆記本", "鋼筆", "貼紙", "明信片"],
  "fun": {
    "電影": ["影城", "電影"],
    "唱歌": ["KTV", "歡唱"],
    "展演": ["展覽", "門票", "演唱會", "售票"],
    "遊樂": ["遊樂園", "密室", "桌遊"]
  },
  "pet_food": ["飼料", "寵物罐頭", "貓罐頭", "狗罐頭", "寵物零食"],
  "pet_supply": ["貓砂", "尿布墊", "寵物玩具", "牽繩"],
  "cat": ["貓"],
  "dog": ["狗", "犬"],
  "alcohol": ["啤酒", "紅酒", "白酒", "威士忌", "清酒", "燒酎", "調酒"],
  "not_alcohol": ["米酒", "料理酒", "酒釀"]
}
```

把 `configs/brands.json` 整檔換成：

```json
[
  {"brand": "7-ELEVEN", "keywords": ["統一超商"], "channel": "超商"},
  {"brand": "全家", "keywords": ["全家便利商店"], "channel": "超商"},
  {"brand": "萊爾富", "keywords": ["萊爾富"], "channel": "超商"},
  {"brand": "OK超商", "keywords": ["來來超商"], "channel": "超商"},
  {"brand": "全聯", "keywords": ["全聯實業"], "channel": "超市"},
  {"brand": "家樂福", "keywords": ["家福股份有限公司", "家樂福"], "channel": "量販"},
  {"brand": "好市多", "keywords": ["好市多"], "channel": "量販"},
  {"brand": "大潤發", "keywords": ["大潤發"], "channel": "量販"},
  {"brand": "美廉社", "keywords": ["三商家購"], "channel": "超市"},
  {"brand": "星巴克", "keywords": ["統一星巴克"], "channel": "咖啡"},
  {"brand": "路易莎", "keywords": ["路易莎"], "channel": "咖啡"},
  {"brand": "麥當勞", "keywords": ["麥當勞", "和德昌"], "channel": "餐飲"},
  {"brand": "摩斯漢堡", "keywords": ["安心食品"], "channel": "餐飲"},
  {"brand": "85度C", "keywords": ["美食達人"], "channel": "咖啡"},
  {"brand": "屈臣氏", "keywords": ["屈臣氏"], "channel": "一般店家"},
  {"brand": "康是美", "keywords": ["統一生活事業"], "channel": "一般店家"},
  {"brand": "寶雅", "keywords": ["寶雅國際"], "channel": "一般店家"},
  {"brand": "無印良品", "keywords": ["無印良品"], "channel": "選物"},
  {"brand": "燦坤", "keywords": ["燦坤"], "channel": "3C"},
  {"brand": "全國電子", "keywords": ["全國電子"], "channel": "3C"},
  {"brand": "台灣高鐵", "keywords": ["高速鐵路"], "channel": "長途交通"},
  {"brand": "臺鐵", "keywords": ["臺灣鐵路"], "channel": "長途交通"},
  {"brand": "台灣中油", "keywords": ["中油"], "channel": "加油"},
  {"brand": "示範餐坊", "keywords": ["示範餐坊"], "channel": "餐飲"},
  {"brand": "示範茶屋", "keywords": ["示範茶屋"], "channel": "手搖"},
  {"brand": "示範烘焙店", "keywords": ["示範烘焙店"], "channel": "餐飲"},
  {"brand": "示範運動館", "keywords": ["示範運動館"], "channel": "運動"},
  {"brand": "示範數位店", "keywords": ["示範數位店"], "channel": "3C"},
  {"brand": "示範客運", "keywords": ["示範客運"], "channel": "一般店家"},
  {"brand": "示範超商", "keywords": ["示範超商"], "channel": "超商"},
  {"brand": "示範咖啡", "keywords": ["示範咖啡"], "channel": "咖啡"},
  {"brand": "示範水餃館", "keywords": ["示範水餃館"], "channel": "餐飲"},
  {"brand": "示範量販", "keywords": ["示範量販"], "channel": "量販"},
  {"brand": "示範精品咖啡", "keywords": ["示範精品咖啡"], "channel": "咖啡"},
  {"brand": "示範超市", "keywords": ["示範超市"], "channel": "超市"},
  {"brand": "示範選物店", "keywords": ["示範選物店"], "channel": "選物"},
  {"brand": "示範生活館", "keywords": ["示範生活館"], "channel": "選物"}
]
```

- [ ] **Step 4: Implement**

建立 `src/receipt/attributes.py`：

```python
"""Read what one purchase line says about itself: traits of the item, and the kind of shop it came from."""
import re

from .address import normalize_place

# Category indices from configs/report.json.
MEAL, DRINK, DESSERT, FRESH, SPORT, DAILY, TECH = 0, 1, 2, 3, 4, 8, 9
FOOD = {MEAL, DRINK, DESSERT, FRESH}
GOODS = {4, 5, 6, 7, 8, 9}  # confirmed categories that are not food
GENERAL = "一般店家"


def fold(text):
    """Compare without spacing, with 台 written as 臺, and ignoring letter case."""
    return normalize_place(text or "").casefold()


def has(text, words):
    folded = fold(text)
    return any(fold(word) in folded for word in words)


def channel_of(merchant, brands, vocabulary):
    """A listed brand decides first, then words in the seller name; anything else is an ordinary shop."""
    for entry in brands:
        if has(merchant, entry["keywords"]):
            return entry["channel"]
    for entry in vocabulary["seller_channels"]:
        if has(merchant, entry["keywords"]):
            return entry["channel"]
    return GENERAL


def sugar_of(name, channel, vocabulary):
    """0 for unsweetened through 1 for full sugar; None when the name gives no hint."""
    for word, sugar in vocabulary["sugar_words"]:
        if has(name, [word]):
            return sugar
    for entry in vocabulary["sugar_defaults"]:
        if has(name, entry["keywords"]):
            return entry["sugar"]
    # Tea shops sweeten fully unless told otherwise.
    return 1 if channel == "手搖" else None


def species_of(name, vocabulary):
    if has(name, vocabulary["cat"]):
        return "cat"
    if has(name, vocabulary["dog"]):
        return "dog"
    return None


def fun_of(name, merchant, vocabulary):
    return next((kind for kind, words in vocabulary["fun"].items() if has(name, words) or has(merchant, words)), None)


def describe(row, channel, vocabulary):
    """Every question the signals ask about one line, answered once."""
    name, category = row["name"], row["category"]
    goods = category in GOODS
    return {
        "food": category in FOOD,
        "clearance": category in FOOD and has(name, vocabulary["clearance"]),
        "sugar": sugar_of(name, channel, vocabulary) if category == DRINK else None,
        "quick": category == MEAL and has(name, vocabulary["quick"]),
        "cooking": category == FRESH and not has(name, vocabulary["fruit"]),
        "kitchen": category in (FRESH, DAILY) and has(name, vocabulary["kitchen"]),
        "sport_supply": has(name, vocabulary["sport_supply"]),
        "sport_gear": goods and has(name, vocabulary["sport_gear"]),
        "car_care": goods and has(name, vocabulary["car_care"]),
        "bulk": has(name, vocabulary["bulk"]) or bool(re.search(r"\d+入", fold(name))) or row["quantity"] >= 3,
        "home": goods and has(name, vocabulary["home"]),
        "stationery": goods and has(name, vocabulary["stationery"]),
        "fun": fun_of(name, row["merchant"], vocabulary),
        "pet_food": has(name, vocabulary["pet_food"]),
        "pet_supply": has(name, vocabulary["pet_supply"]),
        "species": species_of(name, vocabulary),
        "alcohol": has(name, vocabulary["alcohol"]) and not has(name, vocabulary["not_alcohol"]),
    }
```

- [ ] **Step 5: Run tests to verify they pass**

Run: `python -m unittest tests.test_attributes tests.test_tags -v`
Expected: 全部 OK（`test_tags` 確認舊的品牌比對不受 `channel` 欄位影響）

- [ ] **Step 6: Commit**

```bash
git add configs/attributes.json configs/brands.json src/receipt/attributes.py tests/test_attributes.py
git commit -m "feat: read item attributes and shop channels from invoice lines" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 訊號、特質與一般人的位置

**Files:**
- Create: `configs/traits.json`
- Create: `configs/calendar-2026.json`
- Create: `src/receipt/signals.py`
- Create: `src/receipt/traits.py`
- Test: `tests/test_traits.py`

**Interfaces:**
- Consumes: Task 2 的 `channel_of`、`describe`、`fold`、`has` 與分類常數
- 明細格式（`rows` 的每一筆）：`{"date": datetime.date, "day": int, "invoice": str, "merchant": str, "district": str | None, "name": str, "quantity": int, "amount": int, "category": int, "provisional": bool}`；`period` 是 `[(year, month), ...]`
- Produces:
  - `signals.calendar_days(period, calendar) -> (days: list[date], off: set[date], long_weekend: set[date])`
  - `signals.measure(rows, period, context) -> {"signals": dict[str, float | None], "counts": dict[str, int], "constants": {"offday_share", "offday_double", "long_holiday_share"}}`
  - `traits.load_context(root) -> {"brands", "vocabulary", "traits", "calendar"}`
  - `traits.dated(months) -> (rows, period)`：把報告的月份資料（`{"2026-03": {"year", "monthNumber", "rows", ...}}`）攤平並加上 `date`
  - `traits.between(value, low, mid, high)`、`traits.push(value, signal, constants)`、`traits.reaches(signal, direction)`、`traits.trait_value(trait, measured)`
  - `traits.build_vector(rows, period, context) -> list[float | None] | None`（順序同 `traits.json`，18 格）
  - `traits.similarity_model(settings)`：產生 Task 1 的 `model`
  - `traits.typical(vectors, settings) -> list[float]`、`traits.relative(vector, centers) -> list[float | None] | None`

- [ ] **Step 1: Write the failing test**

建立 `tests/test_traits.py`：

```python
"""Taste traits on small fictional purchase sets, one behaviour at a time."""
import unittest
from datetime import date
from pathlib import Path

from src.receipt.signals import calendar_days
from src.receipt.traits import between, build_vector, load_context, relative, trait_value, typical

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
TRAITS = CONTEXT["traits"]["traits"]
INDEX = {trait["id"]: index for index, trait in enumerate(TRAITS)}
PERIOD = [(2026, 3), (2026, 4)]
DAYS, OFF, LONG = calendar_days(PERIOD, CONTEXT["calendar"])
WORKDAYS = [day for day in DAYS if day not in OFF]
LONG_DAYS = sorted(LONG)
HOME, AWAY = "高雄市苓雅區", "屏東縣恆春鎮"


def bought(*groups):
    """Rows from (days, name, category, amount, merchant, district) groups; every purchase is its own invoice."""
    rows = []
    for days, name, category, amount, merchant, district in groups:
        for day in days:
            rows.append({"date": day, "day": day.day, "invoice": f"T{len(rows):03}", "merchant": merchant,
                         "district": district, "name": name, "quantity": 1, "amount": amount, "category": category,
                         "provisional": False})
    return rows


def lunches(count=20):
    """Plain lunches at a neighbourhood shop, to reach the 20-item minimum without saying much."""
    return (WORKDAYS[:count], "測試排骨便當", 0, 100, "測試便當店", HOME)


def trait(rows, name):
    vector = build_vector(rows, PERIOD, CONTEXT)
    return vector[INDEX[name]]


class ConfigTests(unittest.TestCase):
    def test_shipped_traits_match_the_spec(self):
        self.assertEqual(len(TRAITS), 18)
        self.assertEqual([trait["id"] for trait in TRAITS if trait["kind"] == "two_sided"],
                         ["spend", "meals", "motive", "cooking", "sweet", "routine", "travel", "stock", "days", "holiday"])
        for trait in TRAITS:
            self.assertAlmostEqual(sum(signal["weight"] for signal in trait["signals"]), 1, msg=trait["id"])
            self.assertEqual(trait["weight"], 1)
        self.assertEqual(CONTEXT["traits"]["min_items"], 20)
        self.assertEqual(CONTEXT["traits"]["similarity"], {"shrink": 0.25, "min_shared_two_sided": 5})
        self.assertEqual(CONTEXT["calendar"]["holidays"], ["2026-04-03", "2026-04-06"])


class CalendarTests(unittest.TestCase):
    def test_spring_2026_long_weekend_and_days_off(self):
        self.assertEqual(LONG_DAYS, [date(2026, 4, 3), date(2026, 4, 4), date(2026, 4, 5), date(2026, 4, 6)])
        self.assertEqual(len(OFF), 19)
        self.assertEqual(len(DAYS), 61)


class ScaleTests(unittest.TestCase):
    def test_between_climbs_and_falls(self):
        self.assertEqual(between(0, 0, 0.3, 1), -1)
        self.assertAlmostEqual(between(0.5, 0, 0.3, 1), 0.2 / 0.7)
        self.assertEqual(between(2, 0, 0.3, 1), 1)
        self.assertAlmostEqual(between(0.6, 0.7, 0.45, 0.2), -0.6)
        self.assertEqual(between(0.1, 0.7, 0.45, 0.2), 1)

    def test_both_ends_stay_reachable_and_missing_signals_hand_over_their_weight(self):
        spend = TRAITS[INDEX["spend"]]
        measured = {"counts": {"food_items": 10}, "constants": {},
                    "signals": {"meal_cost": 90, "clearance_share": 0.3, "premium_drink_share": None}}
        self.assertEqual(trait_value(spend, measured), -1)
        measured["signals"] = {"meal_cost": 300, "clearance_share": 0, "premium_drink_share": 0.5}
        self.assertEqual(trait_value(spend, measured), 1)
        measured["counts"] = {"food_items": 9}
        self.assertIsNone(trait_value(spend, measured))


class TraitTests(unittest.TestCase):
    def test_too_few_items_leave_no_vector(self):
        self.assertIsNone(build_vector(bought(lunches(19)), PERIOD, CONTEXT))
        self.assertIsNotNone(build_vector(bought(lunches(20)), PERIOD, CONTEXT))

    def test_clearance_lunches_at_80_dollars_mean_saving(self):
        rows = bought((WORKDAYS[:24], "測試即期雞腿便當", 0, 80, "示範超商", HOME))
        self.assertLessEqual(trait(rows, "spend"), -0.5)
        rows = bought((WORKDAYS[:12], "測試和牛定食", 0, 400, "測試定食屋", HOME),
                      (WORKDAYS[12:24], "測試精品手沖", 1, 180, "測試咖啡館", HOME))
        self.assertGreaterEqual(trait(rows, "spend"), 0.5)

    def test_daily_rice_balls_mean_quick_meals_and_shops_mean_proper_ones(self):
        rows = bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME))
        self.assertLessEqual(trait(rows, "meals"), -0.5)
        rows = bought((WORKDAYS[:24], "測試牛肉麵", 0, 150, "測試麵館", HOME))
        self.assertGreaterEqual(trait(rows, "meals"), 0.5)
        self.assertIsNone(trait(bought(lunches(7), (WORKDAYS[7:20], "測試無糖綠茶", 1, 25, "示範超商", HOME)), "meals"))

    def test_clearance_and_rice_balls_send_convenience_store_shoppers_opposite_ways(self):
        saving = bought((WORKDAYS[:24], "測試即期排骨便當", 0, 69, "示範超商", HOME))
        hurried = bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME))
        self.assertLessEqual(trait(saving, "motive"), -0.5)
        self.assertGreaterEqual(trait(hurried, "motive"), 0.5)

    def test_market_vegetables_mean_cooking_but_fruit_does_not(self):
        rows = bought((WORKDAYS[:16], "測試高麗菜", 3, 120, "測試傳統市場", HOME),
                      (WORKDAYS[16:20], "測試白米", 3, 200, "測試傳統市場", HOME),
                      (WORKDAYS[20:24], "測試醬油", 3, 90, "測試傳統市場", HOME))
        self.assertGreaterEqual(trait(rows, "cooking"), 0.5)
        rows = bought((WORKDAYS[:6], "測試香蕉", 3, 60, "測試水果攤", HOME),
                      (WORKDAYS[6:24], "測試排骨便當", 0, 100, "測試便當店", HOME))
        self.assertLessEqual(trait(rows, "cooking"), -0.5)

    def test_sugar_level_sets_light_or_sweet(self):
        rows = bought((WORKDAYS[:12], "測試冰美式", 1, 60, "測試咖啡館", HOME),
                      (WORKDAYS[12:24], "測試無糖綠茶", 1, 25, "示範超商", HOME))
        self.assertLessEqual(trait(rows, "sweet"), -0.7)
        rows = bought((WORKDAYS[:16], "測試全糖紅茶", 1, 40, "測試飲料店", HOME),
                      (WORKDAYS[16:24], "測試巧克力蛋糕", 2, 80, "測試甜點店", HOME))
        self.assertGreaterEqual(trait(rows, "sweet"), 0.7)

    def test_long_weekend_trips(self):
        base = lunches()
        rows = bought(base, (LONG_DAYS[:2], "測試海鮮套餐", 0, 600, "測試海港餐廳", AWAY))
        self.assertGreaterEqual(trait(rows, "holiday"), 0.5)
        rows = bought(base, (WORKDAYS[30:32], "測試海鮮套餐", 0, 600, "測試海港餐廳", AWAY))
        self.assertLessEqual(trait(rows, "holiday"), -0.3)
        rows = bought(base, (LONG_DAYS[:1], "測試海鮮套餐", 0, 600, "測試海港餐廳", AWAY))
        self.assertIsNone(trait(rows, "holiday"))

    def test_workday_only_shopping_leans_to_workdays(self):
        self.assertEqual(trait(bought(lunches(24)), "days"), -1)

    def test_entertainment_pets_and_drinks(self):
        rows = bought(lunches(),
                      (WORKDAYS[20:22], "測試電影票", 5, 300, "測試影城", HOME),
                      (WORKDAYS[22:24], "測試歡唱時段", 5, 350, "測試KTV", HOME),
                      (WORKDAYS[24:26], "測試展覽門票", 5, 250, "測試展覽館", HOME),
                      (WORKDAYS[26:28], "測試密室逃脫", 5, 500, "測試密室", HOME))
        self.assertAlmostEqual(trait(rows, "fun"), 1)
        rows = bought(lunches(),
                      (WORKDAYS[20:24], "測試貓飼料", 8, 400, "測試寵物店", HOME),
                      (WORKDAYS[24:26], "測試貓砂", 8, 300, "測試寵物店", HOME))
        self.assertAlmostEqual(trait(rows, "pets_cat"), 1)
        self.assertEqual(trait(rows, "pets_dog"), 0)
        rows = bought(lunches(),
                      (WORKDAYS[20:36], "測試生啤酒", 1, 60, "示範超商", HOME),
                      (WORKDAYS[36:44], "測試料理米酒", 3, 50, "示範超商", HOME))
        self.assertAlmostEqual(trait(rows, "alcohol"), 0.7)


class TypicalTests(unittest.TestCase):
    def test_two_sided_traits_are_measured_from_the_average_and_levels_stay(self):
        settings = {"traits": [{"kind": "two_sided"}, {"kind": "level"}, {"kind": "two_sided"}]}
        centers = typical([[0.2, 0.5, None], [-0.6, 0.1, None], None], settings)
        for got, expected in zip(centers, [-0.2, 0.0, 0.0]):
            self.assertAlmostEqual(got, expected)
        self.assertEqual(relative([1.0, 0.5, None], centers), [1.0, 0.5, None])
        self.assertAlmostEqual(relative([0.0, 0.0, 0.3], centers)[0], 0.2)
        self.assertIsNone(relative(None, centers))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_traits -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.signals'`

- [ ] **Step 3: Add the trait settings and the calendar**

建立 `configs/traits.json`：

```json
{
  "min_items": 20,
  "similarity": {"shrink": 0.25, "min_shared_two_sided": 5},
  "traits": [
    {"id": "spend", "name": "省錢 ↔ 享受", "ends": ["省錢", "享受"], "kind": "two_sided", "weight": 1,
     "requires": {"food_items": 10},
     "signals": [
       {"id": "meal_cost", "weight": 0.5, "scale": [100, 200, 300]},
       {"id": "clearance_share", "weight": 0.3, "toward": -1, "full": 0.3},
       {"id": "premium_drink_share", "weight": 0.2, "toward": 1, "full": 0.5}
     ]},
    {"id": "meals", "name": "快速解決 ↔ 好好吃飯", "ends": ["快速解決", "好好吃飯"], "kind": "two_sided", "weight": 1,
     "requires": {"meal_items": 8},
     "signals": [
       {"id": "store_meal_share", "weight": 0.4, "toward": -1, "full": 0.8},
       {"id": "weekday_quick_share", "weight": 0.3, "toward": -1, "full": 0.6},
       {"id": "shop_meal_share", "weight": 0.3, "toward": 1, "full": 0.8}
     ]},
    {"id": "motive", "name": "超商：省錢 ↔ 省時", "ends": ["為了省錢", "為了省時"], "kind": "two_sided", "weight": 1,
     "requires": {"store_food_items": 8},
     "signals": [
       {"id": "store_clearance_share", "weight": 0.5, "toward": -1, "full": 0.4},
       {"id": "weekday_quick_share", "weight": 0.5, "toward": 1, "full": 0.6}
     ]},
    {"id": "cooking", "name": "外食 ↔ 自己煮", "ends": ["外食", "自己煮"], "kind": "two_sided", "weight": 1,
     "requires": {"food_items": 10},
     "signals": [
       {"id": "fresh_share", "weight": 0.5, "toward": 1, "full": 0.4},
       {"id": "ready_meal_share", "weight": 0.3, "toward": -1, "full": 0.6},
       {"id": "kitchen_per_month", "weight": 0.2, "toward": 1, "full": 2}
     ]},
    {"id": "sweet", "name": "清爽 ↔ 香甜", "ends": ["清爽", "香甜"], "kind": "two_sided", "weight": 1,
     "requires": {"known_sugar_drinks": 3},
     "signals": [
       {"id": "sugar_mean", "weight": 0.8, "scale": [0, 0.3, 1]},
       {"id": "dessert_share", "weight": 0.2, "toward": 1, "full": 0.3}
     ]},
    {"id": "routine", "name": "固定習慣 ↔ 喜歡嘗鮮", "ends": ["固定習慣", "喜歡嘗鮮"], "kind": "two_sided", "weight": 1,
     "requires": {"items": 20},
     "signals": [
       {"id": "repeat_rate", "weight": 0.4, "scale": [0.7, 0.45, 0.2]},
       {"id": "shop_focus", "weight": 0.3, "scale": [0.8, 0.55, 0.3]},
       {"id": "new_shop_share", "weight": 0.3, "scale": [0.2, 0.4, 0.6]}
     ]},
    {"id": "sport", "name": "運動投入", "kind": "level", "weight": 1,
     "signals": [
       {"id": "sport_visits", "weight": 0.6, "toward": 1, "full": 8},
       {"id": "sport_supplies", "weight": 0.25, "toward": 1, "full": 4},
       {"id": "sport_gear", "weight": 0.15, "toward": 1, "full": 1}
     ]},
    {"id": "driving", "name": "自己開車騎車", "kind": "level", "weight": 1,
     "signals": [
       {"id": "fuel_visits", "weight": 0.6, "toward": 1, "full": 4},
       {"id": "parking_visits", "weight": 0.25, "toward": 1, "full": 4},
       {"id": "car_care", "weight": 0.15, "toward": 1, "full": 1}
     ]},
    {"id": "travel", "name": "待在生活圈 ↔ 常出遊", "ends": ["待在生活圈", "常出遊"], "kind": "two_sided", "weight": 1,
     "requires": {"district_invoices": 10},
     "signals": [
       {"id": "away_share", "weight": 0.5, "scale": [0, 0.1, 0.3]},
       {"id": "stays", "weight": 0.3, "toward": 1, "full": 1},
       {"id": "long_trips", "weight": 0.2, "toward": 1, "full": 2}
     ]},
    {"id": "stock", "name": "囤貨 ↔ 少量即買", "ends": ["囤貨", "少量即買"], "kind": "two_sided", "weight": 1,
     "requires": {"daily_items": 3},
     "signals": [
       {"id": "convenience_share", "weight": 0.5, "scale": [0, 0.5, 1]},
       {"id": "bulk_share", "weight": 0.3, "toward": -1, "full": 0.5},
       {"id": "small_daily_visits", "weight": 0.2, "toward": 1, "full": 4}
     ]},
    {"id": "lifestyle", "name": "生活質感小物", "kind": "level", "weight": 1,
     "signals": [
       {"id": "home_items", "weight": 0.4, "toward": 1, "full": 2},
       {"id": "stationery_items", "weight": 0.3, "toward": 1, "full": 2},
       {"id": "select_visits", "weight": 0.3, "toward": 1, "full": 2}
     ]},
    {"id": "tech", "name": "3C 投入", "kind": "level", "weight": 1,
     "signals": [
       {"id": "tech_items", "weight": 0.4, "toward": 1, "full": 3},
       {"id": "tech_spend", "weight": 0.4, "toward": 1, "full": 3000},
       {"id": "tech_visits", "weight": 0.2, "toward": 1, "full": 2}
     ]},
    {"id": "days", "name": "上班日型 ↔ 休假日型", "ends": ["上班日型", "休假日型"], "kind": "two_sided", "weight": 1,
     "requires": {"invoices": 10},
     "signals": [
       {"id": "offday_invoice_share", "weight": 0.6, "scale": [0, "offday_share", "offday_double"]},
       {"id": "offday_amount_share", "weight": 0.4, "scale": [0, "offday_share", "offday_double"]}
     ]},
    {"id": "holiday", "name": "避開連假 ↔ 連假出遊", "ends": ["避開連假", "連假出遊"], "kind": "two_sided", "weight": 1,
     "requires": {"trip_days": 2, "long_holidays": 1},
     "signals": [
       {"id": "holiday_trip_share", "weight": 1, "scale": [0, "long_holiday_share", 1]}
     ]},
    {"id": "fun", "name": "娛樂體驗", "kind": "level", "weight": 1,
     "signals": [
       {"id": "fun_visits", "weight": 0.7, "toward": 1, "full": 4},
       {"id": "fun_kinds", "weight": 0.3, "toward": 1, "full": 4}
     ]},
    {"id": "pets_cat", "name": "有養寵物（貓）", "group": "有養寵物", "kind": "level", "weight": 1,
     "signals": [
       {"id": "pet_food_cat", "weight": 0.6, "toward": 1, "full": 2},
       {"id": "pet_supply_cat", "weight": 0.25, "toward": 1, "full": 1},
       {"id": "pet_visits_cat", "weight": 0.15, "toward": 1, "full": 1}
     ]},
    {"id": "pets_dog", "name": "有養寵物（狗）", "group": "有養寵物", "kind": "level", "weight": 1,
     "signals": [
       {"id": "pet_food_dog", "weight": 0.6, "toward": 1, "full": 2},
       {"id": "pet_supply_dog", "weight": 0.25, "toward": 1, "full": 1},
       {"id": "pet_visits_dog", "weight": 0.15, "toward": 1, "full": 1}
     ]},
    {"id": "alcohol", "name": "小酌", "kind": "level", "weight": 1,
     "signals": [
       {"id": "alcohol_items", "weight": 0.7, "toward": 1, "full": 8},
       {"id": "bar_visits", "weight": 0.3, "toward": 1, "full": 4}
     ]}
  ]
}
```

建立 `configs/calendar-2026.json`：

```json
{
  "source": "行政院人事行政總處「115年政府行政機關辦公日曆表」：兒童節（4/4，週六）於 4/3 補假，清明節（4/5，週日）於 4/6 補假",
  "covers": ["2026-03", "2026-04"],
  "holidays": ["2026-04-03", "2026-04-06"],
  "workdays": []
}
```

- [ ] **Step 4: Implement the signals**

建立 `src/receipt/signals.py`：

```python
"""Measure one person's purchases: the shares, monthly counts and medians the taste traits weigh."""
from collections import Counter
from datetime import date, timedelta
from statistics import mean, median

from .attributes import DAILY, DESSERT, DRINK, MEAL, SPORT, TECH, channel_of, describe, fold, has

CONFIRMED = 10  # category 10 still waits for review
MEAL_BILL = {MEAL, DRINK, DESSERT}  # what a meal bill may include when estimating cost per person
NOT_SHOP_MEALS = {"超商", "量販", "超市"}
STORES = {"超商", "量販"}
SPLIT = {"cat": (("cat", 1.0),), "dog": (("dog", 1.0),), None: (("cat", 0.5), ("dog", 0.5))}


def calendar_days(period, calendar):
    """All dates in the covered months, the days off among them, and the days inside long weekends.

    Days off are weekends and listed holidays, minus listed make-up workdays; a long weekend is three
    or more days off in a row.
    """
    holidays = {date.fromisoformat(day) for day in calendar["holidays"]}
    workdays = {date.fromisoformat(day) for day in calendar["workdays"]}
    days = []
    for year, month in period:
        day = date(year, month, 1)
        while day.month == month:
            days.append(day)
            day += timedelta(days=1)
    off = {day for day in days if day in holidays or (day.weekday() >= 5 and day not in workdays)}
    long_weekend, run = set(), []
    for day in days:
        if day in off and run and day - run[-1] == timedelta(days=1):
            run.append(day)
            continue
        if len(run) >= 3:
            long_weekend.update(run)
        run = [day] if day in off else []
    if len(run) >= 3:
        long_weekend.update(run)
    return days, off, long_weekend


def share(part, whole):
    return part / whole if whole else None


def count(pool, test):
    return sum(1 for entry in pool if test(entry))


def ranked(counter):
    """Most frequent first; ties fall back to the key so results never depend on input order."""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def home_cities(located):
    """Cities of the districts holding at least a fifth of the located bills (two at most): where someone lives and works."""
    districts = Counter(invoice["district"] for invoice in located)
    total = sum(districts.values())
    return {district[:3] for district, seen in ranked(districts)[:2] if seen >= total * 0.2}


def gather(rows, context):
    """Answer the item questions once per line, then group the lines into invoices."""
    brands, vocabulary = context["brands"], context["vocabulary"]
    channels, lines, invoices = {}, [], {}
    for row in rows:
        merchant = row["merchant"]
        if merchant not in channels:
            channels[merchant] = channel_of(merchant, brands, vocabulary)
        line = {**row, "channel": channels[merchant], **describe(row, channels[merchant], vocabulary)}
        lines.append(line)
        invoice = invoices.setdefault(row["invoice"], {
            "date": row["date"], "merchant": merchant, "channel": channels[merchant],
            # Online, delivery and utility sellers print a company address, not where the buyer was.
            "district": None if has(merchant, vocabulary["remote_sellers"]) else row.get("district"),
            "total": 0, "food": 0, "portions": 0, "lines": []})
        invoice["total"] += row["amount"]
        if not row["provisional"] and row["category"] in MEAL_BILL:
            invoice["food"] += row["amount"]
            # Main-dish portions stand in for the number of people a bill fed.
            if row["category"] == MEAL and row["amount"] > 0:
                invoice["portions"] += row["quantity"]
        invoice["lines"].append(line)
    return lines, invoices


def valid_items(lines):
    """Paid, confirmed lines; one portion per item and invoice, as in the match tags."""
    seen, items = set(), []
    for line in lines:
        key = (line["invoice"], line["name"])
        if line["amount"] > 0 and not line["provisional"] and line["category"] < CONFIRMED and key not in seen:
            seen.add(key)
            items.append(line)
    return items


def average(values):
    return mean(values) if values else None


def in_month(entries, year, month):
    return [entry for entry in entries if (entry["date"].year, entry["date"].month) == (year, month)]


def routine(items, paid, period):
    """Per month: how often names repeat, how concentrated the shops are, and how many shops were one-offs."""
    repeat, focus, one_off = [], [], []
    for year, month in period:
        bought, bills = in_month(items, year, month), in_month(paid, year, month)
        if bought:
            repeat.append(1 - len({fold(item["name"]) for item in bought}) / len(bought))
        if bills:
            shops = Counter(invoice["merchant"] for invoice in bills)
            focus.append(sum(seen for _, seen in shops.most_common(3)) / len(bills))
            one_off.append(count(shops.values(), lambda seen: seen == 1) / len(shops))
    return average(repeat), average(focus), average(one_off)


def weekday_quick_share(meals, off):
    """Workdays with a quick meal that was bought on at least three different workdays, over workdays with a meal."""
    workday_meals = [item for item in meals if item["date"] not in off]
    dates = {}
    for item in workday_meals:
        if item["quick"]:
            dates.setdefault(fold(item["name"]), set()).add(item["date"])
    habits = {name for name, seen in dates.items() if len(seen) >= 3}
    quick = {item["date"] for item in workday_meals if item["quick"] and fold(item["name"]) in habits}
    return share(len(quick), len({item["date"] for item in workday_meals}))


def pet_signals(items, paid, months):
    pets = {"cat": Counter(), "dog": Counter()}
    for item in items:
        for kind in ("pet_food", "pet_supply"):
            if item[kind]:
                for species, part in SPLIT[item["species"]]:
                    pets[species][kind] += part
    for invoice in paid:
        if invoice["channel"] == "寵物":
            known = {line["species"] for line in invoice["lines"] if line["species"]}
            for species, part in SPLIT[known.pop() if len(known) == 1 else None]:
                pets[species]["visits"] += part
    return {f"pet_{kind}_{species}": pets[species][key] / months
            for species in ("cat", "dog") for kind, key in (("food", "pet_food"), ("supply", "pet_supply"), ("visits", "visits"))}


def measure(rows, period, context):
    """Raw signals (None when they cannot be measured), the counts traits require, and calendar constants."""
    days, off, long_weekend = calendar_days(period, context["calendar"])
    months = len(period)
    lines, invoices = gather(rows, context)
    items = valid_items(lines)
    paid = [invoice for invoice in invoices.values() if invoice["total"] > 0]
    food = [item for item in items if item["food"]]
    meals = [item for item in items if item["category"] == MEAL]
    drinks = [item for item in items if item["category"] == DRINK]
    daily = [item for item in items if item["category"] == DAILY]
    tech = [item for item in items if item["category"] == TECH]
    sugars = [item["sugar"] for item in drinks if item["sugar"] is not None]
    store_food = [item for item in food if item["channel"] == "超商"]
    costs = [invoice["food"] / invoice["portions"] for invoice in invoices.values()
             if invoice["portions"] and invoice["food"] > 0]
    located = [invoice for invoice in paid if invoice["district"]]
    home = home_cities(located)
    away = [invoice for invoice in located if invoice["district"][:3] not in home]
    trips = {invoice["date"] for invoice in away} | {invoice["date"] for invoice in paid if invoice["channel"] == "住宿"}
    daily_spend = Counter()
    for item in daily:
        daily_spend[item["invoice"]] += item["amount"]
    store_bills = [invoices[key] for key in daily_spend if invoices[key]["channel"] in STORES]
    fun = {}
    for item in items:
        if item["fun"]:
            fun.setdefault(item["invoice"], set()).add(item["fun"])
    spent = sum(invoice["total"] for invoice in paid)
    repeat_rate, shop_focus, new_shop_share = routine(items, paid, period)

    def visits(channel):
        return count(paid, lambda invoice: invoice["channel"] == channel) / months

    signals = {
        "meal_cost": median(costs) if len(costs) >= 3 else None,
        "clearance_share": share(count(food, lambda item: item["clearance"]), len(food)),
        "premium_drink_share": share(count(drinks, lambda item: item["amount"] / item["quantity"] >= 100), len(drinks)),
        "store_meal_share": share(count(meals, lambda item: item["channel"] == "超商"), len(meals)),
        "weekday_quick_share": weekday_quick_share(meals, off),
        "store_clearance_share": share(count(store_food, lambda item: item["clearance"]), len(store_food)),
        "shop_meal_share": share(count(meals, lambda item: item["channel"] not in NOT_SHOP_MEALS), len(meals)),
        "fresh_share": share(count(food, lambda item: item["cooking"]), len(food)),
        "ready_meal_share": share(len(meals), len(food)),
        "kitchen_per_month": count(items, lambda item: item["kitchen"]) / months,
        "sugar_mean": mean(sugars) if sugars else None,
        "dessert_share": share(count(food, lambda item: item["category"] == DESSERT), len(food)),
        "repeat_rate": repeat_rate, "shop_focus": shop_focus, "new_shop_share": new_shop_share,
        "sport_visits": len({item["invoice"] for item in items if item["category"] == SPORT}) / months,
        "sport_supplies": count(items, lambda item: item["sport_supply"]) / months,
        "sport_gear": count(items, lambda item: item["sport_gear"]) / months,
        "fuel_visits": visits("加油"), "parking_visits": visits("停車"),
        "car_care": count(items, lambda item: item["car_care"]) / months,
        "away_share": share(len(away), len(located)) if home else None,
        "stays": visits("住宿"), "long_trips": visits("長途交通"),
        "convenience_share": share(count(store_bills, lambda bill: bill["channel"] == "超商"), len(store_bills))
        if len(store_bills) >= 2 else None,
        "bulk_share": share(count(daily, lambda item: item["bulk"]), len(daily)),
        "small_daily_visits": count(daily_spend.values(), lambda amount: amount < 150) / months,
        "home_items": count(items, lambda item: item["home"]) / months,
        "stationery_items": count(items, lambda item: item["stationery"]) / months,
        "select_visits": visits("選物"),
        "tech_items": len(tech) / months,
        "tech_spend": sum(min(item["amount"], 3000) for item in tech) / months,
        "tech_visits": visits("3C"),
        "offday_invoice_share": share(count(paid, lambda invoice: invoice["date"] in off), len(paid)),
        "offday_amount_share": share(sum(invoice["total"] for invoice in paid if invoice["date"] in off), spent),
        "holiday_trip_share": share(len(trips & long_weekend), len(trips)),
        "fun_visits": len(fun) / months,
        "fun_kinds": len(set().union(*fun.values())),
        **pet_signals(items, paid, months),
        "alcohol_items": count(items, lambda item: item["alcohol"]) / months,
        "bar_visits": visits("酒吧"),
    }
    counts = {
        "items": len(items), "food_items": len(food), "meal_items": len(meals), "store_food_items": len(store_food),
        "known_sugar_drinks": len(sugars),
        "district_invoices": len(located), "daily_items": len(daily), "invoices": len(paid),
        "trip_days": len(trips), "long_holidays": 1 if long_weekend else 0,
    }
    offday_share = len(off) / len(days)
    constants = {"offday_share": offday_share, "offday_double": min(1.0, 2 * offday_share),
                 "long_holiday_share": len(long_weekend) / len(days)}
    return {"signals": signals, "counts": counts, "constants": constants}
```

- [ ] **Step 5: Implement the traits**

建立 `src/receipt/traits.py`：

```python
"""Weigh measured signals into taste traits, and line the traits up as one vector."""
import json
from datetime import date

from .signals import measure

CONFIGS = (("brands", "brands.json"), ("vocabulary", "attributes.json"), ("traits", "traits.json"), ("calendar", "calendar-2026.json"))


def load_context(root):
    """Everything the trait pipeline reads, from the project's configs folder."""
    return {key: json.loads((root / "configs" / name).read_text(encoding="utf-8")) for key, name in CONFIGS}


def dated(months):
    """Report months flattened into rows that carry their date, plus the (year, month) period they cover."""
    rows = [{**row, "date": date(month["year"], month["monthNumber"], row["day"])}
            for month in months.values() for row in month["rows"]]
    return rows, sorted((month["year"], month["monthNumber"]) for month in months.values())


def between(value, low, mid, high):
    """-1 at low, 0 at mid, +1 at high, straight lines in between and flat beyond; a falling scale works too."""
    if low > high:
        value, low, mid, high = -value, -low, -mid, -high
    if value <= mid:
        return max(-1.0, (value - mid) / (mid - low))
    return min(1.0, (value - mid) / (high - mid))


def push(value, signal, constants):
    """How far one signal moves its trait: up to 1 toward one end, or anywhere from -1 to +1 on a scale."""
    if "full" in signal:
        return signal["toward"] * min(1.0, value / signal["full"])
    low, mid, high = (constants[point] if isinstance(point, str) else point for point in signal["scale"])
    return between(value, low, mid, high)


def reaches(signal, direction):
    """Whether a signal can move its trait toward the + end (1) or the - end (-1)."""
    return "scale" in signal or signal["toward"] == direction


def trait_value(trait, measured):
    """A trait from its signals; signals that cannot be measured hand their weight to the rest."""
    signals, counts, constants = measured["signals"], measured["counts"], measured["constants"]
    if any(counts[name] < minimum for name, minimum in trait.get("requires", {}).items()):
        return None
    parts = [(signal, signals[signal["id"]]) for signal in trait["signals"] if signals[signal["id"]] is not None]
    if not parts:
        return None
    total = sum(signal["weight"] * push(value, signal, constants) for signal, value in parts)
    if trait["kind"] == "level":
        return total / sum(signal["weight"] for signal, _ in parts)
    if total == 0:
        return 0.0
    # Divide by what the available signals could reach on this side, so both ends stay reachable.
    direction = 1 if total > 0 else -1
    return total / sum(signal["weight"] for signal, _ in parts if reaches(signal, direction))


def build_vector(rows, period, context):
    """One value per trait (None where data is thin), or None when the person has too little data at all."""
    settings = context["traits"]
    measured = measure(rows, period, context)
    if measured["counts"]["items"] < settings["min_items"]:
        return None
    return [trait_value(trait, measured) for trait in settings["traits"]]


def similarity_model(settings):
    """What compare() needs: each cell's kind and weight, the shrink constant and the minimum overlap."""
    return {"cells": [{"id": trait["id"], "kind": trait["kind"], "weight": trait["weight"]} for trait in settings["traits"]],
            "shrink": settings["similarity"]["shrink"],
            "min_shared_two_sided": settings["similarity"]["min_shared_two_sided"]}


def typical(vectors, settings):
    """The average person: the mean of each two-sided trait over a reference population; level traits stay at 0."""
    centers = []
    for index, trait in enumerate(settings["traits"]):
        values = [vector[index] for vector in vectors if vector is not None and vector[index] is not None]
        centers.append(sum(values) / len(values) if trait["kind"] == "two_sided" and values else 0.0)
    return centers


def relative(vector, centers):
    """Each trait measured from the average person, kept within -1 and +1."""
    if vector is None:
        return None
    return [None if value is None else max(-1.0, min(1.0, value - center)) for value, center in zip(vector, centers)]
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `python -m unittest tests.test_traits -v`
Expected: 14 tests OK

- [ ] **Step 7: Commit**

```bash
git add configs/traits.json configs/calendar-2026.json src/receipt/signals.py src/receipt/traits.py tests/test_traits.py
git commit -m "feat: weigh purchase signals into taste traits measured from the average person" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 虛構用戶、朋友與「我」的示範資料

**Files:**
- Modify（整檔改寫）: `src/receipt/personas.py`
- Modify（整檔改寫）: `src/receipt/demo.py`
- Modify（整檔改寫）: `configs/item-categories.json`
- Modify: `src/receipt/build.py`（虛構用戶改由 `main()` 建立一次後傳入）
- Modify: `README.md:58`
- Test（整檔改寫）: `tests/test_personas.py`
- 重新產生: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 3 的 `calendar_days`、`load_context`、`build_vector`、`dated`、`typical`、`relative`、`similarity_model`、`measure`；Task 1 的 `compare`
- Produces:
  - `personas.MONTHS = ((2026, 3, 31), (2026, 4, 30))`（`build.py` 既有的 `personaMonths` 繼續使用）、`personas.PERIOD = ((2026, 3), (2026, 4))`
  - `personas.build_personas(calendar, per_type=5, seed=SEED) -> list[{"name", "type", "rows"}]`（40 人，`rows` 帶 `date`）
  - `personas.build_friends(calendar, seed=SEED) -> list[...]`（小安、小宇、小林）
  - `demo.SLOTS`、`demo.build_demo(catalog)`（月份格式不變）
  - `build.build_matches(months, categories, is_demo, population)`（多了 `population` 參數）

- [ ] **Step 1: Write the failing test**

把 `tests/test_personas.py` 整檔換成：

```python
"""The fictional population tells the taste story: types hold together, chosen differences pull apart."""
import json
import unittest
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.personas import PERIOD, build_friends, build_personas
from src.receipt.signals import measure
from src.receipt.similarity import compare
from src.receipt.traits import build_vector, dated, load_context, relative, similarity_model, typical

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
CATALOG = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
INDEX = {trait["id"]: index for index, trait in enumerate(CONTEXT["traits"]["traits"])}
MODEL = similarity_model(CONTEXT["traits"])
DOMINANT = {
    "省錢上班族": {"spend": (None, -0.8), "motive": (None, -0.8)},
    "忙碌工程師": {"meals": (None, -0.8), "motive": (0.8, None), "tech": (0.8, None)},
    "咖啡上班族": {"spend": (0.3, None), "meals": (0.8, None)},
    "手搖學生": {"meals": (0.8, None), "fun": (0.4, None)},
    "健身族": {"sport": (0.5, None), "sweet": (None, -0.8)},
    "家庭下廚": {"cooking": (0.7, None), "stock": (None, -0.8), "driving": (0.3, None)},
    "連假旅人": {"travel": (0.3, None)},
    "質感貓奴": {"lifestyle": (0.8, None), "pets_cat": (0.5, None)},
}


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = build_personas(CONTEXT["calendar"])
        cls.friends = build_friends(CONTEXT["calendar"])
        cls.raw = {person["name"]: build_vector(person["rows"], list(PERIOD), CONTEXT) for person in cls.people + cls.friends}
        centers = typical([cls.raw[person["name"]] for person in cls.people], CONTEXT["traits"])
        cls.vectors = {name: relative(vector, centers) for name, vector in cls.raw.items()}
        rows, period = dated(build_demo(CATALOG))
        cls.me = relative(build_vector(rows, period, CONTEXT), centers)
        cls.types = {}
        for person in cls.people:
            cls.types.setdefault(person["type"], []).append(person["name"])

    def score(self, a, b):
        return compare(self.vectors[a], self.vectors[b], MODEL)["score"]

    def test_forty_reproducible_fictional_people(self):
        self.assertEqual(len(self.people), 40)
        self.assertEqual(build_personas(CONTEXT["calendar"]), self.people)
        self.assertEqual(list(self.types), list(DOMINANT))
        rows = [row for person in self.people + self.friends for row in person["rows"]]
        self.assertTrue(all(row["merchant"].startswith("示範") and row["name"].startswith("示範") for row in rows))
        self.assertTrue(all((row["date"].year, row["date"].month) in PERIOD and row["day"] == row["date"].day for row in rows))
        self.assertEqual([friend["name"] for friend in self.friends], ["小安", "小宇", "小林"])
        self.assertTrue(all(self.raw[name] is not None for name in self.raw))

    def test_each_type_shares_its_dominant_traits(self):
        for kind, limits in DOMINANT.items():
            for name in self.types[kind]:
                for trait, (low, high) in limits.items():
                    value = self.raw[name][INDEX[trait]]
                    with self.subTest(name=name, trait=trait):
                        if low is not None:
                            self.assertGreaterEqual(value, low)
                        if high is not None:
                            self.assertLessEqual(value, high)

    def test_designed_splits_inside_a_type(self):
        # Two-sided splits give a negative part; level splits leave no shared credit, so teammates who share the habit score higher.
        for kind, trait in (("咖啡上班族", "sweet"), ("手搖學生", "sweet"), ("連假旅人", "holiday"), ("省錢上班族", "stock")):
            first, fourth = self.types[kind][0], self.types[kind][3]
            with self.subTest(kind=kind):
                self.assertLess(compare(self.vectors[first], self.vectors[fourth], MODEL)["parts"][INDEX[trait]], 0)
        for kind in ("忙碌工程師", "健身族", "家庭下廚", "質感貓奴"):
            first, fourth, fifth = self.types[kind][0], self.types[kind][3], self.types[kind][4]
            with self.subTest(kind=kind):
                self.assertGreater(self.score(fourth, fifth), self.score(first, fourth))

    def test_clearance_shoppers_and_rice_ball_eaters_both_live_at_the_convenience_store_but_differ(self):
        saving, hurried = self.types["省錢上班族"], self.types["忙碌工程師"]
        for name in saving + hurried:
            person = next(person for person in self.people if person["name"] == name)
            self.assertGreaterEqual(measure(person["rows"], list(PERIOD), CONTEXT)["signals"]["store_meal_share"], 0.8)
        for name in saving[:3]:
            for other in hurried:
                self.assertLess(self.score(name, other), 0, (name, other))
        for name in saving:
            best_teammate = max(self.score(name, other) for other in saving if other != name)
            self.assertLess(max(self.score(name, other) for other in hurried), best_teammate, name)

    def test_me_has_a_clear_match_and_a_clear_opposite(self):
        scored = sorted((compare(self.me, self.vectors[person["name"]], MODEL)["score"], person["type"]) for person in self.people)
        self.assertGreaterEqual(scored[-1][0], 0.5)
        self.assertEqual(scored[-1][1], "手搖學生")
        self.assertLessEqual(scored[0][0], -0.3)
        self.assertEqual(scored[0][1], "省錢上班族")

    def test_friends_an_and_yu_are_alike_except_for_sweetness(self):
        an_yu = compare(self.vectors["小安"], self.vectors["小宇"], MODEL)
        self.assertGreaterEqual(an_yu["score"], 0.3)
        self.assertLess(an_yu["parts"][INDEX["sweet"]], 0)
        self.assertLess(self.score("小安", "小林"), an_yu["score"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_personas -v`
Expected: FAIL，`ImportError: cannot import name 'PERIOD' from 'src.receipt.personas'`

- [ ] **Step 3: Rewrite the fictional population**

把 `src/receipt/personas.py` 整檔換成：

```python
"""Deterministic fictional people to compare against; every shop, item and person here is made up."""
import random

from .signals import calendar_days

SEED = 20261007
MONTHS = ((2026, 3, 31), (2026, 4, 30))
PERIOD = tuple((year, month) for year, month, _ in MONTHS)
LETTERS = "ABCDE"
AWAY = ["屏東縣恆春鎮", "宜蘭縣宜蘭市", "屏東縣東港鎮"]

# A habit buys one item per visit. "merchant" may be a list paired one-to-one with "names".
# "days" is workday, offday, friday, long_weekend or any; "members" picks who in the type has the habit;
# "away" places the visits outside the person's own areas.
TYPES = [
    {"label": "省錢上班族", "areas": {"高雄市前鎮區": 6, "高雄市苓雅區": 4}, "habits": [
        {"category": 0, "merchant": "示範超商", "names": ["示範即期雞腿便當", "示範即期排骨便當", "示範即期咖哩飯"],
         "amount": (59, 79), "visits": (14, 18), "days": "workday"},
        {"category": 0, "merchant": "示範超商", "names": ["示範即期御飯糰"], "amount": (25, 35), "visits": (4, 6), "days": "offday"},
        {"category": 1, "merchant": "示範超商", "names": ["示範無糖綠茶", "示範無糖烏龍茶"], "amount": (20, 30), "visits": (10, 14),
         "days": "workday"},
        {"category": 8, "merchant": "示範量販", "names": ["示範衛生紙箱", "示範洗衣精家庭號", "示範牙膏量販包"], "amount": (300, 600),
         "visits": (2, 3), "days": "offday", "members": (0, 1, 2)},
        {"category": 8, "merchant": "示範超商", "names": ["示範衛生紙", "示範牙膏"], "amount": (45, 90), "visits": (3, 4),
         "members": (3, 4)},
    ]},
    {"label": "忙碌工程師", "areas": {"新竹市東區": 6, "新竹縣竹北市": 4}, "habits": [
        {"category": 0, "merchant": "示範超商", "names": ["示範鮪魚飯糰", "示範肉鬆飯糰", "示範火腿三明治"], "amount": (35, 60),
         "visits": (14, 18), "days": "workday"},
        {"category": 0, "merchant": "示範超商", "names": ["示範微波義大利麵", "示範微波炒飯"], "amount": (79, 99), "visits": (6, 9),
         "days": "workday"},
        {"category": 1, "merchant": "示範超商", "names": ["示範半糖拿鐵", "示範可樂"], "amount": (35, 65), "visits": (12, 16),
         "days": "workday"},
        {"category": 8, "merchant": "示範超商", "names": ["示範衛生紙", "示範牙刷", "示範洗面乳"], "amount": (39, 120), "visits": (3, 5)},
        {"category": 9, "merchant": "示範數位店", "names": ["示範機械鍵盤", "示範耳機", "示範傳輸線", "示範行動電源"],
         "amount": (300, 2500), "visits": (3, 4), "days": "offday"},
        {"category": 0, "merchant": "示範速食店", "names": ["示範雞排堡", "示範牛肉堡"], "amount": (120, 200), "visits": (3, 5),
         "days": "offday"},
        {"category": 1, "merchant": "示範居酒屋", "names": ["示範生啤酒"], "amount": (120, 180), "visits": (3, 4), "days": "friday",
         "members": (3, 4)},
    ]},
    {"label": "咖啡上班族", "areas": {"臺北市信義區": 6, "臺北市內湖區": 4}, "habits": [
        {"category": 1, "merchant": "示範精品咖啡", "names": ["示範冰美式", "示範熱美式"], "amount": (120, 160), "visits": (12, 16),
         "days": "workday", "members": (0, 1, 2)},
        {"category": 1, "merchant": "示範精品咖啡", "names": ["示範半糖拿鐵", "示範半糖焦糖拿鐵"], "amount": (130, 170),
         "visits": (12, 16), "days": "workday", "members": (3, 4)},
        {"category": 0, "merchant": ["示範簡餐店", "示範定食屋", "示範燴飯館"], "names": ["示範雞腿簡餐", "示範鮭魚定食", "示範牛肉燴飯"],
         "amount": (160, 260), "visits": (12, 15), "days": "workday"},
        {"category": 0, "merchant": "示範早午餐", "names": ["示範班尼迪克蛋", "示範鬆餅早午餐"], "amount": (280, 380), "visits": (3, 4),
         "days": "offday"},
        {"category": 2, "merchant": "示範精品咖啡", "names": ["示範可頌"], "amount": (70, 90), "visits": (3, 5), "days": "workday"},
    ]},
    {"label": "手搖學生", "areas": {"高雄市苓雅區": 6, "高雄市新興區": 4}, "habits": [
        {"category": 1, "merchant": ["示範茶屋", "示範果茶舖", "示範奶茶茶飲", "示範青茶坊"],
         "names": ["示範珍珠奶茶", "示範百香果茶", "示範黑糖珍珠鮮奶", "示範冬瓜青茶"], "amount": (45, 75), "visits": (12, 16),
         "members": (0, 1, 2)},
        {"category": 1, "merchant": ["示範茶屋", "示範果茶舖", "示範奶茶茶飲", "示範青茶坊"],
         "names": ["示範無糖綠茶", "示範無糖四季春", "示範無糖烏龍", "示範無糖青茶"], "amount": (35, 50), "visits": (12, 16),
         "members": (3, 4)},
        {"category": 2, "merchant": ["示範甜點店", "示範烘焙店", "示範豆花店"], "names": ["示範焦糖布丁", "示範肉桂捲", "示範花生豆花"],
         "amount": (50, 110), "visits": (5, 8)},
        {"category": 0, "merchant": ["示範餐坊", "示範麵館", "示範小吃店", "示範咖哩屋", "示範拉麵店", "示範越南小館", "示範韓式小館", "示範鬆餅屋"],
         "names": ["示範蔬食餐盒", "示範牛肉麵", "示範滷肉飯", "示範咖哩飯", "示範豚骨拉麵", "示範越南河粉", "示範石鍋拌飯", "示範鬆餅套餐"],
         "amount": (85, 140), "visits": (12, 16)},
        {"category": 5, "merchant": ["示範影城", "示範KTV", "示範桌遊店", "示範密室"],
         "names": ["示範電影票", "示範歡唱時段", "示範桌遊時段", "示範密室逃脫"], "amount": (250, 400), "visits": (2, 4), "days": "offday"},
        {"category": 6, "merchant": "示範客運", "names": ["示範客運票"], "amount": (40, 60), "visits": (5, 7), "days": "workday"},
        {"category": 4, "merchant": "示範運動館", "names": ["示範體適能體驗票"], "amount": (80, 100), "visits": (2, 3)},
        {"category": 8, "merchant": "示範文具店", "names": ["示範手帳", "示範筆記本"], "amount": (60, 120), "visits": (1, 3)},
    ]},
    {"label": "健身族", "areas": {"高雄市前鎮區": 5, "高雄市左營區": 5}, "habits": [
        {"category": 4, "merchant": "示範運動館", "names": ["示範重訓課", "示範健身入場"], "amount": (150, 300), "visits": (8, 10)},
        {"category": 4, "merchant": "示範運動館", "names": ["示範乳清蛋白粉"], "amount": (900, 1200), "visits": (1, 1)},
        {"category": 1, "merchant": "示範超商", "names": ["示範無糖豆漿", "示範無糖綠茶"], "amount": (25, 40), "visits": (8, 10)},
        {"category": 3, "merchant": "示範超市", "names": ["示範雞胸肉", "示範地瓜", "示範花椰菜", "示範雞蛋"], "amount": (80, 200),
         "visits": (6, 8), "days": "offday"},
        {"category": 0, "merchant": "示範餐坊", "names": ["示範雞肉餐盒", "示範舒肥雞沙拉"], "amount": (120, 160), "visits": (8, 10),
         "days": "workday"},
        {"category": 6, "merchant": "示範加油站", "names": ["示範95無鉛汽油"], "amount": (300, 600), "visits": (3, 4), "members": (3, 4)},
        {"category": 6, "merchant": "示範停車場", "names": ["示範停車費"], "amount": (40, 80), "visits": (4, 6), "members": (3, 4)},
    ]},
    {"label": "家庭下廚", "areas": {"桃園市中壢區": 7, "新北市板橋區": 3}, "habits": [
        {"category": 3, "merchant": "示範量販", "names": ["示範豬肉片", "示範雞腿肉", "示範高麗菜", "示範洋蔥", "示範雞蛋"],
         "amount": (150, 400), "visits": (8, 10), "days": "offday"},
        {"category": 3, "merchant": "示範量販", "names": ["示範醬油", "示範白米"], "amount": (90, 300), "visits": (2, 3), "days": "offday"},
        {"category": 8, "merchant": "示範量販", "names": ["示範衛生紙箱", "示範洗衣精家庭號", "示範洗碗精3入"], "amount": (300, 900),
         "visits": (3, 4), "days": "offday"},
        {"category": 6, "merchant": "示範加油站", "names": ["示範95無鉛汽油"], "amount": (800, 1500), "visits": (3, 4)},
        {"category": 0, "merchant": "示範水餃館", "names": ["示範韭菜豬肉水餃"], "amount": (150, 300), "visits": (2, 3)},
        {"category": 1, "merchant": "示範超商", "names": ["示範鮮奶"], "amount": (50, 90), "visits": (3, 5)},
        {"category": 8, "merchant": "示範寵物店", "names": ["示範犬用飼料", "示範狗零食"], "amount": (300, 900), "visits": (2, 3),
         "members": (0, 1, 2)},
        {"category": 8, "merchant": "示範寵物店", "names": ["示範貓飼料", "示範貓砂"], "amount": (250, 800), "visits": (2, 3),
         "members": (3, 4)},
    ]},
    {"label": "連假旅人", "areas": {"臺北市內湖區": 6, "新北市板橋區": 4}, "habits": [
        {"category": 7, "merchant": "示範旅宿", "names": ["示範旅店雙人房"], "amount": (1800, 3200), "visits": (2, 3),
         "days": "long_weekend", "away": AWAY, "members": (0, 1, 2)},
        {"category": 6, "merchant": "示範高鐵", "names": ["示範高鐵車票"], "amount": (700, 1500), "visits": (2, 2),
         "days": "long_weekend", "members": (0, 1, 2)},
        {"category": 0, "merchant": "示範海港餐廳", "names": ["示範海鮮套餐", "示範燒肉套餐"], "amount": (450, 900), "visits": (3, 4),
         "days": "long_weekend", "away": AWAY, "members": (0, 1, 2)},
        {"category": 7, "merchant": "示範旅宿", "names": ["示範旅店雙人房"], "amount": (1800, 3200), "visits": (1, 2),
         "days": "workday", "away": AWAY, "members": (3, 4)},
        {"category": 6, "merchant": "示範高鐵", "names": ["示範高鐵車票"], "amount": (700, 1500), "visits": (1, 1),
         "days": "workday", "members": (3, 4)},
        {"category": 0, "merchant": "示範海港餐廳", "names": ["示範海鮮套餐", "示範燒肉套餐"], "amount": (450, 900), "visits": (2, 3),
         "days": "workday", "away": AWAY, "members": (3, 4)},
        {"category": 0, "merchant": "示範便當店", "names": ["示範雞腿便當", "示範排骨便當"], "amount": (100, 140), "visits": (10, 13),
         "days": "workday"},
        {"category": 1, "merchant": "示範超商", "names": ["示範礦泉水", "示範無糖綠茶"], "amount": (20, 40), "visits": (4, 6)},
        {"category": 5, "merchant": "示範遊樂園", "names": ["示範遊樂園門票"], "amount": (600, 900), "visits": (1, 1), "days": "offday"},
    ]},
    {"label": "質感貓奴", "areas": {"臺北市信義區": 5, "臺北市內湖區": 5}, "habits": [
        {"category": 8, "merchant": "示範選物店", "names": ["示範香氛蠟燭", "示範擴香瓶", "示範陶瓷杯"], "amount": (300, 800),
         "visits": (2, 3), "days": "offday"},
        {"category": 8, "merchant": "示範文具店", "names": ["示範手帳", "示範鋼筆", "示範紙膠帶貼紙"], "amount": (120, 400),
         "visits": (2, 3)},
        {"category": 8, "merchant": "示範寵物店", "names": ["示範貓飼料", "示範貓砂", "示範貓罐頭"], "amount": (200, 700), "visits": (3, 4)},
        {"category": 1, "merchant": "示範咖啡", "names": ["示範燕麥拿鐵", "示範手沖咖啡"], "amount": (110, 160), "visits": (6, 9)},
        {"category": 1, "merchant": "示範餐酒館", "names": ["示範精釀啤酒", "示範調酒"], "amount": (200, 350), "visits": (3, 4),
         "days": "offday", "members": (0, 1, 2)},
        {"category": 0, "merchant": ["示範餐坊", "示範義式餐館"], "names": ["示範青醬燉飯", "示範番茄義大利麵"], "amount": (220, 320),
         "visits": (8, 10)},
    ]},
]
FRIENDS = (("小安", "咖啡上班族", 0), ("小宇", "咖啡上班族", 3), ("小林", "質感貓奴", 0))


def pick_days(rule, days, off, long_weekend):
    if rule == "workday":
        return [day for day in days if day not in off]
    if rule == "offday":
        return [day for day in days if day in off]
    if rule == "friday":
        return [day for day in days if day.weekday() == 4 and day not in off]
    if rule == "long_weekend":
        return [day for day in days if day in long_weekend]
    return days


def build_person(name, kind, member, code, rng, calendar):
    days, off, long_weekend = calendar_days(PERIOD, calendar)
    areas, weights = zip(*kind["areas"].items())
    rows = []
    for year, month in PERIOD:
        month_days = [day for day in days if day.month == month]
        for habit in kind["habits"]:
            if member not in habit.get("members", range(len(LETTERS))):
                continue
            pool = pick_days(habit.get("days", "any"), month_days, off, long_weekend)
            for _ in range(rng.randint(*habit["visits"]) if pool else 0):
                when = rng.choice(pool)
                pick = rng.randrange(len(habit["names"]))
                merchant = habit["merchant"][pick] if isinstance(habit["merchant"], list) else habit["merchant"]
                rows.append({
                    "date": when, "day": when.day, "invoice": f"{code}-{year}-{month:02}-{len(rows) + 1:03}",
                    "merchant": merchant,
                    "district": rng.choice(habit["away"]) if "away" in habit else rng.choices(areas, weights)[0],
                    "name": habit["names"][pick], "quantity": 1, "amount": rng.randint(*habit["amount"]),
                    "category": habit["category"], "provisional": False,
                })
    return {"name": name, "type": kind["label"], "rows": rows}


def build_personas(calendar, per_type=5, seed=SEED):
    rng = random.Random(seed)
    people = []
    for kind in TYPES:
        for member in range(per_type):
            people.append(build_person(f"{kind['label']} {LETTERS[member]}", kind, member, f"P{len(people) + 1:02}", rng, calendar))
    return people


def build_friends(calendar, seed=SEED):
    """小安、小宇 and 小林 for the friend comparison, made the same way as the fictional population."""
    kinds = {kind["label"]: kind for kind in TYPES}
    return [build_person(name, kinds[label], member, f"F{index + 1}", random.Random(seed + index + 1), calendar)
            for index, (name, label, member) in enumerate(FRIENDS)]
```

- [ ] **Step 4: Rewrite my demo purchases and their categories**

把 `src/receipt/demo.py` 整檔換成：

```python
"""Deterministic fictional purchases; never reads or transforms private records."""
import calendar

# One slot per kind of purchase: (shop and item pairs, price, visits in March, visits in April, district).
# Visits rotate through the pairs, so a slot can span several shops and dishes.
SLOTS = [
    ([("示範餐坊", "示範蔬食餐盒"), ("示範燉飯屋", "示範番茄燉飯"), ("示範麵館", "示範香菇湯麵"),
      ("示範咖哩屋", "示範蔬菜咖哩"), ("示範越南小館", "示範越南河粉"), ("示範韓式小館", "示範石鍋拌飯")],
     125, 13, 11, "高雄市苓雅區"),
    ([("示範茶屋", "示範花果茶"), ("示範果茶舖", "示範百香果茶"), ("示範青茶坊", "示範半糖冬瓜青茶")], 65, 9, 12, "高雄市苓雅區"),
    ([("示範烘焙店", "示範燕麥餅"), ("示範甜點店", "示範焦糖布丁"), ("示範豆花店", "示範花生豆花")], 85, 5, 4, "高雄市新興區"),
    ([("示範蔬果舖", "示範綜合蔬菜箱"), ("示範傳統市場", "示範有機蔬菜")], 230, 4, 5, "高雄市苓雅區"),
    ([("示範運動館", "示範體適能體驗票")], 90, 4, 6, "高雄市前鎮區"),
    ([("示範洗衣坊", "示範衣物清潔服務")], 180, 2, 1, "高雄市苓雅區"),
    ([("示範客運", "示範市區接駁票")], 45, 5, 7, "高雄市新興區"),
    ([("示範旅宿", "示範旅店雙人房")], 2100, 1, 1, "屏東縣恆春鎮"),
    ([("示範生活館", "示範環保清潔劑")], 160, 3, 2, "高雄市新興區"),
    ([("示範數位店", "示範無線滑鼠")], 780, 1, 1, "高雄市前鎮區"),
    ([("示範選物店", "示範未分類商品")], 75, 1, 1, "高雄市新興區"),
]


def build_demo(catalog):
    months = {}
    for month in (3, 4):
        key = f"2026-{month:02}"
        days = calendar.monthrange(2026, month)[1]
        rows = []
        for index, (pairs, price, march, april, district) in enumerate(SLOTS):
            for visit in range(march if month == 3 else april):
                merchant, name = pairs[visit % len(pairs)]
                rows.append({
                    "day": (index * 3 + visit * 5 + month) % days + 1,
                    "invoice": f"DEMO-{key}-{len(rows) + 1:03}",
                    "merchant": merchant, "district": district, "name": name, "quantity": 1,
                    "amount": price + (15 if month == 4 and index == 0 else 0),
                    **catalog[name],
                })
        first = rows[0]
        for name, amount in (("示範餐盒折扣", -25), ("示範隨餐贈品", 0)):
            rows.append({**first, "name": name, "amount": amount, **catalog[name]})
        months[key] = {"year": 2026, "monthNumber": month, "month": f"2026 年 {month} 月",
                       "days": days, "source": f"虛構示範資料（{month} 月）",
                       "rows": sorted(rows, key=lambda row: row["day"])}
    return months
```

把 `configs/item-categories.json` 整檔換成：

```json
{
  "示範蔬食餐盒": {"category": 0, "provisional": false},
  "示範番茄燉飯": {"category": 0, "provisional": false},
  "示範香菇湯麵": {"category": 0, "provisional": false},
  "示範蔬菜咖哩": {"category": 0, "provisional": false},
  "示範越南河粉": {"category": 0, "provisional": false},
  "示範石鍋拌飯": {"category": 0, "provisional": false},
  "示範花果茶": {"category": 1, "provisional": false},
  "示範百香果茶": {"category": 1, "provisional": false},
  "示範半糖冬瓜青茶": {"category": 1, "provisional": false},
  "示範燕麥餅": {"category": 2, "provisional": false},
  "示範焦糖布丁": {"category": 2, "provisional": false},
  "示範花生豆花": {"category": 2, "provisional": false},
  "示範綜合蔬菜箱": {"category": 3, "provisional": false},
  "示範有機蔬菜": {"category": 3, "provisional": false},
  "示範體適能體驗票": {"category": 4, "provisional": false},
  "示範衣物清潔服務": {"category": 5, "provisional": false},
  "示範市區接駁票": {"category": 6, "provisional": false},
  "示範旅店雙人房": {"category": 7, "provisional": false},
  "示範環保清潔劑": {"category": 8, "provisional": false},
  "示範無線滑鼠": {"category": 9, "provisional": false},
  "示範未分類商品": {"category": 10, "provisional": true},
  "示範餐盒折扣": {"category": 0, "provisional": false},
  "示範隨餐贈品": {"category": 0, "provisional": false}
}
```

- [ ] **Step 5: Build the population once in `build.py`**

`build_personas` 現在需要日曆，所以改由 `main()` 建立一次再傳給舊配對頁。

在 `src/receipt/build.py` 頂端，把

```python
from .tags import build_profile
```

換成

```python
from .tags import build_profile
from .traits import load_context
```

把 `build_matches` 的開頭

```python
def build_matches(months, categories, is_demo):
    """Profile the report and keep only the scores and words the match page shows."""
```

換成

```python
def build_matches(months, categories, is_demo, population):
    """Profile the report and keep only the scores and words the match page shows."""
```

同一個函式裡，把

```python
              for person in build_personas()]
```

換成

```python
              for person in population]
```

在 `main()` 裡，把

```python
    matches = build_matches(months, config["categories"], not args.private)
```

換成

```python
    context = load_context(ROOT)
    population = build_personas(context["calendar"])
    matches = build_matches(months, config["categories"], not args.private, population)
```

- [ ] **Step 6: Update the demo name count in the README**

在 `README.md` 第 58 行，把

```markdown
- `configs/item-categories.json` 包含 13 個虛構示範品名，其中未分類商品標記為暫定
```

換成

```markdown
- `configs/item-categories.json` 包含 23 個虛構示範品名，其中未分類商品標記為暫定
```

- [ ] **Step 7: Run all Python tests**

Run: `python -m unittest discover -s tests -v`
Expected: 全部 OK（`test_personas` 6 個、`test_build_report` 照常通過；舊配對頁使用新人物）

- [ ] **Step 8: Rebuild the public demo and run the Node tests**

Run: `python scripts/build_report.py`
Expected 輸出包含：

```text
2026-03 50 rows; total 7910
2026-04 53 rows; total 8095
match candidates: 5 of 40 fictional people
```

Run: `node --test tests/*.test.cjs`
Expected: 35 tests pass

- [ ] **Step 9: Commit**

```bash
git add src/receipt/personas.py src/receipt/demo.py configs/item-categories.json src/receipt/build.py README.md tests/test_personas.py invoice-insights.html
git commit -m "feat: give fictional people and my demo the details taste traits need" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 產生報告時印出品味相似度分布

**Files:**
- Modify: `src/receipt/build.py`
- Test: `tests/test_build_report.py`

**Interfaces:**
- Consumes: Task 1 的 `compare`、`percent`；Task 3 的 `build_vector`、`dated`、`relative`、`similarity_model`、`typical`；Task 4 的 `PERIOD`、`build_friends`
- Produces: `build.taste_summary(months, population, friends, context) -> (me: list | None, scores: list[float])`（`scores` 由低到高排序，不含無法比較的人）；終端機輸出一行 `taste similarity to N fictional people: highest X%, median Y%, lowest Z%`，或 `taste vector: not enough data to compare`

- [ ] **Step 1: Write the failing assertions**

在 `tests/test_build_report.py` 的 `test_default_build_ignores_private_sources_and_preserves_private_html` 裡，把

```python
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            html = (project / "invoice-insights.html").read_text(encoding="utf-8")
```

換成

```python
            result = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn("taste similarity to 40 fictional people", result.stdout)
            html = (project / "invoice-insights.html").read_text(encoding="utf-8")
```

在 `test_build_from_another_directory_is_self_contained_and_repeatable` 裡，把

```python
            first = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
```

換成

```python
            first = subprocess.run(command, cwd=folder, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            self.assertIn("taste vector: not enough data to compare", first.stdout)
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_build_report -v`
Expected: 2 個 FAIL，`AssertionError: 'taste similarity to 40 fictional people' not found in ...` 與 `'taste vector: not enough data to compare' not found in ...`

- [ ] **Step 3: Implement**

在 `src/receipt/build.py` 頂端，把

```python
from .personas import MONTHS, build_personas
```

換成

```python
from .personas import MONTHS, PERIOD, build_friends, build_personas
from .similarity import compare, percent
```

再把

```python
from .traits import load_context
```

換成

```python
from .traits import build_vector, dated, load_context, relative, similarity_model, typical
```

在 `def main():` 的正上方加入：

```python
def taste_summary(months, population, friends, context):
    """My taste vector and my similarity to each fictional person, all measured from the average person."""
    settings = context["traits"]
    raw = {person["name"]: build_vector(person["rows"], list(PERIOD), context) for person in population + friends}
    centers = typical([raw[person["name"]] for person in population], settings)
    rows, period = dated(months)
    me = relative(build_vector(rows, period, context), centers)
    model = similarity_model(settings)
    scores = [compare(me, relative(raw[person["name"]], centers), model)["score"] for person in population]
    return me, sorted(score for score in scores if score is not None)


```

在 `main()` 的最後一行

```python
    print("match candidates:", len(matches["candidates"]), "of", matches["population"], "fictional people")
```

後面加上：

```python
    me, scores = taste_summary(months, population, build_friends(context["calendar"]), context)
    if me is None or not scores:
        print("taste vector: not enough data to compare")
    else:
        middle = scores[len(scores) // 2]
        print(f"taste similarity to {len(scores)} fictional people: highest {percent(scores[-1])}%, "
              f"median {percent(middle)}%, lowest {percent(scores[0])}%")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_build_report -v`
Expected: 2 tests OK

Run: `python scripts/build_report.py`
Expected 最後一行：`taste similarity to 40 fictional people: highest 62%, median 8%, lowest -42%`

Run: `git status --short invoice-insights.html`
Expected: 沒有輸出（這個任務只多印一行，網頁內容不變）

- [ ] **Step 5: Commit**

```bash
git add src/receipt/build.py tests/test_build_report.py
git commit -m "feat: print how my taste compares with the fictional population" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 最終驗證（由主控執行，不交給子代理）

- [ ] **Step 1: 全部測試**

Run: `python -m unittest discover -s tests -v`
Expected: 74 tests OK

Run: `node --test tests/*.test.cjs`
Expected: 35 tests pass

- [ ] **Step 2: 產生結果可重現、只動到預期的檔案**

Run: `python scripts/build_report.py && git status --short`
Expected: 只看到未追蹤的 `report-data.js`（私人檔案，不加入 Git）；`invoice-insights.html` 沒有變動。

用瀏覽器打開 `invoice-insights.html`（雙擊即可），確認：消費回顧的 3 月 50 筆、4 月 53 筆照常顯示；「找到同好」配對頁照常開啟，列出新的虛構用戶；朋友比較頁照常顯示小安與小宇的品項連線圖。

- [ ] **Step 3: 用真實資料做冒煙測試（只印數量）**

只在記憶體中計算，不寫任何檔案，只印數量與分布，不印品名、店家或金額：

```bash
python - <<'EOF'
import json
from src.receipt.build import ROOT, taste_summary
from src.receipt.invoices import build_month
from src.receipt.personas import build_friends, build_personas
from src.receipt.similarity import percent
from src.receipt.traits import load_context

config = json.loads((ROOT / "data" / "private" / "report.json").read_text(encoding="utf-8"))
catalog = json.loads((ROOT / config["category_catalog"]).read_text(encoding="utf-8"))
months = dict(build_month(ROOT / name, catalog) for name in config["input_files"])
context = load_context(ROOT)
me, scores = taste_summary(months, build_personas(context["calendar"]), build_friends(context["calendar"]), context)
print("months:", len(months), "| vector:", "ready" if me else "not enough data",
      "| filled cells:", sum(value is not None for value in me) if me else 0)
if scores:
    print("comparable:", len(scores), "| highest", percent(scores[-1]), "| lowest", percent(scores[0]))
EOF
```

Expected: 印出月份數、向量是否足夠、有值的格數與分布；沒有任何品名或店家。把這兩行數字記下，第二段校準門檻時使用。

- [ ] **Step 4: 回報使用者**

回報 Task 1～5 的 commit、測試結果、Step 3 的數字。不要 push、不要合併：分支要等第二段（配對頁與神經網路連線圖）完成後才一起合併。
