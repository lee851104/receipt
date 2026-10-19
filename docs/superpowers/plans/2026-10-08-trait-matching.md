# 配對頁改用品味特質 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 「找到同好」改用第一段的品味特質相似度：Python 嵌入「我」與 40 位虛構用戶的相對向量，瀏覽器用 `trait-similarity.js` 算分數、挑出合拍（+30% 以上）與相反（−30% 以下）的人，卡片說明最像與最不像的特質；距離篩選保留成次要篩選；移除舊的標籤配對程式。

**Architecture:** `places.py` 算生活圈與距離，`signals.category_counts` 算 10 類筆數，`traits.population_vectors` 是「我、40 人、平均」的共用算法；`build.py` 把這些組成 `matchReportData`。`match-filter.js` 是純函式（名單、文字、你的品味特質），`match.html` 只負責畫面。點卡片仍打開現有的類別連線圖，大字分數改成品味相似度。

**Tech Stack:** Python 3.10+ 標準函式庫（`unittest`）、原生 JavaScript、Node.js `node:test`

**Spec:** `docs/superpowers/specs/2026-10-08-trait-matching-design.md`

## Global Constraints

- Python 只用標準函式庫；`pyproject.toml` 不變。
- 不讀取、不修改 `data/` 底下任何檔案（私人資料）。執行 `python scripts/build_report.py` 會寫入 `data/processed/report-data.js`（公開示範版的輸出），這是允許的；絕不使用 `--private`。
- 根目錄的 `report-data.js` 與 `*.csv` 是私人檔案，絕不加入 Git。每個任務只 `git add`（或 `git rm`）該任務列出的檔案，不要用 `git add -A` 或 `git add .`。
- 測試與設定只用虛構名稱（以「示範」或「測試」開頭）。行政區只用：高雄市苓雅區、高雄市新興區、高雄市前鎮區、高雄市左營區、臺北市信義區、臺北市內湖區、新北市板橋區、桃園市中壢區、新竹市東區、新竹縣竹北市、宜蘭縣宜蘭市、屏東縣恆春鎮、屏東縣東港鎮。
- `src/web/` 只改本計畫列出的檔案：`match.html`、`match-filter.js`、`taste-profile.js`、`taste-comparison.html`。
- 報告維持單一 HTML 檔、沒有外部資源。
- 程式碼與文字照本計畫逐字輸入。百分比的負號是 U+2212（−），程式裡一律寫成 `String.fromCharCode(0x2212)`，不要換成連字號。
- 在 `feature/taste-traits` 分支工作；不要 push。
- Commit 訊息用英文，結尾一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 指令都在專案根目錄用 Git Bash 執行：
  - 全部 Python 測試：`python -m unittest discover -s tests`
  - 單一檔：`python -m unittest tests.test_places -v`
  - Node 測試：`node --test tests/*.test.cjs`
- `tests/match-page.test.cjs` 讀取根目錄已產生的 `invoice-insights.html`。只有 Task 5 重新產生並 commit 它；Task 3、4 不要執行 `python scripts/build_report.py`，因為舊的 `match.html` 要到 Task 5 才換掉，中間產生會得到壞掉的配對頁。
- Git 在 Windows 上會提示「LF will be replaced by CRLF」，可以忽略。

## 試做結果（已在專案副本驗證）

- 全部任務完成後：Python 54 個、Node 40 個測試全部通過。
- `python scripts/build_report.py` 印出三行（不再印 `match candidates`）：
  ```text
  2026-03 50 rows; total 7910
  2026-04 53 rows; total 8095
  taste similarity to 40 fictional people: highest 62%, median 8%, lowest -42%
  ```
- 示範配對頁：
  - 合拍：手搖學生 A +62%、手搖學生 B +62%、手搖學生 C +53%、連假旅人 E +34%、連假旅人 D +32%。選「同縣市」後只剩手搖學生 A、B、C。
  - 相反（打開開關）：「8 位品味相似度 −30% 以下，顯示前 5 位。」省錢上班族 E −42%，B、A、D、C −41%。
  - 你的品味特質：「跟一般人比：偏香甜・偏避開連假・偏喜歡嘗鮮」「也有運動、生活小物、3C 的紀錄」。
- 新的 10 類筆數和舊程式算出的完全相同（「我」與 40 人），點卡片後的類別圖不變。
- 點相反名單的卡片，連線頁顯示「品味相似度 −42%」，下方小字「消費類型相似度 83%（下圖）」。

## 檔案結構

| 檔案 | 動作 | 責任 |
|---|---|---|
| `configs/regions.json` | 新增 | 地區對照表（從 `tags.json` 搬來） |
| `src/receipt/signals.py` | 修改 | 生活圈行政區 `home_districts`；10 類筆數 `category_counts` |
| `src/receipt/places.py` | 新增 | 一個人的生活圈、兩人的距離 |
| `configs/traits.json` | 修改 | 配對門檻 `match`；8 個程度型的短詞 `habit` |
| `src/receipt/traits.py` | 修改 | 共用的 `population_vectors` |
| `src/web/match-filter.js` | 改寫 | 名單、卡片文字、你的品味特質、狀態文字（純函式） |
| `src/web/taste-profile.js`、`src/web/taste-comparison.html` | 修改 | 連線頁接受負分、大字分數改名並帶正負號 |
| `src/receipt/build.py` | 改寫 | 產生新的 `matchReportData`；配對頁嵌入 `trait-similarity.js` |
| `src/web/match.html` | 改寫 | 新配對頁畫面 |
| `src/receipt/tags.py`、`src/receipt/matching.py`、`configs/tags.json` | 刪除 | 舊配對 |
| `tests/test_places.py` | 新增 | 生活圈與距離 |
| `tests/test_traits.py` | 修改 | 10 類筆數、配對設定、共用函式 |
| `tests/test_personas.py` | 修改 | 改用共用函式 |
| `tests/match-filter.test.cjs` | 改寫 | 名單與文字規則 |
| `tests/taste-profile.test.cjs` | 修改 | `fromPair` 接受 −100～+100 |
| `tests/test_build_report.py` | 修改 | 新的配對資料 |
| `tests/match-page.test.cjs` | 新增 | 用實際產生的示範頁驗證名單 |
| `tests/test_tags.py`、`tests/test_matching.py` | 刪除 | 舊配對的測試 |
| `invoice-insights.html` | 重新產生 | 公開示範版（Task 5） |

---

### Task 1: 生活圈、距離與 10 類筆數

**Files:**
- Create: `configs/regions.json`
- Modify: `src/receipt/signals.py`
- Create: `src/receipt/places.py`
- Create: `tests/test_places.py`
- Modify: `tests/test_traits.py`

**Interfaces:**
- Consumes: `signals.gather(rows, context)`（每筆明細要有 `date`）、`signals.ranked`、`signals.valid_items`、`traits.load_context(root)`
- Produces:
  - `signals.home_districts(located) -> list[str]`：占有行政區付費發票 20% 以上的行政區，最多兩個，依發票數排序、同數依名稱；`signals.home_cities(located)` 改用它，行為不變
  - `signals.category_counts(rows) -> list[int]`（10 格）
  - `places.load_regions(root) -> dict[str, str]`（縣市 → 地區）
  - `places.areas_of(rows, context) -> list[str]`（一個人的生活圈行政區）
  - `places.place_distance(a, b, regions) -> int`、`places.distance(mine, theirs, regions) -> int`（0～3）

- [ ] **Step 1: Write the failing tests**

建立 `tests/test_places.py`：

```python
"""Home districts and how far apart two people live, from fictional bills."""
import unittest
from datetime import date
from pathlib import Path

from src.receipt.places import areas_of, distance, load_regions, place_distance
from src.receipt.traits import load_context

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
REGIONS = load_regions(ROOT)


def bills(*groups):
    """One paid bill per entry, from (count, district, merchant) groups."""
    rows = []
    for count, district, merchant in groups:
        for _ in range(count):
            rows.append({"date": date(2026, 3, 2), "day": 2, "invoice": f"T{len(rows):03}", "merchant": merchant,
                         "district": district, "name": "測試便當", "quantity": 1, "amount": 100, "category": 0,
                         "provisional": False})
    return rows


class AreaTests(unittest.TestCase):
    def test_home_districts_hold_a_fifth_of_located_bills_two_at_most(self):
        rows = bills((6, "高雄市苓雅區", "測試便當店"), (3, "高雄市新興區", "測試便當店"), (1, "屏東縣恆春鎮", "測試海港餐廳"))
        self.assertEqual(areas_of(rows, CONTEXT), ["高雄市苓雅區", "高雄市新興區"])
        # Equal counts fall back to the district name, so the order never depends on the input.
        rows = bills((4, "臺北市信義區", "測試便當店"), (3, "臺北市內湖區", "測試便當店"), (3, "新北市板橋區", "測試便當店"))
        self.assertEqual(areas_of(rows, CONTEXT), ["臺北市信義區", "新北市板橋區"])

    def test_online_sellers_and_bills_without_a_district_do_not_count(self):
        rows = bills((3, "高雄市苓雅區", "測試便當店"), (5, "臺北市信義區", "蝦皮購物"), (4, None, "測試小店"))
        self.assertEqual(areas_of(rows, CONTEXT), ["高雄市苓雅區"])

    def test_nobody_reaching_a_fifth_leaves_no_home(self):
        districts = ["高雄市苓雅區", "高雄市新興區", "高雄市前鎮區", "高雄市左營區", "臺北市信義區", "臺北市內湖區"]
        self.assertEqual(areas_of(bills(*[(1, district, "測試便當店") for district in districts]), CONTEXT), [])


class DistanceTests(unittest.TestCase):
    def test_four_distances(self):
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市苓雅區", REGIONS), 0)
        self.assertEqual(place_distance("高雄市苓雅區", "高雄市左營區", REGIONS), 1)
        self.assertEqual(place_distance("高雄市苓雅區", "屏東縣恆春鎮", REGIONS), 2)
        self.assertEqual(place_distance("高雄市苓雅區", "臺北市信義區", REGIONS), 3)

    def test_the_closest_pair_counts_and_no_home_is_far(self):
        self.assertEqual(distance(["臺北市信義區", "高雄市新興區"], ["高雄市苓雅區"], REGIONS), 1)
        self.assertEqual(distance([], ["高雄市苓雅區"], REGIONS), 3)
        self.assertEqual(distance(["高雄市苓雅區"], [], REGIONS), 3)

    def test_regions_come_from_their_own_config(self):
        self.assertEqual(REGIONS["高雄市"], "南部")
        self.assertEqual(REGIONS["新竹縣"], "北部")
        self.assertEqual(len(REGIONS), 22)


if __name__ == "__main__":
    unittest.main()
```

在 `tests/test_traits.py` 中，把

```python
from src.receipt.signals import calendar_days
```

換成

```python
from src.receipt.signals import calendar_days, category_counts
```

再把

```python
class TypicalTests(unittest.TestCase):
```

換成

```python
class CategoryCountTests(unittest.TestCase):
    def test_valid_items_per_category_once_per_bill(self):
        rows = bought((WORKDAYS[:3], "測試排骨便當", 0, 100, "測試便當店", HOME),
                      (WORKDAYS[3:5], "測試紅茶", 1, 30, "測試飲料店", HOME))
        rows.append(dict(rows[0]))                                    # the same item again on the same bill
        rows.append({**rows[0], "name": "測試贈品", "amount": 0})        # a free gift
        rows.append({**rows[0], "name": "測試未分類", "category": 10, "provisional": True})
        self.assertEqual(category_counts(rows), [3, 2, 0, 0, 0, 0, 0, 0, 0, 0])


class TypicalTests(unittest.TestCase):
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_places -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.places'`

Run: `python -m unittest tests.test_traits -v`
Expected: FAIL，`ImportError: cannot import name 'category_counts' from 'src.receipt.signals'`

- [ ] **Step 3: Implement**

建立 `configs/regions.json`：

```json
{
  "北部": ["臺北市", "新北市", "基隆市", "桃園市", "新竹市", "新竹縣", "宜蘭縣"],
  "中部": ["苗栗縣", "臺中市", "彰化縣", "南投縣", "雲林縣"],
  "南部": ["嘉義市", "嘉義縣", "臺南市", "高雄市", "屏東縣"],
  "東部": ["花蓮縣", "臺東縣"],
  "離島": ["澎湖縣", "金門縣", "連江縣"]
}
```

在 `src/receipt/signals.py` 中，把

```python
def home_cities(located):
    """Cities of the districts holding at least a fifth of the located bills (two at most): where someone lives and works."""
    districts = Counter(invoice["district"] for invoice in located)
    total = sum(districts.values())
    return {district[:3] for district, seen in ranked(districts)[:2] if seen >= total * 0.2}
```

換成

```python
def home_districts(located):
    """Districts holding at least a fifth of the located bills (two at most), most bills first: where someone lives and works."""
    districts = Counter(invoice["district"] for invoice in located)
    total = sum(districts.values())
    return [district for district, seen in ranked(districts)[:2] if seen >= total * 0.2]


def home_cities(located):
    """Cities of the home districts."""
    return {district[:3] for district in home_districts(located)}
```

同一個檔案裡，在 `def valid_items(lines):` 函式結尾的

```python
            seen.add(key)
            items.append(line)
    return items
```

後面（`def average(values):` 之前）加入：

```python


def category_counts(rows):
    """Valid items per confirmed category, for the category comparison on the connection page."""
    counts = [0] * CONFIRMED
    for item in valid_items(rows):
        counts[item["category"]] += 1
    return counts
```

建立 `src/receipt/places.py`：

```python
"""Where someone shops most, and how far apart two people's home districts are."""
import json

from .signals import gather, home_districts


def load_regions(root):
    """City or county → region, from configs/regions.json."""
    regions = json.loads((root / "configs" / "regions.json").read_text(encoding="utf-8"))
    return {city: region for region, cities in regions.items() for city in cities}


def areas_of(rows, context):
    """Someone's home districts: at least a fifth of their located, paid bills, two at most, most bills first."""
    _, invoices = gather(rows, context)
    return home_districts([invoice for invoice in invoices.values() if invoice["total"] > 0 and invoice["district"]])


def place_distance(a, b, regions):
    """0 for the same district, 1 for the same city or county, 2 for the same region, 3 otherwise."""
    if a == b:
        return 0
    if a[:3] == b[:3]:
        return 1
    region = regions.get(a[:3])
    return 2 if region is not None and region == regions.get(b[:3]) else 3


def distance(mine, theirs, regions):
    """The closest pair of home districts; 3 when either side has none."""
    return min((place_distance(a, b, regions) for a in mine for b in theirs), default=3)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_places tests.test_traits -v`
Expected: 24 tests OK（`test_places` 6 個、`test_traits` 18 個）

Run: `python -m unittest discover -s tests`
Expected: 85 tests OK

- [ ] **Step 5: Commit**

```bash
git add configs/regions.json src/receipt/signals.py src/receipt/places.py tests/test_places.py tests/test_traits.py
git commit -m "feat: find home districts, distances and category counts for trait matching" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 配對設定與共用向量函式

**Files:**
- Modify: `configs/traits.json`
- Modify: `src/receipt/traits.py`
- Modify: `tests/test_traits.py`
- Modify: `tests/test_personas.py`

**Interfaces:**
- Consumes: `traits.build_vector`、`traits.typical`、`traits.relative`
- Produces:
  - `traits.json` 頂層 `"match": {"min_score": 0.3, "top": 5}`；8 個程度型各有 `"habit"`
  - `traits.population_vectors(people, period, context, extra=()) -> {"centers": list[float], "raw": dict[name, vector], "relative": dict[name, vector]}`：中間點只由 `people` 算出；`raw` 與 `relative` 依 `people` 再 `extra` 的順序；名字重複時拋出 `ValueError`

- [ ] **Step 1: Write the failing tests**

在 `tests/test_traits.py` 中，把

```python
from src.receipt.traits import between, build_vector, load_context, relative, trait_value, typical
```

換成

```python
from src.receipt.traits import between, build_vector, load_context, population_vectors, relative, trait_value, typical
```

把

```python
        self.assertEqual(CONTEXT["traits"]["similarity"], {"shrink": 0.25, "min_shared_two_sided": 5})
```

換成

```python
        self.assertEqual(CONTEXT["traits"]["similarity"], {"shrink": 0.25, "min_shared_two_sided": 5})
        self.assertEqual(CONTEXT["traits"]["match"], {"min_score": 0.3, "top": 5})
        self.assertEqual({trait["id"]: trait["habit"] for trait in TRAITS if trait["kind"] == "level"},
                         {"sport": "運動", "driving": "開車騎車", "lifestyle": "生活小物", "tech": "3C", "fun": "娛樂",
                          "pets_cat": "養貓", "pets_dog": "養狗", "alcohol": "小酌"})
```

把

```python
        self.assertIsNone(relative(None, centers))
```

換成

```python
        self.assertIsNone(relative(None, centers))

    def test_the_average_comes_from_the_population_and_extra_people_get_vectors_too(self):
        people = [{"name": "測試甲", "rows": bought(lunches())},
                  {"name": "測試乙", "rows": bought((WORKDAYS[:24], "測試全糖紅茶", 1, 40, "測試飲料店", HOME))}]
        friend = {"name": "測試丙", "rows": bought((WORKDAYS[:24], "測試冰美式", 1, 60, "測試咖啡館", HOME))}
        vectors = population_vectors(people, PERIOD, CONTEXT, extra=[friend])
        raw = vectors["raw"]
        self.assertEqual(list(raw), ["測試甲", "測試乙", "測試丙"])
        self.assertEqual(vectors["centers"], typical([raw["測試甲"], raw["測試乙"]], CONTEXT["traits"]))
        self.assertEqual(vectors["relative"]["測試丙"], relative(raw["測試丙"], vectors["centers"]))
        with self.assertRaises(ValueError):
            population_vectors(people, PERIOD, CONTEXT, extra=[{**friend, "name": "測試甲"}])
```

在 `tests/test_personas.py` 中，把

```python
from src.receipt.traits import build_vector, dated, load_context, relative, similarity_model, typical
```

換成

```python
from src.receipt.traits import build_vector, dated, load_context, population_vectors, relative, similarity_model
```

再把 `setUpClass` 裡的

```python
        cls.raw = {person["name"]: build_vector(person["rows"], list(PERIOD), CONTEXT) for person in cls.people + cls.friends}
        centers = typical([cls.raw[person["name"]] for person in cls.people], CONTEXT["traits"])
        cls.vectors = {name: relative(vector, centers) for name, vector in cls.raw.items()}
        rows, period = dated(build_demo(CATALOG))
        cls.me = relative(build_vector(rows, period, CONTEXT), centers)
```

換成

```python
        vectors = population_vectors(cls.people, list(PERIOD), CONTEXT, extra=cls.friends)
        cls.raw, cls.vectors = vectors["raw"], vectors["relative"]
        rows, period = dated(build_demo(CATALOG))
        cls.me = relative(build_vector(rows, period, CONTEXT), vectors["centers"])
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_traits tests.test_personas -v`
Expected: FAIL，`ImportError: cannot import name 'population_vectors' from 'src.receipt.traits'`

- [ ] **Step 3: Implement**

在 `configs/traits.json` 中做下列 9 處替換，每處都只出現一次：

| 原文 | 換成 |
|---|---|
| `  "similarity": {"shrink": 0.25, "min_shared_two_sided": 5},` | 同一行，後面再加一行 `  "match": {"min_score": 0.3, "top": 5},` |
| `{"id": "sport", "name": "運動投入", "kind"` | `{"id": "sport", "name": "運動投入", "habit": "運動", "kind"` |
| `{"id": "driving", "name": "自己開車騎車", "kind"` | `{"id": "driving", "name": "自己開車騎車", "habit": "開車騎車", "kind"` |
| `{"id": "lifestyle", "name": "生活質感小物", "kind"` | `{"id": "lifestyle", "name": "生活質感小物", "habit": "生活小物", "kind"` |
| `{"id": "tech", "name": "3C 投入", "kind"` | `{"id": "tech", "name": "3C 投入", "habit": "3C", "kind"` |
| `{"id": "fun", "name": "娛樂體驗", "kind"` | `{"id": "fun", "name": "娛樂體驗", "habit": "娛樂", "kind"` |
| `{"id": "pets_cat", "name": "有養寵物（貓）", "group"` | `{"id": "pets_cat", "name": "有養寵物（貓）", "habit": "養貓", "group"` |
| `{"id": "pets_dog", "name": "有養寵物（狗）", "group"` | `{"id": "pets_dog", "name": "有養寵物（狗）", "habit": "養狗", "group"` |
| `{"id": "alcohol", "name": "小酌", "kind"` | `{"id": "alcohol", "name": "小酌", "habit": "小酌", "kind"` |

改完後檔案開頭三行是：

```json
{
  "min_items": 20,
  "similarity": {"shrink": 0.25, "min_shared_two_sided": 5},
  "match": {"min_score": 0.3, "top": 5},
```

在 `src/receipt/traits.py` 的檔案最後（`relative` 函式之後）加入：

```python


def population_vectors(people, period, context, extra=()):
    """The average person from `people`, and everyone's raw and relative vectors, people first and then `extra`.

    Names must be unique, so no one can silently replace someone else.
    """
    everyone = [*people, *extra]
    names = [person["name"] for person in everyone]
    if len(set(names)) != len(names):
        raise ValueError("Every person needs a unique name")
    raw = {person["name"]: build_vector(person["rows"], period, context) for person in everyone}
    centers = typical([raw[person["name"]] for person in people], context["traits"])
    return {"centers": centers, "raw": raw, "relative": {name: relative(vector, centers) for name, vector in raw.items()}}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `python -m unittest tests.test_traits tests.test_personas -v`
Expected: 26 tests OK（`test_traits` 19 個、`test_personas` 7 個）

Run: `python -m unittest discover -s tests`
Expected: 86 tests OK

- [ ] **Step 5: Commit**

```bash
git add configs/traits.json src/receipt/traits.py tests/test_traits.py tests/test_personas.py
git commit -m "feat: add match settings and one shared way to build population vectors" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 配對頁的名單與文字

**Files:**
- Modify（整檔改寫）: `src/web/match-filter.js`
- Modify（整檔改寫）: `tests/match-filter.test.cjs`

**Interfaces:**
- Consumes: `src/web/trait-similarity.js` 的 `compare`、`percent`（Node 以 `require('./trait-similarity.js')` 取得；瀏覽器用全域 `TraitSimilarity`，所以頁面要先載入 `trait-similarity.js`）
- Produces（`MatchFilter`，Node 以 `require('../src/web/match-filter.js')` 取得）：
  - 資料格式（`data`，即 Task 5 的 `matchReportData`）：`{model, traits: [{id, name, kind, ends?, habit?}], settings: {min_score, top, min_items}, me: {vector | null, months, areas, counts}, people: [{name, vector, distance, place, counts}], isDemo, population, personaMonths}`
  - `view(data, choice)`，`choice = {range: null | 0 | 1 | 2, opposite: boolean}`：
    - 「我」沒有向量時回傳 `{ready: false, mine, thin}`
    - 否則回傳 `{ready: true, mine: {lean, habits}, note, ranges: [{level, label, disabled}], match: {status, cards}, opposite: {status, cards} | null}`
  - 卡片：`{person, name, score: '+62%', percent: 62, opposite: boolean, place, alike, unlike}`
  - 另外輸出 `RANGES`、`signed`、`scored`、`pick`、`phrase`、`reasons`、`mine`、`status` 供測試

- [ ] **Step 1: Write the failing test**

把 `tests/match-filter.test.cjs` 整檔換成：

```javascript
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { RANGES, signed, pick, phrase, reasons, mine, view } = require('../src/web/match-filter.js');

const MINUS = String.fromCharCode(0x2212);
const traits = [
  { id: 'spend', name: '省錢 ↔ 享受', kind: 'two_sided', ends: ['省錢', '享受'] },
  { id: 'sweet', name: '清爽 ↔ 香甜', kind: 'two_sided', ends: ['清爽', '香甜'] },
  { id: 'travel', name: '待在生活圈 ↔ 常出遊', kind: 'two_sided', ends: ['待在生活圈', '常出遊'] },
  { id: 'routine', name: '固定習慣 ↔ 喜歡嘗鮮', kind: 'two_sided', ends: ['固定習慣', '喜歡嘗鮮'] },
  { id: 'meals', name: '快速解決 ↔ 好好吃飯', kind: 'two_sided', ends: ['快速解決', '好好吃飯'] },
  { id: 'cooking', name: '外食 ↔ 自己煮', kind: 'two_sided', ends: ['外食', '自己煮'] },
  { id: 'pets_cat', name: '有養寵物（貓）', kind: 'level', habit: '養貓' },
];
const model = { cells: traits.map(trait => ({ id: trait.id, kind: trait.kind, weight: 1 })), shrink: 0.25, min_shared_two_sided: 5 };
const settings = { min_score: 0.3, top: 5, min_items: 20 };
const entry = (name, score, distance = 0) => ({ person: { name, distance }, score });
const names = list => list.map(item => item.name ?? item.person.name);
const counts = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0];
const meVector = [0.5, 0.5, 0.5, 0.5, 0.5, 0.5, 0.4];
const flipped = meVector.map((value, index) => (traits[index].kind === 'level' ? value : -value));
const data = {
  model, traits, settings,
  me: { vector: meVector, months: ['2026-03', '2026-04'], areas: ['高雄市苓雅區'], counts },
  people: [
    { name: '測試甲', vector: meVector, distance: 0, place: '高雄市苓雅區', counts },
    { name: '測試乙', vector: flipped, distance: 3, place: '臺北市信義區', counts },
    { name: '測試丙', vector: [0, 0, 0, 0, 0, 0, 0], distance: 1, place: null, counts },
    // Only four two-sided cells in common with me, so this person cannot be compared.
    { name: '測試丁', vector: [0.5, null, null, 0.5, 0.5, 0.5, 0.4], distance: 0, place: null, counts },
  ],
};

test('scores read +62%, −42% and 0%, halves rounding up', () => {
  assert.equal(signed(0.6227), '+62%');
  assert.equal(signed(-0.4193), MINUS + '42%');
  assert.equal(signed(0), '0%');
  assert.equal(signed(-0.004), '0%');
  assert.equal(signed(0.625), '+63%');
});

test('the match list keeps people at +30% or more, strongest first, ties by name, five at most', () => {
  const entries = [entry('F', 0.31), entry('B', 0.6), entry('A', 0.6), entry('C', 0.45), entry('D', 0.3), entry('E', 0.9),
    entry('G', 0.29), entry('H', -0.5)];
  const result = pick(entries, settings, false, null);
  assert.equal(result.eligible, 6);
  assert.equal(result.within, 6);
  assert.deepEqual(names(result.shown), ['E', 'A', 'B', 'C', 'F']);
});

test('the opposite list mirrors it at −30% or less, most opposite first', () => {
  const entries = [entry('A', -0.3), entry('B', -0.5), entry('C', -0.29), entry('D', 0.8), entry('E', -0.5)];
  const result = pick(entries, settings, true, null);
  assert.equal(result.eligible, 3);
  assert.deepEqual(names(result.shown), ['B', 'E', 'A']);
});

test('a distance narrows people before the top five are taken', () => {
  const entries = ['A', 'B', 'C', 'D', 'E', 'F', 'G'].map((name, i) => entry(name, 0.9 - i * 0.05, i < 5 ? 3 : 1));
  const near = pick(entries, settings, false, 1);
  assert.deepEqual([near.eligible, near.within], [7, 2]);
  assert.deepEqual(names(near.shown), ['F', 'G']);
  assert.deepEqual(names(pick(entries, settings, false, 0).shown), []);
  assert.deepEqual(RANGES.map(option => [option.level, option.label]), [[null, '不限'], [0, '同一區'], [1, '同縣市'], [2, '同地區']]);
});

test('a card says which way both lean, which way each leans, or which habit both have', () => {
  assert.equal(phrase(traits[1], 1, 0.4), '都偏香甜');
  assert.equal(phrase(traits[1], -0.3, -1), '都偏清爽');
  assert.equal(phrase(traits[2], 0.61, -0.19), '你偏常出遊，對方偏待在生活圈');
  assert.equal(phrase(traits[6], 0.4, 0.7), '都有養貓的紀錄');
  assert.equal(phrase({ kind: 'level', habit: '3C' }, 0.3, 0.5), '都有 3C 的紀錄');
});

test('the most and least alike cells come from the largest and smallest parts, or nothing', () => {
  const me = [0.5, 1, 0.6, 0.2, 0.1, 0, 0.4];
  const alike = { name: 'A', vector: [0.4, 1, -0.2, 0.3, 0.1, 0.2, 0.5] };
  assert.deepEqual(reasons({ person: alike, parts: [0.05, 0.3, -0.04, 0.02, 0.003, 0, 0.06] }, me, traits),
    { alike: '都偏香甜', unlike: '你偏常出遊，對方偏待在生活圈' });
  assert.deepEqual(reasons({ person: alike, parts: [0.05, null, 0.01, 0, 0, 0, 0] }, me, traits), { alike: '都偏享受', unlike: null });
  const opposite = { name: 'B', vector: [-0.4, -0.6, 0, 0, 0, 0, 0] };
  assert.deepEqual(reasons({ person: opposite, parts: [-0.05, -0.2, 0, 0, 0, 0, 0] }, me, traits),
    { alike: null, unlike: '你偏香甜，對方偏清爽' });
});

test('my traits list up to three leanings past 0.2, then the habits on record', () => {
  assert.deepEqual(mine([0.25, 1, -1, 0.65, 0.1, -0.19, 0.4], traits),
    { lean: '跟一般人比：偏香甜・偏待在生活圈・偏喜歡嘗鮮', habits: '也有養貓的紀錄' });
  assert.deepEqual(mine([0.1, 0, 0, 0, 0, 0, 0.3], traits), { lean: '', habits: '也有養貓的紀錄' });
  assert.deepEqual(mine([0.1, -0.1, 0, 0.05, null, 0, 0], traits), { lean: '跟一般人差不多', habits: '' });
  assert.deepEqual(mine(null, traits), { lean: '資料還不夠，看不出品味特質', habits: '' });
});

test('the page lists matches, and opposites only when asked', () => {
  const shown = view(data, { range: null, opposite: false });
  assert.equal(shown.ready, true);
  assert.deepEqual(shown.mine, { lean: '跟一般人比：偏享受・偏香甜・偏常出遊', habits: '也有養貓的紀錄' });
  assert.equal(shown.note, '你的生活圈：高雄市苓雅區');
  assert.ok(shown.ranges.every(option => !option.disabled));
  assert.equal(shown.match.status, '1 位品味相似度 +30% 以上。');
  const [first] = shown.match.cards;
  assert.deepEqual([first.name, first.score, first.percent, first.opposite, first.place, first.alike, first.unlike],
    ['測試甲', '+87%', 87, false, '高雄市苓雅區', '都偏享受', null]);
  assert.equal(shown.opposite, null);
  const both = view(data, { range: null, opposite: true });
  assert.equal(both.opposite.status, '1 位品味相似度 ' + MINUS + '30% 以下。');
  const [other] = both.opposite.cards;
  assert.deepEqual([other.name, other.score, other.percent, other.opposite, other.alike, other.unlike],
    ['測試乙', MINUS + '70%', -70, true, '都有養貓的紀錄', '你偏享受，對方偏省錢']);
});

test('the page explains an empty distance, missing home districts, nobody close and thin data', () => {
  assert.equal(view(data, { range: 0, opposite: true }).opposite.status,
    '這個距離內沒有品味相似度 ' + MINUS + '30% 以下的人，試試放寬距離。');
  const homeless = view({ ...data, me: { ...data.me, areas: [] } }, { range: 0, opposite: false });
  assert.equal(homeless.note, '看不出你的生活圈，只能選「不限」。');
  assert.deepEqual(homeless.ranges.map(option => option.disabled), [false, true, true, true]);
  assert.equal(homeless.match.status, '1 位品味相似度 +30% 以上。');
  const nobody = view({ ...data, people: [data.people[2], data.people[3]] }, { range: null, opposite: true });
  assert.equal(nobody.match.status, '目前沒有品味夠相似的人（+30% 以上）。');
  assert.equal(nobody.opposite.status, '目前沒有和你明顯相反的人（' + MINUS + '30% 以下）。');
  const many = view({ ...data, people: ['A', 'B', 'C', 'D', 'E', 'F', 'G'].map(name => ({ ...data.people[0], name })) },
    { range: null, opposite: false });
  assert.equal(many.match.status, '7 位品味相似度 +30% 以上，顯示前 5 位。');
  assert.equal(many.match.cards.length, 5);
  assert.deepEqual(view({ ...data, me: { ...data.me, vector: null } }, { range: null, opposite: false }), {
    ready: false, mine: { lean: '資料還不夠，看不出品味特質', habits: '' },
    thin: '你的資料還不夠（有效品項少於 20 筆），先累積更多發票，再來找同好。' });
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/match-filter.test.cjs`
Expected: FAIL（舊檔沒有 `signed`、`pick` 等函式，出現 `TypeError: signed is not a function` 之類的錯誤）

- [ ] **Step 3: Implement**

把 `src/web/match-filter.js` 整檔換成：

```javascript
/* Who the match page shows and what it says; the page and its tests share these pure functions. */
(function (root) {
  'use strict';
  const similarity = typeof module !== 'undefined' && module.exports ? require('./trait-similarity.js') : root.TraitSimilarity;
  const MINUS = String.fromCharCode(0x2212);  // the minus sign, not a hyphen
  const RANGES = Object.freeze([
    { level: null, label: '不限' }, { level: 0, label: '同一區' }, { level: 1, label: '同縣市' }, { level: 2, label: '同地區' }]);
  // Code-point order, as Python sorts names, so both sides break ties the same way.
  const byName = (a, b) => (a < b ? -1 : a > b ? 1 : 0);

  // +62%, −42% or 0%, rounding halves up as percent() does.
  function signed(score) {
    const whole = similarity.percent(score);
    return (whole > 0 ? '+' : whole < 0 ? MINUS : '') + Math.abs(whole) + '%';
  }

  // Everyone who can be compared with me, in the payload's order, with their score and each cell's share of it.
  function scored(data) {
    return data.people.map(person => ({ person, ...similarity.compare(data.me.vector, person.vector, data.model) }))
      .filter(entry => entry.comparable);
  }

  // People past the threshold on one side, then within the chosen distance; strongest first, ties by name.
  function pick(entries, settings, opposite, range) {
    const eligible = entries.filter(entry => (opposite ? entry.score <= -settings.min_score : entry.score >= settings.min_score));
    const within = eligible.filter(entry => range === null || entry.person.distance <= range)
      .sort((a, b) => (opposite ? a.score - b.score : b.score - a.score) || byName(a.person.name, b.person.name));
    return { eligible: eligible.length, within: within.length, shown: within.slice(0, settings.top) };
  }

  const end = (trait, value) => trait.ends[value > 0 ? 1 : 0];
  const latin = /[A-Za-z0-9]/;
  // Chinese next to Latin letters or digits gets a space, as the report writes 「3C 投入」.
  function words(...pieces) {
    return pieces.reduce((text, piece) => {
      const gap = text && piece && latin.test(text[text.length - 1]) !== latin.test(piece[0]);
      return text + (gap ? ' ' : '') + piece;
    }, '');
  }

  // How one cell reads on a card: a habit both have, both on one side, or opposite sides.
  function phrase(trait, mine, theirs) {
    if (trait.kind === 'level') return words('都有', trait.habit, '的紀錄');
    if (mine * theirs > 0) return '都偏' + end(trait, mine);
    return '你偏' + end(trait, mine) + '，對方偏' + end(trait, theirs);
  }

  // The cell that adds most to the score and the one that takes most away; null when there is none.
  function reasons(entry, me, traits) {
    let best = null, worst = null;
    entry.parts.forEach((part, index) => {
      if (part === null) return;
      if (part > 0 && (best === null || part > entry.parts[best])) best = index;
      if (part < 0 && (worst === null || part < entry.parts[worst])) worst = index;
    });
    const describe = index => (index === null ? null : phrase(traits[index], me[index], entry.person.vector[index]));
    return { alike: describe(best), unlike: describe(worst) };
  }

  // My three most distinctive two-sided traits (at least 0.2 from the average) and the habits on record.
  function mine(vector, traits) {
    if (!vector) return { lean: '資料還不夠，看不出品味特質', habits: '' };
    const leaning = traits.map((trait, index) => ({ trait, index, value: vector[index] }))
      .filter(({ trait, value }) => trait.kind === 'two_sided' && value !== null && Math.abs(value) >= 0.2)
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value) || a.index - b.index)
      .slice(0, 3).map(({ trait, value }) => '偏' + end(trait, value));
    const habits = traits.filter((trait, index) => trait.kind === 'level' && vector[index] > 0).map(trait => trait.habit);
    if (!leaning.length && !habits.length) return { lean: '跟一般人差不多', habits: '' };
    return { lean: leaning.length ? '跟一般人比：' + leaning.join('・') : '', habits: habits.length ? words('也有', habits.join('、'), '的紀錄') : '' };
  }

  function status(result, settings, opposite) {
    const line = signed(opposite ? -settings.min_score : settings.min_score) + (opposite ? ' 以下' : ' 以上');
    if (!result.eligible) return opposite ? '目前沒有和你明顯相反的人（' + line + '）。' : '目前沒有品味夠相似的人（' + line + '）。';
    if (!result.within) return '這個距離內沒有品味相似度 ' + line + '的人，試試放寬距離。';
    return result.within + ' 位品味相似度 ' + line + (result.within > settings.top ? '，顯示前 ' + settings.top + ' 位' : '') + '。';
  }

  function card(entry, data) {
    const why = reasons(entry, data.me.vector, data.traits);
    return { person: entry.person, name: entry.person.name, score: signed(entry.score), percent: similarity.percent(entry.score),
      opposite: entry.score < 0, place: entry.person.place, alike: why.alike, unlike: why.unlike };
  }

  // Everything the page shows for a choice of distance (null for any) and whether opposites are wanted.
  function view(data, choice) {
    const { settings, me } = data;
    const profile = mine(me.vector, data.traits);
    if (!me.vector) {
      return { ready: false, mine: profile, thin: '你的資料還不夠（有效品項少於 ' + settings.min_items + ' 筆），先累積更多發票，再來找同好。' };
    }
    const entries = scored(data), located = me.areas.length > 0, range = located ? choice.range : null;
    const list = opposite => {
      const result = pick(entries, settings, opposite, range);
      return { status: status(result, settings, opposite), cards: result.shown.map(entry => card(entry, data)) };
    };
    return {
      ready: true, mine: profile,
      note: located ? '你的生活圈：' + me.areas.join('、') : '看不出你的生活圈，只能選「不限」。',
      ranges: RANGES.map(option => ({ ...option, disabled: option.level !== null && !located })),
      match: list(false), opposite: choice.opposite ? list(true) : null,
    };
  }

  const api = Object.freeze({ RANGES, signed, scored, pick, phrase, reasons, mine, status, view });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.MatchFilter = api;
})(globalThis);
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/match-filter.test.cjs`
Expected: 9 tests pass

Run: `node --test tests/*.test.cjs`
Expected: 37 tests pass

不要執行 `python scripts/build_report.py`（見 Global Constraints）。

- [ ] **Step 5: Commit**

```bash
git add src/web/match-filter.js tests/match-filter.test.cjs
git commit -m "feat: pick matches and word the cards from trait similarity" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 連線頁接受負分（過渡）

**Files:**
- Modify: `src/web/taste-profile.js`
- Modify: `src/web/taste-comparison.html`
- Modify: `tests/taste-profile.test.cjs`

**Interfaces:**
- Consumes: 配對頁傳來的 `pair = {score: 整數百分比, left, right}`（Task 5 的卡片 `percent`）
- Produces: `TasteProfile.fromPair(pair)` 接受 −100～+100 的整數；連線頁大字標籤為「品味相似度」，數字帶正負號

- [ ] **Step 1: Write the failing test**

在 `tests/taste-profile.test.cjs` 中，把最後一個測試

```javascript
test('a match pair carries a whole-number score and two valid profiles',()=>{
 const side=(name,demo)=>({name,demo,months:['2026-03','2026-04'],counts:[3,2,0,0,0,0,0,0,0,0]});
 const pair=taste.fromPair({score:81,left:side('你',false),right:side('手搖學生 D',true)});
 assert.equal(pair.score,81);assert.equal(pair.left.name,'你');assert.equal(pair.right.schema,taste.schema);
 for(const invalid of [null,{score:81.5,left:side('你',false),right:side('D',true)},{score:101,left:side('你',false),right:side('D',true)},
  {score:81,left:side('你',false),right:{...side('D',true),counts:[1]}}])assert.throws(()=>taste.fromPair(invalid));
});
```

換成

```javascript
test('a match pair carries a whole-number score from -100 to 100 and two valid profiles',()=>{
 const side=(name,demo)=>({name,demo,months:['2026-03','2026-04'],counts:[3,2,0,0,0,0,0,0,0,0]});
 const pair=taste.fromPair({score:62,left:side('你',false),right:side('手搖學生 A',true)});
 assert.equal(pair.score,62);assert.equal(pair.left.name,'你');assert.equal(pair.right.schema,taste.schema);
 for(const score of [-100,-42,0,100])assert.equal(taste.fromPair({score,left:side('你',false),right:side('A',true)}).score,score);
 for(const invalid of [null,{score:61.5,left:side('你',false),right:side('A',true)},{score:101,left:side('你',false),right:side('A',true)},
  {score:-101,left:side('你',false),right:side('A',true)},{score:62,left:side('你',false),right:{...side('A',true),counts:[1]}}])assert.throws(()=>taste.fromPair(invalid));
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/taste-profile.test.cjs`
Expected: 1 個 FAIL（`fromPair` 拒絕 −100）

- [ ] **Step 3: Implement**

在 `src/web/taste-profile.js` 中，把

```javascript
  if(!pair||!Number.isSafeInteger(pair.score)||pair.score<0||pair.score>100)throw
```

換成

```javascript
  if(!pair||!Number.isSafeInteger(pair.score)||pair.score<-100||pair.score>100)throw
```

在 `src/web/taste-comparison.html` 中，把

```javascript
document.querySelector('.overall-label').textContent=pair?'配對分數':
```

換成

```javascript
document.querySelector('.overall-label').textContent=pair?'品味相似度':
```

再把

```javascript
if(pair){$('overall-score').textContent=pair.score;
```

換成

```javascript
if(pair){$('overall-score').textContent=(pair.score>0?'+':pair.score<0?String.fromCharCode(0x2212):'')+Math.abs(pair.score);
```

（這兩處都在很長的一行裡，只替換這段文字，同一行的其他內容不動。）

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/taste-profile.test.cjs`
Expected: 6 tests pass

Run: `node --test tests/*.test.cjs`
Expected: 37 tests pass

不要執行 `python scripts/build_report.py`（見 Global Constraints）。

- [ ] **Step 5: Commit**

```bash
git add src/web/taste-profile.js src/web/taste-comparison.html tests/taste-profile.test.cjs
git commit -m "feat: let the connection page show a negative taste similarity" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 產生配對資料、新配對頁，移除舊配對

**Files:**
- Modify（整檔改寫）: `src/receipt/build.py`
- Modify（整檔改寫）: `src/web/match.html`
- Delete: `src/receipt/tags.py`、`src/receipt/matching.py`、`configs/tags.json`、`tests/test_tags.py`、`tests/test_matching.py`
- Modify: `tests/test_build_report.py`
- Create: `tests/match-page.test.cjs`
- 重新產生: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 1 的 `areas_of`、`distance`、`load_regions`、`category_counts`；Task 2 的 `population_vectors` 與 `traits.json` 的 `match`、`habit`；Task 3 的 `MatchFilter.view`、`MatchFilter.signed`；Task 4 的 `fromPair`
- Produces:
  - `build.build_matches(months, population, context, regions, is_demo) -> matchReportData`（格式見 Task 3 的 Interfaces）
  - `build.trait_words(settings)`；`build.taste_summary(months, population, friends, context)` 介面不變
  - 配對頁依序嵌入 `trait-similarity.js`、`match-filter.js`、`match-data.js`

- [ ] **Step 1: Write the failing tests**

在 `tests/test_build_report.py` 的 `test_default_build_ignores_private_sources_and_preserves_private_html` 裡，把

```python
            self.assertIn('data-source="match-filter.js"', match_page)
            self.assertIn("此配對頁只用行政區與連鎖品牌", match_page)
            payload = json.loads(re.search(r"const matchReportData = (.*?);\n</script>", match_page, re.S).group(1))
            self.assertTrue(payload["isDemo"])
            self.assertEqual(payload["population"], 40)
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

換成

```python
            self.assertIn('data-source="trait-similarity.js"', match_page)
            self.assertIn('data-source="match-filter.js"', match_page)
            self.assertIn("此配對頁只用行政區與特質分數", match_page)
            payload = json.loads(re.search(r"const matchReportData = (.*?);\n</script>", match_page, re.S).group(1))
            self.assertTrue(payload["isDemo"])
            self.assertEqual(payload["population"], 40)
            self.assertEqual(payload["settings"], {"min_score": 0.3, "top": 5, "min_items": 20})
            self.assertEqual(payload["personaMonths"], ["2026-03", "2026-04"])
            self.assertEqual(len(payload["model"]["cells"]), 18)
            self.assertEqual([trait["id"] for trait in payload["traits"]], [cell["id"] for cell in payload["model"]["cells"]])
            self.assertEqual(len(payload["me"]["vector"]), 18)
            self.assertEqual(payload["me"]["months"], ["2026-03", "2026-04"])
            self.assertEqual(payload["me"]["areas"], ["高雄市苓雅區", "高雄市新興區"])
            self.assertEqual(len(payload["me"]["counts"]), 10)
            self.assertEqual(len(payload["people"]), 40)
            for person in payload["people"]:
                self.assertEqual(set(person), {"name", "vector", "distance", "place", "counts"})
                self.assertEqual((len(person["vector"]), len(person["counts"])), (18, 10))
            # Shop and item names in the demo all start with 示範; none may reach the match page's data.
            self.assertNotIn("示範", json.dumps(payload, ensure_ascii=False))
```

同一個檔案的 `test_build_from_another_directory_is_self_contained_and_repeatable` 裡，把

```python
            self.assertFalse(payload["me"]["ready"])
            self.assertEqual(payload["candidates"], [])
```

換成

```python
            self.assertIsNone(payload["me"]["vector"])
            self.assertEqual(len(payload["people"]), 40)
```

建立 `tests/match-page.test.cjs`：

```javascript
const { test } = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { view } = require('../src/web/match-filter.js');

const MINUS = String.fromCharCode(0x2212);
const between = (text, start, end) => {
  const from = text.indexOf(start) + start.length;
  return text.slice(from, text.indexOf(end, from));
};
const unescapeHtml = text => [['&lt;', '<'], ['&gt;', '>'], ['&quot;', '"'], ['&#x27;', "'"], ['&amp;', '&']]
  .reduce((result, [entity, character]) => result.split(entity).join(character), text);
// The built demo report keeps the match page, escaped, inside a template element.
const html = fs.readFileSync(path.join(__dirname, '..', 'invoice-insights.html'), 'utf8');
const page = unescapeHtml(between(html, '<template id="match-page-source">', '</template>'));
const data = JSON.parse(between(page, 'const matchReportData = ', '</script>').trim().replace(/;$/, ''));
const summary = cards => cards.map(card => [card.name, card.score]);

test('the demo lists the three sweet-toothed students and two holiday travellers', () => {
  const shown = view(data, { range: null, opposite: false });
  assert.equal(shown.match.status, '5 位品味相似度 +30% 以上。');
  assert.deepEqual(summary(shown.match.cards), [['手搖學生 A', '+62%'], ['手搖學生 B', '+62%'], ['手搖學生 C', '+53%'],
    ['連假旅人 E', '+34%'], ['連假旅人 D', '+32%']]);
  const [first, , , fourth] = shown.match.cards;
  assert.deepEqual([first.alike, first.unlike, first.place], ['都偏香甜', '你偏常出遊，對方偏待在生活圈', '高雄市苓雅區']);
  assert.deepEqual([fourth.alike, fourth.unlike], ['都偏避開連假', '你偏香甜，對方偏清爽']);
  assert.deepEqual(shown.mine, { lean: '跟一般人比：偏香甜・偏避開連假・偏喜歡嘗鮮', habits: '也有運動、生活小物、3C 的紀錄' });
  assert.equal(shown.note, '你的生活圈：高雄市苓雅區、高雄市新興區');
});

test('within the same city only the three students remain', () => {
  const shown = view(data, { range: 1, opposite: false });
  assert.deepEqual(shown.match.cards.map(card => card.name), ['手搖學生 A', '手搖學生 B', '手搖學生 C']);
});

test('the opposite list is the five thrifty office workers', () => {
  const shown = view(data, { range: null, opposite: true });
  assert.equal(shown.opposite.status, '8 位品味相似度 ' + MINUS + '30% 以下，顯示前 5 位。');
  assert.deepEqual(summary(shown.opposite.cards), [['省錢上班族 E', MINUS + '42%'], ['省錢上班族 B', MINUS + '41%'],
    ['省錢上班族 A', MINUS + '41%'], ['省錢上班族 D', MINUS + '41%'], ['省錢上班族 C', MINUS + '41%']]);
  assert.ok(shown.opposite.cards.every(card => card.alike === '都偏省錢' && card.unlike === '你偏香甜，對方偏清爽'));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_build_report -v`
Expected: 2 個 FAIL（例如 `'data-source="trait-similarity.js"' not found`、`KeyError: 'vector'`）

Run: `node --test tests/match-page.test.cjs`
Expected: FAIL（根目錄的 `invoice-insights.html` 還是舊資料，沒有 `model`、`people`）

- [ ] **Step 3: Rewrite the build**

把 `src/receipt/build.py` 整檔換成：

```python
"""Generate a standalone HTML report from configuration, source assets and local data."""
import argparse
from html import escape
import json
import re
from pathlib import Path

from .invoices import build_month
from .demo import build_demo
from .personas import PERIOD, build_friends, build_personas
from .places import areas_of, distance, load_regions
from .signals import category_counts
from .similarity import compare, percent
from .traits import build_vector, dated, load_context, population_vectors, relative, similarity_model

ROOT = Path(__file__).resolve().parents[2]
WEB = ROOT / "src" / "web"
CONFIG = ROOT / "configs" / "report.json"


def embed_scripts(html, scripts):
    """Refresh inline scripts, accepting either original references or a prior build."""
    for name, source in scripts.items():
        pattern = (r'<script\b[^>]*\b(?:src|data-source)="'
                   + re.escape(name) + r'"[^>]*>.*?</script\s*>')
        # An HTML parser recognizes closing script tags even inside JS strings.
        safe_source = re.sub(r'</script', lambda match: r'<\/' + match[0][2:],
                             source, flags=re.IGNORECASE)
        replacement = f'<script data-source="{name}">\n{safe_source.rstrip()}\n</script>'
        html, count = re.subn(pattern, lambda _: replacement, html, flags=re.DOTALL)
        if count != 1:
            raise ValueError(f'Expected exactly one script block for {name}; got {count}')
    return html


def embed_page(html, template_id, page):
    """Place a standalone page inside a template element so the report stays one file."""
    marker = f'<template id="{template_id}"></template>'
    if html.count(marker) != 1:
        raise ValueError(f"Expected exactly one template: {template_id}")
    return html.replace(marker, f'<template id="{template_id}">' + escape(page) + "</template>", 1)


def script_constant(name, value):
    # A product name must not be able to introduce an HTML script element.
    payload = json.dumps(value, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    return f"'use strict';\nconst {name} = " + payload + ";\n"


def trait_words(settings):
    """How the match page names each trait: its two ends, or the short word for a habit."""
    words = []
    for trait in settings["traits"]:
        entry = {"id": trait["id"], "name": trait["name"], "kind": trait["kind"]}
        entry.update({"ends": trait["ends"]} if trait["kind"] == "two_sided" else {"habit": trait["habit"]})
        words.append(entry)
    return words


def build_matches(months, population, context, regions, is_demo):
    """Everyone's taste vector, measured from the average person, for the match page to score in the browser."""
    settings = context["traits"]
    vectors = population_vectors(population, list(PERIOD), context)
    rows, period = dated(months)
    mine = areas_of(rows, context)
    people = []
    for person in population:
        areas = areas_of(person["rows"], context)
        people.append({"name": person["name"], "vector": vectors["relative"][person["name"]],
                       "distance": distance(mine, areas, regions), "place": areas[0] if areas else None,
                       "counts": category_counts(person["rows"])})
    return {
        "isDemo": is_demo, "population": len(people),
        "personaMonths": [f"{year}-{month:02}" for year, month in PERIOD],
        "model": similarity_model(settings), "traits": trait_words(settings),
        "settings": {**settings["match"], "min_items": settings["min_items"]},
        "me": {"vector": relative(build_vector(rows, period, context), vectors["centers"]), "months": sorted(months),
               "areas": mine, "counts": category_counts(rows)},
        "people": people,
    }


def taste_summary(months, population, friends, context):
    """My taste vector and my similarity to each fictional person, all measured from the average person."""
    vectors = population_vectors(population, list(PERIOD), context, extra=friends)
    rows, period = dated(months)
    me = relative(build_vector(rows, period, context), vectors["centers"])
    model = similarity_model(context["traits"])
    scores = [compare(me, vectors["relative"][person["name"]], model)["score"] for person in population]
    return me, sorted(score for score in scores if score is not None)


def main():
    parser = argparse.ArgumentParser(description="Build a public demo, or an explicitly requested private report.")
    parser.add_argument("--private", action="store_true", help="Read data/private/report.json and write invoice-insights-private.html")
    args = parser.parse_args()
    config_path = ROOT / "data" / "private" / "report.json" if args.private else CONFIG
    config = json.loads(config_path.read_text(encoding="utf-8"))
    catalog = json.loads((ROOT / config["category_catalog"]).read_text(encoding="utf-8"))
    if args.private:
        months = {}
        for filename in config["input_files"]:
            key, month = build_month(ROOT / filename, catalog)
            if key in months:
                raise ValueError(f"Duplicate month in input files: {key}")
            months[key] = month
    else:
        months = build_demo(catalog)
    data = {"isDemo": not args.private, "categories": config["categories"], "months": months}
    data_script = script_constant("expenseReportData", data)
    scripts = {"report-data.js": data_script}
    for name in ("insights-ui.js", "monthly-comparison.js", "comparison-ui.js", "flow-navigation.js", "taste-profile.js", "taste-export.js", "taste-navigation.js"):
        scripts[name] = (WEB / name).read_text(encoding="utf-8")
    template = (WEB / "invoice-insights.html").read_text(encoding="utf-8")
    style_link = '<link rel="stylesheet" href="styles.css">'
    if template.count(style_link) != 1:
        raise ValueError("Expected exactly one stylesheet link in the HTML template")
    stylesheet = (WEB / "styles.css").read_text(encoding="utf-8")
    html = embed_scripts(template.replace(style_link, "<style>" + stylesheet + "</style>", 1), scripts)
    comparison = (WEB / "taste-comparison.html").read_text(encoding="utf-8")
    comparison = embed_scripts(comparison, {"taste-profile.js": scripts["taste-profile.js"]})
    html = embed_page(html, "taste-page-source", comparison)
    context = load_context(ROOT)
    population = build_personas(context["calendar"])
    matches = build_matches(months, population, context, load_regions(ROOT), not args.private)
    match_page = embed_scripts((WEB / "match.html").read_text(encoding="utf-8"), {
        "trait-similarity.js": (WEB / "trait-similarity.js").read_text(encoding="utf-8"),
        "match-filter.js": (WEB / "match-filter.js").read_text(encoding="utf-8"),
        "match-data.js": script_constant("matchReportData", matches)})
    html = embed_page(html, "match-page-source", match_page)
    processed = ROOT / "data" / ("private" if args.private else "processed")
    processed.mkdir(parents=True, exist_ok=True)
    (processed / "report-data.js").write_text(data_script, encoding="utf-8")
    output = "invoice-insights-private.html" if args.private else "invoice-insights.html"
    (ROOT / output).write_text(html, encoding="utf-8")
    for key, month in months.items():
        print(key, len(month["rows"]), "rows; total", sum(row["amount"] for row in month["rows"]))
    me, scores = taste_summary(months, population, build_friends(context["calendar"]), context)
    if me is None or not scores:
        print("taste vector: not enough data to compare")
    else:
        middle = scores[len(scores) // 2]
        print(f"taste similarity to {len(scores)} fictional people: highest {percent(scores[-1])}%, "
              f"median {percent(middle)}%, lowest {percent(scores[0])}%")


if __name__ == "__main__":
    main()
```

- [ ] **Step 4: Rewrite the match page**

把 `src/web/match.html` 整檔換成：

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
.mine{margin-top:18px;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px 18px}.mine h2{margin:0 0 2px}.mine p{margin:0}
.matches,.opposites{margin-top:26px}.status{margin:0 0 4px}
.ranges{display:flex;flex-wrap:wrap;gap:8px 18px;margin:12px 0 4px}
.ranges label{display:flex;align-items:center;gap:6px;cursor:pointer}.ranges input{accent-color:var(--teal);width:16px;height:16px;margin:0}
.ranges label.off{color:#77756f;cursor:not-allowed}
.switch{display:flex;align-items:center;gap:8px;margin-top:22px;cursor:pointer;width:max-content}.switch input{accent-color:var(--amber);width:16px;height:16px;margin:0}
.card{display:block;width:100%;text-align:left;font:inherit;color:inherit;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:16px 20px;margin-top:12px;cursor:pointer}
.card:hover,.card:focus-visible{border-color:var(--teal);outline:none}
.card-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px}
.score{font-size:24px;font-weight:600;color:var(--teal)}.score.opposite{color:var(--amber)}
.place{display:inline-block;border:1px solid var(--line);border-radius:999px;padding:0 9px;font-size:11px;font-weight:400;color:var(--muted);margin-left:8px;vertical-align:middle}
.pair{display:grid;grid-template-columns:auto 1fr;gap:4px 12px;margin:10px 0 0;font-size:13px}
.pair dt{color:var(--muted)}.pair dd{margin:0;min-width:0;overflow-wrap:anywhere}.pair .like{color:var(--teal)}.pair .unlike{color:var(--amber)}
details{margin-top:22px;color:var(--muted);font-size:12px}details summary{cursor:pointer}details p{margin:8px 0}
@media(max-width:640px){h1{font-size:23px}.card{padding:14px}}
</style>
</head>
<body>
<main>
<a id="return-report" class="return-report" href="#report" hidden>← 返回消費洞察</a>
<p class="eyebrow">FIND YOUR PEOPLE · 找到同好</p>
<h1>從消費習慣，找到合拍的人。</h1>
<p class="note" id="match-note"></p>
<section class="mine" aria-labelledby="mine-title">
<h2 id="mine-title">你的品味特質</h2>
<p id="my-lean"></p>
<p class="note" id="my-habits" hidden></p>
</section>
<section class="matches" aria-labelledby="matches-title">
<h2 id="matches-title">和你最合拍的人</h2>
<p class="status" id="match-status" role="status" aria-live="polite"></p>
<div id="filters" hidden>
<p class="note" id="range-note"></p>
<div class="ranges" id="ranges" role="radiogroup" aria-label="要找多遠"></div>
</div>
<div id="match-list"></div>
<label class="switch" id="opposite-switch" hidden><input type="checkbox" id="show-opposites">也看看跟你相反的人</label>
</section>
<section class="opposites" id="opposites" aria-labelledby="opposites-title" hidden>
<h2 id="opposites-title">和你最不一樣的人</h2>
<p class="status" id="opposite-status" role="status" aria-live="polite"></p>
<div id="opposite-list"></div>
</section>
<details><summary>怎麼算的？</summary><div id="method"></div></details>
</main>
<script src="trait-similarity.js"></script>
<script src="match-filter.js"></script>
<script src="match-data.js"></script>
<script>
'use strict';
(function () {
  const data = matchReportData, settings = data.settings;
  const $ = id => document.getElementById(id);
  const pageHost = window.parent !== window && window.frameElement?.id === 'match-frame' ? window.parent : null;
  function make(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function pairFor(card) {
    return {
      score: card.percent,
      left: { name: '你', demo: data.isDemo, months: data.me.months, counts: data.me.counts },
      right: { name: card.name, demo: true, months: data.personaMonths, counts: card.person.counts },
    };
  }
  function cardButton(card) {
    const button = make('button', undefined, 'card');
    button.type = 'button';
    button.title = '查看你和' + card.name + '的連線圖';
    const title = make('h3', card.name);
    if (card.place) title.append(make('span', card.place, 'place'));
    const head = make('div', undefined, 'card-head');
    head.append(title, make('span', card.score, card.opposite ? 'score opposite' : 'score'));
    const pair = make('dl', undefined, 'pair');
    for (const [label, text, className] of [['最像你', card.alike, 'like'], ['最不像你', card.unlike, 'unlike']]) {
      if (text) pair.append(make('dt', label), make('dd', text, className));
    }
    button.append(head, pair);
    button.addEventListener('click', () => pageHost?.ReceiptPages.showConnection?.(pairFor(card)));
    return button;
  }
  const choice = { range: null, opposite: false };
  function fill(statusId, listId, list) {
    $(statusId).textContent = list.status;
    $(listId).replaceChildren(...list.cards.map(cardButton));
  }
  function render() {
    const shown = MatchFilter.view(data, choice);
    fill('match-status', 'match-list', shown.match);
    $('opposites').hidden = !shown.opposite;
    if (shown.opposite) fill('opposite-status', 'opposite-list', shown.opposite);
  }
  const first = MatchFilter.view(data, choice);
  $('my-lean').textContent = first.mine.lean;
  $('my-lean').hidden = !first.mine.lean;
  $('my-habits').textContent = first.mine.habits;
  $('my-habits').hidden = !first.mine.habits;
  if (first.ready) {
    $('filters').hidden = false;
    $('opposite-switch').hidden = false;
    $('range-note').textContent = first.note;
    for (const option of first.ranges) {
      const label = make('label', undefined, option.disabled ? 'off' : undefined), input = make('input');
      input.type = 'radio';
      input.name = 'range';
      input.checked = option.level === null;
      input.disabled = option.disabled;
      input.addEventListener('change', () => { choice.range = option.level; render(); });
      label.append(input, option.label);
      $('ranges').append(label);
    }
    $('show-opposites').addEventListener('change', event => { choice.opposite = event.target.checked; render(); });
    render();
  } else {
    $('match-status').textContent = first.thin;
  }
  $('match-note').textContent = '配對對象是 ' + data.population + ' 位虛構示範用戶。'
    + (data.isDemo ? '「我」也是虛構示範資料。' : '你的品味特質來自這份私人報告，只存在這個檔案裡。') + '點一個人，看你們的連線圖。';
  const signed = MatchFilter.signed;
  $('method').append(
    make('p', '每個人的發票先整理成 17 項品味特質（18 格），例如「省錢 ↔ 享受」「清爽 ↔ 香甜」「運動投入」。兩端型特質減去 '
      + data.population + ' 位虛構用戶的平均，表示跟一般人比偏哪一邊。'),
    make('p', '兩個人的相似度用餘弦相似度計算，範圍 ' + signed(-1) + '～' + signed(1) + '，負數表示品味方向相反。特質都很淡的人，分數會往 0 收斂。'),
    make('p', '相似度 ' + signed(settings.min_score) + ' 以上才列為合拍，最多 ' + settings.top + ' 位。打開「也看看跟你相反的人」，會另外列出 '
      + signed(-settings.min_score) + ' 以下的人。'),
    make('p', '距離看生活圈：占你發票 20% 以上的行政區，最多兩個。同一區、同縣市、同地區依兩人生活圈最接近的一組判斷。'),
    make('p', '「最像你」「最不像你」是對分數加分最多與扣分最多的特質。'),
    make('p', '此配對頁只用行政區與特質分數，不顯示店名、品名、日期或金額。'
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

- [ ] **Step 5: Remove the old matching**

```bash
git rm src/receipt/tags.py src/receipt/matching.py configs/tags.json tests/test_tags.py tests/test_matching.py
```

- [ ] **Step 6: Run the Python tests**

Run: `python -m unittest discover -s tests`
Expected: 54 tests OK

- [ ] **Step 7: Rebuild the public demo and run the Node tests**

Run: `python scripts/build_report.py`
Expected 輸出正好三行：

```text
2026-03 50 rows; total 7910
2026-04 53 rows; total 8095
taste similarity to 40 fictional people: highest 62%, median 8%, lowest -42%
```

Run: `node --test tests/*.test.cjs`
Expected: 40 tests pass

Run: `git status --short`
Expected: 只有本任務的檔案（含 `invoice-insights.html`），以及未追蹤的 `report-data.js`。

- [ ] **Step 8: Commit**

```bash
git add src/receipt/build.py src/web/match.html tests/test_build_report.py tests/match-page.test.cjs invoice-insights.html
git commit -m "feat: score the match page with taste traits and remove tag matching" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

（Step 5 的 `git rm` 已經把刪除放進暫存區，這次 commit 會一起包含。）

---

### Task 6: 最終驗證（由主控執行，不交給子代理）

- [ ] **Step 1: 全部測試**

Run: `python -m unittest discover -s tests`
Expected: 54 tests OK

Run: `node --test tests/*.test.cjs`
Expected: 40 tests pass

- [ ] **Step 2: 產生結果可重現、只動到預期的檔案**

Run: `python scripts/build_report.py && git status --short`
Expected: 輸出同 Task 5 Step 7；`git status` 只看到未追蹤的 `report-data.js`，`invoice-insights.html` 沒有變動。

- [ ] **Step 3: 瀏覽器檢查**

用瀏覽器打開 `invoice-insights.html`，進「找到同好」確認：

- 「你的品味特質」顯示「跟一般人比：偏香甜・偏避開連假・偏喜歡嘗鮮」與「也有運動、生活小物、3C 的紀錄」。
- 合拍名單是手搖學生 A、B、C 與連假旅人 E、D；選「同縣市」後只剩三位手搖學生。
- 打開「也看看跟你相反的人」，出現省錢上班族 E、B、A、D、C。
- 點省錢上班族 E 的卡片，連線頁大字顯示「品味相似度 −42%」；「← 返回配對清單」回來後，開關與距離選擇仍保留。
- 消費回顧（3 月 50 筆、4 月 53 筆）與朋友比較頁照常。

- [ ] **Step 4: 回報使用者**

回報 Task 1～5 的 commit 與測試結果。不要 push、不要合併：第二段三輪都完成後才一起合併。
