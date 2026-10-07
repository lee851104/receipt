# 消費標籤與同好配對 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 每筆明細帶行政區；由明細產生消費標籤；和 40 位虛構用戶比較，在報告內的新頁面讓使用者確認生活圈，顯示前 5 名、配對理由與差異說明。

**Architecture:** Python 在產生報告時完成分數計算（`address.py` → `tags.py` → `matching.py`，虛構用戶來自 `personas.py`），輸出品味 70% 以上的候選名單；`build.py` 把名單與 `match-filter.js` 嵌入新的 `match.html`，再以 `<template>` 放進單一報告檔。配對頁依使用者勾選的生活圈套用 80%／70% 門檻；`taste-navigation.js` 用 `#match` 切換頁面。

**Tech Stack:** Python 3.10+ 標準函式庫（`unittest`）、原生 HTML/CSS/JavaScript、Node.js 22 `node:test`

**Spec:** `docs/superpowers/specs/2026-10-07-tags-matching-design.md`

## Global Constraints

- Python 只用標準函式庫；`pyproject.toml` 的 `dependencies = []` 不變。
- 不讀取、不修改 `data/` 底下任何檔案（私人資料）。
- 測試、設定、文件只用虛構店名（以「示範」或「測試」開頭）。範例行政區只用：高雄市苓雅區、高雄市新興區、高雄市前鎮區、高雄市左營區、臺北市信義區、臺北市內湖區、新北市板橋區、桃園市中壢區、新竹市東區、新竹縣竹北市、宜蘭縣宜蘭市、屏東縣恆春鎮、屏東縣東港鎮。
- 網頁只能嵌入 `district`（縣市＋區），不得嵌入完整地址或統編。
- 報告維持單一 HTML 檔、沒有外部資源。
- 配對頁的資料一律用 `textContent` 或 DOM 節點寫入，不用 `innerHTML`。
- 權重：品類 0.35、常消費地區 0.3、品牌 0.15、葷素紀錄 0.1、消費檔次 0.1。門檻：品味 0.8；地區重疊且使用者確認時 0.7。品類需 10 筆有效品項。
- 在 `feature/tags-matching` 分支工作，不要 push。只 `git add` 本任務列出的檔案（`docs/architecture.svg` 不屬於本計畫）。
- Commit 訊息用英文，結尾一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 指令都在專案根目錄 `D:\receipt` 用 Git Bash 執行：
  - Python 測試：`python -m unittest discover -s tests -v`
  - Node 測試：`node --test tests/*.test.cjs`
- Node 測試讀取根目錄已產生的 `invoice-insights.html`；改到 `src/web/*` 或會影響輸出的 `src/receipt/*` 後，要執行 `python scripts/build_report.py` 重新產生，並把它一起 commit。

## 校準結果（原型，供參考）

下列參數已用原型驗證：同類型 160 組全部通過；不同類型 1,400 組中，確認生活圈後通過 44 組（手搖學生與健身族、自己下廚與家庭採買）；示範的「我」有 5 位手搖學生在 80% 以上，另有 5 位健身族在 71%–75% 且常在高雄市苓雅區消費；同區的 3C 玩家只有 36%–38%。

## 檔案結構

| 檔案 | 動作 | 責任 |
|---|---|---|
| `src/receipt/address.py` | 新增 | 地址 → 縣市＋區；地名正規化 |
| `src/receipt/invoices.py` | 修改 | 明細加 `district` |
| `src/receipt/demo.py` | 修改 | 示範店家指定行政區 |
| `src/receipt/tags.py` | 新增 | 明細 → 個人檔案與標籤 |
| `src/receipt/matching.py` | 新增 | 相似度、可比較條件、候選名單、理由、差異 |
| `src/receipt/personas.py` | 新增 | 40 位虛構用戶 |
| `src/receipt/build.py` | 修改 | 計算候選名單並嵌入配對頁 |
| `configs/tags.json`、`configs/brands.json` | 新增 | 門檻、詞典、非實體賣方、權重；品牌關鍵字 |
| `src/web/match-filter.js` | 新增 | 依確認的生活圈套用推薦門檻 |
| `src/web/match.html` | 新增 | 配對頁 |
| `src/web/invoice-insights.html` | 修改 | 行政區欄、「找到同好」連結、配對頁容器 |
| `src/web/insights-ui.js` | 修改 | 行政區欄、頁尾說明 |
| `src/web/taste-navigation.js` | 修改 | 切換朋友比較頁與配對頁 |
| `src/web/styles.css` | 修改 | 配對頁容器樣式 |
| `tests/test_address.py`、`tests/test_tags.py`、`tests/test_matching.py`、`tests/test_personas.py`、`tests/match-filter.test.cjs` | 新增 | 單元測試 |
| `tests/test_report_data.py`、`tests/test_build_report.py`、`tests/comparison-interface.test.cjs` | 修改 | 既有測試補上新行為 |
| `invoice-insights.html` | 重新產生 | 公開示範版 |

---

### Task 1: 地址解析

**Files:**
- Create: `src/receipt/address.py`
- Test: `tests/test_address.py`

**Interfaces:**
- Consumes: 無
- Produces: `normalize_place(text: str) -> str`（移除所有空白、「台」改「臺」）；`parse_district(address: str | None) -> str | None`（例如 `"高雄市苓雅區"`）

- [ ] **Step 1: Write the failing test**

建立 `tests/test_address.py`：

```python
"""Address reduction keeps only city and district; every street here is fictional."""
import unittest

from src.receipt.address import normalize_place, parse_district


class AddressTests(unittest.TestCase):
    def test_postal_code_and_municipality_district(self):
        self.assertEqual(parse_district("802高雄市苓雅區示範路1號"), "高雄市苓雅區")

    def test_variant_character_becomes_formal(self):
        self.assertEqual(parse_district("台北市信義區示範路2號"), "臺北市信義區")

    def test_spaces_are_ignored_and_municipal_districts_end_with_qu(self):
        # 前鎮區 contains 鎮, so a municipality must read on until 區.
        self.assertEqual(parse_district("806 高雄市前\u3000鎮區示範路3號"), "高雄市前鎮區")

    def test_county_district_ends_with_township_or_city(self):
        self.assertEqual(parse_district("新竹縣竹北市示範路4號"), "新竹縣竹北市")
        self.assertEqual(parse_district("臺灣省屏東縣東港鎮示範路5號"), "屏東縣東港鎮")

    def test_county_city_without_county_gets_its_county(self):
        self.assertEqual(parse_district("宜蘭市示範路6號"), "宜蘭縣宜蘭市")

    def test_unreadable_addresses_return_none(self):
        for address in (None, "", "PRIVATE-ADDRESS", "高雄市", "海外示範地址"):
            self.assertIsNone(parse_district(address), address)

    def test_normalize_place_unifies_spacing_and_variant(self):
        self.assertEqual(normalize_place(" 台灣 中油 "), "臺灣中油")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_address -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.address'`

- [ ] **Step 3: Write minimal implementation**

建立 `src/receipt/address.py`：

```python
"""Reduce a seller address to its city and district, never keeping street details."""
import re

MUNICIPALITIES = ("臺北市", "新北市", "桃園市", "臺中市", "臺南市", "高雄市", "基隆市", "新竹市", "嘉義市")
COUNTIES = ("新竹縣", "苗栗縣", "彰化縣", "南投縣", "雲林縣", "嘉義縣", "屏東縣", "宜蘭縣",
            "花蓮縣", "臺東縣", "澎湖縣", "金門縣", "連江縣")
# County-administered cities sometimes appear without their county.
COUNTY_CITIES = {
    "竹北市": "新竹縣", "苗栗市": "苗栗縣", "頭份市": "苗栗縣", "彰化市": "彰化縣", "員林市": "彰化縣",
    "南投市": "南投縣", "斗六市": "雲林縣", "太保市": "嘉義縣", "朴子市": "嘉義縣", "屏東市": "屏東縣",
    "宜蘭市": "宜蘭縣", "花蓮市": "花蓮縣", "臺東市": "臺東縣", "馬公市": "澎湖縣",
}


def normalize_place(text):
    """Drop all spacing and write 台 as 臺, so place and brand names compare equal."""
    return re.sub(r"\s+", "", text).replace("台", "臺")


def parse_district(address):
    """Return city plus district, such as 高雄市苓雅區, or None when it cannot be read."""
    if not address:
        return None
    text = re.sub(r"^(臺灣省|臺灣)", "", re.sub(r"^\d+", "", normalize_place(address)))
    for city in MUNICIPALITIES + COUNTIES:
        if text.startswith(city):
            ending = "區" if city in MUNICIPALITIES else "[鄉鎮市]"
            match = re.match(r"\D{1,3}?" + ending, text[len(city):])
            return city + match.group() if match else None
    for town, county in COUNTY_CITIES.items():
        if text.startswith(town):
            return county + town
    return None
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_address -v`
Expected: 7 tests OK

- [ ] **Step 5: Commit**

```bash
git add src/receipt/address.py tests/test_address.py
git commit -F - <<'EOF'
feat: reduce seller addresses to city and district

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 2: 明細帶行政區，報告顯示行政區欄

**Files:**
- Modify: `src/receipt/invoices.py`（import 區與 `rows.append` 區塊）
- Modify: `src/receipt/demo.py`（`shops` 之後、`rows.append` 內）
- Modify: `src/web/invoice-insights.html:32`（明細表表頭）
- Modify: `src/web/insights-ui.js:73-74`（明細列、頁尾說明）
- Modify: `tests/test_report_data.py`、`tests/test_build_report.py`、`tests/comparison-interface.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 1 的 `parse_district`
- Produces: 每筆報告明細多一個鍵 `"district": str | None`；示範資料店家的行政區如下表（Task 5 的測試依賴這些值）

| 示範店家 | 行政區 |
|---|---|
| 示範餐坊、示範茶屋、示範蔬果舖、示範洗衣坊 | 高雄市苓雅區 |
| 示範烘焙店、示範客運、示範生活館、示範選物店 | 高雄市新興區 |
| 示範運動館、示範數位店 | 高雄市前鎮區 |
| 示範旅宿 | 屏東縣恆春鎮 |

- [ ] **Step 1: Write the failing tests**

`tests/test_report_data.py`：把第 42 行的鍵集合加上 `"district"`：

```python
        self.assertTrue(all(set(row) == {"day", "invoice", "merchant", "district", "name", "quantity", "amount", "category", "provisional"} for row in rows))
```

並在 `test_unreviewed_invoice_rejected` 之後加入：

```python
    def test_district_replaces_full_address_and_tax_id(self):
        fields = ["發票日期", "發票狀態", "發票號碼", "賣方名稱", "賣方地址", "賣方統一編號", "消費明細_品名", "消費明細_數量", "消費明細_金額"]
        with self.path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow(dict(zip(fields, ["20260302", "開立已確認", "X1", "測試商店", "802高雄市苓雅區測試路99號", "TEST-TAX-ID", "測試餐盒", 1, 120])))
        _, month = build_month(self.path, self.catalog)
        self.assertEqual(month["rows"][0]["district"], "高雄市苓雅區")
        self.assertNotIn("測試路", str(month))
        self.assertNotIn("TEST-TAX-ID", str(month))
```

`tests/test_build_report.py`：
- 在 `test_default_build_ignores_private_sources_and_preserves_private_html` 的 `self.assertNotIn("PRIVATE-", html)` 之後加入：

```python
            self.assertIn('"district": "高雄市苓雅區"', html)
```

- 在 `test_build_from_another_directory_is_self_contained_and_repeatable` 的 fixture `row` 字典中，`"賣方地址": "PRIVATE-ADDRESS",` 之後加入 `"賣方統一編號": "PRIVATE-TAX-ID",`，並把隱私檢查的迴圈改成：

```python
            for private_value in ("PRIVATE-INVOICE-001", "PRIVATE-ADDRESS", "PRIVATE-CARRIER", "PRIVATE-TAX-ID"):
                self.assertNotIn(private_value, html)
```

`tests/comparison-interface.test.cjs`：在第一個測試 `standalone HTML loads both months without external scripts` 的 `assert.match(nodes.get('report-tag').textContent, /虛構示範/);` 之後加入：

```js
  assert.match(nodes.get('audit-rows').innerHTML, /<td>高雄市苓雅區<\/td>/);
  assert.match(nodes.get('report-source').textContent, /與行政區，不嵌入原始號碼、統編或完整地址/);
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest discover -s tests -v`
Expected: FAIL — `test_footer_discount_free_item_and_private_id`（鍵集合不符）、`test_district_replaces_full_address_and_tax_id`（`KeyError: 'district'`）、`test_default_build...`（找不到 `"district"`）

Run: `node --test tests/*.test.cjs`
Expected: FAIL — `standalone HTML loads both months without external scripts`

- [ ] **Step 3: Implement**

`src/receipt/invoices.py`：在 `from datetime import datetime` 下方空一行後加入：

```python

from .address import parse_district
```

並把 `rows.append({` 區塊中的 `"merchant": row["賣方名稱"],` 改成兩行：

```python
                "merchant": row["賣方名稱"],
                "district": parse_district(row.get("賣方地址")),
```

`src/receipt/demo.py`：在 `shops = [...]` 那一行之後加入：

```python
    # Fictional shops placed in real districts; no street address is ever generated.
    districts = ["高雄市苓雅區", "高雄市苓雅區", "高雄市新興區", "高雄市苓雅區", "高雄市前鎮區", "高雄市苓雅區",
                 "高雄市新興區", "屏東縣恆春鎮", "高雄市新興區", "高雄市前鎮區", "高雄市新興區"]
```

並把 `"merchant": shops[index], "name": name, "quantity": 1,` 改成：

```python
                    "merchant": shops[index], "district": districts[index], "name": name, "quantity": 1,
```

`src/web/invoice-insights.html` 第 32 行：把 `<th>賣方</th><th>品項</th>` 改成 `<th>賣方</th><th>行政區</th><th>品項</th>`。

`src/web/insights-ui.js` 第 73 行：把

```js
'</td><td>' + escapeHTML(row.merchant) + '</td><td>' + escapeHTML(row.name)
```

改成

```js
'</td><td>' + escapeHTML(row.merchant) + '</td><td>' + escapeHTML(row.district || '未知') + '</td><td>' + escapeHTML(row.name)
```

第 74 行：把 `頁面只保留匿名發票代碼，不嵌入原始號碼、統編或地址。` 改成 `頁面只保留匿名發票代碼與行政區，不嵌入原始號碼、統編或完整地址。`

- [ ] **Step 4: Rebuild the public demo**

Run: `python scripts/build_report.py`
Expected: 印出 `2026-03 50 rows; total 7910` 與 `2026-04 53 rows; total 8095`

- [ ] **Step 5: Run all tests to verify they pass**

Run: `python -m unittest discover -s tests -v`
Expected: 全部 OK

Run: `node --test tests/*.test.cjs`
Expected: `# pass 15`、`# fail 0`

- [ ] **Step 6: Commit**

```bash
git add src/receipt/invoices.py src/receipt/demo.py src/web/invoice-insights.html src/web/insights-ui.js tests/test_report_data.py tests/test_build_report.py tests/comparison-interface.test.cjs invoice-insights.html
git commit -F - <<'EOF'
feat: keep district on invoice rows and show it in the audit table

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 3: 設定檔與用戶標籤

**Files:**
- Create: `configs/tags.json`、`configs/brands.json`、`src/receipt/tags.py`
- Test: `tests/test_tags.py`

**Interfaces:**
- Consumes: Task 1 的 `normalize_place`；報告明細格式（含 `district`、`quantity`）
- Produces:
  - `percent(value: float) -> int`：0.5 進位的整數百分比，顯示與門檻共用
  - `brand_of(merchant, brands) -> str | None`、`is_remote(merchant, keywords) -> bool`
  - `flavor_of(name, flavor) -> int | None`：素 0、葷 1、未知 None
  - `flavor_label(ratio, flavor) -> str | None`：`"素食品項較多"`、`"葷食品項較多"`、`"葷素品項都有"` 或 None
  - `build_profile(rows, categories, brands, settings) -> dict`，鍵：
    - `item_count: int`（同張同品名去重後的有效品項數）
    - `category_counts: list[int] | None`（長度 10；不足 `category_min_items` 時為 None）
    - `top_categories: list[int]`
    - `district_shares: dict[str, float]`、`areas: list[str]`（常消費地區）
    - `brand_shares: dict[str, float]`、`frequent_brands: list[tuple[str, int]]`
    - `price_level: int | None`、`meat_ratio: float | None`
    - `flavor_items: dict[str, dict[str, int]]`（品牌 → 品名 → 次數）
    - `tags: list[{"dimension": str, "text": str}]`，dimension 為 品類偏好、常消費地區、常去品牌、消費檔次、葷素紀錄

- [ ] **Step 1: Create the configuration files**

`configs/tags.json`：

```json
{
  "min_records": 3,
  "category_min_items": 10,
  "category_top": 2,
  "district_top": 2,
  "district_min_invoices": 2,
  "brand_min_invoices": 3,
  "price_levels": [
    {"label": "小資型", "below": 150},
    {"label": "均衡型", "below": 400},
    {"label": "享受型"}
  ],
  "remote_sellers": ["富邦媒體", "網路家庭", "蝦皮", "酷澎", "博客來", "富胖達", "優食", "中華電信", "台灣大哥大", "遠傳電信", "台灣電力", "台灣自來水"],
  "flavor": {
    "categories": ["正餐", "飲品", "零食甜點", "生鮮食材"],
    "vegetarian": ["素食", "全素", "蛋奶素", "奶蛋素", "五辛素", "植物肉", "蔬食", "素肉", "素料", "素雞", "素鴨", "素火腿", "素香腸"],
    "meat": ["豬肉", "牛肉", "雞肉", "雞腿", "雞排", "雞塊", "雞柳", "羊肉", "鴨肉", "鵝肉", "鮮蝦", "蝦仁", "鮭魚", "鯛魚", "鮪魚", "鱈魚", "魚排", "海鮮", "排骨", "培根", "火腿", "肉燥", "肉絲", "肉片", "肉鬆", "香腸", "叉燒", "燒肉", "滷肉", "魯肉", "牛排", "豬排"],
    "min_items": 3,
    "vegetarian_at_most": 0.3,
    "meat_at_least": 0.7,
    "difference_at_least": 0.6
  },
  "weights": {"category": 0.35, "district": 0.3, "brand": 0.15, "flavor": 0.1, "price": 0.1},
  "thresholds": {"taste": 0.8, "taste_same_area": 0.7},
  "top_matches": 5
}
```

`configs/brands.json`：

```json
[
  {"brand": "7-ELEVEN", "keywords": ["統一超商"]},
  {"brand": "全家", "keywords": ["全家便利商店"]},
  {"brand": "萊爾富", "keywords": ["萊爾富"]},
  {"brand": "OK超商", "keywords": ["來來超商"]},
  {"brand": "全聯", "keywords": ["全聯實業"]},
  {"brand": "家樂福", "keywords": ["家福股份有限公司", "家樂福"]},
  {"brand": "好市多", "keywords": ["好市多"]},
  {"brand": "大潤發", "keywords": ["大潤發"]},
  {"brand": "美廉社", "keywords": ["三商家購"]},
  {"brand": "星巴克", "keywords": ["統一星巴克"]},
  {"brand": "路易莎", "keywords": ["路易莎"]},
  {"brand": "麥當勞", "keywords": ["麥當勞", "和德昌"]},
  {"brand": "摩斯漢堡", "keywords": ["安心食品"]},
  {"brand": "85度C", "keywords": ["美食達人"]},
  {"brand": "屈臣氏", "keywords": ["屈臣氏"]},
  {"brand": "康是美", "keywords": ["統一生活事業"]},
  {"brand": "寶雅", "keywords": ["寶雅國際"]},
  {"brand": "無印良品", "keywords": ["無印良品"]},
  {"brand": "燦坤", "keywords": ["燦坤"]},
  {"brand": "全國電子", "keywords": ["全國電子"]},
  {"brand": "台灣高鐵", "keywords": ["高速鐵路"]},
  {"brand": "臺鐵", "keywords": ["臺灣鐵路"]},
  {"brand": "台灣中油", "keywords": ["中油"]},
  {"brand": "示範餐坊", "keywords": ["示範餐坊"]},
  {"brand": "示範茶屋", "keywords": ["示範茶屋"]},
  {"brand": "示範烘焙店", "keywords": ["示範烘焙店"]},
  {"brand": "示範運動館", "keywords": ["示範運動館"]},
  {"brand": "示範數位店", "keywords": ["示範數位店"]},
  {"brand": "示範客運", "keywords": ["示範客運"]},
  {"brand": "示範超商", "keywords": ["示範超商"]},
  {"brand": "示範咖啡", "keywords": ["示範咖啡"]},
  {"brand": "示範水餃館", "keywords": ["示範水餃館"]},
  {"brand": "示範量販", "keywords": ["示範量販"]}
]
```

- [ ] **Step 2: Write the failing test**

建立 `tests/test_tags.py`：

```python
"""Tag rules on small fictional purchase sets."""
import json
import unittest
from pathlib import Path

from src.receipt.tags import brand_of, build_profile, flavor_of, percent

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))


def row(invoice, category=0, amount=100, name="測試品項", merchant="測試小店", district="高雄市苓雅區",
        provisional=False, quantity=1):
    return {"day": 1, "invoice": invoice, "merchant": merchant, "district": district, "name": name,
            "quantity": quantity, "amount": amount, "category": category, "provisional": provisional}


def profile_of(rows):
    return build_profile(rows, CATEGORIES, BRANDS, SETTINGS)


def texts(profile, dimension):
    return [tag["text"] for tag in profile["tags"] if tag["dimension"] == dimension]


class TagTests(unittest.TestCase):
    def test_shipped_settings_match_the_spec(self):
        self.assertAlmostEqual(sum(SETTINGS["weights"].values()), 1)
        self.assertEqual(SETTINGS["thresholds"], {"taste": 0.8, "taste_same_area": 0.7})
        self.assertEqual(SETTINGS["category_min_items"], 10)
        self.assertEqual([level["label"] for level in SETTINGS["price_levels"]], ["小資型", "均衡型", "享受型"])
        self.assertNotIn("蔬菜", SETTINGS["flavor"]["vegetarian"])
        self.assertTrue(SETTINGS["remote_sellers"])
        self.assertTrue(all(entry["brand"] and entry["keywords"] for entry in BRANDS))

    def test_percent_rounds_half_up(self):
        self.assertEqual(percent(0.805), 81)
        self.assertEqual(percent(0.8), 80)
        self.assertEqual(percent(0.7949), 79)

    def test_brand_keywords_ignore_variant_characters(self):
        self.assertEqual(brand_of("台灣高速鐵路股份有限公司", BRANDS), "台灣高鐵")
        self.assertEqual(brand_of("統一超商股份有限公司高雄示範分公司", BRANDS), "7-ELEVEN")
        self.assertIsNone(brand_of("示範巷口麵店", BRANDS))

    def test_flavor_words_prefer_explicit_vegetarian_markers(self):
        flavor = SETTINGS["flavor"]
        self.assertEqual(flavor_of("示範全素香腸", flavor), 0)
        self.assertEqual(flavor_of("示範素食雞排", flavor), 0)
        self.assertEqual(flavor_of("示範蔬食餐盒", flavor), 0)
        self.assertEqual(flavor_of("示範蔬菜豬肉水餃", flavor), 1)
        self.assertEqual(flavor_of("示範鮮蝦水餃", flavor), 1)
        self.assertIsNone(flavor_of("示範蔬菜水餃", flavor))
        self.assertIsNone(flavor_of("示範牛奶", flavor))
        self.assertIsNone(flavor_of("示範肉桂捲", flavor))

    def test_category_tags_count_confirmed_paid_items(self):
        rows = [row(f"D{i}", 1) for i in range(7)] + [row(f"M{i}", 0) for i in range(3)]
        rows += [row("E", 2, amount=-10), row("F", 2, amount=0), row("G", 3, provisional=True), row("H", 10, provisional=True)]
        profile = profile_of(rows)
        self.assertEqual(profile["item_count"], 10)
        self.assertEqual(profile["category_counts"][:4], [3, 7, 0, 0])
        self.assertEqual(texts(profile, "品類偏好"), ["常買飲品（70%）", "常買正餐（30%）"])

    def test_category_needs_ten_items(self):
        few = profile_of([row(f"D{i}", 1) for i in range(9)])
        self.assertEqual(few["item_count"], 9)
        self.assertIsNone(few["category_counts"])
        self.assertEqual(texts(few, "品類偏好"), [])

    def test_one_portion_per_item_and_invoice(self):
        rows = [row("A", 1, name="示範紅茶"), row("A", 1, name="示範紅茶"), row("B", 1, name="示範紅茶", quantity=4)]
        rows += [row(f"M{i}", 0, name="示範便當") for i in range(8)]
        profile = profile_of(rows)
        self.assertEqual(profile["item_count"], 10)
        self.assertEqual(profile["category_counts"][:2], [8, 2])

    def test_area_tags_need_enough_invoices_and_two_per_district(self):
        profile = profile_of([row("A"), row("B"), row("C", district="高雄市新興區"), row("D", district="高雄市新興區"),
                              row("E", district="臺北市信義區"), row("F", district=None)])
        self.assertEqual(texts(profile, "常消費地區"), ["高雄市新興區", "高雄市苓雅區"])
        self.assertAlmostEqual(profile["district_shares"]["高雄市苓雅區"], 0.4)
        few = profile_of([row("A"), row("B")])
        self.assertEqual(few["district_shares"], {})
        self.assertEqual(texts(few, "常消費地區"), [])

    def test_remote_sellers_do_not_count_as_places(self):
        online = [row(f"O{i}", merchant="富邦媒體科技股份有限公司", district="臺北市內湖區") for i in range(3)]
        profile = profile_of(online + [row(f"L{i}") for i in range(3)])
        self.assertEqual(profile["district_shares"], {"高雄市苓雅區": 1.0})
        self.assertEqual(texts(profile, "常消費地區"), ["高雄市苓雅區"])

    def test_frequent_brands_need_three_invoices(self):
        profile = profile_of([row(f"S{i}", merchant="統一超商股份有限公司示範門市") for i in range(3)]
                             + [row("C1", merchant="示範咖啡信義店"), row("C2", merchant="示範咖啡信義店")])
        self.assertEqual(texts(profile, "常去品牌"), ["7-ELEVEN（3 次）"])
        self.assertAlmostEqual(profile["brand_shares"]["示範咖啡"], 0.4)

    def test_price_level_uses_median_personal_invoice(self):
        cheap, middle = SETTINGS["price_levels"][0]["below"], SETTINGS["price_levels"][1]["below"]

        def level(totals):
            return texts(profile_of([row(f"I{i}", amount=total) for i, total in enumerate(totals)]), "消費檔次")

        self.assertEqual(level([cheap - 1, cheap - 1, middle + 1]), ["小資型"])
        self.assertEqual(level([cheap, cheap, middle + 1]), ["均衡型"])
        self.assertEqual(level([middle, middle, 1]), ["享受型"])
        self.assertEqual(level([middle, middle]), [])
        discounted = profile_of([row("D", amount=cheap + 10), row("D", amount=-20, name="測試折扣"),
                                 row("E", amount=cheap - 10), row("F", amount=cheap - 10)])
        self.assertEqual(texts(discounted, "消費檔次"), ["小資型"])

    def test_shared_bills_stay_out_of_price_level(self):
        cheap = SETTINGS["price_levels"][0]["below"]
        personal = [row(f"P{i}", amount=cheap - 10) for i in range(3)]
        portions = [row(f"S{i}", amount=1600, quantity=4) for i in range(3)]
        repeated = [row(f"R{i}", amount=800, name="示範火鍋") for i in range(3) for _ in range(2)]
        self.assertEqual(texts(profile_of(portions + personal), "消費檔次"), ["小資型"])
        self.assertEqual(texts(profile_of(repeated + personal), "消費檔次"), ["小資型"])
        self.assertEqual(texts(profile_of(portions + personal[:2]), "消費檔次"), [])

    def test_flavor_tag_describes_purchases(self):
        rows = [row("A", name="示範全素水餃"), row("B", name="示範全素水餃"), row("C", name="示範鮮蝦水餃", merchant="示範水餃館")]
        profile = profile_of(rows)
        self.assertEqual(texts(profile, "葷素紀錄"), ["葷素品項都有"])
        self.assertEqual(profile["flavor_items"], {"示範水餃館": {"示範鮮蝦水餃": 1}})
        self.assertEqual(texts(profile_of(rows[:2]), "葷素紀錄"), [])
        self.assertEqual(texts(profile_of([row(f"V{i}", name="示範素食便當") for i in range(3)]), "葷素紀錄"), ["素食品項較多"])
        self.assertIsNone(profile_of([row(f"V{i}", name="示範蔬菜水餃") for i in range(3)])["meat_ratio"])
        self.assertIsNone(profile_of([row(f"G{i}", category=4, name="示範雞肉造型背包") for i in range(3)])["meat_ratio"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 3: Run test to verify it fails**

Run: `python -m unittest tests.test_tags -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.tags'`

- [ ] **Step 4: Write minimal implementation**

建立 `src/receipt/tags.py`：

```python
"""Summarize purchases into comparable dimensions and short tags that describe the records."""
from collections import Counter
from statistics import median

from .address import normalize_place

CONFIRMED = 10  # category 10 marks rows that still await review


def percent(value):
    """Whole percentage rounded half up, used for both display and thresholds."""
    return int(value * 100 + 0.5)


def mentions(merchant, keywords):
    name = normalize_place(merchant or "")
    return any(normalize_place(keyword) in name for keyword in keywords)


def brand_of(merchant, brands):
    """Return the chain brand whose keyword appears in the seller name, if any."""
    return next((entry["brand"] for entry in brands if mentions(merchant, entry["keywords"])), None)


def is_remote(merchant, keywords):
    """Online, delivery and utility sellers print a company address, not where the buyer was."""
    return mentions(merchant, keywords)


def flavor_of(name, flavor):
    """0 when the name says vegetarian, 1 for meat or seafood, None otherwise (plain 蔬菜 proves nothing)."""
    if any(word in name for word in flavor["vegetarian"]):
        return 0
    if any(word in name for word in flavor["meat"]):
        return 1
    return None


def flavor_label(ratio, flavor):
    if ratio is None:
        return None
    if ratio <= flavor["vegetarian_at_most"]:
        return "素食品項較多"
    if ratio >= flavor["meat_at_least"]:
        return "葷食品項較多"
    return "葷素品項都有"


def level_of(amount, levels):
    for index, level in enumerate(levels):
        if "below" not in level or amount < level["below"]:
            return index


def ranked(counter):
    """Most frequent first; ties fall back to the key so results never depend on input order."""
    return sorted(counter.items(), key=lambda item: (-item[1], item[0]))


def shares(counter):
    total = sum(counter.values())
    return {key: value / total for key, value in counter.items()}


def build_profile(rows, categories, brands, settings):
    names = [category["name"] for category in categories]
    flavor, minimum = settings["flavor"], settings["min_records"]
    # One portion per item and invoice: four hotpots on one bill count once.
    seen, valid = set(), []
    for row in rows:
        key = (row["invoice"], row["name"])
        if row["amount"] > 0 and not row["provisional"] and row["category"] < CONFIRMED and key not in seen:
            seen.add(key)
            valid.append(row)
    counts = [0] * CONFIRMED
    for row in valid:
        counts[row["category"]] += 1
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
    districts = Counter(invoice["district"] for invoice in paid if invoice["district"])
    chains = Counter(invoice["brand"] for invoice in paid if invoice["brand"])
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
    known_area = sum(districts.values()) >= minimum
    profile = {
        "item_count": len(valid),
        "category_counts": counts if enough_items else None,
        "top_categories": [index for index, count in ranked(dict(enumerate(counts))) if count][:settings["category_top"]]
        if enough_items else [],
        "district_shares": shares(districts) if known_area else {},
        "areas": [district for district, count in ranked(districts)
                  if count >= settings["district_min_invoices"]][:settings["district_top"]] if known_area else [],
        "brand_shares": shares(chains) if sum(chains.values()) >= minimum else {},
        "frequent_brands": [(brand, count) for brand, count in ranked(chains) if count >= settings["brand_min_invoices"]],
        "price_level": level_of(median(invoice["total"] for invoice in personal), settings["price_levels"])
        if len(personal) >= minimum else None,
        "meat_ratio": sum(flavored) / len(flavored) if len(flavored) >= flavor["min_items"] else None,
        "flavor_items": flavor_items,
    }
    profile["tags"] = describe(profile, names, settings)
    return profile


def describe(profile, names, settings):
    counts, tags = profile["category_counts"], []
    if counts:
        total = sum(counts)
        tags += [{"dimension": "品類偏好", "text": f"常買{names[index]}（{percent(counts[index] / total)}%）"}
                 for index in profile["top_categories"]]
    tags += [{"dimension": "常消費地區", "text": area} for area in profile["areas"]]
    tags += [{"dimension": "常去品牌", "text": f"{brand}（{count} 次）"} for brand, count in profile["frequent_brands"]]
    if profile["price_level"] is not None:
        tags.append({"dimension": "消費檔次", "text": settings["price_levels"][profile["price_level"]]["label"]})
    label = flavor_label(profile["meat_ratio"], settings["flavor"])
    if label:
        tags.append({"dimension": "葷素紀錄", "text": label})
    return tags
```

- [ ] **Step 5: Run test to verify it passes**

Run: `python -m unittest tests.test_tags -v`
Expected: 13 tests OK

- [ ] **Step 6: Commit**

```bash
git add configs/tags.json configs/brands.json src/receipt/tags.py tests/test_tags.py
git commit -F - <<'EOF'
feat: build purchase profiles and tags that describe the records

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 4: 配對分數、可比較條件與候選名單

**Files:**
- Create: `src/receipt/matching.py`
- Test: `tests/test_matching.py`

**Interfaces:**
- Consumes: Task 3 的 `percent`、`flavor_of`、`flavor_label`、`build_profile` 與其回傳格式
- Produces:
  - `overlap(a: dict, b: dict) -> float | None`
  - `weighted(parts: dict, weights: dict, names) -> float | None`
  - `ready(profile) -> bool`：品類可比較，且品牌、葷素紀錄、消費檔次至少有一項
  - `compare(me, other, settings) -> {"parts": dict, "comparable": bool, "taste": float | None, "total": float | None}`
  - `reasons(me, other, parts, names, settings) -> list[str]`
  - `differences(me, other, settings) -> list[str]`
  - `eligible(me, candidates: list[{"name": str, "profile": dict}], names, settings) -> list[{"name", "total", "taste", "areas", "tags", "basis", "reasons", "differences"}]`，`total` 與 `taste` 為整數百分比；只含可比較且品味至少 `taste_same_area` 的人，依總分排序

- [ ] **Step 1: Write the failing test**

建立 `tests/test_matching.py`：

```python
"""Similarity, comparability and explanations on hand-made profiles."""
import json
import unittest
from pathlib import Path

from src.receipt.matching import compare, differences, eligible, overlap, ready, reasons, weighted
from src.receipt.tags import build_profile

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
NAMES = [category["name"] for category in CATEGORIES]


def profile(**changes):
    base = {"item_count": 10, "category_counts": [5, 5, 0, 0, 0, 0, 0, 0, 0, 0], "top_categories": [0, 1],
            "district_shares": {"高雄市苓雅區": 1.0}, "areas": ["高雄市苓雅區"],
            "brand_shares": {"示範茶屋": 1.0}, "frequent_brands": [("示範茶屋", 5)],
            "price_level": 0, "meat_ratio": 0.0, "flavor_items": {}, "tags": []}
    base.update(changes)
    return base


def neighbour():
    """Lives in the same district but buys entirely different things."""
    return profile(category_counts=[0, 0, 0, 0, 0, 0, 0, 0, 0, 10], top_categories=[9],
                   brand_shares={"示範數位店": 1.0}, frequent_brands=[("示範數位店", 5)], price_level=2, meat_ratio=1.0)


class MatchingTests(unittest.TestCase):
    def test_identical_profiles_score_full_marks(self):
        result = compare(profile(), profile(), SETTINGS)
        self.assertTrue(result["comparable"])
        self.assertAlmostEqual(result["taste"], 1)
        self.assertAlmostEqual(result["total"], 1)

    def test_overlap_is_histogram_intersection(self):
        self.assertAlmostEqual(overlap({"A": 0.6, "B": 0.4}, {"A": 0.3, "C": 0.7}), 0.3)
        self.assertIsNone(overlap({}, {"A": 1.0}))

    def test_missing_parts_hand_their_weight_to_the_rest(self):
        weights = SETTINGS["weights"]
        parts = {"category": 1.0, "district": None, "brand": None, "flavor": 0.0, "price": None}
        self.assertAlmostEqual(weighted(parts, weights, weights), weights["category"] / (weights["category"] + weights["flavor"]))
        self.assertIsNone(weighted(dict.fromkeys(parts), weights, weights))

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
        self.assertIsNone(result["taste"])
        self.assertIsNone(result["total"])

    def test_one_more_taste_dimension_is_required(self):
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
        self.assertIsNone(result["taste"])
        self.assertFalse(ready(sparse))

    def test_reasons_follow_contribution(self):
        me, other = profile(price_level=1), profile(price_level=1)
        parts = compare(me, other, SETTINGS)["parts"]
        self.assertEqual(reasons(me, other, parts, NAMES, SETTINGS), ["都很常買正餐", "都常在高雄市苓雅區消費", "都常去示範茶屋"])

    def test_flavor_and_price_reasons_and_fallback(self):
        me = profile(top_categories=[0], frequent_brands=[])
        other = profile(top_categories=[1], district_shares={"臺北市信義區": 1.0}, areas=["臺北市信義區"], frequent_brands=[])
        parts = compare(me, other, SETTINGS)["parts"]
        self.assertEqual(reasons(me, other, parts, NAMES, SETTINGS), ["都買比較多素食品項", "消費檔次都是小資型"])
        stranger = profile(top_categories=[9], areas=[], district_shares={}, frequent_brands=[], meat_ratio=None, price_level=2)
        parts = compare(profile(), stranger, SETTINGS)["parts"]
        self.assertEqual(reasons(profile(), stranger, parts, NAMES, SETTINGS), ["整體消費比例相近"])

    def test_differences_name_the_shared_store(self):
        veg = profile(meat_ratio=0.0, frequent_brands=[("示範水餃館", 4)], flavor_items={"示範水餃館": {"示範全素水餃": 4}})
        meat = profile(meat_ratio=1.0, frequent_brands=[("示範水餃館", 4)],
                       flavor_items={"示範水餃館": {"示範鮮蝦水餃": 3, "示範全素水餃": 1}})
        self.assertEqual(differences(veg, meat, SETTINGS), ["都常去示範水餃館，但點的不一樣（示範全素水餃／示範鮮蝦水餃）"])
        self.assertEqual(differences(veg, profile(meat_ratio=1.0), SETTINGS), ["購買紀錄不同：一位素食品項較多、一位葷食品項較多"])
        self.assertEqual(differences(veg, profile(meat_ratio=0.5), SETTINGS), [])
        self.assertEqual(differences(veg, profile(meat_ratio=None), SETTINGS), [])

    def test_eligible_keeps_the_area_band_and_sorts(self):
        candidates = [{"name": f"示範用戶 {i}", "profile": profile(price_level=i % 3)} for i in range(4)]
        candidates += [{"name": "示範鄰居", "profile": neighbour()},
                       {"name": "示範資料不足", "profile": profile(category_counts=None, top_categories=[])},
                       {"name": "示範中間", "profile": profile(brand_shares={"示範超商": 1.0}, frequent_brands=[("示範超商", 5)], meat_ratio=0.5)}]
        result = eligible(profile(), candidates, NAMES, SETTINGS)
        self.assertEqual([match["name"] for match in result], ["示範用戶 0", "示範用戶 3", "示範用戶 1", "示範用戶 2", "示範中間"])
        self.assertEqual(result[-1]["taste"], 71)
        self.assertEqual(set(result[0]), {"name", "total", "taste", "areas", "tags", "basis", "reasons", "differences"})
        self.assertEqual(result[0]["basis"], ["品類", "常消費地區", "品牌", "葷素紀錄", "消費檔次"])


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_matching -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.matching'`

- [ ] **Step 3: Write minimal implementation**

建立 `src/receipt/matching.py`：

```python
"""Score how alike two purchase profiles are and explain it; the page applies the area rule."""
import math

from .tags import flavor_label, flavor_of, percent

TASTE = ("category", "brand", "flavor", "price")
LABELS = {"category": "品類", "district": "常消費地區", "brand": "品牌", "flavor": "葷素紀錄", "price": "消費檔次"}
FLAVOR_REASONS = {"素食品項較多": "都買比較多素食品項", "葷食品項較多": "都買比較多葷食品項", "葷素品項都有": "葷素品項都有買"}


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
    return {"category": category, "district": overlap(me["district_shares"], other["district_shares"]),
            "brand": overlap(me["brand_shares"], other["brand_shares"]), "flavor": flavor, "price": price}


def weighted(parts, weights, names):
    """Weighted mean of the available parts; missing parts hand their weight to the rest."""
    available = [name for name in names if parts[name] is not None]
    weight = sum(weights[name] for name in available)
    return sum(weights[name] * parts[name] for name in available) / weight if weight else None


def ready(profile):
    """Enough data to be matched at all: category plus one more taste dimension."""
    return profile["category_counts"] is not None and (
        bool(profile["brand_shares"]) or profile["meat_ratio"] is not None or profile["price_level"] is not None)


def compare(me, other, settings):
    parts = similarities(me, other, settings)
    # Category is required, plus at least one more taste dimension, so thin data cannot score 100%.
    comparable = parts["category"] is not None and any(parts[name] is not None for name in TASTE[1:])
    return {"parts": parts, "comparable": comparable,
            "taste": weighted(parts, settings["weights"], TASTE) if comparable else None,
            "total": weighted(parts, settings["weights"], settings["weights"]) if comparable else None}


def reasons(me, other, parts, names, settings):
    found = []
    areas = [area for area in me["areas"] if area in other["areas"]]
    if areas:
        found.append(("district", f"都常在{areas[0]}消費"))
    theirs = {brand for brand, _ in other["frequent_brands"]}
    brands = [brand for brand, _ in me["frequent_brands"] if brand in theirs]
    if brands:
        found.append(("brand", f"都常去{brands[0]}"))
    categories = [index for index in me["top_categories"] if index in other["top_categories"]]
    if categories:
        found.append(("category", f"都很常買{names[categories[0]]}"))
    label = flavor_label(me["meat_ratio"], settings["flavor"])
    if label and label == flavor_label(other["meat_ratio"], settings["flavor"]):
        found.append(("flavor", FLAVOR_REASONS[label]))
    if me["price_level"] is not None and me["price_level"] == other["price_level"]:
        found.append(("price", f"消費檔次都是{settings['price_levels'][me['price_level']]['label']}"))
    weights = settings["weights"]
    found.sort(key=lambda item: -weights[item[0]] * (parts[item[0]] or 0))
    return [text for _, text in found[:3]] or ["整體消費比例相近"]


def favorite(items):
    return min(items, key=lambda name: (-items[name], name))


def differences(me, other, settings):
    flavor = settings["flavor"]
    if me["meat_ratio"] is None or other["meat_ratio"] is None:
        return []
    if abs(me["meat_ratio"] - other["meat_ratio"]) + 1e-9 < flavor["difference_at_least"]:
        return []
    theirs = {brand for brand, _ in other["frequent_brands"]}
    for brand, _ in me["frequent_brands"]:
        mine, others = me["flavor_items"].get(brand), other["flavor_items"].get(brand)
        if brand not in theirs or not mine or not others:
            continue
        a, b = favorite(mine), favorite(others)
        if flavor_of(a, flavor) != flavor_of(b, flavor):
            return [f"都常去{brand}，但點的不一樣（{a}／{b}）"]
    return ["購買紀錄不同：一位素食品項較多、一位葷食品項較多"]


def eligible(me, candidates, names, settings):
    """Everyone who could pass once an area is confirmed, best first; the page applies the final rule."""
    floor = percent(settings["thresholds"]["taste_same_area"])
    scored = [(candidate, compare(me, candidate["profile"], settings)) for candidate in candidates]
    scored = [(candidate, result) for candidate, result in scored
              if result["comparable"] and percent(result["taste"]) >= floor]
    scored.sort(key=lambda pair: (-pair[1]["total"], -pair[1]["taste"], pair[0]["name"]))
    return [{
        "name": candidate["name"], "total": percent(result["total"]), "taste": percent(result["taste"]),
        "areas": candidate["profile"]["areas"], "tags": candidate["profile"]["tags"],
        "basis": [label for name, label in LABELS.items() if result["parts"][name] is not None],
        "reasons": reasons(me, candidate["profile"], result["parts"], names, settings),
        "differences": differences(me, candidate["profile"], settings),
    } for candidate, result in scored]
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_matching -v`
Expected: 11 tests OK

- [ ] **Step 5: Commit**

```bash
git add src/receipt/matching.py tests/test_matching.py
git commit -F - <<'EOF'
feat: score and explain matches, refusing thin data

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 5: 虛構用戶

**Files:**
- Create: `src/receipt/personas.py`
- Test: `tests/test_personas.py`

**Interfaces:**
- Consumes: Task 2 的示範資料（含行政區）；Task 3 的 `build_profile`；Task 4 的 `compare`、`differences`、`eligible`
- Produces: `build_personas(per_type=5, seed=SEED) -> list[{"name": str, "type": str, "rows": list[dict]}]`，40 人，`rows` 格式與報告明細相同

下列類型參數已用原型校準過（見「校準結果」）。請照抄，不要自行調整。

- [ ] **Step 1: Write the failing test**

建立 `tests/test_personas.py`：

```python
"""The fictional population separates types, explains flavor gaps and respects the area rule."""
import json
import unittest
from pathlib import Path

from src.receipt.demo import build_demo
from src.receipt.matching import compare, differences, eligible
from src.receipt.personas import build_personas
from src.receipt.tags import build_profile

ROOT = Path(__file__).resolve().parents[1]
CATEGORIES = json.loads((ROOT / "configs" / "report.json").read_text(encoding="utf-8"))["categories"]
CATALOG = json.loads((ROOT / "configs" / "item-categories.json").read_text(encoding="utf-8"))
BRANDS = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
SETTINGS = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
NAMES = [category["name"] for category in CATEGORIES]


class PersonaTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.people = build_personas()
        cls.profiles = {person["name"]: build_profile(person["rows"], CATEGORIES, BRANDS, SETTINGS) for person in cls.people}
        demo_rows = [row for month in build_demo(CATALOG).values() for row in month["rows"]]
        cls.me = build_profile(demo_rows, CATEGORIES, BRANDS, SETTINGS)
        candidates = [{"name": name, "profile": profile} for name, profile in cls.profiles.items()]
        cls.pool = eligible(cls.me, candidates, NAMES, SETTINGS)

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
                       key=lambda other: compare(mine, self.profiles[other["name"]], SETTINGS)["total"])
            self.assertEqual(best["type"], person["type"], person["name"])

    def test_same_store_different_filling_is_explained(self):
        found = differences(self.profiles["手搖學生 A"], self.profiles["手搖學生 D"], SETTINGS)
        self.assertEqual(found, ["都常去示範餐坊，但點的不一樣（示範蔬食餐盒／示範鮮蝦餐盒）"])

    def test_neighbours_with_other_tastes_are_not_candidates(self):
        pool = {candidate["name"] for candidate in self.pool}
        for person in self.people:
            if person["type"] == "3C 玩家":
                self.assertTrue(set(self.profiles[person["name"]]["areas"]) & set(self.me["areas"]), person["name"])
                self.assertNotIn(person["name"], pool)

    def test_confirming_an_area_unlocks_more_people(self):
        high = [c for c in self.pool if c["taste"] >= 80]
        band = [c for c in self.pool if 70 <= c["taste"] < 80 and set(c["areas"]) & set(self.me["areas"])]
        self.assertGreaterEqual(len(high), 1)
        self.assertGreaterEqual(len(band), 1)
        self.assertTrue(any(candidate["differences"] for candidate in self.pool))


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_personas -v`
Expected: FAIL，`ModuleNotFoundError: No module named 'src.receipt.personas'`

- [ ] **Step 3: Write minimal implementation**

建立 `src/receipt/personas.py`：

```python
"""Deterministic fictional people to match against; every shop and person here is made up."""
import random

SEED = 20261007
MONTHS = ((2026, 3, 31), (2026, 4, 30))
LETTERS = "ABCDE"

# Habit: (category index, merchant, item names, (lowest, highest) amount, (fewest, most) visits a month).
# Item names given as {"veg": [...], "meat": [...]} differ between members listed in meat_members.
TYPES = [
    {"label": "咖啡上班族", "areas": {"臺北市信義區": 6, "臺北市內湖區": 4}, "habits": [
        (1, "示範咖啡", ["示範拿鐵", "示範美式"], (150, 220), (14, 18)),
        (0, "示範便當店", ["示範雞腿便當", "示範排骨便當"], (100, 140), (10, 13)),
        (2, "示範咖啡", ["示範可頌"], (160, 200), (3, 5)),
        (6, "示範捷運", ["示範捷運儲值"], (300, 500), (2, 3)),
    ]},
    {"label": "手搖學生", "areas": {"高雄市苓雅區": 6, "高雄市新興區": 4}, "meat_members": (3, 4), "habits": [
        (1, "示範茶屋", ["示範花果茶", "示範青茶"], (45, 75), (9, 12)),
        (0, "示範餐坊", {"veg": ["示範蔬食餐盒"], "meat": ["示範鮮蝦餐盒"]}, (95, 130), (9, 12)),
        (0, "示範水餃館", {"veg": ["示範蔬菜水餃"], "meat": ["示範鮮蝦水餃"]}, (70, 110), (2, 3)),
        (6, "示範客運", ["示範客運票"], (40, 60), (5, 7)),
        (2, "示範烘焙店", ["示範燕麥餅"], (70, 100), (3, 5)),
        (4, "示範運動館", ["示範體適能體驗票"], (80, 100), (2, 3)),
        (8, "示範生活館", ["示範文具組"], (60, 120), (1, 3)),
    ]},
    {"label": "健身族", "areas": {"高雄市前鎮區": 5, "高雄市苓雅區": 5}, "habits": [
        (4, "示範運動館", ["示範重訓課", "示範健身月票"], (300, 600), (6, 8)),
        (0, "示範餐坊", ["示範雞肉餐盒", "示範蔬食沙拉"], (120, 160), (8, 10)),
        (1, "示範超商", ["示範無糖豆漿", "示範乳清飲"], (35, 60), (8, 10)),
        (3, "示範量販", ["示範雞肉分裝包"], (200, 300), (2, 3)),
    ]},
    {"label": "自己下廚", "areas": {"新北市板橋區": 7, "臺北市內湖區": 3}, "habits": [
        (3, "示範量販", ["示範綜合蔬菜箱", "示範蔬菜組合"], (250, 400), (8, 10)),
        (3, "示範蔬果舖", ["示範當季蔬菜"], (80, 150), (4, 6)),
        (8, "示範量販", ["示範廚房紙巾", "示範洗碗精"], (80, 200), (3, 4)),
        (1, "示範超商", ["示範鮮奶"], (50, 90), (3, 5)),
        (0, "示範早餐店", ["示範蛋餅"], (40, 70), (3, 4)),
    ]},
    {"label": "3C 玩家", "areas": {"高雄市苓雅區": 10}, "habits": [
        (9, "示範數位店", ["示範機械鍵盤", "示範耳機", "示範傳輸線", "示範行動電源"], (300, 2500), (6, 8)),
        (0, "示範速食店", ["示範雞排堡", "示範牛肉堡"], (120, 200), (4, 6)),
        (1, "示範超商", ["示範能量飲"], (40, 70), (2, 3)),
        (2, "示範超商", ["示範洋芋片"], (40, 80), (1, 2)),
    ]},
    {"label": "旅行族", "areas": {"屏東縣恆春鎮": 5, "宜蘭縣宜蘭市": 5}, "habits": [
        (7, "示範旅宿", ["示範旅店雙人房"], (1800, 3200), (2, 3)),
        (6, "示範高鐵", ["示範高鐵車票"], (700, 1500), (2, 4)),
        (0, "示範海港餐廳", ["示範海鮮套餐", "示範燒肉套餐"], (450, 900), (4, 6)),
        (1, "示範超商", ["示範礦泉水"], (20, 40), (2, 4)),
        (2, "示範超商", ["示範伴手禮"], (300, 600), (1, 2)),
    ]},
    {"label": "零食夜貓", "areas": {"新竹市東區": 6, "新竹縣竹北市": 4}, "habits": [
        (2, "示範超商", ["示範洋芋片", "示範巧克力", "示範布丁"], (30, 90), (12, 16)),
        (1, "示範超商", ["示範奶茶", "示範可樂"], (25, 60), (8, 12)),
        (0, "示範超商", ["示範鮪魚飯糰", "示範肉鬆飯糰"], (35, 80), (6, 9)),
        (8, "示範超商", ["示範衛生紙"], (50, 120), (1, 2)),
    ]},
    {"label": "家庭採買", "areas": {"桃園市中壢區": 7, "新北市板橋區": 3}, "habits": [
        (8, "示範量販", ["示範洗衣精", "示範衛生紙箱", "示範洗髮精"], (400, 1200), (4, 6)),
        (3, "示範量販", ["示範豬肉片", "示範雞肉分裝包", "示範蔬菜組合"], (500, 1200), (4, 6)),
        (2, "示範量販", ["示範家庭號餅乾"], (150, 300), (2, 3)),
        (0, "示範水餃館", ["示範韭菜豬肉水餃", "示範蔬菜水餃"], (150, 300), (3, 4)),
        (5, "示範洗衣坊", ["示範衣物清潔服務"], (150, 300), (1, 2)),
    ]},
]


def build_personas(per_type=5, seed=SEED):
    rng = random.Random(seed)
    people = []
    for kind in TYPES:
        areas, weights = zip(*kind["areas"].items())
        for member in range(per_type):
            flavor = "meat" if member in kind.get("meat_members", ()) else "veg"
            code, rows = f"P{len(people) + 1:02}", []
            for year, month, days in MONTHS:
                for category, merchant, items, (low, high), (fewest, most) in kind["habits"]:
                    names = items[flavor] if isinstance(items, dict) else items
                    for _ in range(rng.randint(fewest, most)):
                        rows.append({
                            "day": rng.randint(1, days), "invoice": f"{code}-{year}-{month:02}-{len(rows) + 1:03}",
                            "merchant": merchant, "name": rng.choice(names), "quantity": 1,
                            "amount": rng.randint(low, high), "category": category, "provisional": False,
                            "district": rng.choices(areas, weights)[0],
                        })
            people.append({"name": f"{kind['label']} {LETTERS[member]}", "type": kind["label"], "rows": rows})
    return people
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m unittest tests.test_personas -v`
Expected: 5 tests OK

- [ ] **Step 5: Run the whole Python suite**

Run: `python -m unittest discover -s tests -v`
Expected: 全部 OK

- [ ] **Step 6: Commit**

```bash
git add src/receipt/personas.py tests/test_personas.py
git commit -F - <<'EOF'
feat: add a deterministic fictional population for matching

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 6: 依確認的生活圈套用門檻

**Files:**
- Create: `src/web/match-filter.js`
- Test: `tests/match-filter.test.cjs`

**Interfaces:**
- Consumes: Task 4 `eligible()` 的輸出格式（`taste` 為整數百分比、`areas` 為字串陣列）
- Produces: 瀏覽器全域 `MatchFilter.recommend(candidates, confirmedAreas, thresholds)`，Node 中以 `require` 取得同一個函式；回傳符合門檻的候選人，保留原本順序

- [ ] **Step 1: Write the failing test**

建立 `tests/match-filter.test.cjs`：

```js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { recommend } = require('../src/web/match-filter.js');

const thresholds = { taste: 0.8, taste_same_area: 0.7 };
const people = [
  { name: 'A', taste: 80, areas: [] },
  { name: 'B', taste: 79, areas: ['高雄市苓雅區'] },
  { name: 'C', taste: 70, areas: ['高雄市苓雅區'] },
  { name: 'D', taste: 69, areas: ['高雄市苓雅區'] },
  { name: 'E', taste: 75, areas: ['臺北市信義區'] },
];
const names = list => list.map(person => person.name);

test('without a confirmed area only the higher bar applies', () => {
  assert.deepEqual(names(recommend(people, [], thresholds)), ['A']);
});

test('a confirmed shared area lowers the bar to 70%', () => {
  assert.deepEqual(names(recommend(people, ['高雄市苓雅區'], thresholds)), ['A', 'B', 'C']);
});

test('an area that nobody shares changes nothing', () => {
  assert.deepEqual(names(recommend(people, ['高雄市新興區'], thresholds)), ['A']);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/match-filter.test.cjs`
Expected: FAIL，`Cannot find module '../src/web/match-filter.js'`

- [ ] **Step 3: Write minimal implementation**

建立 `src/web/match-filter.js`：

```js
/* The final recommendation rule, shared by the match page and its tests. */
(function (root) {
  'use strict';
  const whole = value => Math.round(value * 100);
  function recommend(candidates, confirmedAreas, thresholds) {
    const chosen = new Set(confirmedAreas);
    return candidates.filter(candidate => candidate.taste >= whole(thresholds.taste)
      || (candidate.taste >= whole(thresholds.taste_same_area) && candidate.areas.some(area => chosen.has(area))));
  }
  const api = Object.freeze({ recommend });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.MatchFilter = api;
})(globalThis);
```

- [ ] **Step 4: Run test to verify it passes**

Run: `node --test tests/*.test.cjs`
Expected: `# pass 18`、`# fail 0`

- [ ] **Step 5: Commit**

```bash
git add src/web/match-filter.js tests/match-filter.test.cjs
git commit -F - <<'EOF'
feat: apply the confirmed-area threshold rule in the browser

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 7: 配對頁與報告整合

**Files:**
- Create: `src/web/match.html`
- Modify: `src/receipt/build.py`（imports、新增 `embed_page`、`script_constant`、`build_matches`，`main()` 的資料腳本與嵌入段落）
- Modify: `src/web/invoice-insights.html`（第 15–16 行的按鈕與說明、第 89–90 行的頁面容器）
- Modify: `src/web/taste-navigation.js`（整檔改寫）
- Modify: `src/web/styles.css:395`
- Modify: `tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: `build_profile`（Task 3）、`eligible`、`ready`（Task 4）、`build_personas`（Task 5）、`match-filter.js`（Task 6）
- Produces: 報告中的 `<template id="match-page-source">`；配對頁內的常數 `matchReportData`，格式：`{"isDemo": bool, "population": int, "settings": {"weights", "thresholds", "top_matches", "category_min_items"}, "me": {"ready": bool, "item_count": int, "areas": [...], "tags": [...]}, "candidates": [...eligible 的輸出]}`；`window.ReceiptPages.showReport()` 照舊

- [ ] **Step 1: Write the failing test**

`tests/test_build_report.py`：
- 在 `test_default_build_ignores_private_sources_and_preserves_private_html` 中，`self.assertIn("receipt-taste/categories-v1", comparison)` 之後加入：

```python
            match_source = re.search(r'<template id="match-page-source">(.*?)</template>', html, re.S)
            self.assertIsNotNone(match_source)
            match_page = unescape(match_source.group(1))
            matched = ResourceParser()
            matched.feed(match_page)
            self.assertEqual(matched.external, [])
            self.assertIn('data-source="match-filter.js"', match_page)
            payload = json.loads(re.search(r"const matchReportData = (.*?);\n</script>", match_page, re.S).group(1))
            self.assertTrue(payload["isDemo"])
            self.assertEqual(payload["population"], 40)
            self.assertEqual(payload["settings"]["thresholds"], {"taste": 0.8, "taste_same_area": 0.7})
            self.assertTrue(payload["me"]["ready"])
            self.assertEqual(payload["me"]["areas"], ["高雄市苓雅區", "高雄市新興區"])
            self.assertGreaterEqual(len(payload["candidates"]), 1)
            self.assertIn('href="#match"', html)
```

- 在 `test_build_from_another_directory_is_self_contained_and_repeatable` 中，`self.assertEqual(len(parsed.scripts), 8)` 之後加入：

```python
            match_page = unescape(re.search(r'<template id="match-page-source">(.*?)</template>', html, re.S).group(1))
            payload = json.loads(re.search(r"const matchReportData = (.*?);\n</script>", match_page, re.S).group(1))
            self.assertFalse(payload["isDemo"])
            self.assertFalse(payload["me"]["ready"])
            self.assertEqual(payload["candidates"], [])
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m unittest tests.test_build_report -v`
Expected: FAIL — `match_source` 為 None；另一個測試在 `re.search(...).group(1)` 出現 `AttributeError`

- [ ] **Step 3: Create the match page**

建立 `src/web/match.html`：

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
h1{font-size:28px;line-height:1.3;margin:0 0 8px}h2{font-size:15px;margin:0 0 10px}h3{font-size:17px;margin:0}
.note{color:var(--muted);font-size:12px;margin:0}
.card{background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:18px 20px;margin-top:16px}
.chips{display:flex;flex-wrap:wrap;gap:6px;list-style:none;margin:0;padding:0}
.chips li{border:1px solid var(--line);border-radius:999px;padding:3px 11px;font-size:12px}
.chips small{color:var(--muted);margin-right:5px}
.areas{display:flex;flex-wrap:wrap;gap:8px 18px;margin-top:12px}
.areas label{display:flex;align-items:center;gap:6px;cursor:pointer}.areas input{accent-color:var(--teal);width:16px;height:16px}
.matches{margin-top:30px}
.match-head{display:flex;justify-content:space-between;align-items:baseline;gap:12px;flex-wrap:wrap;margin-bottom:10px}
.score{font-size:24px;font-weight:600;color:var(--teal)}.score small{font-size:12px;color:var(--muted);font-weight:400;margin-left:6px}
.basis{color:var(--muted);font-size:12px;margin:10px 0 0}
.reasons,.differences{margin:8px 0 0;padding-left:20px}
.reasons li::marker{content:"✓  ";color:var(--teal)}.differences li::marker{content:"≠  ";color:var(--amber)}
.empty{color:var(--muted);margin-top:16px}
.method{margin-top:22px;color:var(--muted);font-size:12px}.method summary{cursor:pointer}.method p{margin:8px 0}
@media(max-width:640px){h1{font-size:23px}.card{padding:15px}}
</style>
</head>
<body>
<main>
<a id="return-report" class="return-report" href="#report" hidden>← 返回消費洞察</a>
<p class="eyebrow">FIND YOUR PEOPLE · 找到同好</p>
<h1>從消費習慣，找到合拍的人。</h1>
<p class="note" id="match-note"></p>
<section class="card" aria-labelledby="my-tags-title"><h2 id="my-tags-title">我的消費標籤</h2><ul class="chips" id="my-tags"></ul></section>
<section class="card" aria-labelledby="areas-title"><h2 id="areas-title">確認生活圈</h2><p class="note" id="areas-note"></p><div class="areas" id="my-areas"></div></section>
<section class="matches" aria-labelledby="matches-title"><h2 id="matches-title">和你最合拍的人</h2><p class="note" id="match-status" role="status" aria-live="polite"></p><div id="match-list"></div></section>
<details class="method"><summary>怎麼算的？</summary><div id="method"></div></details>
</main>
<script src="match-filter.js"></script>
<script src="match-data.js"></script>
<script>
'use strict';
(function () {
  const data = matchReportData, settings = data.settings;
  const $ = id => document.getElementById(id);
  const pct = value => Math.round(value * 100) + '%';
  function make(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined) node.textContent = text;
    if (className) node.className = className;
    return node;
  }
  function chipItems(tags) {
    return tags.map(tag => {
      const item = make('li');
      item.append(make('small', tag.dimension), tag.text);
      return item;
    });
  }
  function lines(texts, className) {
    const list = make('ul', undefined, className);
    for (const text of texts) list.append(make('li', text));
    return list;
  }
  function card(match) {
    const article = make('article', undefined, 'card');
    const head = make('div', undefined, 'match-head');
    const score = make('div', match.total + '%', 'score');
    score.append(make('small', '品味 ' + match.taste + '%'));
    head.append(make('h3', match.name), score);
    const tags = make('ul', undefined, 'chips');
    tags.append(...chipItems(match.tags));
    article.append(head, tags, make('p', '比較了：' + match.basis.join('、'), 'basis'), lines(match.reasons, 'reasons'));
    if (match.differences.length) article.append(lines(match.differences, 'differences'));
    return article;
  }
  const chosen = new Set();
  function render() {
    const list = $('match-list');
    if (!data.me.ready) {
      $('match-status').textContent = '';
      list.replaceChildren(make('p', '資料不足，還不能配對：需要至少 ' + settings.category_min_items + ' 筆已分類品項（目前 '
        + data.me.item_count + ' 筆），以及品牌、葷素紀錄或消費檔次其中一項。多掃幾張發票再看看。', 'empty'));
      return;
    }
    const passed = MatchFilter.recommend(data.candidates, [...chosen], settings.thresholds);
    const shown = passed.slice(0, settings.top_matches);
    $('match-status').textContent = '符合條件 ' + passed.length + ' 位' + (passed.length > shown.length ? '，顯示前 ' + shown.length + ' 位' : '') + '。';
    list.replaceChildren(...(shown.length ? shown.map(card) : [make('p', '目前沒有夠相似的人，多掃幾張發票再看看。', 'empty')]));
  }
  $('match-note').textContent = '配對對象是 ' + data.population + ' 位虛構示範用戶。'
    + (data.isDemo ? '「我」也是虛構示範資料。' : '你的標籤來自這份私人報告，只存在這個檔案裡。');
  const mine = $('my-tags');
  if (data.me.tags.length) mine.append(...chipItems(data.me.tags));
  else mine.replaceWith(make('p', '資料還不夠產生標籤。', 'note'));
  $('areas-note').textContent = data.me.areas.length
    ? '下面是依發票賣方地址推測的常消費地區。勾選真的是你生活圈的地方：同生活圈的人，品味門檻從 ' + pct(settings.thresholds.taste)
      + ' 降到 ' + pct(settings.thresholds.taste_same_area) + '。不勾選就不會用來放寬門檻。'
    : '目前推測不出常消費地區，所以只用 ' + pct(settings.thresholds.taste) + ' 的門檻。';
  for (const area of data.me.areas) {
    const label = make('label'), box = make('input');
    box.type = 'checkbox';
    box.addEventListener('change', () => { if (box.checked) chosen.add(area); else chosen.delete(area); render(); });
    label.append(box, area);
    $('my-areas').append(label);
  }
  const weights = settings.weights;
  $('method').append(
    make('p', '五個面向加權：品類 ' + pct(weights.category) + '、常消費地區 ' + pct(weights.district) + '、品牌 ' + pct(weights.brand)
      + '、葷素紀錄 ' + pct(weights.flavor) + '、消費檔次 ' + pct(weights.price) + '。缺資料的面向不計分，權重分給其他面向。'),
    make('p', '品類一定要能比較（各自至少 ' + settings.category_min_items + ' 筆已分類品項），另外至少再有品牌、葷素紀錄、消費檔次其中一項，才會配對。'),
    make('p', '品味分數不含地區，至少 ' + pct(settings.thresholds.taste) + ' 才推薦；對方常在你勾選的生活圈消費時，放寬為 '
      + pct(settings.thresholds.taste_same_area) + '。大字是總分，用來排序。'),
    make('p', '同一張發票的同一品項只算一次；有品項買 2 份以上的發票，可能是多人一起消費，不列入消費檔次。'),
    make('p', '只用行政區與連鎖品牌，不顯示分店、日期或金額。配對對象皆為虛構示範用戶，他們的常消費地區視為已確認的生活圈。'));
  render();
  const pageHost = window.parent !== window && window.frameElement?.id === 'match-frame' ? window.parent : null;
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

- [ ] **Step 4: Compute and embed the candidates in the build**

`src/receipt/build.py`：
- 在 `from .demo import build_demo` 之後加入三行 import：

```python
from .matching import eligible, ready
from .personas import build_personas
from .tags import build_profile
```

- 在 `embed_scripts` 函式之後加入：

```python
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


def build_matches(months, categories, is_demo):
    """Profile the report and keep only the scores and words the match page shows."""
    settings = json.loads((ROOT / "configs" / "tags.json").read_text(encoding="utf-8"))
    brands = json.loads((ROOT / "configs" / "brands.json").read_text(encoding="utf-8"))
    me = build_profile([row for month in months.values() for row in month["rows"]], categories, brands, settings)
    people = [{"name": person["name"], "profile": build_profile(person["rows"], categories, brands, settings)}
              for person in build_personas()]
    names = [category["name"] for category in categories]
    return {
        "isDemo": is_demo, "population": len(people),
        "settings": {key: settings[key] for key in ("weights", "thresholds", "top_matches", "category_min_items")},
        "me": {"ready": ready(me), "item_count": me["item_count"], "areas": me["areas"], "tags": me["tags"]},
        "candidates": eligible(me, people, names, settings) if ready(me) else [],
    }
```

- 在 `main()` 中，把

```python
    # A product name must not be able to introduce an HTML script element.
    payload = json.dumps(data, ensure_ascii=False, indent=2).replace("<", "\\u003c")
    data_script = "'use strict';\nconst expenseReportData = " + payload + ";\n"
```

改成

```python
    data_script = script_constant("expenseReportData", data)
```

- 在 `main()` 中，把

```python
    marker = '<template id="taste-page-source"></template>'
    if html.count(marker) != 1:
        raise ValueError("Expected exactly one embedded comparison template")
    html = html.replace(marker, '<template id="taste-page-source">' + escape(comparison) + '</template>', 1)
```

改成

```python
    html = embed_page(html, "taste-page-source", comparison)
    matches = build_matches(months, config["categories"], not args.private)
    match_page = embed_scripts((WEB / "match.html").read_text(encoding="utf-8"), {
        "match-filter.js": (WEB / "match-filter.js").read_text(encoding="utf-8"),
        "match-data.js": script_constant("matchReportData", matches)})
    html = embed_page(html, "match-page-source", match_page)
```

- 在 `main()` 最後的 `for key, month in months.items():` 迴圈之後加入：

```python
    print("match candidates:", len(matches["candidates"]), "of", matches["population"], "fictional people")
```

- [ ] **Step 5: Link the page from the report**

`src/web/invoice-insights.html` 第 15–16 行：把

```html
 <div class="taste-actions"><a class="taste-primary" id="compare-friends" href="#friends">比較跟朋友品味差多少 ↗</a><button id="export-taste" type="button" disabled title="功能準備中">匯出我的品味連結</button></div>
 <p class="taste-caption">把消費偏好帶到朋友比較頁。品味連結匯出功能準備中。</p>
```

改成

```html
 <div class="taste-actions"><a class="taste-primary" id="compare-friends" href="#friends">比較跟朋友品味差多少 ↗</a><a id="find-matches" href="#match">找到同好 ↗</a><button id="export-taste" type="button" disabled title="功能準備中">匯出我的品味連結</button></div>
 <p class="taste-caption">把消費偏好帶到朋友比較頁，或到「找到同好」看看誰和你最合拍。品味連結匯出功能準備中。</p>
```

第 89–90 行：把

```html
<section id="taste-view" aria-label="朋友品味比較" hidden><iframe id="taste-frame" title="朋友品味比較" referrerpolicy="no-referrer"></iframe></section>
<template id="taste-page-source"></template>
```

改成

```html
<section id="taste-view" aria-label="朋友品味比較" hidden><iframe id="taste-frame" title="朋友品味比較" referrerpolicy="no-referrer"></iframe></section>
<section id="match-view" aria-label="找到同好" hidden><iframe id="match-frame" title="找到同好" referrerpolicy="no-referrer"></iframe></section>
<template id="taste-page-source"></template>
<template id="match-page-source"></template>
```

`src/web/styles.css` 第 395 行：把

```css
#taste-view{position:fixed;inset:0;background:var(--paper);z-index:1000}#taste-frame{display:block;width:100%;height:100%;border:0;background:var(--paper)}
```

改成

```css
#taste-view,#match-view{position:fixed;inset:0;background:var(--paper);z-index:1000}#taste-frame,#match-frame{display:block;width:100%;height:100%;border:0;background:var(--paper)}
```

把 `src/web/taste-navigation.js` 整檔改成：

```js
/* Secondary pages are embedded in this file, and created only on demand. */
(function(){
 'use strict';
 if(typeof window==='undefined')return;
 const pages=[
  {view:'taste-view',frame:'taste-frame',source:'taste-page-source',link:'compare-friends',matches:hash=>hash==='#friends'||hash.startsWith('#taste=')},
  {view:'match-view',frame:'match-frame',source:'match-page-source',link:'find-matches',matches:hash=>hash==='#match'},
 ].map(page=>({...page,view:document.getElementById(page.view),frame:document.getElementById(page.frame),source:document.getElementById(page.source),loaded:false}))
  .filter(page=>page.view&&page.frame&&page.source);
 if(!pages.length)return;
 let showing=null,reportHash='',reportScroll=0,lastTasteHash='';
 function route(){
  const hash=location.hash,page=pages.find(candidate=>candidate.matches(hash));
  if(page){
   if(!showing)reportScroll=window.scrollY;
   for(const other of pages)other.view.hidden=other!==page;
   document.body.classList.add('taste-view-open');
   if(!page.loaded){page.frame.srcdoc=page.source.content.textContent;page.loaded=true;}
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
 window.ReceiptPages=Object.freeze({showReport(){location.hash=reportHash||'#report';}});
 window.addEventListener('hashchange',route);
 route();
})();
```

- [ ] **Step 6: Rebuild the public demo**

Run: `python scripts/build_report.py`
Expected: 兩個月份的摘要與 `match candidates: 10 of 40 fictional people`

- [ ] **Step 7: Run all tests to verify they pass**

Run: `python -m unittest discover -s tests -v`
Expected: 全部 OK

Run: `node --test tests/*.test.cjs`
Expected: `# pass 18`、`# fail 0`

- [ ] **Step 8: Commit**

```bash
git add src/web/match.html src/receipt/build.py src/web/invoice-insights.html src/web/taste-navigation.js src/web/styles.css tests/test_build_report.py invoice-insights.html
git commit -F - <<'EOF'
feat: add the find-your-people page with area confirmation

Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>
EOF
```

---

### Task 8: 最終驗證（由主控執行，不交給子代理）

**Files:** 無新增；只檢查。

- [ ] **Step 1: 全部測試**

Run: `python -m unittest discover -s tests -v` 與 `node --test tests/*.test.cjs`
Expected: 全部通過

- [ ] **Step 2: 在瀏覽器檢查公開示範版**

用本機 HTTP 伺服器開啟 `invoice-insights.html`：
- 明細表有「行政區」欄。
- 「找到同好 ↗」切到配對頁：標籤卡、兩個可勾選的常消費地區、「符合條件 5 位」。
- 勾選高雄市苓雅區後變成「符合條件 10 位，顯示前 5 位」；取消勾選後恢復。
- 偏葷的手搖學生卡片有「≠ 都常去示範餐坊，但點的不一樣（示範蔬食餐盒／示範鮮蝦餐盒）」。
- 「← 返回消費洞察」回到報告原本的捲動位置；「比較跟朋友品味差多少」仍正常。
- 手機寬度（375px）沒有水平捲動。

- [ ] **Step 3: 用真實資料做冒煙測試（只印數量）**

在記憶體中用 `data/private/report.json` 的輸入檔建立月份資料與候選名單，**不寫入任何檔案**，只印出：行政區解析成功與失敗的筆數、非實體賣方的發票數、各標籤面向的數量、`ready` 與候選人數。

- [ ] **Step 4: 回報使用者**

列出測試結果、校準數字與冒煙測試的數量。詢問是否要重新產生私人報告（會覆寫 `invoice-insights-private.html`），以及是否接著更新 README。
