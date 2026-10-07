# 配對頁簡化與分數統一 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 配對頁只列出最合拍的人，每人兩個標籤（最像你、最不像你），點進去看你和對方的連線圖；配對分數不含地區，地區只在沒有人到 80% 時由使用者選距離範圍才用；消費檔次改為估算每人每餐花費；報告動畫縮短為 18 秒。

**Architecture:** Python 在產生報告時算好配對分數（`matching.py`）、距離（行政區層級）與兩個標籤，嵌入配對頁；`match-filter.js` 的 `view()` 決定清單要顯示什麼，`match.html` 只負責畫出來。點卡片時，配對頁透過報告的 `ReceiptPages.showConnection(pair)` 開啟一個重用朋友比較頁原始碼的 iframe（配對模式）。

**Tech Stack:** Python 3.10+ 標準函式庫（`unittest`）、原生 HTML/CSS/JavaScript、Node.js 22 `node:test`

**Spec:** `docs/superpowers/specs/2026-10-07-match-simplify-design.md`（它取代的舊規格段落列在文件開頭；舊規格為 `docs/superpowers/specs/2026-10-07-tags-matching-design.md`）

## Global Constraints

- Python 只用標準函式庫；`pyproject.toml` 的 `dependencies = []` 不變。
- 不讀取、不修改 `data/` 底下任何檔案（私人資料）。唯一例外是 Task 7 Step 3 的冒煙測試：只在記憶體中執行、只印數量。
- 測試、設定、文件只用虛構店名（以「示範」或「測試」開頭）。範例行政區只用：高雄市苓雅區、高雄市新興區、高雄市前鎮區、高雄市左營區、臺北市信義區、臺北市內湖區、新北市板橋區、桃園市中壢區、新竹市東區、新竹縣竹北市、宜蘭縣宜蘭市、屏東縣恆春鎮、屏東縣東港鎮。
- 網頁只嵌入計算結果：不放虛構用戶的常消費地區、完整標籤或明細；「我」的部分只放行政區、標籤文字與 10 類筆數，不放完整地址或統編。
- 報告維持單一 HTML 檔、沒有外部資源。
- 配對頁與連線圖的資料一律用 `textContent` 或 DOM 節點寫入，不用 `innerHTML`。
- 權重：品類 0.35、品牌 0.15、葷素紀錄 0.1、消費檔次 0.1（不含地區）。門檻：`match` 0.8、`nearby` 0.7。消費檔次級距：小資型未滿 100 元、均衡型未滿 300 元、其餘享受型。
- 原始碼不得含控制字元（例如 NUL）；需要組合鍵時用 `JSON.stringify`，不要用 `\u0000` 這類跳脫字元。
- 在 `feature/tags-matching` 分支工作。只 `git add` 本任務列出的檔案（`docs/architecture.svg` 不屬於本計畫）。
- Commit 訊息用英文，結尾一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 指令都在專案根目錄 `D:\receipt` 用 Git Bash 執行：
  - Python 測試：`python -m unittest discover -s tests -v`
  - Node 測試：`node --test tests/*.test.cjs`
- Node 測試讀取根目錄已產生的 `invoice-insights.html`；改到 `src/web/*` 或會影響輸出的 `src/receipt/*` 後，要執行 `python scripts/build_report.py` 重新產生，並把它一起 commit。唯一例外是 Task 2（見該任務說明）。

## 校準結果（試做驗證，供參考）

以下參數已在試做中驗證：每位虛構用戶最接近的都是同類型；同類型 160 組全部 80% 以上，不同類型 1,400 組沒有任何一組達到 80%；示範的「我」對手搖學生 80%–96%、健身族 71%–75%，其他類型 58% 以下；示範的「我」的消費檔次為均衡型（每人每餐 125 元）。真實資料（只算數量）：0 位 80% 以上，4 位 70%–79%，同地區範圍內 4 位。

## 檔案結構

| 檔案 | 動作 | 責任 |
|---|---|---|
| `configs/tags.json` | 修改 | 消費檔次級距與餐飲分類（Task 1）；權重、門檻、地區分組（Task 2） |
| `src/receipt/tags.py` | 修改 | 每人每餐花費（Task 1）；標籤加比對用的 `key`、移除 `flavor_items`（Task 2） |
| `src/receipt/matching.py` | 改寫 | 配對分數、距離、最像你／最不像你、候選人輸出 |
| `src/receipt/build.py` | 修改 | 新的配對嵌入資料格式 |
| `src/web/match-filter.js` | 改寫 | `recommend()` 推薦規則與 `view()` 畫面內容 |
| `src/web/match.html` | 改寫 | 配對清單 |
| `src/web/taste-profile.js` | 修改 | 同張同品名只算一次；`fromPair()` 驗證配對資料 |
| `src/web/taste-comparison.html` | 修改 | 說明文字；配對模式 |
| `src/web/taste-navigation.js` | 修改 | 連線圖畫面與 `ReceiptPages` 新方法 |
| `src/web/invoice-insights.html` | 修改 | 匯出說明、連線圖容器、動畫時間軸 |
| `src/web/styles.css` | 修改 | 連線圖容器樣式 |
| `src/web/insights-ui.js` | 修改 | 動畫每段 6 秒 |
| `tests/test_tags.py`、`tests/test_personas.py`、`tests/test_build_report.py`、`tests/taste-profile.test.cjs`、`tests/comparison-interface.test.cjs` | 修改 | 既有測試補上新行為 |
| `tests/test_matching.py`、`tests/match-filter.test.cjs` | 改寫 | 新的配對與畫面規則 |
| `tests/page-navigation.test.cjs` | 新增 | 頁面切換 |
| `invoice-insights.html` | 重新產生 | 公開示範版 |

---

### Task 1: 消費檔次改為估算每人每餐花費

**Files:**
- Modify: `configs/tags.json`（`price_levels` 與新增 `meal`）
- Modify: `src/receipt/tags.py`（`build_profile` 的發票彙整與 `price_level`）
- Modify: `src/web/match.html`（「怎麼算的」其中一句）
- Test: `tests/test_tags.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: 報告明細格式（含 `quantity`、`category`、`provisional`）
- Produces: `profile["price_level"]` 改由每人每餐花費的中位數決定（0 小資型、1 均衡型、2 享受型、`None` 資料不足）；設定 `settings["meal"] = {"portion_category": "正餐", "food_categories": ["正餐", "飲品", "零食甜點"]}`

- [ ] **Step 1: Write the failing tests**

`tests/test_tags.py`：在 `test_shipped_settings_match_the_spec` 的 `self.assertEqual([level["label"] for level in SETTINGS["price_levels"]], ["小資型", "均衡型", "享受型"])` 之後加入：

```python
        self.assertEqual([level.get("below") for level in SETTINGS["price_levels"]], [100, 300, None])
        self.assertEqual(SETTINGS["meal"], {"portion_category": "正餐", "food_categories": ["正餐", "飲品", "零食甜點"]})
```

把 `test_price_level_uses_median_personal_invoice` 與 `test_shared_bills_stay_out_of_price_level` 兩個測試整段換成：

```python
    def test_price_level_divides_a_meal_bill_by_its_main_dishes(self):
        # Four people, four different hotpots and four drinks on each bill: 450 a head, not 1,800 a bill.
        rows = [row(f"H{i}", 0, amount=amount, name=name) for i in range(3)
                for name, amount in (("示範牛肉鍋", 420), ("示範雞肉鍋", 380), ("示範海鮮鍋", 450), ("示範蔬菜鍋", 350))]
        rows += [row(f"H{i}", 1, amount=200, name="示範紅茶", quantity=4) for i in range(3)]
        self.assertEqual(texts(profile_of(rows), "消費檔次"), ["享受型"])
        bentos = [row(f"B{i}", 0, amount=800, name="示範便當", quantity=4) for i in range(3)]
        self.assertEqual(texts(profile_of(bentos), "消費檔次"), ["均衡型"])

    def test_price_level_uses_the_median_meal(self):
        cheap, middle = SETTINGS["price_levels"][0]["below"], SETTINGS["price_levels"][1]["below"]

        def level(amounts):
            return texts(profile_of([row(f"I{i}", 0, amount=amount) for i, amount in enumerate(amounts)]), "消費檔次")

        self.assertEqual(level([cheap - 1, cheap - 1, middle + 1]), ["小資型"])
        self.assertEqual(level([cheap, cheap, middle + 1]), ["均衡型"])
        self.assertEqual(level([middle, middle, 1]), ["享受型"])
        self.assertEqual(level([middle, middle]), [])

    def test_drinks_and_discounts_on_a_meal_bill_count(self):
        # With the drink, D is 120 and the median is 120; without it the median would fall to 80.
        drinks = [row("D", 0, amount=80, name="示範便當"), row("D", 1, amount=40, name="示範紅茶"),
                  row("E", 0, amount=120), row("F", 0, amount=50)]
        self.assertEqual(texts(profile_of(drinks), "消費檔次"), ["均衡型"])
        # With the discount, G is 90 and the median is 95; without it the median would rise to 110.
        discounts = [row("G", 0, amount=110, name="示範便當"), row("G", 0, amount=-20, name="示範折扣"),
                     row("H", 0, amount=95), row("I", 0, amount=300)]
        self.assertEqual(texts(profile_of(discounts), "消費檔次"), ["小資型"])

    def test_bills_without_a_main_dish_stay_out_of_price_level(self):
        drinks = [row(f"T{i}", 1, amount=60, name="示範紅茶") for i in range(3)]
        gadgets = [row(f"G{i}", 9, amount=2000, name="示範耳機") for i in range(3)]
        self.assertEqual(texts(profile_of(drinks + gadgets), "消費檔次"), [])
        meals = [row(f"M{i}", 0, amount=120) for i in range(3)]
        self.assertEqual(texts(profile_of(drinks + gadgets + meals), "消費檔次"), ["均衡型"])
        unreviewed = [row(f"P{i}", 10, amount=120, provisional=True) for i in range(3)]
        self.assertEqual(texts(profile_of(unreviewed), "消費檔次"), [])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_tags -v`
Expected: FAIL — `test_shipped_settings_match_the_spec`（級距仍是 150／400）、`test_price_level_divides_a_meal_bill_by_its_main_dishes`、`test_drinks_and_discounts_on_a_meal_bill_count`、`test_bills_without_a_main_dish_stay_out_of_price_level`

- [ ] **Step 3: Implement**

`configs/tags.json`：把

```json
    {"label": "小資型", "below": 150},
    {"label": "均衡型", "below": 400},
```

改成

```json
    {"label": "小資型", "below": 100},
    {"label": "均衡型", "below": 300},
```

並在 `"remote_sellers": [...]` 那一行之前加入一行：

```json
  "meal": {"portion_category": "正餐", "food_categories": ["正餐", "飲品", "零食甜點"]},
```

`src/receipt/tags.py`：把 `build_profile` 中從 `enough_items = ...` 到 `personal = ...` 的這段

```python
    enough_items = len(valid) >= settings["category_min_items"]
    invoices = {}
    for row in rows:
        invoice = invoices.setdefault(row["invoice"], {
            "total": 0, "shared": False, "names": set(), "brand": brand_of(row["merchant"], brands),
            "district": None if is_remote(row["merchant"], settings["remote_sellers"]) else row.get("district")})
        invoice["total"] += row["amount"]
        if row["amount"] > 0:
            # Several portions of one item suggest the bill also covered other people.
            invoice["shared"] |= row["quantity"] >= 2 or row["name"] in invoice["names"]
            invoice["names"].add(row["name"])
    paid = [invoice for invoice in invoices.values() if invoice["total"] > 0]
    personal = [invoice for invoice in paid if not invoice["shared"]]
```

改成

```python
    enough_items = len(valid) >= settings["category_min_items"]
    portion = names.index(settings["meal"]["portion_category"])
    food = {names.index(name) for name in settings["meal"]["food_categories"]}
    invoices = {}
    for row in rows:
        invoice = invoices.setdefault(row["invoice"], {
            "total": 0, "food": 0, "portions": 0, "brand": brand_of(row["merchant"], brands),
            "district": None if is_remote(row["merchant"], settings["remote_sellers"]) else row.get("district")})
        invoice["total"] += row["amount"]
        if not row["provisional"] and row["category"] in food:
            invoice["food"] += row["amount"]
            # Main-dish portions stand in for the number of people a bill fed.
            if row["category"] == portion and row["amount"] > 0:
                invoice["portions"] += row["quantity"]
    paid = [invoice for invoice in invoices.values() if invoice["total"] > 0]
    meals = [invoice["food"] / invoice["portions"] for invoice in invoices.values()
             if invoice["portions"] and invoice["food"] > 0]
```

並把 `profile` 字典中的

```python
        "price_level": level_of(median(invoice["total"] for invoice in personal), settings["price_levels"])
        if len(personal) >= minimum else None,
```

改成

```python
        "price_level": level_of(median(meals), settings["price_levels"]) if len(meals) >= minimum else None,
```

`src/web/match.html`：把

```js
    make('p', '同一張發票的同一品項只算一次；有品項買 2 份以上的發票，可能是多人一起消費，不列入消費檔次。'),
```

改成

```js
    make('p', '同一張發票的同一品項只算一次。消費檔次用每張發票的正餐份數估計幾人份，再看每人每餐花多少；合菜會讓每人金額偏低。'),
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_tags -v`
Expected: 16 tests OK

Run: `python -m unittest discover -s tests -v`
Expected: 45 tests OK（虛構用戶的校準測試照樣通過）

- [ ] **Step 5: Rebuild the public demo**

Run: `python scripts/build_report.py`
Expected: `2026-03 50 rows; total 7910`、`2026-04 53 rows; total 8095`、`match candidates: 10 of 40 fictional people`

Run: `node --test tests/*.test.cjs`
Expected: `# pass 18`、`# fail 0`

- [ ] **Step 6: Commit**

```bash
git add configs/tags.json src/receipt/tags.py src/web/match.html tests/test_tags.py invoice-insights.html
git commit -F - <<'EOF'
feat: estimate spending per person per meal for the price level

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: 配對分數不含地區、距離與兩個標籤

**Files:**
- Modify: `configs/tags.json`（`weights`、`thresholds`、新增 `regions`）
- Modify: `src/receipt/tags.py`（葷素統計、`describe`）
- Rewrite: `src/receipt/matching.py`
- Modify: `src/receipt/build.py`（import 與 `build_matches`）
- Test: `tests/test_tags.py`、`tests/test_matching.py`（改寫）、`tests/test_personas.py`（改寫）、`tests/test_build_report.py`

本任務**不要**重新產生 `invoice-insights.html`：舊的配對頁讀不了新的資料格式，Task 3 改完配對頁後再一起產生。根目錄的 `invoice-insights.html` 在本任務結束時仍是 Task 1 的版本，Node 測試照樣通過。

**Interfaces:**
- Consumes: Task 1 的 `price_level`
- Produces:
  - 每個標籤多一個鍵 `key`：品類偏好為分類名稱、常消費地區為行政區、常去品牌為品牌、消費檔次為級距名稱、葷素紀錄為標籤文字
  - 個人檔案不再有 `flavor_items`
  - `matching.compare(me, other, settings) -> {"parts": {"category", "brand", "flavor", "price"}, "comparable": bool, "score": float | None}`
  - `matching.weighted(parts, weights) -> float | None`
  - `matching.place_distance(a, b, regions) -> int`（0 同一區、1 同縣市、2 同地區、3 其他）
  - `matching.distance(mine, theirs, regions) -> int`（任一方沒有地區時為 3）
  - `matching.most_alike(me, other)`、`matching.least_alike(me, other) -> {"dimension", "text"} | None`
  - `matching.eligible(me, candidates, settings) -> list[{"name", "score", "distance", "like", "unlike", "counts"}]`（`score` 為整數百分比，只含配對分數至少 70% 的人，依分數高到低、同分依名稱）
  - 嵌入資料 `matchReportData`：頂層新增 `personaMonths`；`settings` 多 `price_levels`；`me` 為 `{"ready", "item_count", "months", "areas", "tags": [{"dimension", "text"}], "counts"}`

- [ ] **Step 1: Write the failing tests**

`tests/test_tags.py`：在 `test_shipped_settings_match_the_spec` 中，把

```python
        self.assertAlmostEqual(sum(SETTINGS["weights"].values()), 1)
        self.assertEqual(SETTINGS["thresholds"], {"taste": 0.8, "taste_same_area": 0.7})
```

改成

```python
        self.assertEqual(SETTINGS["weights"], {"category": 0.35, "brand": 0.15, "flavor": 0.1, "price": 0.1})
        self.assertEqual(SETTINGS["thresholds"], {"match": 0.8, "nearby": 0.7})
        cities = [city for group in SETTINGS["regions"].values() for city in group]
        self.assertEqual(len(set(cities)), 22)
        self.assertTrue(all(len(city) == 3 for city in cities))
```

刪掉 `test_flavor_tag_describes_purchases` 中的這一行：

```python
        self.assertEqual(profile["flavor_items"], {"示範水餃館": {"示範鮮蝦水餃": 1}})
```

並在 `def test_flavor_tag_describes_purchases(self):` 之前加入：

```python
    def test_tags_carry_comparison_keys(self):
        rows = [row(f"S{i}", 0, merchant="統一超商股份有限公司示範門市", name="示範素食便當") for i in range(10)]
        keys = {(tag["dimension"], tag["key"]) for tag in profile_of(rows)["tags"]}
        self.assertEqual(keys, {("品類偏好", "正餐"), ("常消費地區", "高雄市苓雅區"), ("常去品牌", "7-ELEVEN"),
                                ("消費檔次", "均衡型"), ("葷素紀錄", "素食品項較多")})

```

把 `tests/test_matching.py` 整檔改成：

```python
"""Scores, distances and the two tags shown for each match, on hand-made profiles."""
import json
import unittest
from pathlib import Path

from src.receipt.matching import (compare, distance, eligible, least_alike, most_alike, overlap, place_distance,
                                  ready, weighted)
from src.receipt.tags import build_profile, describe

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
NAMES = [category["name"] for category in CATEGORIES]
REGIONS = SETTINGS["regions"]


def profile(**changes):
    base = {"item_count": 10, "category_counts": [5, 5, 0, 0, 0, 0, 0, 0, 0, 0], "top_categories": [0, 1],
            "district_shares": {"高雄市苓雅區": 1.0}, "areas": ["高雄市苓雅區"],
            "brand_shares": {"示範茶屋": 1.0}, "frequent_brands": [("示範茶屋", 5)],
            "price_level": 0, "meat_ratio": 0.0}
    base.update(changes)
    base["tags"] = describe(base, NAMES, SETTINGS)
    return base


def neighbour():
    """Shops in the same district but buys entirely different things."""
    return profile(category_counts=[0, 0, 0, 0, 0, 0, 0, 0, 0, 10], top_categories=[9],
                   brand_shares={"示範數位店": 1.0}, frequent_brands=[("示範數位店", 5)], price_level=2, meat_ratio=1.0)


def tag(dimension, text):
    return {"dimension": dimension, "text": text}


class ScoreTests(unittest.TestCase):
    def test_identical_profiles_score_full_marks(self):
        result = compare(profile(), profile(), SETTINGS)
        self.assertTrue(result["comparable"])
        self.assertAlmostEqual(result["score"], 1)

    def test_area_does_not_change_the_score(self):
        far = profile(district_shares={"臺北市信義區": 1.0}, areas=["臺北市信義區"])
        result = compare(profile(), far, SETTINGS)
        self.assertAlmostEqual(result["score"], compare(profile(), profile(), SETTINGS)["score"])
        self.assertNotIn("district", result["parts"])

    def test_overlap_is_histogram_intersection(self):
        self.assertAlmostEqual(overlap({"A": 0.6, "B": 0.4}, {"A": 0.3, "C": 0.7}), 0.3)
        self.assertIsNone(overlap({}, {"A": 1.0}))

    def test_missing_parts_hand_their_weight_to_the_rest(self):
        weights = SETTINGS["weights"]
        parts = {"category": 1.0, "brand": None, "flavor": 0.0, "price": None}
        self.assertAlmostEqual(weighted(parts, weights), weights["category"] / (weights["category"] + weights["flavor"]))
        self.assertIsNone(weighted(dict.fromkeys(parts), weights))

    def test_price_and_flavor_similarity(self):
        result = compare(profile(price_level=0, meat_ratio=0.0), profile(price_level=2, meat_ratio=1.0), SETTINGS)
        self.assertEqual(result["parts"]["price"], 0)
        self.assertEqual(result["parts"]["flavor"], 0)
        result = compare(profile(price_level=1, meat_ratio=None), profile(price_level=2), SETTINGS)
        self.assertEqual(result["parts"]["price"], 0.5)
        self.assertIsNone(result["parts"]["flavor"])

    def test_category_is_required(self):
        result = compare(profile(category_counts=None, top_categories=[]), profile(), SETTINGS)
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["score"])

    def test_one_more_dimension_is_required(self):
        bare = profile(brand_shares={}, frequent_brands=[], meat_ratio=None, price_level=None)
        self.assertFalse(compare(bare, profile(), SETTINGS)["comparable"])
        self.assertFalse(ready(bare))
        self.assertTrue(ready(dict(bare, price_level=1)))
        self.assertFalse(ready(profile(category_counts=None)))

    def test_three_uncategorized_invoices_cannot_be_compared(self):
        rows = [{"day": 1, "invoice": f"U{i}", "merchant": "測試小店", "district": "高雄市苓雅區", "name": "測試未分類",
                 "quantity": 1, "amount": 120, "category": 10, "provisional": True} for i in range(3)]
        sparse = build_profile(rows, CATEGORIES, BRANDS, SETTINGS)
        result = compare(sparse, sparse, SETTINGS)
        self.assertFalse(result["comparable"])
        self.assertIsNone(result["score"])
        self.assertFalse(ready(sparse))


class DistanceTests(unittest.TestCase):
    def test_place_distance_steps_up_by_administrative_level(self):
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市苓雅區", REGIONS), 0)
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市前鎮區", REGIONS), 1)
        self.assertEqual(place_distance("高雄市苓雅區", "屏東縣恆春鎮", REGIONS), 2)
        self.assertEqual(place_distance("臺北市信義區", "新北市板橋區", REGIONS), 2)
        self.assertEqual(place_distance("宜蘭縣宜蘭市", "臺北市內湖區", REGIONS), 2)
        self.assertEqual(place_distance("高雄市苓雅區", "臺北市信義區", REGIONS), 3)

    def test_distance_takes_the_closest_pair_of_areas(self):
        self.assertEqual(distance(["高雄市苓雅區", "臺北市信義區"], ["新北市板橋區"], REGIONS), 2)
        self.assertEqual(distance([], ["高雄市苓雅區"], REGIONS), 3)
        self.assertEqual(distance(["高雄市苓雅區"], [], REGIONS), 3)


class TagPickTests(unittest.TestCase):
    def test_most_alike_checks_brand_flavor_price_then_category(self):
        me = profile()
        self.assertEqual(most_alike(me, profile(price_level=1, meat_ratio=1.0)), tag("常去品牌", "示範茶屋（5 次）"))
        other_store = {"brand_shares": {"示範超商": 1.0}, "frequent_brands": [("示範超商", 5)]}
        self.assertEqual(most_alike(me, profile(**other_store)), tag("葷素紀錄", "素食品項較多"))
        self.assertEqual(most_alike(me, profile(**other_store, meat_ratio=1.0)), tag("消費檔次", "小資型"))
        self.assertEqual(most_alike(me, profile(**other_store, meat_ratio=1.0, price_level=2)),
                         tag("品類偏好", "常買正餐（50%）"))

    def test_least_alike_checks_flavor_price_brand_then_category(self):
        me = profile()
        self.assertEqual(least_alike(me, profile(meat_ratio=1.0)), tag("葷素紀錄", "葷食品項較多"))
        self.assertEqual(least_alike(me, profile(price_level=2)), tag("消費檔次", "享受型"))
        self.assertEqual(least_alike(me, profile(frequent_brands=[("示範茶屋", 5), ("示範水餃館", 4)])),
                         tag("常去品牌", "示範水餃館（4 次）"))
        self.assertEqual(least_alike(me, profile(category_counts=[5, 0, 5, 0, 0, 0, 0, 0, 0, 0], top_categories=[0, 2])),
                         tag("品類偏好", "常買零食甜點（50%）"))
        self.assertIsNone(least_alike(me, profile()))

    def test_areas_never_explain_a_match(self):
        stranger = neighbour()
        self.assertEqual(stranger["areas"], profile()["areas"])
        self.assertIsNone(most_alike(profile(), stranger))
        self.assertEqual(least_alike(profile(), stranger), tag("葷素紀錄", "葷食品項較多"))

    def test_labels_i_lack_cannot_differ(self):
        me = profile(meat_ratio=None, price_level=None)
        other = profile(meat_ratio=1.0, price_level=2)
        self.assertIsNone(least_alike(me, other))
        self.assertEqual(most_alike(me, other), tag("常去品牌", "示範茶屋（5 次）"))


class EligibleTests(unittest.TestCase):
    def test_eligible_keeps_seventy_and_up_sorted_by_score(self):
        candidates = [{"name": f"示範用戶 {i}", "profile": profile(price_level=i % 3)} for i in range(4)]
        candidates += [
            {"name": "示範遠方", "profile": profile(district_shares={"臺北市信義區": 1.0}, areas=["臺北市信義區"])},
            {"name": "示範鄰居", "profile": neighbour()},
            {"name": "示範資料不足", "profile": profile(category_counts=None, top_categories=[])},
            {"name": "示範中間", "profile": profile(brand_shares={"示範超商": 1.0}, frequent_brands=[("示範超商", 5)],
                                                 meat_ratio=0.5)},
        ]
        result = eligible(profile(), candidates, SETTINGS)
        self.assertEqual([(match["name"], match["score"]) for match in result],
                         [("示範用戶 0", 100), ("示範用戶 3", 100), ("示範遠方", 100), ("示範用戶 1", 93),
                          ("示範用戶 2", 86), ("示範中間", 71)])
        self.assertEqual(set(result[0]), {"name", "score", "distance", "like", "unlike", "counts"})
        self.assertEqual([match["distance"] for match in result[:3]], [0, 0, 3])
        self.assertEqual(result[0]["counts"], [5, 5, 0, 0, 0, 0, 0, 0, 0, 0])
        self.assertEqual(result[-1]["like"], tag("消費檔次", "小資型"))
        self.assertEqual(result[-1]["unlike"], tag("葷素紀錄", "葷素品項都有"))


if __name__ == "__main__":
    unittest.main()
```

把 `tests/test_personas.py` 整檔改成：

```python
"""The fictional population separates types at the match threshold and leaves nearby people for a distance choice."""
import json
import unittest
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.matching import compare, eligible
from src.receipt.personas import build_personas
from src.receipt.tags import build_profile, percent

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
CATALOG = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = build_personas()
        cls.profiles = {person["name"]: build_profile(person["rows"], CATEGORIES, BRANDS, SETTINGS) for person in cls.people}
        demo_rows = [row for month in build_demo(CATALOG).values() for row in month["rows"]]
        cls.me = build_profile(demo_rows, CATEGORIES, BRANDS, SETTINGS)
        candidates = [{"name": name, "profile": profile} for name, profile in cls.profiles.items()]
        cls.pool = eligible(cls.me, candidates, SETTINGS)

    def test_forty_reproducible_fictional_people(self):
        self.assertEqual(len(self.people), 40)
        self.assertEqual(build_personas(), self.people)
        self.assertEqual(len({person["type"] for person in self.people}), 8)
        self.assertTrue(all(row["merchant"].startswith("示範") and row["name"].startswith("示範")
                            for person in self.people for row in person["rows"]))

    def test_everyone_is_closest_to_their_own_type(self):
        for person in self.people:
            mine = self.profiles[person["name"]]
            best = max((other for other in self.people if other is not person),
                       key=lambda other: compare(mine, self.profiles[other["name"]], SETTINGS)["score"])
            self.assertEqual(best["type"], person["type"], person["name"])

    def test_types_separate_at_the_match_threshold(self):
        bar = percent(SETTINGS["thresholds"]["match"])
        for person in self.people:
            for other in self.people:
                if other is person:
                    continue
                score = percent(compare(self.profiles[person["name"]], self.profiles[other["name"]], SETTINGS)["score"])
                if person["type"] == other["type"]:
                    self.assertGreaterEqual(score, bar, (person["name"], other["name"]))
                else:
                    self.assertLess(score, bar, (person["name"], other["name"]))

    def test_least_alike_names_the_flavor_gap(self):
        found = next(candidate for candidate in self.pool if candidate["name"] == "手搖學生 D")
        self.assertEqual(found["unlike"], {"dimension": "葷素紀錄", "text": "葷食品項較多"})

    def test_neighbours_with_other_tastes_are_not_candidates(self):
        pool = {candidate["name"] for candidate in self.pool}
        for person in self.people:
            if person["type"] == "3C 玩家":
                self.assertTrue(set(self.profiles[person["name"]]["areas"]) & set(self.me["areas"]), person["name"])
                self.assertNotIn(person["name"], pool)

    def test_nearby_people_wait_for_a_distance_choice(self):
        high = [c["name"] for c in self.pool if c["score"] >= 80]
        band = [c for c in self.pool if 70 <= c["score"] < 80 and c["distance"] == 0]
        self.assertEqual(high, ["手搖學生 A", "手搖學生 B", "手搖學生 C", "手搖學生 D", "手搖學生 E"])
        self.assertGreaterEqual(len(band), 1)


if __name__ == "__main__":
    unittest.main()
```

`tests/test_build_report.py`：在 `test_default_build_ignores_private_sources_and_preserves_private_html` 中，把

```python
            self.assertEqual(payload["settings"]["thresholds"], {"taste": 0.8, "taste_same_area": 0.7})
            self.assertTrue(payload["me"]["ready"])
            self.assertEqual(payload["me"]["areas"], ["高雄市苓雅區", "高雄市新興區"])
            self.assertGreaterEqual(len(payload["candidates"]), 1)
```

改成

```python
            self.assertEqual(payload["settings"]["thresholds"], {"match": 0.8, "nearby": 0.7})
            self.assertEqual(payload["personaMonths"], ["2026-03", "2026-04"])
            self.assertTrue(payload["me"]["ready"])
            self.assertEqual(payload["me"]["months"], ["2026-03", "2026-04"])
            self.assertEqual(payload["me"]["areas"], ["高雄市苓雅區", "高雄市新興區"])
            self.assertEqual(len(payload["me"]["counts"]), 10)
            self.assertTrue(all(set(tag) == {"dimension", "text"} for tag in payload["me"]["tags"]))
            self.assertGreaterEqual(len(payload["candidates"]), 1)
            self.assertEqual(set(payload["candidates"][0]), {"name", "score", "distance", "like", "unlike", "counts"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL／ERROR — `test_matching` 無法匯入 `distance`；`test_personas` 的 `setUpClass` 因 `eligible()` 參數不同而出錯；`test_tags` 的設定與 `key` 測試失敗；`test_build_report` 的門檻名稱不符

- [ ] **Step 3: Implement**

`configs/tags.json`：把

```json
  "weights": {"category": 0.35, "district": 0.3, "brand": 0.15, "flavor": 0.1, "price": 0.1},
  "thresholds": {"taste": 0.8, "taste_same_area": 0.7},
```

改成

```json
  "weights": {"category": 0.35, "brand": 0.15, "flavor": 0.1, "price": 0.1},
  "thresholds": {"match": 0.8, "nearby": 0.7},
  "regions": {
    "北部": ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"],
    "中部": ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
    "南部": ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"],
    "東部": ["花蓮縣", "臺東縣"],
    "離島": ["澎湖縣", "金門縣", "連江縣"]
  },
```

`src/receipt/tags.py`：把

```python
    flavored, flavor_items = [], {}
    for row in valid:
        if names[row["category"]] not in flavor["categories"]:
            continue
        value = flavor_of(row["name"], flavor)
        if value is None:
            continue
        flavored.append(value)
        brand = brand_of(row["merchant"], brands)
        if brand:
            items = flavor_items.setdefault(brand, {})
            items[row["name"]] = items.get(row["name"], 0) + 1
```

改成

```python
    judged = [flavor_of(row["name"], flavor) for row in valid if names[row["category"]] in flavor["categories"]]
    flavored = [value for value in judged if value is not None]
```

刪掉 `profile` 字典中的這一行：

```python
        "flavor_items": flavor_items,
```

並把整個 `describe` 函式改成：

```python
def describe(profile, names, settings):
    """Tags in display order; two tags of one dimension are the same when their keys match."""
    counts, tags = profile["category_counts"], []
    if counts:
        total = sum(counts)
        tags += [{"dimension": "品類偏好", "key": names[index], "text": f"常買{names[index]}（{percent(counts[index] / total)}%）"}
                 for index in profile["top_categories"]]
    tags += [{"dimension": "常消費地區", "key": area, "text": area} for area in profile["areas"]]
    tags += [{"dimension": "常去品牌", "key": brand, "text": f"{brand}（{count} 次）"}
             for brand, count in profile["frequent_brands"]]
    if profile["price_level"] is not None:
        level = settings["price_levels"][profile["price_level"]]["label"]
        tags.append({"dimension": "消費檔次", "key": level, "text": level})
    label = flavor_label(profile["meat_ratio"], settings["flavor"])
    if label:
        tags.append({"dimension": "葷素紀錄", "key": label, "text": label})
    return tags
```

把 `src/receipt/matching.py` 整檔改成：

```python
"""Score how alike two purchase profiles are, pick the tags that show it, and measure how far apart they shop."""
import math

from .tags import percent

TASTE = ("category", "brand", "flavor", "price")
# The other person's tags are checked one dimension at a time, in these orders. Areas never explain a match:
# they come from seller addresses, so they only matter once someone chooses a distance on the page.
LIKE = ("常去品牌", "葷素紀錄", "消費檔次", "品類偏好")
UNLIKE = ("葷素紀錄", "消費檔次", "常去品牌", "品類偏好")
LABELED = ("葷素紀錄", "消費檔次")  # a label I lack cannot differ from theirs


def overlap(a, b):
    """Histogram intersection of two share maps, or None when either side lacks data."""
    if not a or not b:
        return None
    return sum(min(value, b.get(key, 0)) for key, value in a.items())


def similarities(me, other, settings):
    mine, theirs = me["category_counts"], other["category_counts"]
    category = None
    if mine and theirs:
        norm = math.hypot(*mine) * math.hypot(*theirs)
        category = min(1.0, sum(x * y for x, y in zip(mine, theirs)) / norm) if norm else None
    span = len(settings["price_levels"]) - 1
    price = None
    if me["price_level"] is not None and other["price_level"] is not None:
        price = 1 - abs(me["price_level"] - other["price_level"]) / span if span else 1.0
    flavor = None
    if me["meat_ratio"] is not None and other["meat_ratio"] is not None:
        flavor = 1 - abs(me["meat_ratio"] - other["meat_ratio"])
    return {"category": category, "brand": overlap(me["brand_shares"], other["brand_shares"]),
            "flavor": flavor, "price": price}


def weighted(parts, weights):
    """Weighted mean of the available parts; missing parts hand their weight to the rest."""
    available = [name for name in weights if parts[name] is not None]
    weight = sum(weights[name] for name in available)
    return sum(weights[name] * parts[name] for name in available) / weight if weight else None


def ready(profile):
    """Enough data to be matched at all: category plus one more dimension."""
    return profile["category_counts"] is not None and (
        bool(profile["brand_shares"]) or profile["meat_ratio"] is not None or profile["price_level"] is not None)


def compare(me, other, settings):
    parts = similarities(me, other, settings)
    # Category is required, plus at least one more dimension, so thin data cannot score 100%.
    comparable = parts["category"] is not None and any(parts[name] is not None for name in TASTE[1:])
    return {"parts": parts, "comparable": comparable,
            "score": weighted(parts, settings["weights"]) if comparable else None}


def place_distance(a, b, regions):
    """0 for the same district, 1 for the same city or county, 2 for the same region, 3 otherwise."""
    if a == b:
        return 0
    if a[:3] == b[:3]:
        return 1
    region = {city: name for name, cities in regions.items() for city in cities}
    return 2 if region.get(a[:3]) is not None and region.get(a[:3]) == region.get(b[:3]) else 3


def distance(mine, theirs, regions):
    """The closest pair of frequent areas; 3 when either side has none."""
    return min((place_distance(a, b, regions) for a in mine for b in theirs), default=3)


def shown(tag):
    return {"dimension": tag["dimension"], "text": tag["text"]}


def most_alike(me, other):
    """The other person's first tag that I share, checked in LIKE order."""
    mine = {(tag["dimension"], tag["key"]) for tag in me["tags"]}
    return next((shown(tag) for dimension in LIKE for tag in other["tags"]
                 if tag["dimension"] == dimension and (dimension, tag["key"]) in mine), None)


def least_alike(me, other):
    """The other person's first tag that I do not share, checked in UNLIKE order."""
    mine = {(tag["dimension"], tag["key"]) for tag in me["tags"]}
    have = {tag["dimension"] for tag in me["tags"]}
    return next((shown(tag) for dimension in UNLIKE for tag in other["tags"]
                 if tag["dimension"] == dimension and (dimension, tag["key"]) not in mine
                 and (dimension not in LABELED or dimension in have)), None)


def eligible(me, candidates, settings):
    """Everyone at or above the nearby threshold, best first; the page decides who is shown."""
    floor = percent(settings["thresholds"]["nearby"])
    scored = []
    for candidate in candidates:
        result = compare(me, candidate["profile"], settings)
        if result["comparable"] and percent(result["score"]) >= floor:
            scored.append((percent(result["score"]), candidate))
    scored.sort(key=lambda pair: (-pair[0], pair[1]["name"]))
    return [{
        "name": candidate["name"], "score": score,
        "distance": distance(me["areas"], candidate["profile"]["areas"], settings["regions"]),
        "like": most_alike(me, candidate["profile"]), "unlike": least_alike(me, candidate["profile"]),
        "counts": candidate["profile"]["category_counts"],
    } for score, candidate in scored]
```

`src/receipt/build.py`：把 `from .personas import build_personas` 改成 `from .personas import MONTHS, build_personas`，並把 `build_matches` 中從 `people = [...]` 之後到函式結尾的

```python
    names = [category["name"] for category in categories]
    return {
        "isDemo": is_demo, "population": len(people),
        "settings": {key: settings[key] for key in ("weights", "thresholds", "top_matches", "category_min_items")},
        "me": {"ready": ready(me), "item_count": me["item_count"], "areas": me["areas"], "tags": me["tags"]},
        "candidates": eligible(me, people, names, settings) if ready(me) else [],
    }
```

改成

```python
    return {
        "isDemo": is_demo, "population": len(people),
        "personaMonths": [f"{year}-{month:02}" for year, month, _ in MONTHS],
        "settings": {key: settings[key] for key in ("weights", "thresholds", "price_levels", "top_matches", "category_min_items")},
        "me": {"ready": ready(me), "item_count": me["item_count"], "months": sorted(months), "areas": me["areas"],
               "tags": [{"dimension": tag["dimension"], "text": tag["text"]} for tag in me["tags"]],
               "counts": me["category_counts"]},
        "candidates": eligible(me, people, settings) if ready(me) else [],
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest discover -s tests -v`
Expected: 51 tests OK

Run: `node --test tests/*.test.cjs`
Expected: `# pass 18`、`# fail 0`（根目錄的報告仍是 Task 1 的版本）

- [ ] **Step 5: Commit**

```bash
git add configs/tags.json src/receipt/tags.py src/receipt/matching.py src/receipt/build.py tests/test_tags.py tests/test_matching.py tests/test_personas.py tests/test_build_report.py
git commit -F - <<'EOF'
feat: score matches without areas and pick two tags from the other person

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: 配對頁

**Files:**
- Rewrite: `src/web/match-filter.js`
- Rewrite: `src/web/match.html`
- Test: `tests/match-filter.test.cjs`（改寫）
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 2 的嵌入資料 `matchReportData`
- Produces:
  - `MatchFilter.recommend(candidates, maxDistance, thresholds)`：有人達到 `match` 門檻時只回傳這些人（忽略距離）；否則 `maxDistance` 為 `null` 時回傳 `[]`；否則回傳配對分數達到 `nearby` 門檻且 `distance <= maxDistance` 的人；保留原順序
  - `MatchFilter.view(data, maxDistance) -> {"status", "note", "options": [{"level", "label", "count", "disabled"}], "cards": [{"candidate", "place"}], "empty"}`
  - 卡片點擊時呼叫 `window.parent.ReceiptPages.showConnection?.(pair)`；`pair` 格式為 `{"score", "left": {"name": "你", "demo", "months", "counts"}, "right": {"name", "demo": true, "months": personaMonths, "counts"}}`（報告端在 Task 5 才提供這個方法，在那之前點擊不會有反應）

- [ ] **Step 1: Write the failing test**

把 `tests/match-filter.test.cjs` 整檔改成：

```js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { recommend, view } = require('../src/web/match-filter.js');

const thresholds = { match: 0.8, nearby: 0.7 };
const settings = { thresholds, top_matches: 5, category_min_items: 10 };
const me = { ready: true, item_count: 50, areas: ['高雄市苓雅區'] };
const person = (name, score, distance) => ({ name, score, distance, like: null, unlike: null, counts: [] });
const names = list => list.map(item => item.name);
const nearby = [person('A', 79, 0), person('B', 75, 1), person('C', 72, 2), person('D', 70, 3), person('E', 69, 0)];

test('anyone at 80% or more is recommended and distance is ignored', () => {
  const people = [person('A', 85, 3), person('B', 80, 2), person('C', 79, 0)];
  assert.deepEqual(names(recommend(people, null, thresholds)), ['A', 'B']);
  assert.deepEqual(names(recommend(people, 0, thresholds)), ['A', 'B']);
});

test('without anyone at 80%, nobody is shown until a distance is chosen', () => {
  assert.deepEqual(recommend(nearby, null, thresholds), []);
});

test('a chosen distance shows 70% and up within it, in the original order', () => {
  assert.deepEqual(names(recommend(nearby, 0, thresholds)), ['A']);
  assert.deepEqual(names(recommend(nearby, 1, thresholds)), ['A', 'B']);
  assert.deepEqual(names(recommend(nearby, 3, thresholds)), ['A', 'B', 'C', 'D']);
});

test('the page lists strong matches and caps the list at five', () => {
  const people = ['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((name, i) => person(name, 95 - i, 3));
  const shown = view({ settings, me, candidates: people }, null);
  assert.equal(shown.status, '7 位配對分數 80% 以上，顯示前 5 位。');
  assert.deepEqual(shown.cards.map(card => card.candidate.name), ['A', 'B', 'C', 'D', 'E']);
  assert.ok(shown.cards.every(card => card.place === null));
  assert.deepEqual(shown.options, []);
  assert.equal(view({ settings, me, candidates: people.slice(0, 2) }, null).status, '2 位配對分數 80% 以上。');
});

test('without strong matches the page offers distances with counts', () => {
  const shown = view({ settings, me, candidates: nearby }, null);
  assert.equal(shown.status, '目前沒有 80% 以上的人。放寬到 70%，要找多遠？');
  assert.equal(shown.note, '以你的常消費地區為準：高雄市苓雅區。');
  assert.deepEqual(shown.options.map(option => [option.label, option.count, option.disabled]),
    [['同一區', 1, false], ['同縣市', 2, false], ['同地區', 3, false], ['不限', 4, false]]);
  assert.deepEqual(shown.cards, []);
  const chosen = view({ settings, me, candidates: nearby }, 1);
  assert.deepEqual(chosen.cards.map(card => [card.candidate.name, card.place]), [['A', '同一區'], ['B', '同縣市']]);
});

test('without frequent areas only the widest range can be chosen', () => {
  const far = nearby.map(candidate => ({ ...candidate, distance: 3 }));
  const shown = view({ settings, me: { ...me, areas: [] }, candidates: far }, null);
  assert.equal(shown.note, '推測不出你的常消費地區，只能選「不限」。');
  assert.deepEqual(shown.options.map(option => option.disabled), [true, true, true, false]);
});

test('the page explains when nobody is close enough or the data is thin', () => {
  assert.equal(view({ settings, me, candidates: [person('A', 69, 0)] }, null).empty, '目前沒有夠相似的人，多掃幾張發票再看看。');
  const thin = view({ settings, me: { ready: false, item_count: 4, areas: [] }, candidates: [] }, null);
  assert.match(thin.empty, /需要至少 10 筆已分類品項（目前 4 筆）/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/match-filter.test.cjs`
Expected: FAIL — `view is not a function`，且舊的 `recommend` 讀不到 `thresholds.match`

- [ ] **Step 3: Implement the rule and the page**

把 `src/web/match-filter.js` 整檔改成：

```js
/* Who the match page shows and what it says, shared by the page and its tests. */
(function (root) {
  'use strict';
  const RANGES = ['同一區', '同縣市', '同地區', '不限'];
  const PLACES = ['同一區', '同縣市', '同地區', '其他地區'];
  const whole = value => Math.round(value * 100);
  function recommend(candidates, maxDistance, thresholds) {
    const strong = candidates.filter(candidate => candidate.score >= whole(thresholds.match));
    if (strong.length) return strong;
    if (maxDistance === null) return [];
    return candidates.filter(candidate => candidate.score >= whole(thresholds.nearby) && candidate.distance <= maxDistance);
  }
  function view(data, maxDistance) {
    const { settings, me, candidates } = data;
    const { thresholds, top_matches: top } = settings;
    const blank = { status: '', note: '', options: [], cards: [], empty: '' };
    const cards = (list, withPlace) => list.slice(0, top)
      .map(candidate => ({ candidate, place: withPlace ? PLACES[candidate.distance] : null }));
    if (!me.ready) {
      return { ...blank, empty: '資料不足，還不能配對：需要至少 ' + settings.category_min_items + ' 筆已分類品項（目前 '
        + me.item_count + ' 筆），以及品牌、葷素紀錄或消費檔次其中一項。多掃幾張發票再看看。' };
    }
    const strong = recommend(candidates, null, thresholds);
    if (strong.length) {
      return { ...blank, cards: cards(strong, false), status: strong.length + ' 位配對分數 ' + whole(thresholds.match) + '% 以上'
        + (strong.length > top ? '，顯示前 ' + top + ' 位' : '') + '。' };
    }
    if (!candidates.some(candidate => candidate.score >= whole(thresholds.nearby))) {
      return { ...blank, empty: '目前沒有夠相似的人，多掃幾張發票再看看。' };
    }
    const options = RANGES.map((label, level) => {
      const count = recommend(candidates, level, thresholds).length;
      return { level, label, count, disabled: count === 0 };
    });
    return {
      ...blank, options,
      status: '目前沒有 ' + whole(thresholds.match) + '% 以上的人。放寬到 ' + whole(thresholds.nearby) + '%，要找多遠？',
      note: me.areas.length ? '以你的常消費地區為準：' + me.areas.join('、') + '。' : '推測不出你的常消費地區，只能選「不限」。',
      cards: maxDistance === null ? [] : cards(recommend(candidates, maxDistance, thresholds), true),
    };
  }
  const api = Object.freeze({ recommend, view });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.MatchFilter = api;
})(globalThis);
```

把 `src/web/match.html` 整檔改成：

```html
<!doctype html>
<html lang="zh-Hant">
<head>
<meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>找到同好 · You are what you buy.</title>
<style>
:root{color-scheme:dark;--paper:#101010;--surface:#191919;--ink:#f2f1ed;--muted:#bbb8b2;--line:#30302e;--pink:#ef8588;--teal:#5eeac7;--amber:#ffb65c;--font:"Segoe UI","Microsoft JhengHei",sans-serif}
*{box-sizing:border-box}body{margin:0;background:var(--paper);color:var(--ink);font:14px/1.7 var(--font);-webkit-font-smoothing:antialiased}
main{max-width:880px;margin:0 auto;padding:24px 18px 56px}
.return-report{display:inline-block;color:var(--muted);font-size:12px;text-decoration:none;margin-bottom:14px}.return-report:hover{color:var(--pink)}
.eyebrow{color:var(--pink);font-size:11px;letter-spacing:2px;margin:0 0 6px}
h1{font-size:28px;line-height:1.3;margin:0 0 8px}h2{font-size:15px;margin:0 0 8px}h3{font-size:17px;margin:0}
.note{color:var(--muted);font-size:12px;margin:0}
.matches{margin-top:26px}.status{margin:0 0 4px}
.ranges{display:flex;flex-wrap:wrap;gap:8px 18px;margin:12px 0 4px}
.ranges label{display:flex;align-items:center;gap:6px;cursor:pointer}.ranges input{accent-color:var(--teal);width:16px;height:16px;margin:0}
.ranges label.off{color:#77756f;cursor:not-allowed}
.card{display:block;width:100%;text-align:left;font:inherit;color:inherit;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 20px;margin-top:12px;cursor:pointer}
.card:hover,.card:focus-visible{border-color:var(--teal);outline:none}
.card-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.score{font-size:24px;font-weight:600;color:var(--teal)}
.place{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:0 9px;font-size:11px;font-weight:400;color:var(--muted);margin-left:8px;vertical-align:middle}
.pair{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:10px 0 0;font-size:13px}
.pair dt{color:var(--muted)}.pair dd{margin:0;min-width:0;overflow-wrap:anywhere}.pair .like{color:var(--teal)}.pair .unlike{color:var(--amber)}
.empty{color:var(--muted);margin-top:16px}
details{margin-top:22px;color:var(--muted);font-size:12px}details summary{cursor:pointer}details p{margin:8px 0}
.chips{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:10px 0 0;padding:0}
.chips li{border:1px solid var(--line);border-radius:999px;padding:3px 11px;color:var(--ink)}.chips small{color:var(--muted);margin-right:5px}
@media(max-width:640px){h1{font-size:23px}.card{padding:14px}}
</style>
</head>
<body>
<main>
<a id="return-report" class="return-report" href="#report" hidden>← 返回消費洞察</a>
<p class="eyebrow">FIND YOUR PEOPLE · 找到同好</p>
<h1>從消費習慣，找到合拍的人。</h1>
<p class="note" id="match-note"></p>
<section class="matches" aria-labelledby="matches-title">
<h2 id="matches-title">和你最合拍的人</h2>
<p class="status" id="match-status" role="status" aria-live="polite"></p>
<p class="note" id="range-note" hidden></p>
<div class="ranges" id="ranges" role="radiogroup" aria-label="要找多遠" hidden></div>
<div id="match-list"></div>
</section>
<details><summary>你的消費標籤</summary><ul class="chips" id="my-tags"></ul></details>
<details><summary>怎麼算的？</summary><div id="method"></div></details>
</main>
<script src="match-filter.js"></script>
<script src="match-data.js"></script>
<script>
'use strict';
(function () {
  const data = matchReportData, settings = data.settings;
  const $ = id => document.getElementById(id);
  const pct = value => Math.round(value * 100) + '%';
  const pageHost = window.parent !== window && window.frameElement?.id === 'match-frame' ? window.parent : null;
  function make(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function pairFor(candidate) {
    return {
      score: candidate.score,
      left: { name: '你', demo: data.isDemo, months: data.me.months, counts: data.me.counts },
      right: { name: candidate.name, demo: true, months: data.personaMonths, counts: candidate.counts },
    };
  }
  function card({ candidate, place }) {
    const button = make('button', undefined, 'card');
    button.type = 'button';
    button.title = '查看你和' + candidate.name + '的連線圖';
    const title = make('h3', candidate.name);
    if (place) title.append(make('span', place, 'place'));
    const head = make('div', undefined, 'card-head');
    head.append(title, make('span', candidate.score + '%', 'score'));
    const pair = make('dl', undefined, 'pair');
    for (const [label, tag, className] of [['最像你', candidate.like, 'like'], ['最不像你', candidate.unlike, 'unlike']]) {
      if (tag) pair.append(make('dt', label), make('dd', tag.dimension + '：' + tag.text, className));
    }
    button.append(head, pair);
    button.addEventListener('click', () => pageHost?.ReceiptPages.showConnection?.(pairFor(candidate)));
    return button;
  }
  let range = null;
  function renderList() {
    const shown = MatchFilter.view(data, range);
    $('match-list').replaceChildren(...(shown.cards.length ? shown.cards.map(card)
      : shown.empty ? [make('p', shown.empty, 'empty')] : []));
  }
  const first = MatchFilter.view(data, null);
  $('match-status').textContent = first.status;
  $('range-note').textContent = first.note;
  $('range-note').hidden = !first.note;
  $('ranges').hidden = !first.options.length;
  for (const option of first.options) {
    const label = make('label', undefined, option.disabled ? 'off' : undefined), input = make('input');
    input.type = 'radio';
    input.name = 'range';
    input.disabled = option.disabled;
    input.addEventListener('change', () => { range = option.level; renderList(); });
    label.append(input, option.label + ' · ' + option.count + ' 位');
    $('ranges').append(label);
  }
  renderList();
  $('match-note').textContent = '配對對象是 ' + data.population + ' 位虛構示範用戶。'
    + (data.isDemo ? '「我」也是虛構示範資料。' : '你的標籤來自這份私人報告，只存在這個檔案裡。') + '點一個人，看你們的連線圖。';
  const mine = $('my-tags');
  for (const tag of data.me.tags) {
    const item = make('li');
    item.append(make('small', tag.dimension), tag.text);
    mine.append(item);
  }
  if (!data.me.tags.length) mine.replaceWith(make('p', '資料還不夠產生標籤。'));
  const weights = settings.weights, levels = settings.price_levels;
  $('method').append(
    make('p', '配對分數：品類、品牌、葷素紀錄、消費檔次依 ' + [weights.category, weights.brand, weights.flavor, weights.price]
      .map(weight => Math.round(weight * 100)).join('：') + ' 加權，缺資料的面向不計分，權重分給其他面向。地區不算分。'),
    make('p', '品類一定要能比較（各自至少 ' + settings.category_min_items + ' 筆已分類品項），另外至少再有品牌、葷素紀錄、消費檔次其中一項，才會配對。'),
    make('p', '配對分數 ' + pct(settings.thresholds.match) + ' 以上直接推薦。沒有人達到時，可以選要找多遠（同一區、同縣市、同地區或不限），範圍內 '
      + pct(settings.thresholds.nearby) + ' 以上的人會被推薦；距離依你和對方的常消費地區判斷。'),
    make('p', '消費檔次只看有正餐的發票：用正餐份數估計幾人份，再取每人每餐花費的中位數。' + levels[0].label + '未滿 ' + levels[0].below
      + ' 元，' + levels[1].label + '未滿 ' + levels[1].below + ' 元，其餘為' + levels[2].label + '。合菜會讓每人金額偏低。'),
    make('p', '「最像你」「最不像你」取自對方自己的標籤，常消費地區不當成理由。同一張發票的同一品項只算一次。'),
    make('p', '此配對頁只用行政區與連鎖品牌，不顯示分店、日期或金額。'
      + (data.isDemo ? '' : '這份私人報告的其他頁面仍有完整交易明細，分享整份檔案就會一併分享。')
      + '配對對象皆為虛構示範用戶。'));
  if (pageHost) {
    const back = $('return-report');
    back.hidden = false;
    back.addEventListener('click', event => { event.preventDefault(); pageHost.ReceiptPages.showReport(); });
  }
})();
</script>
</body>
</html>
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/match-filter.test.cjs`
Expected: `# pass 7`、`# fail 0`

- [ ] **Step 5: Rebuild the public demo and run all tests**

Run: `python scripts/build_report.py`
Expected: 兩個月份的摘要與 `match candidates: 10 of 40 fictional people`

Run: `python -m unittest discover -s tests -v`
Expected: 51 tests OK

Run: `node --test tests/*.test.cjs`
Expected: `# pass 22`、`# fail 0`

- [ ] **Step 6: Commit**

```bash
git add src/web/match-filter.js src/web/match.html tests/match-filter.test.cjs invoice-insights.html
git commit -F - <<'EOF'
feat: list matches with two tags and offer distances below 80%

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: 朋友比較的計數規則與配對資料驗證

**Files:**
- Modify: `src/web/taste-profile.js`（`fromReport`、新增 `fromPair`、匯出清單）
- Modify: `src/web/taste-comparison.html`（分類模式說明的一句）
- Modify: `src/web/invoice-insights.html`（匯出面板說明的一句）
- Test: `tests/taste-profile.test.cjs`、`tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 3 的 `pair` 格式
- Produces: `TasteProfile.fromPair(pair) -> {"score", "left", "right"}`（`left`、`right` 經 `validate` 補上 `schema`）；分數不是 0–100 的整數或任一側無效時丟出錯誤。`TasteProfile.fromReport` 改為同一張發票的同一品名只算一次

- [ ] **Step 1: Write the failing tests**

在 `tests/taste-profile.test.cjs` 檔尾加入：

```js
test('one portion per item and invoice, as in the match tags',()=>{
 const report={isDemo:false,categories:[{name:'飲品'},{name:'正餐'}],months:{'2026-03':{rows:[
  {category:0,amount:50,invoice:'A',name:'紅茶'},{category:0,amount:50,invoice:'A',name:'紅茶'},
  {category:0,amount:50,invoice:'B',name:'紅茶'},{category:1,amount:90,invoice:'A',name:'便當'}]}}};
 const p=taste.fromReport(report,'小明');
 assert.equal(p.counts[1],2);assert.equal(p.counts[0],1);
});
test('a match pair carries a whole-number score and two valid profiles',()=>{
 const side=(name,demo)=>({name,demo,months:['2026-03','2026-04'],counts:[3,2,0,0,0,0,0,0,0,0]});
 const pair=taste.fromPair({score:81,left:side('你',false),right:side('手搖學生 D',true)});
 assert.equal(pair.score,81);assert.equal(pair.left.name,'你');assert.equal(pair.right.schema,taste.schema);
 for(const invalid of [null,{score:81.5,left:side('你',false),right:side('D',true)},{score:101,left:side('你',false),right:side('D',true)},
  {score:81,left:side('你',false),right:{...side('D',true),counts:[1]}}])assert.throws(()=>taste.fromPair(invalid));
});
```

`tests/test_build_report.py`：在 `test_default_build_ignores_private_sources_and_preserves_private_html` 的 `self.assertIn("receipt-taste/categories-v1", comparison)` 之後加入：

```python
            self.assertIn("同一張發票的同一品項只算一次", comparison)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/taste-profile.test.cjs`
Expected: `# pass 4`、`# fail 2`

Run: `python -m unittest tests.test_build_report -v`
Expected: FAIL — `test_default_build_ignores_private_sources_and_preserves_private_html`

- [ ] **Step 3: Implement**

`src/web/taste-profile.js`：把整個 `fromReport` 函式

```js
 function fromReport(report,name){
  const counts=categories.map(()=>0),months=Object.keys(report.months).sort();
  for(const month of Object.values(report.months))for(const row of month.rows){
   const i=categories.indexOf(report.categories[row.category]?.name);
   if(i>=0&&!row.provisional&&Number.isFinite(row.amount)&&row.amount>0)counts[i]++;
  }
  return validate({schema,name:name.trim()||'我的偏好',demo:report.isDemo===true,months,counts});
 }
```

改成

```js
 function fromReport(report,name){
  const counts=categories.map(()=>0),months=Object.keys(report.months).sort(),seen=new Set();
  for(const month of Object.values(report.months))for(const row of month.rows){
   const i=categories.indexOf(report.categories[row.category]?.name);
   if(i<0||row.provisional||!Number.isFinite(row.amount)||row.amount<=0)continue;
   // One portion per item and invoice, as in the match tags; rows without an invoice code each count.
   if(row.invoice!==undefined){const key=JSON.stringify([row.invoice,row.name]);if(seen.has(key))continue;seen.add(key);}
   counts[i]++;
  }
  return validate({schema,name:name.trim()||'我的偏好',demo:report.isDemo===true,months,counts});
 }
 function fromPair(pair){
  if(!pair||!Number.isSafeInteger(pair.score)||pair.score<0||pair.score>100)throw new Error('配對資料不正確，請回配對清單重新選擇。');
  return {score:pair.score,left:validate({schema,...pair.left}),right:validate({schema,...pair.right})};
 }
```

並把

```js
 const api=Object.freeze({categories,schema,validate,fromReport,toURL,fromURL,cosine});
```

改成

```js
 const api=Object.freeze({categories,schema,validate,fromReport,fromPair,toURL,fromURL,cosine});
```

`src/web/taste-comparison.html`：把 `10 類已確認消費品項的筆數，每筆正金額的品項算一次，` 改成 `10 類已確認消費品項的筆數，同一張發票的同一品項只算一次，`。

`src/web/invoice-insights.html`：把 `依正金額、分類已確認的品項筆數計算；` 改成 `依正金額、分類已確認的品項筆數計算，同一張發票的同一品項只算一次；`。

- [ ] **Step 4: Rebuild and run all tests**

Run: `python scripts/build_report.py`
Expected: 兩個月份的摘要與 `match candidates: 10 of 40 fictional people`

Run: `python -m unittest discover -s tests -v`
Expected: 51 tests OK

Run: `node --test tests/*.test.cjs`
Expected: `# pass 24`、`# fail 0`

- [ ] **Step 5: Commit**

```bash
git add src/web/taste-profile.js src/web/taste-comparison.html src/web/invoice-insights.html tests/taste-profile.test.cjs tests/test_build_report.py invoice-insights.html
git commit -F - <<'EOF'
feat: count one portion per item in friend comparisons and validate match pairs

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: 連線圖的配對模式

**Files:**
- Modify: `src/web/taste-navigation.js`（整檔改寫）
- Modify: `src/web/invoice-insights.html`（連線圖容器）
- Modify: `src/web/styles.css:395`
- Modify: `src/web/taste-comparison.html`（配對模式）
- Test: `tests/page-navigation.test.cjs`（新增）、`tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 3 的 `showConnection(pair)` 呼叫；Task 4 的 `TasteProfile.fromPair`
- Produces: `window.ReceiptPages` 增加 `showMatches()`、`showConnection(pair)`、`connection()`；路由 `#connection` 顯示 `connection-view`，每次顯示都重新載入 iframe；沒有配對資料時改回 `#match`

- [ ] **Step 1: Write the failing tests**

建立 `tests/page-navigation.test.cjs`：

```js
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');

const source = fs.readFileSync(path.join(__dirname, '..', 'src', 'web', 'taste-navigation.js'), 'utf8');

function setup(hash) {
  const nodes = {};
  for (const name of ['taste', 'match', 'connection']) {
    nodes[name + '-view'] = { hidden: true };
    nodes[name + '-frame'] = { srcdoc: '', focus() {} };
  }
  for (const name of ['taste', 'match']) nodes[name + '-page-source'] = { content: { textContent: name + ' page' } };
  for (const id of ['compare-friends', 'find-matches']) nodes[id] = { focus() {} };
  const location = { hash };
  const listeners = {};
  const window = { scrollY: 0, scrollTo() {}, addEventListener(name, callback) { listeners[name] = callback; } };
  vm.runInContext(source, vm.createContext({
    window, location,
    history: { replaceState(state, title, url) { location.hash = url; } },
    document: { getElementById: id => nodes[id] || null, body: { classList: { add() {}, remove() {} } } },
    requestAnimationFrame: callback => callback(),
  }));
  const go = next => { location.hash = next; listeners.hashchange(); };
  const visible = () => Object.keys(nodes).filter(id => id.endsWith('-view') && !nodes[id].hidden);
  return { nodes, location, go, visible, pages: window.ReceiptPages };
}

test('each match opens a freshly loaded chart and the list keeps its state', () => {
  const { nodes, location, go, visible, pages } = setup('#match');
  assert.deepEqual(visible(), ['match-view']);
  nodes['match-frame'].srcdoc = 'list with a chosen range';
  const pair = { score: 81 };
  pages.showConnection(pair);
  assert.equal(location.hash, '#connection');
  go('#connection');
  assert.deepEqual(visible(), ['connection-view']);
  assert.equal(nodes['connection-frame'].srcdoc, 'taste page');
  assert.equal(pages.connection(), pair);
  nodes['connection-frame'].srcdoc = 'chart of the previous match';
  pages.showMatches();
  go(location.hash);
  assert.deepEqual(visible(), ['match-view']);
  assert.equal(nodes['match-frame'].srcdoc, 'list with a chosen range');
  pages.showConnection({ score: 75 });
  go('#connection');
  assert.equal(nodes['connection-frame'].srcdoc, 'taste page');
});

test('a connection address without a chosen match falls back to the list', () => {
  const { location, visible } = setup('#connection');
  assert.equal(location.hash, '#match');
  assert.deepEqual(visible(), ['match-view']);
});

test('the friend comparison still opens on its own', () => {
  const { go, visible } = setup('');
  assert.deepEqual(visible(), []);
  go('#friends');
  assert.deepEqual(visible(), ['taste-view']);
});
```

`tests/test_build_report.py`：在 `test_default_build_ignores_private_sources_and_preserves_private_html` 的 `self.assertIn('href="#match"', html)` 之後加入：

```python
            self.assertIn('<iframe id="connection-frame"', html)
            self.assertIn("connection-frame", comparison)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/page-navigation.test.cjs`
Expected: `# pass 1`、`# fail 2`（第 1 個測試因 `showConnection` 不存在而 TypeError，第 2 個測試沒有退回 `#match`；第 3 個是回歸測試，本來就會通過）

Run: `python -m unittest tests.test_build_report -v`
Expected: FAIL — 找不到 `connection-frame`

- [ ] **Step 3: Implement the routing**

把 `src/web/taste-navigation.js` 整檔改成：

```js
/* Secondary pages are embedded in this file, and created only on demand. */
(function(){
 'use strict';
 if(typeof window==='undefined')return;
 const pages=[
  {view:'taste-view',frame:'taste-frame',source:'taste-page-source',link:'compare-friends',matches:hash=>hash==='#friends'||hash.startsWith('#taste=')},
  {view:'match-view',frame:'match-frame',source:'match-page-source',link:'find-matches',matches:hash=>hash==='#match'},
  // One match's chart reuses the comparison page and reloads every time, so no earlier pair lingers.
  {view:'connection-view',frame:'connection-frame',source:'taste-page-source',link:'find-matches',matches:hash=>hash==='#connection',fresh:true},
 ].map(page=>({...page,view:document.getElementById(page.view),frame:document.getElementById(page.frame),source:document.getElementById(page.source),loaded:false}))
  .filter(page=>page.view&&page.frame&&page.source);
 if(!pages.length)return;
 let showing=null,reportHash='',reportScroll=0,lastTasteHash='',connection=null;
 function route(){
  let hash=location.hash;
  if(hash==='#connection'&&!connection){history.replaceState(null,'','#match');hash='#match';}
  const page=pages.find(candidate=>candidate.matches(hash));
  if(page){
   if(!showing)reportScroll=window.scrollY;
   for(const other of pages)other.view.hidden=other!==page;
   document.body.classList.add('taste-view-open');
   if(page.fresh||!page.loaded){page.frame.srcdoc=page.source.content.textContent;page.loaded=true;}
   else if(page.view.id==='taste-view'&&hash.startsWith('#taste=')&&hash!==lastTasteHash)page.frame.contentWindow.refreshTasteFromLocation?.();
   if(page.view.id==='taste-view')lastTasteHash=hash;
   showing=page;page.frame.focus();
  }else{
   const was=showing;showing=null;reportHash=hash;
   for(const other of pages)other.view.hidden=true;
   document.body.classList.remove('taste-view-open');
   if(was){document.getElementById(was.link)?.focus({preventScroll:true});requestAnimationFrame(()=>window.scrollTo({top:reportScroll,behavior:'instant'}));}
  }
 }
 window.ReceiptPages=Object.freeze({
  showReport(){location.hash=reportHash||'#report';},
  showMatches(){location.hash='#match';},
  showConnection(pair){connection=pair;location.hash='#connection';},
  connection(){return connection;},
 });
 window.addEventListener('hashchange',route);
 route();
})();
```

`src/web/invoice-insights.html`：在 `<section id="match-view" ...></section>` 那一行之後加入：

```html
<section id="connection-view" aria-label="你和配對對象的連線圖" hidden><iframe id="connection-frame" title="你和配對對象的連線圖" referrerpolicy="no-referrer"></iframe></section>
```

`src/web/styles.css` 第 395 行：把

```css
#taste-view,#match-view{position:fixed;inset:0;background:var(--paper);z-index:1000}#taste-frame,#match-frame{display:block;width:100%;height:100%;border:0;background:var(--paper)}
```

改成

```css
#taste-view,#match-view,#connection-view{position:fixed;inset:0;background:var(--paper);z-index:1000}#taste-frame,#match-frame,#connection-frame{display:block;width:100%;height:100%;border:0;background:var(--paper)}
```

- [ ] **Step 4: Implement the pair mode on the comparison page**

`src/web/taste-comparison.html` 依序修改六處：

1. 把

```js
const pageHost=window.parent!==window&&window.frameElement?.id==='taste-frame'?window.parent:null;
```

改成

```js
const hostFrame=window.parent!==window?window.frameElement?.id:null;
const pageHost=['taste-frame','connection-frame'].includes(hostFrame)?window.parent:null;
```

2. 在 `for(const person of Object.values(profiles)){ ... }` 迴圈（設定 `demoCounts` 與 `categoryCounts` 的那段）結束的 `}` 之後加入：

```js
// Opened from the match list: the sides are fixed to you and that match, and the big number is the match score.
let pair=null;
if(hostFrame==='connection-frame'){
 try{pair=TasteProfile.fromPair(pageHost.ReceiptPages.connection());}catch(error){pageHost.ReceiptPages.showMatches();}
 if(pair){
  profiles.me={name:pair.left.name,payload:pair.left};profiles.match={name:pair.right.name,payload:pair.right};leftKey='me';rightKey='match';
  for(const part of document.querySelectorAll('.import-title-row, .imports'))part.hidden=true;
 }
}
```

3. 在 `prepareMode()` 中，把

```js
 document.querySelector('.overall-label').textContent=categoryMode?'消費類型相似度':'綜合品味相似指數';
```

改成

```js
 document.querySelector('.overall-label').textContent=pair?'配對分數':categoryMode?'消費類型相似度':'綜合品味相似指數';
```

4. 在 `draw()` 中，`const scopeScore=similarity(indices),count=loadedSides().length;` 這一行之前加入：

```js
 if(pair){$('overall-score').textContent=pair.score;$('overall-note').textContent='消費類型相似度 '+indexPercent(overall)+'%（下圖）';}
```

5. 在 `draw()` 中，把人名標籤的

```js
key?chartName(key,mobile)+' · '+(side==='a'?'你':'朋友'):
```

改成

```js
key?chartName(key,mobile)+(pair?(side==='a'?'':' · 配對對象'):' · '+(side==='a'?'你':'朋友')):
```

6. 在檔尾的 `if(pageHost){ ... }` 區塊中，把

```js
 for(const link of [back,document.querySelector('header .brand')])link.addEventListener('click',event=>{event.preventDefault();pageHost.ReceiptPages.showReport();});
```

改成

```js
 if(pair)back.textContent='← 返回配對清單';
 back.addEventListener('click',event=>{event.preventDefault();if(pair)pageHost.ReceiptPages.showMatches();else pageHost.ReceiptPages.showReport();});
 document.querySelector('header .brand').addEventListener('click',event=>{event.preventDefault();pageHost.ReceiptPages.showReport();});
```

- [ ] **Step 5: Rebuild and run all tests**

Run: `python scripts/build_report.py`
Expected: 兩個月份的摘要與 `match candidates: 10 of 40 fictional people`

Run: `python -m unittest discover -s tests -v`
Expected: 51 tests OK

Run: `node --test tests/*.test.cjs`
Expected: `# pass 27`、`# fail 0`

- [ ] **Step 6: Commit**

```bash
git add src/web/taste-navigation.js src/web/invoice-insights.html src/web/styles.css src/web/taste-comparison.html tests/page-navigation.test.cjs tests/test_build_report.py invoice-insights.html
git commit -F - <<'EOF'
feat: open the connection chart for a match from the list

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: 報告動畫縮短為 18 秒

**Files:**
- Modify: `src/web/insights-ui.js`（動畫常數與使用處）
- Modify: `src/web/invoice-insights.html`（時間軸上限與預設時間文字）
- Test: `tests/comparison-interface.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: 無
- Produces: 每段 6 秒（日期推進 5 秒、停留 1 秒），共 18 秒；時間軸 `max` 為 18

- [ ] **Step 1: Write the failing test**

`tests/comparison-interface.test.cjs`：在 `initial view uses April and compares fictional sport purchases against March` 測試的 `assert.equal(nodes.get('compare-current-heading').textContent, '本月 · 4 月');` 之後加入：

```js
  assert.equal(nodes.get('time').textContent, '00:05 / 00:18');
  assert.equal(nodes.get('timeline').max, '18');
```

（測試環境的 `matchMedia` 回報減少動態效果，所以動畫停在第一段結尾 5.99 秒。）

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/comparison-interface.test.cjs`
Expected: FAIL — `expected: '00:05 / 00:18'`、`actual: '00:11 / 00:36'`

- [ ] **Step 3: Implement**

`src/web/insights-ui.js` 依序修改：

1. 在 `let rhythmMetric = 'count';` 之後加入：

```js
// Each chapter plays through the month's days, then holds for a moment; three chapters in all.
const CHAPTER = 6, PLAY = 5, LENGTH = CHAPTER * 3;
```

2. `let position = autoplay ? 0 : 11.99,` 改成 `let position = autoplay ? 0 : CHAPTER - 0.01,`
3. `position >= 36 ? '播放完畢'` 改成 `position >= LENGTH ? '播放完畢'`
4. `Math.floor(position / 12)` 改成 `Math.floor(position / CHAPTER)`
5. `(position - index * 12) / 10)` 改成 `(position - index * CHAPTER) / PLAY)`
6. `' / 00:36'` 改成 `' / 00:' + String(LENGTH).padStart(2, '0')`
7. `position = Math.min(36, position + (now - lastTime) / 1000 * speed); if (position >= 36)` 改成 `position = Math.min(LENGTH, position + (now - lastTime) / 1000 * speed); if (position >= LENGTH)`
8. `$('play').onclick = () => { if (position >= 36) position = 0;` 改成 `$('play').onclick = () => { if (position >= LENGTH) position = 0;`
9. `$('finish').onclick = () => { position = activeScene * 12 + 11.99;` 改成 `$('finish').onclick = () => { position = activeScene * CHAPTER + CHAPTER - 0.01;`
10. `position = Number(el.dataset.chapter) * 12 + (playing ? 0 : 11.99);` 改成 `position = Number(el.dataset.chapter) * CHAPTER + (playing ? 0 : CHAPTER - 0.01);`
11. 在 `  $('speed').textContent = '1×';` 這一行之前加入一行：

```js
  $('timeline').max = String(LENGTH);
```

改完後 `insights-ui.js` 不應再有 `36`、`11.99`、`* 12`、`/ 12` 這些舊的時間數字（`360` 這類金額不算）。

`src/web/invoice-insights.html`：把時間軸的 `max="36" step="0.01"` 改成 `max="18" step="0.01"`，並把 `00:00 / 00:36` 改成 `00:00 / 00:18`。

- [ ] **Step 4: Rebuild and run all tests**

Run: `python scripts/build_report.py`
Expected: 兩個月份的摘要與 `match candidates: 10 of 40 fictional people`

Run: `node --test tests/*.test.cjs`
Expected: `# pass 27`、`# fail 0`

Run: `python -m unittest discover -s tests -v`
Expected: 51 tests OK

- [ ] **Step 5: Commit**

```bash
git add src/web/insights-ui.js src/web/invoice-insights.html tests/comparison-interface.test.cjs invoice-insights.html
git commit -F - <<'EOF'
feat: play the report animation in 18 seconds

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: 最終驗證（由主控執行，不交給子代理）

**Files:** 無新增；只檢查。

- [ ] **Step 1: 全部測試**

Run: `python -m unittest discover -s tests -v` 與 `node --test tests/*.test.cjs`
Expected: 51 tests OK；`# pass 27`、`# fail 0`

- [ ] **Step 2: 在瀏覽器檢查公開示範版**

用本機 HTTP 伺服器開啟報告的副本（不要直接開專案根目錄，以免 `data/` 可被讀取）。另外產生一份把所有配對分數調低 20 分的副本，用來看示範版看不到的距離選項：

```bash
SERVE="$(mktemp -d)" && cp invoice-insights.html "$SERVE/report.html" && python - "$SERVE" <<'EOF'
import re, sys
from pathlib import Path
serve = Path(sys.argv[1])
html = (serve / "report.html").read_text(encoding="utf-8")
lowered, count = re.subn(r"&quot;score&quot;: (\d+)", lambda m: f"&quot;score&quot;: {int(m.group(1)) - 20}", html)
(serve / "nearby.html").write_text(lowered, encoding="utf-8")
print(serve, "scores lowered:", count)
EOF
```

檢查項目：
- `report.html#match`：「5 位配對分數 80% 以上。」；5 張卡片都是手搖學生，每張只有「最像你」「最不像你」兩行；手搖學生 D 的最不像你是「葷素紀錄：葷食品項較多」；沒有距離選項。
- 點手搖學生 D：切到連線圖，大字「配對分數 81%」，小字「消費類型相似度 95%（下圖）」，左側「你」、右側「手搖學生 D · 配對對象」，沒有匯入區，返回連結為「← 返回配對清單」。
- 返回後清單仍在；再點手搖學生 A，連線圖換成 96%。
- `report.html#friends`：朋友比較頁照舊（匯入區、示範的小安與小宇）。
- `nearby.html#match`：「目前沒有 80% 以上的人。放寬到 70%，要找多遠？」、「以你的常消費地區為準：高雄市苓雅區、高雄市新興區。」，四個選項各標「· 3 位」；選「同一區」後出現 3 張標有「同一區」的卡片。
- 報告動畫的時間顯示「/ 00:18」。
- 手機寬度（375px）時，配對頁與連線圖都沒有水平捲動；主控台沒有錯誤。

- [ ] **Step 3: 用真實資料做冒煙測試（只印數量）**

只在記憶體中執行、不寫任何檔案，只印出數量：

```bash
PYTHONDONTWRITEBYTECODE=1 python - <<'EOF'
import csv, json
from collections import Counter
from pathlib import Path
from src.receipt.build import build_matches
from src.receipt.invoices import build_month

config = json.loads(Path("data/private/report.json").read_text(encoding="utf-8"))
catalog = json.loads(Path(config["category_catalog"]).read_text(encoding="utf-8"))
months, private_values = {}, set()
for filename in config["input_files"]:
    key, month = build_month(Path(filename), catalog)
    months[key] = month
    with Path(filename).open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            for field in ("賣方地址", "賣方統一編號"):
                if (row.get(field) or "").strip():
                    private_values.add(row[field].strip())
payload = build_matches(months, config["categories"], False)
candidates = payload["candidates"]
print("ready:", payload["me"]["ready"], "| items:", payload["me"]["item_count"], "| tags:", dict(Counter(t["dimension"] for t in payload["me"]["tags"])))
print(">=80%:", sum(c["score"] >= 80 for c in candidates), "| 70-79%:", sum(c["score"] < 80 for c in candidates),
      "| within range:", {label: sum(c["distance"] <= level for c in candidates) for level, label in enumerate(["同一區", "同縣市", "同地區", "不限"])})
print("like found:", sum(bool(c["like"]) for c in candidates), "| unlike found:", sum(bool(c["unlike"]) for c in candidates))
page = json.dumps({"months": months, "matches": payload}, ensure_ascii=False)
print("addresses and tax IDs checked:", len(private_values), "| leaked:", sum(value in page for value in private_values))
EOF
```

Expected: `ready: True`；`>=80%: 0`、`70-79%: 4`；同地區範圍內 4 位；leaked 為 0。標籤的面向名稱若在終端機顯示成亂碼，是輸出編碼問題，可加 `PYTHONIOENCODING=utf-8` 重跑。

- [ ] **Step 4: Push 並回報使用者**

```bash
git push
```

確認 `git status -sb` 顯示 `feature/tags-matching...origin/feature/tags-matching` 且沒有落後或領先；不動 `main`。

回報：測試結果、瀏覽器檢查結果、冒煙測試的數量；詢問是否要重新產生私人報告（會覆寫 `invoice-insights-private.html`）、是否要合併到 `main`，以及是否接著更新 README。
