# 品味連結新版、匯出與實際品項 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use subagent-driven-development (recommended) or executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 把自己的品味帶出報告：「匯出我的品味連結」產生新版連結（帶品味特質、推力、訊號與每個訊號最常買的品項），朋友貼上後就看得到兩人的品味特質連線圖；連線圖上點一個訊號，外面長出一小排真的買過的東西（看得出買了什麼，看不出在哪裡買）。同時收緊資料檢查、補上連線頁的煙霧測試、照實改寫隱私說明。

**Architecture:** Python 的 `signals.measure` 記下每個訊號背後算進來的消費，新檔 `items.py` 依品名規則（住宿、交通方式、拿掉地名）整理成每個訊號最多 3 個品項，`traits.explain` 一起交出；`build.py` 把品項清單嵌入主頁（新的 `tasteExportData`，給匯出用）、配對頁與連線頁。瀏覽器只檢查資料（`TraitNetwork.validate` 收緊並檢查品項）、畫圖（`trait-network.js` 的純函式算出品項點的位置與留白）、編成連結（`TasteProfile` 新版 `receipt-taste/traits-v2`，舊版照常可讀）。

**Tech Stack:** Python 3.10+ 標準函式庫（`unittest`）、原生 JavaScript、Node.js `node:test`

**Spec:** `docs/superpowers/specs/2026-10-11-taste-link-v2-design.md`

## Global Constraints

- Python 只用標準函式庫；`pyproject.toml` 不變。
- 不讀取、不修改 `data/` 底下任何檔案（私人資料）。執行 `python scripts/build_report.py` 會寫入 `data/processed/report-data.js`（公開示範版的輸出），這是允許的；絕不使用 `--private`。
- 根目錄的 `report-data.js` 與 `*.csv` 是私人檔案，絕不加入 Git。每個任務只 `git add` 該任務列出的檔案，不要用 `git add -A` 或 `git add .`。
- 測試只用虛構名稱（「示範」「測試」開頭，或小安、小宇、小林與 40 位虛構用戶）。
- `src/web/` 只改本計畫列出的檔案：`trait-network.js`、`taste-profile.js`、`taste-export.js`、`match-filter.js`、`match.html`、`taste-comparison.html`、`invoice-insights.html`、`styles.css`。
- 報告維持單一 HTML 檔、沒有外部資源。
- 程式碼與文字照本計畫逐字輸入。
- 改檔一律用編輯工具（Edit／Write）。不要用 shell 的 heredoc、`sed` 或 `echo` 寫入含反斜線（`\`）的程式碼：這個環境的 shell 會把反斜線吃掉一半（`\n` 會變成真的換行）。
- 本計畫的程式碼區塊都不在編號清單裡，照原樣貼上（Python 的縮排有意義）。
- 在 `feature/taste-traits` 分支工作；不要 push。
- Commit 訊息用英文，結尾一行 `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`。
- 指令都在專案根目錄用 Git Bash 執行：
  - 全部 Python 測試：`python -m unittest discover -s tests`
  - 單一檔：`python -m unittest tests.test_items -v`
  - Node 測試：`node --test tests/*.test.cjs`；單一檔：`node --test tests/trait-network.test.cjs`
- 根目錄的 `invoice-insights.html` 是產生出來的示範報告，`tests/match-page.test.cjs`、`tests/connection-page.test.cjs`、`tests/taste-export.test.cjs` 會讀它。改到會被嵌入報告的檔案（`src/web/*`、`configs/*.json`、`src/receipt/*.py`）的任務，最後都要執行 `python scripts/build_report.py`，並把 `invoice-insights.html` 一起 commit（內容沒變時 Git 不會列出它，就不用加）。
- 在 Windows 上產生的 `invoice-insights.html` 是 CRLF 換行；讀它的 Node 測試切出 JSON 後一律先 `trim()`，不要假設是 `\n`。
- Git 在 Windows 上會提示「LF will be replaced by CRLF」，可以忽略。

## 試做結果（已在專案副本逐任務驗證）

- 每個任務結束時的測試數：

  | 任務後 | Python | Node |
  |---|---|---|
  | 開始前 | 61 | 56 |
  | Task 1 | 61 | 59 |
  | Task 2 | 61 | 60 |
  | Task 3 | 63 | 60 |
  | Task 4 | 74 | 60 |
  | Task 5 | 74 | 60 |
  | Task 6 | 74 | 61 |
  | Task 7 | 74 | 65 |
  | Task 8 | 74 | 68 |
  | Task 9 | 74 | 71 |
  | Task 10 | 74 | 72 |

- `python scripts/build_report.py` 每次都印出同樣三行（配對與分數完全不變）：
  ```text
  2026-03 50 rows; total 7910
  2026-04 53 rows; total 8095
  taste similarity to 40 fictional people: highest 71%, median 14%, lowest -12%
  ```
- 示範的「我」的品項（`items`）：每餐花費、餐廳正餐、現成餐點都是「蔬食餐盒 ×5、番茄燉飯 ×4、蔬菜咖哩 ×4」；飲料甜度「半糖冬瓜青茶 ×7、百香果茶 ×7、花果茶 ×7」；住宿「旅館住宿 ×2」；共 16 個不同的品名。示範資料只有「旅館住宿」「高鐵票」兩個名稱和原始品名不同，沒有品名被地名規則誤改。
- 匯出：預覽列「虛構示範 · 2026-03、2026-04 · 97 筆已分類品項 · 17 項品味特質」；品名清單 16 個；連結約 2,070 字元。按「帶到朋友比較頁」：「我的偏好 × 小宇」大字 +41；換成小林 +27、小安 +14（Python 算出的值）。
- 連線頁：配對清單第一張（手搖學生 B）大字 +71；點左邊「飲料甜度」兩側各長出 3 個品項點，說明列前兩行是「你：飲料甜度 約 8 分糖（半糖冬瓜青茶 ×7、百香果茶 ×7、花果茶 ×7），往「高甜度」推 0.61」「手搖學生 B：飲料甜度 約 10 分糖（冬瓜青茶 ×10、黑糖珍珠鮮奶 ×8、珍珠奶茶 ×6），往「高甜度」推 0.80」。
- 預留空間：你 × 手搖學生 B 的桌機 `viewBox` 是 `-54 0 1301 640`（整張圖約小 8%）；手機是 `0 -97 600 1009`（只變長，不變窄）。
- 報告從約 278 KB 變成約 330 KB（品項清單放在 `<template>` 裡，JSON 的引號會被轉成 `&quot;`）。

## 與規格原稿不同的地方（試做時決定，規格已同步）

1. **品項點排成一小排直的**，不是規格寫的「沿扇面方向往外展開」：扇面頂端與底部的訊號，往外展開的 3 個點會左右並排（相距約 30），約 100 寬的標籤會互相蓋住。改成桌機在訊號外側（你在左、對方在右）排一小排、每列間隔 20；手機在上下兩團外面的空白帶排一小排、每列間隔 26，名稱放在點的右邊。這樣任何位置都不重疊，手機也不必把整張圖縮小。
2. **留白依兩人實際的品項計算**（畫圖時就決定，點選時不縮放），不是「最長的標籤（10 個字）」：示範資料桌機只小約 8%。
3. 報告約 330 KB、連結約 2,070 字元（規格寫約 310 KB、約 2,300 字元）。
4. `items.listed(purchases, rows, context)`：設定從 `context` 取，不另傳 `settings`。
5. 規格沒寫到的三句：兩邊都沒有資料時按鈕旁寫「匯入兩邊的資料後才能看品味特質」；有品味特質但沒有任何品項時寫「連結裡沒有品名。」；匯出面板的說明由 `taste-export.js` 依設定填入（「17 項」「10 類」都由程式產生）。
6. 煙霧測試直接在報告裡的配對頁點第一張卡片，拿配對頁真正交給連線頁的資料；所以配對頁漏傳品項時測試會失敗。
7. 配對頁頁首那句搬到 `MatchFilter.intro(data, ready)`，才測得到「資料不足時不寫『點一個人…』」。

## 檔案結構

| 檔案 | 動作 | 責任 |
|---|---|---|
| `tests/connection-page.test.cjs` | 新增 | 連線頁的煙霧測試：用假 DOM 跑報告裡的配對頁與連線頁 |
| `tests/built-report.cjs` | 新增 | 測試共用：讀產生的報告與 `<template>` 裡的頁面（`match-page`、`connection-page`、`taste-export` 三個測試共用） |
| `src/web/trait-network.js` | 修改 | 收緊 `validate`、檢查品項；品項點的位置與留白（`purchases`、`viewBox`、`shortName`）；說明列寫出品項 |
| `src/receipt/signals.py` | 修改 | `measure` 多回傳 `purchases`（每個訊號背後的消費） |
| `src/receipt/items.py` | 新增 | 品名規則與每個訊號的品項清單 |
| `src/receipt/traits.py` | 修改 | 多讀 `configs/report.json`；`explain` 交出 `items` |
| `configs/traits.json` | 修改 | 4 個訊號標上 `"list_items": false` |
| `configs/attributes.json` | 修改 | `transport_kinds`、`generic_labels`、`place_words` |
| `src/receipt/build.py` | 修改 | 嵌入品項清單；主頁的 `tasteExportData` |
| `src/web/invoice-insights.html` | 修改 | 主頁嵌入 `taste-export-data.js`；匯出按鈕與面板 |
| `src/web/match.html` | 修改 | 配對卡片交出品項；隱私說明；頁首 |
| `src/web/taste-comparison.html` | 修改 | 示範朋友的 try/catch；外圈品項點；新版連結的讀取與說明 |
| `src/web/taste-profile.js` | 修改 | 新版連結 `receipt-taste/traits-v2` |
| `src/web/taste-export.js` | 修改 | 匯出帶品味特質；品名清單 |
| `src/web/styles.css` | 修改 | 品名清單的樣式 |
| `src/web/match-filter.js` | 修改 | `intro` |
| `tests/test_traits.py`、`tests/test_items.py`（新增）、`tests/test_build_report.py` | 修改 | Python 測試 |
| `tests/trait-network.test.cjs`、`tests/taste-profile.test.cjs`、`tests/taste-export.test.cjs`（新增）、`tests/match-filter.test.cjs` | 修改 | Node 測試 |
| `README.md`、`.gitignore` | 修改 | 連結說明；排除根目錄的 `report-data.js` |
| `invoice-insights.html` | 重新產生 | 公開示範版 |
| 規格、交接文件 | 修改 | Task 11 |

---

### Task 1: 連線頁的煙霧測試

先鎖住現在的行為，之後改連線頁的匯入路徑時才知道有沒有弄壞（交接文件第③輪第 4 項）。測試直接用產生出來的 `invoice-insights.html`：在假 DOM 裡跑配對頁、點第一張卡片，拿到配對頁真正交給連線頁的資料，再跑連線頁。這是描述現有行為的測試，**第一次跑就應該通過**；若沒通過，先停下來回報，不要改程式。

**Files:**
- Create: `tests/connection-page.test.cjs`
- Create: `tests/built-report.cjs`（讀產生的報告的共用輔助函式；檔名不是 `*.test.cjs`，不會被當成測試）
- Modify: `tests/match-page.test.cjs`（改用共用輔助函式）

**Interfaces:**
- Produces（同一個測試檔裡的輔助函式，Task 7、8 會沿用）：`element(tag)`、`fire(node, type, event)`、`findAll(node, check)`、`pairFromMatchList(index) -> { name, pair }`、`open({ pair }) -> { get, views, calls }`。
- Produces：`tests/built-report.cjs` 匯出 `html`、`between`、`templateSource(id)`、`scriptsOf(id)`（Task 8、9 沿用）。

- [ ] **Step 1: Write the test**

新增 `tests/built-report.cjs`（內含反斜線，用 Write 工具）：

```js
// The built demo report and the pages it keeps, escaped, inside template elements; shared by the tests that read it.
const fs = require('node:fs');
const path = require('node:path');

const html = fs.readFileSync(path.join(__dirname, '..', 'invoice-insights.html'), 'utf8');
const between = (text, start, end) => {
  const from = text.indexOf(start) + start.length;
  return text.slice(from, text.indexOf(end, from));
};
const unescapeHtml = text => [['&lt;', '<'], ['&gt;', '>'], ['&quot;', '"'], ['&#x27;', "'"], ['&amp;', '&']]
  .reduce((result, [entity, character]) => result.split(entity).join(character), text);
// A page the report keeps inside <template id="…">, unescaped.
const templateSource = id => unescapeHtml(between(html, `<template id="${id}">`, '</template>'));
// The inline scripts of such a page, in order.
const scriptsOf = id => [...templateSource(id).matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);

module.exports = { html, between, templateSource, scriptsOf };
```

在 `tests/match-page.test.cjs` 把開頭的

```js
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
```

換成

```js
const { test } = require('node:test');
const assert = require('node:assert/strict');
const { view } = require('../src/web/match-filter.js');
const { between, templateSource } = require('./built-report.cjs');

const MINUS = String.fromCharCode(0x2212);
// The built demo report keeps the match page, escaped, inside a template element.
const data = JSON.parse(between(templateSource('match-page-source'), 'const matchReportData = ', '</script>').trim().replace(/;$/, ''));
```

新增 `tests/connection-page.test.cjs`：

```js
// Runs the connection page from the built report against a small fake DOM, so its main paths stay covered.
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { scriptsOf } = require('./built-report.cjs');

const scripts = scriptsOf('taste-page-source');
const matchScripts = scriptsOf('match-page-source');

// Just enough of an element for the page: attributes, children, listeners and a few properties.
function element(tag = 'div') {
  const node = {
    tag, attrs: {}, children: [], listeners: {}, style: {}, dataset: {}, hidden: false, disabled: false, value: '', options: [],
    textContent: '', parentElement: null, lastChild: { textContent: '' },
    classList: { names: new Set(), add(name) { this.names.add(name); }, remove(name) { this.names.delete(name); },
      toggle(name, on) { if (on ?? !this.names.has(name)) this.names.add(name); else this.names.delete(name); },
      contains(name) { return this.names.has(name); } },
    setAttribute(key, value) { this.attrs[key] = String(value); },
    getAttribute(key) { return key in this.attrs ? this.attrs[key] : null; },
    removeAttribute(key) { delete this.attrs[key]; },
    append(...nodes) { for (const child of nodes) { child.parentNode = node; node.children.push(child); } },
    replaceChildren(...nodes) { node.children = []; node.append(...nodes); },
    remove() { if (node.parentNode) node.parentNode.children = node.parentNode.children.filter(child => child !== node); },
    addEventListener(type, callback) { (node.listeners[type] ||= []).push(callback); },
    focus() {},
  };
  node.parentElement = { classList: node.classList };
  return node;
}
const fire = (node, type, event = {}) => {
  for (const callback of node.listeners[type] || []) callback({ preventDefault() {}, target: node, key: '', ...event });
};
// Every element below `node` that passes the test, depth first.
const findAll = (node, check) => node.children.flatMap(child => [...(check(child) ? [child] : []), ...findAll(child, check)]);

// Click a card on the built match page and keep the pair it hands to the connection page.
function pairFromMatchList(index) {
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  let pair = null;
  const window = { frameElement: { id: 'match-frame' } };
  window.parent = { ReceiptPages: { showConnection: chosen => { pair = chosen; }, showReport() {} } };
  const context = vm.createContext({ window, document: { getElementById: get, createElement: tag => element(tag) } });
  for (const source of matchScripts) vm.runInContext(source, context);
  const card = get('match-list').children[index];
  fire(card, 'click');
  return { name: card.title, pair };
}

// Load the page as the report would: in the connection frame with a chosen pair, or on its own as the friends page.
function open({ pair = null } = {}) {
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  const category = get('category');
  category.options = ['all', 'dumplings', 'sweetness', '正餐'].map(value => ({ value, disabled: false }));
  const views = ['traits', 'items'].map(view => { const button = element('button'); button.dataset.view = view; return button; });
  const singles = { '.subtitle': element(), '.legend-item': element(), '.negative-label': element(), '.legend-explain': element(),
    '.controls': element(), 'header .brand': element() };
  const lists = { '[data-view]': views, '.summary-case': [element(), element()], '.import-title-row, .imports': [element(), element()],
    '[data-demo-side]': [] };
  const calls = [];
  const host = pair ? {
    location: { search: '', hash: '', href: 'http://127.0.0.1/invoice-insights.html#connection' },
    ReceiptPages: { connection: () => pair, showMatches: () => calls.push('showMatches'), showReport: () => calls.push('showReport') },
  } : null;
  const document = {
    getElementById: get,
    querySelector: selector => singles[selector] || null,
    querySelectorAll: selector => lists[selector] || [],
    createElementNS: (ns, tag) => element(tag),
    addEventListener() {},
  };
  const window = { location: { search: '', hash: '', href: 'http://127.0.0.1/taste-comparison.html' }, addEventListener() {} };
  window.parent = host ? { ...host, window: null } : window;
  window.frameElement = host ? { id: 'connection-frame' } : null;
  const context = vm.createContext({ window, document, location: window.location, URLSearchParams,
    matchMedia: () => ({ matches: false, addEventListener() {} }) });
  for (const source of scripts) vm.runInContext(source, context);
  return { get, views, calls };
}

test('a match opens on the taste network with the taste score, and the item details stay one click away', () => {
  const chosen = pairFromMatchList(0);
  assert.equal(chosen.name, '查看你和手搖學生 B的連線圖');
  const { get, views, calls } = open({ pair: chosen.pair });
  assert.equal(get('overall-score').textContent, '+71');
  assert.equal(get('overall-note').textContent, '依 17 項品味特質計算 · 虛構示範');
  assert.equal(get('scope').textContent, '17 項品味特質 · 46 個訊號');
  assert.equal(views[0].attrs['aria-pressed'], 'true');
  assert.equal(findAll(get('network'), node => node.attrs.class === 't-link').length, 85);
  assert.equal(findAll(get('network'), node => node.attrs.class === 't-cell').length, 15);
  assert.equal(get('summary-best').textContent, '都偏好好吃飯（加 32 分）— 吃飯這件事，從不將就。');
  fire(views[1], 'click');
  assert.equal(views[1].attrs['aria-pressed'], 'true');
  assert.match(get('scope').textContent, /^全類別 · \d+ 個類別點$/);
  assert.equal(get('overall-score').textContent, '+71');
  assert.equal(get('return-report').textContent, '← 返回配對清單');
  fire(get('return-report'), 'click');
  assert.deepEqual(calls, ['showMatches']);
});

test('picking a signal lights its path and writes both people into the detail line', () => {
  const { get } = open({ pair: pairFromMatchList(0).pair });
  const links = findAll(get('network'), node => node.attrs.class === 't-link');
  const [mine] = findAll(get('network'), node => node.attrs['aria-label']?.startsWith('你的飲料甜度'));
  fire(mine, 'click');
  assert.deepEqual(get('detail').textContent.split('\n').slice(0, 2),
    ['你：飲料甜度 約 8 分糖，往「高甜度」推 0.61', '手搖學生 B：飲料甜度 約 10 分糖，往「高甜度」推 0.80']);
  // The picked signal's own lines light up, and lines away from its traits fade out.
  assert.ok(links.some(link => link.style.opacity === '1'));
  assert.ok(links.some(link => link.style.opacity === '.06'));
});

test('the friends page opens on 小安 and 小宇 with their taste score', () => {
  const { get } = open();
  assert.equal(get('overall-score').textContent, '+80');
  assert.equal(get('summary-worst').textContent, '小安偏低甜度，小宇偏高甜度（扣 6 分）— 一個加糖，一個讓糖罐放假。');
});
```

- [ ] **Step 2: Run it**

Run: `node --test tests/connection-page.test.cjs tests/match-page.test.cjs`
Expected: 6 tests pass（現有行為）。

- [ ] **Step 3: Run every Node test**

Run: `node --test tests/*.test.cjs`
Expected: 59 tests pass

- [ ] **Step 4: Commit**

```bash
git add tests/connection-page.test.cjs tests/built-report.cjs tests/match-page.test.cjs
git commit -m "test: smoke-test the connection page from a match card to item details and back" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: 收緊 `TraitNetwork.validate`

交接文件第③輪第 1 項：推力在 −1～+1（程度型 0～1）、特質是 `null` 時推力全空、訊號沒量到時它的推力也必須是空的、每項特質的推力加起來等於那一格的值（容許 0.001）、訊號值 0～1,000,000。現在一個 1e6 的推力會畫出一條超大的線。

**Files:**
- Modify: `src/web/trait-network.js`（`validate`）
- Test: `tests/trait-network.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Produces: `TraitNetwork.validate(person, data)` 介面不變（不合格拋出 `Error('品味資料不正確，請回配對清單重新選擇。')`，合格回傳 `{ vector, pushes, signals }` 的副本）；Task 6 再加上品項。

- [ ] **Step 1: Write the failing test**

新的加總規則也會擋下舊測試裡幾個壞例子，讓向量範圍與有限數的檢查沒有單獨守著的例子。先在 `tests/trait-network.test.cjs` 的測試 `validate keeps well-formed taste data and refuses anything else` 裡，把

```js
  const broken = [
    null, { ...me, vector: me.vector.slice(1) }, { ...me, vector: [1.2, 1, null, 0.3] }, { ...me, vector: [0.7, 1, null, -0.1] },
    { ...me, vector: [NaN, 1, null, 0.3] }, { ...me, pushes: [[0.61], [0, 1], [null, null], [0.375]] },
    { ...me, pushes: [[0.61, 'x'], [0, 1], [null, null], [0.375]] }, { ...me, signals: me.signals.slice(1) },
    { ...me, signals: [Infinity, 0, 0, 1, null, 5] },
  ];
```

換成

```js
  // Each broken person breaks one rule; their pushes still add up unless the sum is what is broken.
  const broken = [
    null, { ...me, vector: me.vector.slice(1) },
    { ...me, vector: [1.2, 1, null, 0.375], pushes: [[0.7, 0.5], [0, 1], [null, null], [0.375]] },
    { ...me, vector: [-1.2, 1, null, 0.375], pushes: [[-0.7, -0.5], [0, 1], [null, null], [0.375]] },
    { ...me, vector: [0.7, 1, null, -0.1] }, { ...me, vector: [NaN, 1, null, 0.375] },
    { ...me, pushes: [[0.61], [0, 1], [null, null], [0.375]] },
    { ...me, pushes: [[0.61, 'x'], [0, 1], [null, null], [0.375]] }, { ...me, signals: me.signals.slice(1) },
    { ...me, signals: [NaN, 0.1429, 0, 1, null, 5] }, { ...me, signals: [Infinity, 0.1429, 0, 1, null, 5] },
  ];
```

再在這個測試後面（它最後一行是 `  for (const person of broken) assert.throws(() => TN.validate(person, data), /品味資料不正確/);` 接 `});`）加上：

```js

test('validate refuses pushes out of range, pushes without data, lines that do not add up and impossible signals', () => {
  // Each broken person breaks exactly one rule; everything else about them is fine.
  const broken = {
    'a push past the end': { ...me, pushes: [[1.5, -0.8], [0, 1], [null, null], [0.375]] },
    'a push of a million': { ...me, pushes: [[1000000, -999999.3], [0, 1], [null, null], [0.375]] },
    'a push on a trait without data': { ...me, pushes: [[0.61, 0.09], [0, 1], [null, 0], [0.375]] },
    'a push from a signal that was not measured': { ...them, signals: [1, 0.2, 0.36, 1, null, 2] },
    'pushes that do not add up': { ...me, pushes: [[0.61, 0.2], [0, 1], [null, null], [0.375]] },
    'a negative signal': { ...me, signals: [-0.1, 0.1429, 0, 1, null, 5] },
    'a signal of millions': { ...me, signals: [0.8333, 0.1429, 0, 1, null, 2000000] },
    'an extra row of pushes': { ...me, pushes: [...me.pushes, [0.5]] },
    'a missing row of pushes': { ...me, pushes: me.pushes.slice(0, 3) },
    'an extra push in a row': { ...me, pushes: [[0.61, 0.09, 0], [0, 1], [null, null], [0.375]] },
    'an extra signal': { ...me, signals: [...me.signals, 1] },
  };
  for (const [name, person] of Object.entries(broken)) assert.throws(() => TN.validate(person, data), /品味資料不正確/, name);
  // Rounding each push to four decimals may leave the sum a hair off the trait.
  assert.doesNotThrow(() => TN.validate({ ...me, pushes: [[0.6105, 0.09], [0, 1], [null, null], [0.375]] }, data));
  assert.doesNotThrow(() => TN.validate(them, data));
  // A habit is only ever pushed up, even when its pushes still add up.
  const habit = { ...data, traits: [...traits.slice(0, 3), { ...traits[3], signals: ['sport_visits', 'dessert_share'] }] };
  assert.doesNotThrow(() => TN.validate({ ...me, pushes: [[0.61, 0.09], [0, 1], [null, null], [0.3, 0.075]] }, habit));
  assert.throws(() => TN.validate({ ...me, pushes: [[0.61, 0.09], [0, 1], [null, null], [0.475, -0.1]] }, habit), /品味資料不正確/);
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/trait-network.test.cjs`
Expected: FAIL，`Missing expected exception: a push past the end`

- [ ] **Step 3: Tighten `validate`**

在 `src/web/trait-network.js` 把

```js
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
```

換成

```js
    const { vector, pushes, signals } = person;
    if (!Array.isArray(vector) || vector.length !== data.traits.length) fail();
    if (!Array.isArray(pushes) || pushes.length !== data.traits.length) fail();
    if (!Array.isArray(signals) || signals.length !== data.signals.length) fail();
    signals.forEach(value => { if (value !== null && (!finite(value) || value < 0 || value > 1e6)) fail(); });
    const order = new Map(data.signals.map((signal, index) => [signal.id, index]));
    data.traits.forEach((trait, index) => {
      const value = vector[index], list = pushes[index], low = trait.kind === 'level' ? 0 : -1;
      if (value !== null && (!finite(value) || value < low || value > 1)) fail();
      if (!Array.isArray(list) || list.length !== trait.signals.length) fail();
      list.forEach((push, slot) => {
        if (push === null) return;
        if (!finite(push) || push < low || push > 1) fail();
        // A trait without data pushes nothing, and neither does a signal that was not measured.
        if (value === null || signals[order.get(trait.signals[slot])] === null) fail();
      });
      // The lines must add up to the trait they draw, give or take the rounding of each push.
      if (value !== null && Math.abs(list.reduce((sum, push) => sum + (push ?? 0), 0) - value) > 0.001) fail();
    });
    return { vector: [...vector], pushes: pushes.map(list => [...list]), signals: [...signals] };
```

- [ ] **Step 4: Run the tests**

Run: `node --test tests/trait-network.test.cjs`
Expected: 16 tests pass

- [ ] **Step 5: Rebuild and run every Node test**

Run: `python scripts/build_report.py && node --test tests/*.test.cjs`
Expected: 三行輸出同「試做結果」；60 tests pass（煙霧測試證明 40 位虛構用戶與朋友的真實資料都過得了新規則）。

- [ ] **Step 6: Commit**

```bash
git add src/web/trait-network.js tests/trait-network.test.cjs invoice-insights.html
git commit -m "feat: refuse taste data whose pushes, sums or signals cannot be right" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: 每個訊號背後的消費（`measure` 的 `purchases`）

這個任務只在 Python 多記一份資料，報告內容不變。

**Files:**
- Modify: `src/receipt/signals.py`
- Test: `tests/test_traits.py`

**Interfaces:**
- Produces: `signals.measure(rows, period, context)` 多回傳 `"purchases": {訊號 id: [line, …]}`，46 個訊號都有鍵；line 是 `gather` 產生的明細（有 `name`、`channel`、`category`、`merchant`、`invoice`、`date` 等），只在 Python 裡用。訊號值是 `None` 時清單為空；`away_share`、`shop_focus`、`new_shop_share`、`holiday_trip_share` 一律是空清單。
- Produces: `signals.quick_habit_meals(meals, off)`、`signals.bill_species(invoice)`（從原本的 `weekday_quick_share`、`pet_signals` 抽出來，行為不變）。

- [ ] **Step 1: Write the failing tests**

在 `tests/test_traits.py` 把

```python
from src.receipt.signals import calendar_days, category_counts
```

換成

```python
from src.receipt.signals import calendar_days, category_counts, measure
```

並在 `class CategoryCountTests(unittest.TestCase):` 之前加上：

```python
class PurchaseTests(unittest.TestCase):
    def test_each_signal_keeps_the_purchases_it_counted(self):
        rows = bought(lunches(),
                      (WORKDAYS[20:23], "測試鮪魚飯糰", 0, 45, "示範超商", HOME),
                      (WORKDAYS[23:25], "測試全糖紅茶", 1, 40, "測試飲料店", HOME),
                      (WORKDAYS[25:27], "測試精品手沖", 1, 180, "測試咖啡館", HOME),
                      (sorted(OFF)[:2], "測試燒肉套餐", 0, 600, "測試海港餐廳", AWAY))
        purchases = measure(rows, PERIOD, CONTEXT)["purchases"]

        def names(key):
            return {line["name"] for line in purchases[key]}

        self.assertEqual(set(purchases), set(signal_ids(CONTEXT["traits"])))
        self.assertEqual(names("sugar_mean"), {"測試全糖紅茶"})
        self.assertEqual(names("premium_drink_share"), {"測試精品手沖"})
        self.assertEqual(names("store_meal_share"), {"測試鮪魚飯糰"})
        self.assertEqual(names("weekday_quick_share"), {"測試鮪魚飯糰"})
        self.assertEqual(names("shop_meal_share"), {"測試排骨便當", "測試燒肉套餐"})
        self.assertEqual(names("offday_invoice_share"), {"測試燒肉套餐"})
        self.assertIn("測試排骨便當", names("repeat_rate"))
        # Where someone shopped is never a list of purchases.
        for key in ("away_share", "shop_focus", "new_shop_share", "holiday_trip_share"):
            self.assertEqual(purchases[key], [], key)

    def test_a_signal_that_cannot_be_measured_keeps_no_purchases(self):
        measured = measure(bought(lunches()), PERIOD, CONTEXT)
        self.assertIsNone(measured["signals"]["sugar_mean"])
        self.assertEqual(measured["purchases"]["sugar_mean"], [])
        self.assertEqual(len(measured["purchases"]["ready_meal_share"]), 20)


```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_traits`
Expected: 2 errors，`KeyError: 'purchases'`

- [ ] **Step 3: Pull out two helpers**

在 `src/receipt/signals.py` 把

```python
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
```

換成

```python
def quick_habit_meals(meals, off):
    """Workday quick meals whose name was bought on at least three different workdays."""
    workday_meals = [item for item in meals if item["date"] not in off]
    dates = {}
    for item in workday_meals:
        if item["quick"]:
            dates.setdefault(fold(item["name"]), set()).add(item["date"])
    habits = {name for name, seen in dates.items() if len(seen) >= 3}
    return [item for item in workday_meals if item["quick"] and fold(item["name"]) in habits]


def weekday_quick_share(meals, off):
    """Workdays with a quick meal that was bought on at least three different workdays, over workdays with a meal."""
    workdays = {item["date"] for item in meals if item["date"] not in off}
    return share(len({item["date"] for item in quick_habit_meals(meals, off)}), len(workdays))


def bill_species(invoice):
    """The one species a pet-shop bill's pet items name, or None when they name neither or both."""
    known = {line["species"] for line in invoice["lines"] if line["species"] and (line["pet_food"] or line["pet_supply"])}
    return known.pop() if len(known) == 1 else None
```

再把 `pet_signals` 裡的

```python
            known = {line["species"] for line in invoice["lines"] if line["species"] and (line["pet_food"] or line["pet_supply"])}
            for species, part in SPLIT[known.pop() if len(known) == 1 else None]:
```

換成

```python
            for species, part in SPLIT[bill_species(invoice)]:
```

- [ ] **Step 4: Keep the purchases behind each signal**

在 `measure` 裡把

```python
        "alcohol_items": count(items, lambda item: item["alcohol"]) / months,
        "bar_visits": visits("酒吧"),
    }
    counts = {
```

換成

```python
        "alcohol_items": count(items, lambda item: item["alcohol"]) / months,
        "bar_visits": visits("酒吧"),
    }
    # The purchases each signal counted, so the page can name them. Signals about where someone shopped list none.
    portioned = {key for key, invoice in invoices.items() if invoice["portions"] and invoice["food"] > 0}
    monthly = Counter((item["date"].year, item["date"].month, fold(item["name"])) for item in items)
    off_bills = {key for key, invoice in invoices.items() if invoice["total"] > 0 and invoice["date"] in off}
    pet_bills = {key: bill_species(invoice) for key, invoice in invoices.items()
                 if invoice["total"] > 0 and invoice["channel"] == "寵物"}
    other = {"cat": "dog", "dog": "cat"}

    def flagged(flag):
        return [item for item in items if item[flag]]

    def at(channel):
        return [item for item in items if item["channel"] == channel]

    behind = {
        "meal_cost": [item for item in meals if item["invoice"] in portioned],
        "clearance_share": [item for item in food if item["clearance"]],
        "premium_drink_share": [item for item in drinks if item["amount"] / max(item["quantity"], 1) >= 100],
        "store_meal_share": [item for item in meals if item["channel"] == "超商"],
        "weekday_quick_share": quick_habit_meals(meals, off),
        "store_clearance_share": [item for item in store_food if item["clearance"]],
        "shop_meal_share": [item for item in meals if item["channel"] not in NOT_SHOP_MEALS],
        "fresh_share": [item for item in food if item["cooking"]],
        "ready_meal_share": meals,
        "kitchen_per_month": flagged("kitchen"),
        "sugar_mean": [item for item in drinks if item["sugar"] is not None],
        "dessert_share": [item for item in food if item["category"] == DESSERT],
        "repeat_rate": [item for item in items if monthly[(item["date"].year, item["date"].month, fold(item["name"]))] > 1],
        "sport_visits": [item for item in items if item["category"] == SPORT],
        "sport_supplies": flagged("sport_supply"), "sport_gear": flagged("sport_gear"),
        "fuel_visits": at("加油"), "parking_visits": at("停車"), "car_care": flagged("car_care"),
        "stays": at("住宿"), "long_trips": at("長途交通"),
        "convenience_share": [item for item in daily if invoices[item["invoice"]]["channel"] == "超商"],
        "bulk_share": [item for item in daily if item["bulk"]],
        "small_daily_visits": [item for item in daily if daily_spend[item["invoice"]] < 150],
        "home_items": flagged("home"), "stationery_items": flagged("stationery"), "select_visits": at("選物"),
        "tech_items": tech, "tech_spend": tech, "tech_visits": at("3C"),
        "offday_invoice_share": [item for item in items if item["invoice"] in off_bills],
        "offday_amount_share": [item for item in items if item["invoice"] in off_bills],
        "fun_visits": flagged("fun"), "fun_kinds": flagged("fun"),
        **{f"pet_{kind}_{species}": [item for item in items if item[f"pet_{kind}"] and item["species"] != other[species]]
           for species in ("cat", "dog") for kind in ("food", "supply")},
        **{f"pet_visits_{species}": [item for item in items if item["invoice"] in pet_bills
                                     and pet_bills[item["invoice"]] != other[species]] for species in ("cat", "dog")},
        "alcohol_items": flagged("alcohol"), "bar_visits": at("酒吧"),
    }
    purchases = {key: behind.get(key, []) if value is not None else [] for key, value in signals.items()}
    counts = {
```

最後把

```python
    return {"signals": signals, "counts": counts, "constants": constants}
```

換成

```python
    return {"signals": signals, "counts": counts, "constants": constants, "purchases": purchases}
```

- [ ] **Step 5: Run the tests**

Run: `python -m unittest tests.test_traits`
Expected: 27 tests OK

Run: `python -m unittest discover -s tests`
Expected: 63 tests OK

- [ ] **Step 6: The report does not change**

Run: `python scripts/build_report.py && git status --short`
Expected: 三行輸出同「試做結果」；`git status` 只列出 `src/receipt/signals.py`、`tests/test_traits.py` 與未追蹤的 `report-data.js`。

- [ ] **Step 7: Commit**

```bash
git add src/receipt/signals.py tests/test_traits.py
git commit -m "feat: keep the purchases behind each signal" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: 品名規則與品項清單（`items.py`）

把每個訊號背後的消費整理成最多 3 個品項，名稱照規格 §1 的品名規則寫，看不出在哪裡買。報告內容仍不變（Task 5 才嵌入）。

**Files:**
- Create: `src/receipt/items.py`
- Create: `tests/test_items.py`
- Modify: `configs/traits.json`、`configs/attributes.json`、`src/receipt/traits.py`

**Interfaces:**
- Consumes: Task 3 的 `measure(...)["purchases"]`。
- Produces: `items.place_words(rows, context) -> list[str]`（長的在前）；`items.label(line, words, context) -> str`（line 要有 `name`、`channel`、`category`、`merchant`）；`items.listed(purchases, rows, context) -> {訊號 id: [[名稱, 發票數], …] 或 None}`；`traits.explain(...)` 的結果多一個 `"items"`（就是 `listed` 的字典）；`traits.load_context(root)` 多一個 `"report"`（`configs/report.json`）。

- [ ] **Step 1: Write the failing tests**

新增 `tests/test_items.py`：

```python
"""How each signal names its purchases: three at most, and never in a way that tells where someone shopped."""
import unittest
from pathlib import Path

from src.receipt.items import label, listed, place_words
from src.receipt.signals import calendar_days, measure
from src.receipt.traits import explain, load_context, signal_ids

ROOT = Path(__file__).resolve().parents[1]
CONTEXT = load_context(ROOT)
PERIOD = [(2026, 3), (2026, 4)]
DAYS, OFF, _ = calendar_days(PERIOD, CONTEXT["calendar"])
WORKDAYS = [day for day in DAYS if day not in OFF]
HOME = "高雄市苓雅區"
PLACE_SIGNALS = {"away_share", "shop_focus", "new_shop_share", "holiday_trip_share"}


def bought(*groups):
    """Rows from (days, name, category, amount, merchant, district) groups; every purchase is its own invoice."""
    rows = []
    for days, name, category, amount, merchant, district in groups:
        for day in days:
            rows.append({"date": day, "day": day.day, "invoice": f"T{len(rows):03}", "merchant": merchant,
                         "district": district, "name": name, "quantity": 1, "amount": amount, "category": category,
                         "provisional": False})
    return rows


class LabelTests(unittest.TestCase):
    WORDS = place_words([{"district": HOME}, {"district": "新竹縣竹北市"}, {"district": None}], CONTEXT)

    def name(self, name, channel="一般店家", category=0, merchant="測試商店"):
        return label({"name": name, "channel": channel, "category": category, "merchant": merchant}, self.WORDS, CONTEXT)

    def test_a_hotel_is_only_a_hotel_stay(self):
        self.assertEqual(self.name("示範旅店雙人房", channel="住宿", category=7), "旅館住宿")
        self.assertEqual(self.name("墾丁測試飯店 豪華客房", channel="住宿", category=7), "旅館住宿")

    def test_a_long_trip_names_its_kind_of_ticket_and_never_a_station(self):
        cases = [("高鐵 左營-台北 標準車廂", "台灣高鐵", "高鐵票"), ("自強號 高雄→台中", "臺鐵", "臺鐵票"),
                 ("台北-基隆", "測試客運", "客運票"), ("TPE-KHH 經濟艙", "測試航空", "機票"),
                 ("示範高鐵車票", "示範高鐵", "高鐵票"), ("租車一日", "測試交通", "長途交通票")]
        for name, merchant, expected in cases:
            self.assertEqual(self.name(name, channel="長途交通", category=6, merchant=merchant), expected, name)

    def test_other_names_lose_only_their_place_names(self):
        self.assertEqual(self.name("台中油飯"), "油飯")
        self.assertEqual(self.name("臺南擔仔麵"), "擔仔麵")
        self.assertEqual(self.name("金門高粱", category=1), "高粱")
        self.assertEqual(self.name("苓雅區限定便當"), "限定便當")
        self.assertEqual(self.name("竹北肉圓"), "肉圓")
        self.assertEqual(self.name("淡水阿給"), "阿給")
        self.assertEqual(self.name("高雄市 - 鹽酥雞"), "鹽酥雞")

    def test_a_name_that_was_only_a_place_reads_as_its_category(self):
        self.assertEqual(self.name("台中"), "正餐")
        self.assertEqual(self.name("高雄 123", category=8), "日用品")

    def test_chains_stay_and_the_demo_mark_goes(self):
        self.assertEqual(self.name("星巴克那堤", category=1), "星巴克那堤")
        self.assertEqual(self.name("示範半糖冬瓜青茶", category=1), "半糖冬瓜青茶")

    def test_a_long_name_is_cut_at_twenty_letters(self):
        self.assertEqual(self.name("測" * 20), "測" * 20)
        self.assertEqual(self.name("測" * 25), "測" * 19 + "…")

    def test_place_words_cover_cities_counties_county_cities_and_the_persons_own_districts(self):
        words = place_words([{"district": HOME}, {"district": "新竹市東區"}], CONTEXT)
        for word in ("臺北市", "臺北", "新竹縣", "竹北市", "竹北", "苓雅區", "苓雅", "東區", "淡水"):
            self.assertIn(word, words)
        # A one-letter district name would cut far too much from ordinary names.
        self.assertNotIn("東", words)
        self.assertEqual(words, sorted(words, key=lambda word: (-len(word), word)))


class ListTests(unittest.TestCase):
    def test_each_signal_lists_its_three_most_bought_names_counted_by_bill(self):
        rows = bought((WORKDAYS[:8], "測試排骨便當", 0, 100, "測試便當店", HOME),
                      (WORKDAYS[8:11], "測試台中油飯", 0, 70, "測試小吃店", HOME),
                      (WORKDAYS[11:14], "測試臺南油飯", 0, 70, "測試小吃店", HOME),
                      (WORKDAYS[14:19], "測試牛肉麵", 0, 150, "測試麵館", HOME),
                      (WORKDAYS[19:24], "測試滷肉飯", 0, 60, "測試小吃店", HOME),
                      (WORKDAYS[24:26], "測試旅店雙人房", 7, 2000, "測試旅宿", "屏東縣恆春鎮"))
        # Breakfast on the same hotel bill is still one stay.
        rows.append({**rows[-1], "name": "測試早餐券", "amount": 200})
        lists = listed(measure(rows, PERIOD, CONTEXT)["purchases"], rows, CONTEXT)
        self.assertEqual(set(lists), set(signal_ids(CONTEXT["traits"])))
        # Two dishes that differ only by a place are one name, and ties go by name.
        self.assertEqual(lists["shop_meal_share"], [["測試排骨便當", 8], ["測試油飯", 6], ["測試滷肉飯", 5]])
        self.assertEqual(lists["stays"], [["旅館住宿", 2]])
        self.assertEqual(lists["sugar_mean"], [])
        for key in PLACE_SIGNALS:
            self.assertIsNone(lists[key], key)

    def test_explain_hands_the_lists_on(self):
        rows = bought((WORKDAYS[:24], "測試鮪魚飯糰", 0, 45, "示範超商", HOME))
        person = explain(rows, PERIOD, CONTEXT)
        # weekday_quick_share feeds two traits and has one list for both.
        self.assertEqual(person["items"]["weekday_quick_share"], [["測試鮪魚飯糰", 24]])
        self.assertEqual(person["items"]["store_meal_share"], [["測試鮪魚飯糰", 24]])
        self.assertIsNone(person["items"]["away_share"])


class ConfigTests(unittest.TestCase):
    def test_only_the_four_place_signals_hide_their_purchases(self):
        flags = {}
        for trait in CONTEXT["traits"]["traits"]:
            for signal in trait["signals"]:
                flags.setdefault(signal["id"], set()).add(signal.get("list_items", True))
        self.assertEqual({key for key, seen in flags.items() if False in seen}, PLACE_SIGNALS)
        # A signal shared by two traits says the same in both.
        self.assertTrue(all(len(seen) == 1 for seen in flags.values()))

    def test_the_item_words_are_configured(self):
        vocabulary = CONTEXT["vocabulary"]
        self.assertEqual([kind for kind, _ in vocabulary["transport_kinds"]], ["高鐵票", "臺鐵票", "客運票", "機票"])
        self.assertEqual(vocabulary["generic_labels"], {"住宿": "旅館住宿", "長途交通": "長途交通票"})
        self.assertIn("淡水", vocabulary["place_words"])
        self.assertEqual(CONTEXT["report"]["categories"][0]["name"], "正餐")


if __name__ == "__main__":
    unittest.main()
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_items`
Expected: 1 error，`ModuleNotFoundError: No module named 'src.receipt.items'`

- [ ] **Step 3: Write `items.py`**

新增 `src/receipt/items.py`（內含反斜線，用 Write 工具）：

```python
"""What each signal shows as its purchases: three names at most, written so they never tell where someone shopped."""
import re

from .address import COUNTIES, COUNTY_CITIES, MUNICIPALITIES
from .attributes import has

LONGEST = 20  # letters a name keeps; a longer one is cut and ends with …
TOP = 3       # purchases listed per signal


def place_words(rows, context):
    """Place names a purchase name may carry, longest first so 臺中市 goes before 臺中: cities and counties,
    county-administered cities, the person's own districts with and without 區, 鄉, 鎮 or 市, and the listed words."""
    words = set(context["vocabulary"]["place_words"])
    for city in (*MUNICIPALITIES, *COUNTIES, *COUNTY_CITIES):
        words.update((city, city[:-1]))
    for row in rows:
        local = (row.get("district") or "")[3:]
        if local:
            words.add(local)
            # A one-letter name such as 東 would cut far too much from ordinary names.
            if len(local) > 2:
                words.add(local[:-1])
    return sorted(words, key=lambda word: (-len(word), word))


def without_places(name, words):
    """The name with every place name taken out, reading 台 and 臺 alike."""
    for word in words:
        name = re.sub(re.escape(word.replace("台", "臺")).replace("臺", "[台臺]"), "", name)
    return name


def label(line, words, context):
    """How one purchase reads on the page: a hotel stay or a kind of ticket, or the name without its places."""
    vocabulary = context["vocabulary"]
    if line["channel"] == "住宿":
        return vocabulary["generic_labels"]["住宿"]
    if line["channel"] == "長途交通":
        text = line["name"] + line["merchant"]
        return next((kind for kind, keywords in vocabulary["transport_kinds"] if has(text, keywords)),
                    vocabulary["generic_labels"]["長途交通"])
    name = re.sub(r"^[\W_]+|[\W_]+$", "", without_places(line["name"].removeprefix("示範"), words))
    # Nothing but a place, digits or marks left: say what kind of purchase it was instead.
    if not re.search(r"[^\W\d_]", name):
        name = context["report"]["categories"][line["category"]]["name"]
    return name if len(name) <= LONGEST else name[:LONGEST - 1] + "…"


def listed(purchases, rows, context):
    """Each signal's three most bought names as [[name, bills], …], counting the bills a name is on, most first
    and ties by name; None for the signals that never list purchases."""
    words = place_words(rows, context)
    hidden = {signal["id"] for trait in context["traits"]["traits"] for signal in trait["signals"]
              if signal.get("list_items") is False}
    lists = {}
    for key, lines in purchases.items():
        if key in hidden:
            lists[key] = None
            continue
        bills = {}
        for line in lines:
            bills.setdefault(label(line, words, context), set()).add(line["invoice"])
        ranked = sorted(bills.items(), key=lambda pair: (-len(pair[1]), pair[0]))
        lists[key] = [[name, len(seen)] for name, seen in ranked[:TOP]]
    return lists
```

- [ ] **Step 4: Configure the item words**

在 `configs/traits.json` 把這四行各自加上 `, "list_items": false`：

```json
       {"id": "shop_focus", "weight": 0.3, "scale": [0.8, 0.55, 0.3], "label": "常去店家", "unit": "share"},
       {"id": "new_shop_share", "weight": 0.3, "scale": [0.2, 0.4, 0.6], "label": "新店家", "unit": "share"}
       {"id": "away_share", "weight": 0.5, "scale": [0, 0.1, 0.3], "label": "外地消費", "unit": "share"},
       {"id": "holiday_trip_share", "weight": 1, "scale": [0, "long_holiday_share", 1], "label": "連假出遊", "unit": "share"}
```

改完是：

```json
       {"id": "shop_focus", "weight": 0.3, "scale": [0.8, 0.55, 0.3], "label": "常去店家", "unit": "share", "list_items": false},
       {"id": "new_shop_share", "weight": 0.3, "scale": [0.2, 0.4, 0.6], "label": "新店家", "unit": "share", "list_items": false}
       {"id": "away_share", "weight": 0.5, "scale": [0, 0.1, 0.3], "label": "外地消費", "unit": "share", "list_items": false},
       {"id": "holiday_trip_share", "weight": 1, "scale": [0, "long_holiday_share", 1], "label": "連假出遊", "unit": "share", "list_items": false}
```

（這四行在檔案裡不相鄰，逐行改；每行最後的逗號照原樣保留。）

在 `configs/attributes.json` 把最後一個鍵

```json
  "not_alcohol": ["米酒", "料理酒", "酒釀"]
```

換成

```json
  "not_alcohol": ["米酒", "料理酒", "酒釀"],
  "transport_kinds": [["高鐵票", ["高鐵"]], ["臺鐵票", ["臺鐵", "自強", "莒光", "區間"]], ["客運票", ["客運", "巴士"]], ["機票", ["航空", "機票", "航班"]]],
  "generic_labels": {"住宿": "旅館住宿", "長途交通": "長途交通票"},
  "place_words": ["淡水", "九份", "北投", "深坑", "大溪", "三峽", "鶯歌", "礁溪", "鹿港", "日月潭", "埔里", "阿里山", "新港", "關廟", "麻豆", "玉井", "安平", "旗津", "萬巒", "墾丁", "太魯閣", "池上", "關山"]
```

- [ ] **Step 5: Hand the lists on from `explain`**

在 `src/receipt/traits.py`：

把

```python
from .signals import measure
```

換成

```python
from .items import listed
from .signals import measure
```

把

```python
CONFIGS = (("brands", "brands.json"), ("vocabulary", "attributes.json"), ("traits", "traits.json"), ("calendar", "calendar-2026.json"))
```

換成

```python
CONFIGS = (("brands", "brands.json"), ("vocabulary", "attributes.json"), ("traits", "traits.json"), ("calendar", "calendar-2026.json"),
           ("report", "report.json"))
```

把 `explain` 的

```python
    """One person's taste: the vector, each signal's push on each trait, and the measured signals.
```

換成

```python
    """One person's taste: the vector, each signal's push on each trait, the measured signals and the
    purchases each signal lists.
```

並把它最後的

```python
            "signals": measured["signals"]}
```

換成

```python
            "signals": measured["signals"], "items": listed(measured["purchases"], rows, context)}
```

- [ ] **Step 6: Run the tests**

Run: `python -m unittest tests.test_items -v`
Expected: 11 tests OK

Run: `python -m unittest discover -s tests`
Expected: 74 tests OK

- [ ] **Step 7: The report does not change yet**

Run: `python scripts/build_report.py && git status --short`
Expected: 三行輸出同「試做結果」；`invoice-insights.html` 沒有出現在 `git status`。

- [ ] **Step 8: Commit**

```bash
git add src/receipt/items.py src/receipt/traits.py configs/traits.json configs/attributes.json tests/test_items.py
git commit -m "feat: name the purchases behind each signal without telling where they were bought" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: 品項清單嵌入三個頁面

**Files:**
- Modify: `src/receipt/build.py`
- Modify: `src/web/invoice-insights.html`
- Test: `tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 4 的 `explain(...)["items"]`、`load_context(...)["report"]`。
- Produces（網頁拿到的資料）：
  - 每個人的繪圖資料多 `items`：依 `signal_ids` 排成 46 格的陣列，每格 `null`（不列品項的訊號）或 `[[名稱, 發票數], …]`；資料不足時整個是 `null`。出現在 `matchReportData.me`、`matchReportData.people[]`、`traitNetworkData.friends[名字]`。
  - `traitNetworkData.signals[i]` 對不列品項的訊號帶 `"list_items": false`。
  - 主頁新的嵌入常數 `tasteExportData = {"traitCount": 17, "taste": {vector, pushes, signals, items} 或 null}`，由 `<script src="taste-export-data.js">` 嵌入。
  - `build.taste_export_data(settings, me)`。

- [ ] **Step 1: Write the failing tests**

在 `tests/test_build_report.py`：

把

```python
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
```

換成

```python
from pathlib import Path

from src.receipt.traits import signal_ids

ROOT = Path(__file__).resolve().parents[1]
# Demo districts that must never show up inside a purchase name.
DISTRICT_WORDS = ("苓雅", "新興", "前鎮", "恆春", "信義", "內湖", "竹北", "中壢", "板橋", "左營", "東港", "宜蘭", "東區")
```

把

```python
            self.assertEqual(set(network["signals"][0]), {"id", "label", "unit"})
```

換成

```python
            self.assertEqual(set(network["signals"][0]), {"id", "label", "unit"})
            self.assertEqual([signal["id"] for signal in network["signals"] if signal.get("list_items") is False],
                             ["shop_focus", "new_shop_share", "away_share", "holiday_trip_share"])
```

把

```python
                self.assertEqual(set(friend), {"vector", "pushes", "signals"})
                self.assertEqual((len(friend["vector"]), len(friend["signals"])), (18, 46))
```

換成

```python
                self.assertEqual(set(friend), {"vector", "pushes", "signals", "items"})
                self.assertEqual((len(friend["vector"]), len(friend["signals"]), len(friend["items"])), (18, 46, 46))
```

把

```python
            self.assertEqual(set(payload["me"]), {"vector", "pushes", "signals", "months", "areas", "counts"})
            self.assertEqual(len(payload["people"]), 40)
            traits = json.loads((ROOT / "configs" / "traits.json").read_text(encoding="utf-8"))["traits"]
```

換成

```python
            self.assertEqual(set(payload["me"]), {"vector", "pushes", "signals", "items", "months", "areas", "counts"})
            self.assertEqual(len(payload["people"]), 40)
            # Every embedded list follows signal_ids(): the demo me spends NT$125 a meal and NT$780 on 3C.
            ids = signal_ids(json.loads((ROOT / "configs" / "traits.json").read_text(encoding="utf-8")))
            self.assertEqual(payload["me"]["signals"][ids.index("meal_cost")], 125)
            self.assertEqual(payload["me"]["signals"][ids.index("tech_spend")], 780)
            self.assertEqual(payload["me"]["items"][ids.index("sugar_mean")], [["半糖冬瓜青茶", 7], ["百香果茶", 7], ["花果茶", 7]])
            self.assertIsNone(payload["me"]["items"][ids.index("away_share")])
            traits = json.loads((ROOT / "configs" / "traits.json").read_text(encoding="utf-8"))["traits"]
```

把

```python
                self.assertEqual(set(person), {"name", "vector", "pushes", "signals", "distance", "place", "counts"})
                self.assertEqual((len(person["vector"]), len(person["counts"])), (18, 10))
            # Shop and item names in the demo all start with 示範; none may reach the match page's data.
            self.assertNotIn("示範", json.dumps(payload, ensure_ascii=False))
```

換成（內含反斜線，用編輯工具）

```python
                self.assertEqual(set(person), {"name", "vector", "pushes", "signals", "items", "distance", "place", "counts"})
                self.assertEqual((len(person["vector"]), len(person["counts"]), len(person["items"])), (18, 10, 46))
            # Shop and item names in the demo all start with 示範: shops never reach the page, and purchase names
            # arrive without the mark.
            self.assertNotIn("示範", json.dumps(payload, ensure_ascii=False))
            exported = json.loads(re.search(r"const tasteExportData = (.*?);\n</script>", html, re.S).group(1))
            self.assertEqual(exported["traitCount"], 17)
            self.assertEqual(set(exported["taste"]), {"vector", "pushes", "signals", "items"})
            self.assertEqual([exported["taste"][key] for key in ("vector", "pushes", "signals", "items")],
                             [payload["me"][key] for key in ("vector", "pushes", "signals", "items")])
            self.assertNotIn("示範", json.dumps(exported, ensure_ascii=False))
            names = json.dumps([exported["taste"]["items"], *(person["items"] for person in payload["people"]),
                                *(friend["items"] for friend in network["friends"].values())], ensure_ascii=False)
            for word in DISTRICT_WORDS:
                self.assertNotIn(word, names)
```

把私人版測試裡的

```python
            self.assertEqual(len(parsed.scripts), 8)
```

換成（內含反斜線，用編輯工具）

```python
            self.assertEqual(len(parsed.scripts), 9)
            exported = json.loads(re.search(r"const tasteExportData = (.*?);\r?\n</script>", html, re.S).group(1))
            self.assertEqual(exported, {"traitCount": 17, "taste": None})
```

把

```python
            self.assertEqual([payload["me"][key] for key in ("vector", "pushes", "signals")], [None, None, None])
            self.assertEqual(set(payload["me"]), {"vector", "pushes", "signals", "months", "areas", "counts"})
```

換成

```python
            self.assertEqual([payload["me"][key] for key in ("vector", "pushes", "signals", "items")], [None, None, None, None])
            self.assertEqual(set(payload["me"]), {"vector", "pushes", "signals", "items", "months", "areas", "counts"})
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `python -m unittest tests.test_build_report`
Expected: 2 failures（`list_items` 與 `items` 還不存在）

- [ ] **Step 3: Embed the lists**

在 `src/receipt/build.py`：

把

```python
def drawing_of(explained, order):
    """What the network graph draws for one person: each signal's push on each trait, and the measured signals
    listed in signal_ids() order so their names are not repeated for everyone."""
    if explained is None:
        return {"pushes": None, "signals": None}
    return {"pushes": rounded(explained["pushes"]), "signals": [rounded(explained["signals"][key]) for key in order]}
```

換成

```python
def drawing_of(explained, order):
    """What the network graph draws for one person: each signal's push on each trait, then the measured signals
    and the purchases each signal lists, both in signal_ids() order so their names are not repeated for everyone."""
    if explained is None:
        return {"pushes": None, "signals": None, "items": None}
    return {"pushes": rounded(explained["pushes"]), "signals": [rounded(explained["signals"][key]) for key in order],
            "items": [explained["items"][key] for key in order]}
```

在 `trait_network_data` 把

```python
        for signal in trait["signals"]:
            labels.setdefault(signal["id"], {"id": signal["id"], "label": signal["label"], "unit": signal["unit"]})
```

換成

```python
        for signal in trait["signals"]:
            words = {"id": signal["id"], "label": signal["label"], "unit": signal["unit"]}
            # Signals about where someone shopped say so, and never carry a list of purchases.
            if signal.get("list_items") is False:
                words["list_items"] = False
            labels.setdefault(signal["id"], words)
```

在 `def taste_summary(me, people, tastes, context):` 之前加上：

```python
def taste_export_data(settings, me):
    """What the export button puts into a taste link: how many traits the pages talk about (cats and dogs are one),
    and my taste with its pushes, signals and purchase lists, or None when I have too little data."""
    count = len({trait.get("group", trait["id"]) for trait in settings["traits"]})
    return {"traitCount": count,
            "taste": None if me is None else {"vector": me["vector"], **drawing_of(me, signal_ids(settings))}}


```

在 `main()`：「我」的品味要在主頁的程式嵌入之前算好。把

```python
    data = {"isDemo": not args.private, "categories": config["categories"], "months": months}
    data_script = script_constant("expenseReportData", data)
    scripts = {"report-data.js": data_script}
```

換成

```python
    data = {"isDemo": not args.private, "categories": config["categories"], "months": months}
    context = load_context(ROOT)
    rows, period = dated(months)
    me = explain(rows, period, context)
    data_script = script_constant("expenseReportData", data)
    scripts = {"report-data.js": data_script,
               "taste-export-data.js": script_constant("tasteExportData", taste_export_data(context["traits"], me))}
```

把

```python
    html = embed_scripts(template.replace(style_link, "<style>" + stylesheet + "</style>", 1), scripts)
    context = load_context(ROOT)
    people = build_personas(context["calendar"])
```

換成

```python
    html = embed_scripts(template.replace(style_link, "<style>" + stylesheet + "</style>", 1), scripts)
    people = build_personas(context["calendar"])
```

把

```python
    html = embed_page(html, "taste-page-source", comparison)
    rows, period = dated(months)
    me = explain(rows, period, context)
    matches = build_matches(
```

換成

```python
    html = embed_page(html, "taste-page-source", comparison)
    matches = build_matches(
```

在 `src/web/invoice-insights.html` 把

```html
<script src="taste-profile.js"></script>
<script src="taste-export.js"></script>
```

換成

```html
<script src="taste-profile.js"></script>
<script src="taste-export-data.js"></script>
<script src="taste-export.js"></script>
```

- [ ] **Step 4: Run the tests**

Run: `python -m unittest tests.test_build_report`
Expected: 2 tests OK

- [ ] **Step 5: Rebuild and run everything**

Run: `python scripts/build_report.py && python -m unittest discover -s tests && node --test tests/*.test.cjs`
Expected: 三行輸出同「試做結果」；74 tests OK；60 tests pass

- [ ] **Step 6: Commit**

```bash
git add src/receipt/build.py src/web/invoice-insights.html tests/test_build_report.py invoice-insights.html
git commit -m "feat: embed everyone's purchase lists and my taste for the export button" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: 檢查品項、配對卡片交出品項

`validate` 多檢查品項（規格 §3）：長度等於訊號數；不列品項的訊號必須是 `null`；其他訊號最多 3 筆 `[名稱, 次數]`，名稱去掉頭尾空白後 1～20 字、不含控制字元、同一個訊號裡不重複，次數是 1～10,000 的整數。配對卡片把品項交給連線頁；示範朋友的檢查包 try/catch。Task 1 的煙霧測試從配對頁拿資料，所以配對頁漏傳品項時它會失敗。

**Files:**
- Modify: `src/web/trait-network.js`（`validate`）
- Modify: `src/web/match.html`、`src/web/taste-comparison.html`
- Test: `tests/trait-network.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 5 的 `items` 與 `signals[i].list_items`。
- Produces: `TraitNetwork.validate(person, data) -> { vector, pushes, signals, items }`，`items` 的名稱已去掉頭尾空白；沒有 `items` 的資料一律拒收。配對卡片交給連線頁的 `pair.left.traits`、`pair.right.traits` 多 `items`。

- [ ] **Step 1: Write the failing tests**

在 `tests/trait-network.test.cjs` 把

```js
const me = { vector: [0.7, 1, null, 0.375], pushes: [[0.61, 0.09], [0, 1], [null, null], [0.375]], signals: [0.8333, 0.1429, 0, 1, null, 5] };
const them = { vector: [0.94, 0.82, 0.5, 0.2], pushes: [[0.8, 0.14], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, 0.2, 0.36, 1, 0.1, 2] };
```

換成

```js
const me = { vector: [0.7, 1, null, 0.375], pushes: [[0.61, 0.09], [0, 1], [null, null], [0.375]], signals: [0.8333, 0.1429, 0, 1, null, 5],
  items: [[['半糖冬瓜青茶', 7], ['百香果茶', 7], ['花果茶', 7]], [['燕麥餅', 4]], [], [['蔬食餐盒', 5]], [], [['體適能體驗票', 10]]] };
const them = { vector: [0.94, 0.82, 0.5, 0.2], pushes: [[0.8, 0.14], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, 0.2, 0.36, 1, 0.1, 2],
  items: [[['冬瓜青茶', 10], ['黑糖珍珠鮮奶', 8]], [['肉桂捲', 6]], [['鮪魚飯糰', 9]], [['石鍋拌飯', 5]], [['即期便當', 2]], [['體適能體驗票', 4]]] };
```

在 Task 2 加的測試（最後一行是 `  assert.throws(() => TN.validate({ ...me, pushes: [[0.61, 0.09], [0, 1], [null, null], [0.475, -0.1]] }, habit), /品味資料不正確/);` 接 `});`）後面加上（內含反斜線，用編輯工具）：

```js

test('validate checks every list of purchases, and a signal about places never carries one', () => {
  // Pretend 超商即期 is about where someone shops, like 常去店家.
  const placed = { ...data, signals: data.signals.map(signal => (signal.id === 'clearance' ? { ...signal, list_items: false } : signal)) };
  const listed = { ...me, items: [[[' 半糖冬瓜青茶 ', 7], ['百香果茶', 7], ['測'.repeat(20), 1]], [], [], [['蔬食餐盒', 5]], null, [['體適能體驗票', 10]]] };
  assert.deepEqual(TN.validate(listed, placed).items, [[['半糖冬瓜青茶', 7], ['百香果茶', 7], ['測'.repeat(20), 1]], [], [], [['蔬食餐盒', 5]], null, [['體適能體驗票', 10]]]);
  const first = list => ({ ...listed, items: [list, ...listed.items.slice(1)] });
  const broken = {
    'no lists at all': { ...listed, items: undefined },
    'a missing list': { ...listed, items: listed.items.slice(1) },
    'a list for a signal about places': { ...listed, items: [...listed.items.slice(0, 4), [['測試店', 1]], listed.items[5]] },
    'no list for a signal that has one': first(null),
    'four purchases': first([['甲', 1], ['乙', 1], ['丙', 1], ['丁', 1]]),
    'a name of 21 letters': first([['測'.repeat(21), 1]]),
    'a blank name': first([['  ', 1]]),
    'a control character': first([['紅茶\u0007', 1]]),
    'a name that is not text': first([[7, 1]]),
    'a count of zero': first([['紅茶', 0]]),
    'a fractional count': first([['紅茶', 1.5]]),
    'too many bills': first([['紅茶', 10001]]),
    'the same name twice': first([['紅茶', 2], [' 紅茶', 1]]),
    'a purchase that is not a pair': first([['紅茶', 2, 3]]),
  };
  for (const [name, person] of Object.entries(broken)) assert.throws(() => TN.validate(person, placed), /品味資料不正確/, name);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/trait-network.test.cjs`
Expected: 2 failures：`validate keeps well-formed taste data and refuses anything else`（副本少了 `items`）與新的測試

- [ ] **Step 3: Check the purchases**

在 `src/web/trait-network.js` 的 `validate`：把

```js
    const { vector, pushes, signals } = person;
```

換成

```js
    const { vector, pushes, signals, items } = person;
```

把

```js
      if (value !== null && Math.abs(list.reduce((sum, push) => sum + (push ?? 0), 0) - value) > 0.001) fail();
    });
    return { vector: [...vector], pushes: pushes.map(list => [...list]), signals: [...signals] };
```

換成（內含反斜線，用編輯工具）

```js
      if (value !== null && Math.abs(list.reduce((sum, push) => sum + (push ?? 0), 0) - value) > 0.001) fail();
    });
    // Up to three purchases per signal, each a short name and the bills it is on; signals about places list none.
    if (!Array.isArray(items) || items.length !== data.signals.length) fail();
    const lists = items.map((list, index) => {
      if (data.signals[index].list_items === false) return list === null ? null : fail();
      if (!Array.isArray(list) || list.length > 3) fail();
      const seen = new Set();
      return list.map(entry => {
        if (!Array.isArray(entry) || entry.length !== 2) fail();
        const [name, count] = entry;
        if (typeof name !== 'string' || /[\u0000-\u001f\u007f]/.test(name)) fail();
        const trimmed = name.trim(), letters = Array.from(trimmed).length;
        if (letters < 1 || letters > 20 || seen.has(trimmed)) fail();
        if (!Number.isSafeInteger(count) || count < 1 || count > 10000) fail();
        seen.add(trimmed);
        return [trimmed, count];
      });
    });
    return { vector: [...vector], pushes: pushes.map(list => [...list]), signals: [...signals], items: lists };
```

- [ ] **Step 4: Run the tests**

Run: `node --test tests/trait-network.test.cjs`
Expected: 17 tests pass

- [ ] **Step 5: Hand the purchases on**

在 `src/web/match.html` 把

```js
  const taste = person => ({ vector: person.vector, pushes: person.pushes, signals: person.signals });
```

換成

```js
  const taste = person => ({ vector: person.vector, pushes: person.pushes, signals: person.signals, items: person.items });
```

在 `src/web/taste-comparison.html` 把

```js
 person.traits=network&&network.friends[person.name]?TraitNetwork.validate(network.friends[person.name],network):null;
}
```

換成

```js
 // A friend whose embedded data fails the check only loses the taste graph; the rest of the page still works.
 try{person.traits=network&&network.friends[person.name]?TraitNetwork.validate(network.friends[person.name],network):null;}catch{person.traits=null;}
}
```

- [ ] **Step 6: Rebuild and run every Node test**

Run: `python scripts/build_report.py && node --test tests/*.test.cjs`
Expected: 61 tests pass（煙霧測試的大字仍是 +71、+80）

- [ ] **Step 7: Commit**

```bash
git add src/web/trait-network.js src/web/match.html src/web/taste-comparison.html tests/trait-network.test.cjs invoice-insights.html
git commit -m "feat: check every purchase list and hand it from the match card to the graph" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: 外圈小點

點一個訊號時，兩側同一個訊號外面各長出一小排品項點（與規格不同的地方第 1、2 點）：桌機排在訊號外側（左團往左、右團往右），每列間隔 20，名稱在點的外側；手機排在上下兩團外面的空白帶，每列間隔 26，名稱在點的右邊。最常買的在最上面、點最大、連到訊號的線最粗。圖的 `viewBox` 一開始就留好所有訊號可能長出的品項，點選時不縮放；桌機只往左右加寬，手機只往上下加高。說明列在訊號值後面寫出品項；不列品項的訊號寫「（這個訊號不列品項）」。

**Files:**
- Modify: `src/web/trait-network.js`
- Modify: `src/web/taste-comparison.html`
- Test: `tests/trait-network.test.cjs`、`tests/connection-page.test.cjs`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 6 的 `validate` 結果（有 `items`）。
- Produces:
  - `TraitNetwork.shortName(name) -> string`：超過 10 個字截成 9 個字加「…」。
  - `TraitNetwork.purchases(data, graph, people, id, mobile) -> [{ side: 'a'|'b', signal: { x, y }, items: [{ name, count, text, r, width, x, y, anchor, labelX, labelY }] }]`：只列出有品項的那一側；`graph` 是 `layout(...)` 的結果，`people` 是 `[左, 右]`。
  - `TraitNetwork.viewBox(data, graph, people, mobile) -> 'left top width height'`：沒有任何品項時是 `'0 0 1200 640'`（手機 `'0 0 600 820'`）。
  - `SHAPES.desktop.item = { across: 60, step: 20, dot: [2.5, 3.5] }`、`SHAPES.mobile.item = { beyond: 30, step: 26, dot: [3, 4] }`。
  - 連線頁：品項畫在 `<g class="t-outer" aria-hidden="true">` 裡（線 `t-buy-line`、點 `t-buy`、名稱 `t-tip`）。

- [ ] **Step 1: Write the failing tests**

在 `tests/trait-network.test.cjs` 把整個測試

```js
test('a signal sentence says its value and how far it pushed each trait it feeds', () => {
  assert.equal(TN.signalSentence(data, me, '你', 'sugar_mean'), '你：飲料甜度 約 8 分糖，往「高甜度」推 0.61');
  assert.equal(TN.signalSentence(data, them, '對方', 'quick'), '對方：平日固定速食 36%，往「快速解決」推 0.18；往「為了省時」推 0.60');
  assert.equal(TN.signalSentence(data, me, '你', 'quick'), '你：平日固定速食 0%，沒有推動「快速解決 ↔ 好好吃飯」；「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, me, '你', 'clearance'), '你：超商即期，「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, them, '手搖學生 A', 'sport_visits'), '手搖學生 A：運動消費 每月 2 次，往「運動」推 0.20');
  const unmeasured = { ...them, pushes: [[0.8, null], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, null, 0.36, 1, 0.1, 2] };
  assert.equal(TN.signalSentence(data, unmeasured, '對方', 'dessert_share'), '對方：甜點，沒有紀錄');
  // A push that prints as 0.00 moved nothing.
  const faintPush = { ...them, pushes: [[0.004, 0.14], [-0.18, 1], [-0.1, 0.6], [0.2]] };
  assert.equal(TN.signalSentence(data, faintPush, '對方', 'sugar_mean'), '對方：飲料甜度 約 10 分糖，沒有推動「低甜度 ↔ 高甜度」');
});
```

換成

```js
test('a signal sentence says its value, what was bought and how far it pushed each trait it feeds', () => {
  assert.equal(TN.signalSentence(data, me, '你', 'sugar_mean'), '你：飲料甜度 約 8 分糖（半糖冬瓜青茶 ×7、百香果茶 ×7、花果茶 ×7），往「高甜度」推 0.61');
  assert.equal(TN.signalSentence(data, them, '對方', 'quick'), '對方：平日固定速食 36%（鮪魚飯糰 ×9），往「快速解決」推 0.18；往「為了省時」推 0.60');
  // Nothing bought adds nothing to the sentence.
  assert.equal(TN.signalSentence(data, me, '你', 'quick'), '你：平日固定速食 0%，沒有推動「快速解決 ↔ 好好吃飯」；「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, me, '你', 'clearance'), '你：超商即期，「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, them, '手搖學生 A', 'sport_visits'), '手搖學生 A：運動消費 每月 2 次（體適能體驗票 ×4），往「運動」推 0.20');
  const unmeasured = { ...them, pushes: [[0.8, null], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, null, 0.36, 1, 0.1, 2],
    items: [them.items[0], [], ...them.items.slice(2)] };
  assert.equal(TN.signalSentence(data, unmeasured, '對方', 'dessert_share'), '對方：甜點，沒有紀錄');
  // A push that prints as 0.00 moved nothing.
  const faintPush = { ...them, pushes: [[0.004, 0.14], [-0.18, 1], [-0.1, 0.6], [0.2]] };
  assert.equal(TN.signalSentence(data, faintPush, '對方', 'sugar_mean'), '對方：飲料甜度 約 10 分糖（冬瓜青茶 ×10、黑糖珍珠鮮奶 ×8），沒有推動「低甜度 ↔ 高甜度」');
  // A signal about places says it lists nothing on purpose.
  const placed = { ...data, signals: data.signals.map(signal => (signal.id === 'clearance' ? { ...signal, list_items: false } : signal)) };
  assert.equal(TN.signalSentence(placed, { ...them, items: [...them.items.slice(0, 4), null, them.items[5]] }, '對方', 'clearance'),
    '對方：超商即期 10%（這個訊號不列品項），往「為了省錢」推 0.10');
});

test('the purchases behind a signal stand in a short column outside it, most bought first and biggest', () => {
  const graph = TN.layout(data, me, them, false);
  const [mine, theirs] = TN.purchases(data, graph, [me, them], 'sugar_mean', false);
  assert.deepEqual([mine.side, theirs.side], ['a', 'b']);
  assert.deepEqual(mine.items.map(item => item.text), ['半糖冬瓜青茶 ×7', '百香果茶 ×7', '花果茶 ×7']);
  const signal = graph.sides[0].signals.find(entry => entry.id === 'sugar_mean');
  assert.deepEqual([mine.signal.x, mine.signal.y], [signal.x, signal.y]);
  // My column stands left of my signal with its names further left; theirs mirrors it on the right.
  assert.ok(mine.items.every(item => item.x < signal.x - 40 && item.anchor === 'end' && item.labelX < item.x));
  assert.ok(theirs.items.every(item => item.x > graph.sides[1].signals.find(entry => entry.id === 'sugar_mean').x + 40
    && item.anchor === 'start' && item.labelX > item.x));
  mine.items.slice(1).forEach((item, k) => assert.ok(item.y > mine.items[k].y));
  assert.ok(theirs.items[0].r > theirs.items[1].r && theirs.items[0].width > theirs.items[1].width);
  // Nothing bought, nothing drawn: my 超商即期 list is empty, theirs is not.
  assert.deepEqual(TN.purchases(data, graph, [me, them], 'clearance', false).map(side => side.side), ['b']);
});

test('purchase names never cover each other, on desktop or on phones, wherever the signal sits', () => {
  const crowded = { ...me, items: me.items.map(() => [['測試品名一號', 30], ['測試品名二號', 20], ['測試品名三號', 10]]) };
  for (const mobile of [false, true]) {
    const font = TN.SHAPES[mobile ? 'mobile' : 'desktop'].font, graph = TN.layout(data, crowded, crowded, mobile);
    for (const signal of data.signals) {
      for (const side of TN.purchases(data, graph, [crowded, crowded], signal.id, mobile)) {
        const rects = side.items.map(item => TN.labelRect(item.text, font, item.labelX, item.labelY, item.anchor));
        rects.forEach((rect, k) => rects.slice(k + 1).forEach(other => assert.ok(!overlap(rect, other), signal.id)));
      }
    }
  }
});

test('the view box leaves room for every purchase any signal could show, and phones only grow taller', () => {
  for (const mobile of [false, true]) {
    const font = TN.SHAPES[mobile ? 'mobile' : 'desktop'].font, graph = TN.layout(data, me, them, mobile);
    const [left, top, width, height] = TN.viewBox(data, graph, [me, them], mobile).split(' ').map(Number);
    for (const signal of data.signals) {
      for (const side of TN.purchases(data, graph, [me, them], signal.id, mobile)) {
        for (const item of side.items) {
          const box = TN.labelRect(item.text, font, item.labelX, item.labelY, item.anchor);
          assert.ok(box.left >= left && box.right <= left + width && box.top >= top && box.bottom <= top + height, signal.id);
        }
      }
    }
    if (mobile) assert.deepEqual([left, width], [0, 600]);
  }
  // Without any purchases the graph keeps its own size.
  const bare = person => ({ ...person, items: person.items.map(() => []) });
  assert.equal(TN.viewBox(data, TN.layout(data, me, them, false), [bare(me), bare(them)], false), '0 0 1200 640');
});

test('a long purchase name is cut to ten letters on the graph', () => {
  assert.equal(TN.shortName('半糖冬瓜青茶'), '半糖冬瓜青茶');
  assert.equal(TN.shortName('測'.repeat(10)), '測'.repeat(10));
  assert.equal(TN.shortName('測'.repeat(11)), '測'.repeat(9) + '…');
});
```

在 `tests/connection-page.test.cjs` 把整個測試

```js
test('picking a signal lights its path and writes both people into the detail line', () => {
  const { get } = open({ pair: pairFromMatchList(0).pair });
  const links = findAll(get('network'), node => node.attrs.class === 't-link');
  const [mine] = findAll(get('network'), node => node.attrs['aria-label']?.startsWith('你的飲料甜度'));
  fire(mine, 'click');
  assert.deepEqual(get('detail').textContent.split('\n').slice(0, 2),
    ['你：飲料甜度 約 8 分糖，往「高甜度」推 0.61', '手搖學生 B：飲料甜度 約 10 分糖，往「高甜度」推 0.80']);
  // The picked signal's own lines light up, and lines away from its traits fade out.
  assert.ok(links.some(link => link.style.opacity === '1'));
  assert.ok(links.some(link => link.style.opacity === '.06'));
});
```

換成

```js
test('picking a signal grows its purchases on both sides and writes them into the detail line', () => {
  const { get } = open({ pair: pairFromMatchList(0).pair });
  const network = get('network'), bought = () => findAll(network, node => node.attrs.class === 't-buy').length;
  const pick = start => fire(findAll(network, node => node.attrs['aria-label']?.startsWith(start))[0], 'click');
  // Room for the purchases is kept from the start.
  const [left, , width] = network.attrs.viewBox.split(' ').map(Number);
  assert.ok(left < 0 && width > 1200);
  pick('你的飲料甜度');
  assert.deepEqual(get('detail').textContent.split('\n').slice(0, 2), [
    '你：飲料甜度 約 8 分糖（半糖冬瓜青茶 ×7、百香果茶 ×7、花果茶 ×7），往「高甜度」推 0.61',
    '手搖學生 B：飲料甜度 約 10 分糖（冬瓜青茶 ×10、黑糖珍珠鮮奶 ×8、珍珠奶茶 ×6），往「高甜度」推 0.80']);
  // The picked signal's own lines light up, and lines away from its traits fade out.
  const lit = findAll(network, node => node.attrs.class === 't-link').map(link => link.style.opacity);
  assert.ok(lit.includes('1') && lit.includes('.06'));
  assert.equal(bought(), 6);
  assert.equal(network.attrs.viewBox.split(' ')[2], String(width));
  pick('你的常去店家');
  assert.equal(bought(), 0);
  assert.match(get('detail').textContent.split('\n')[0], /^你：常去店家 \d+%（這個訊號不列品項），/);
  pick('你的飲料甜度');
  fire(get('reset'), 'click');
  assert.equal(bought(), 0);
  pick('你，低甜度 ↔ 高甜度');
  assert.equal(bought(), 0);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/trait-network.test.cjs`
Expected: FAIL（`TN.purchases is not a function`、說明列沒有品項等）

- [ ] **Step 3: Place the purchases**

在 `src/web/trait-network.js` 把

```js
  // Desktop puts the two fans side by side; phones stack them, the left person on top. All sizes are SVG units.
  const SHAPES = Object.freeze({
    desktop: Object.freeze({ width: 1200, height: 640, centers: [[430, 325], [770, 325]], stretch: [1, 0.86],
      near: 110, far: 270, none: 72, ring: 312, stagger: 14, dot: [3.5, 9], font: 13 }),
    mobile: Object.freeze({ width: 600, height: 820, centers: [[300, 290], [300, 530]], stretch: [1, 0.9],
      near: 70, far: 190, none: 46, ring: 228, stagger: 12, dot: [5, 11], font: 18 }),
  });
```

換成

```js
  // Desktop puts the two fans side by side; phones stack them, the left person on top. All sizes are SVG units.
  // `item` places the purchases behind a picked signal: a column `across` from the signal on desktop, a column in a
  // band `beyond` the fans on phones, rows `step` apart, dots from dot[0] to dot[0] + dot[1] across.
  const SHAPES = Object.freeze({
    desktop: Object.freeze({ width: 1200, height: 640, centers: [[430, 325], [770, 325]], stretch: [1, 0.86],
      near: 110, far: 270, none: 72, ring: 312, stagger: 14, dot: [3.5, 9], font: 13,
      item: Object.freeze({ across: 60, step: 20, dot: [2.5, 3.5] }) }),
    mobile: Object.freeze({ width: 600, height: 820, centers: [[300, 290], [300, 530]], stretch: [1, 0.9],
      near: 70, far: 190, none: 46, ring: 228, stagger: 12, dot: [5, 11], font: 18,
      item: Object.freeze({ beyond: 30, step: 26, dot: [3, 4] }) }),
  });
```

在 `  // A measured signal as the detail line reads it.` 之前加上：

```js
  // A purchase name the graph can fit: ten letters at most, cut with an ellipsis; the detail line keeps it whole.
  const shortName = name => (Array.from(name).length > 10 ? Array.from(name).slice(0, 9).join('') + '…' : name);

  // The purchases behind one signal for each person who has any: a short column of dots outside the signal, most
  // bought first, each with a line into the signal and its name beside it. Desktop stands the column beside the
  // signal, away from the middle; phones stand it in a band above the top fan or below the bottom one.
  function purchases(data, graph, people, id, mobile) {
    const shape = mobile ? SHAPES.mobile : SHAPES.desktop, { across, beyond, step, dot } = shape.item;
    const order = data.signals.findIndex(signal => signal.id === id);
    return graph.sides.flatMap((side, k) => {
      const list = (people[k].items || [])[order] || [];
      if (!list.length) return [];
      const signal = side.signals.find(entry => entry.id === id), most = Math.max(...list.map(([, count]) => count));
      const rows = list.map(([name, count]) => ({ name, count, text: shortName(name) + ' ×' + count,
        r: dot[0] + dot[1] * count / most, width: 0.7 + 2.2 * count / most }));
      let x, first, anchor;
      if (mobile) {
        // The names must fit inside the phone's width; the band itself only makes the graph taller.
        const widest = Math.max(...rows.map(row => row.r + 5 + textWidth(row.text, shape.font)));
        x = Math.min(Math.max(signal.x, 20), graph.width - widest - 8);
        first = side.side === 'a' ? -beyond - (rows.length - 1) * step : graph.height + beyond;
        anchor = 'start';
      } else {
        x = side.side === 'a' ? signal.x - across : signal.x + across;
        first = signal.y - (rows.length - 1) * step / 2;
        anchor = side.side === 'a' ? 'end' : 'start';
      }
      const items = rows.map((row, slot) => {
        const y = first + slot * step;
        return { ...row, x, y, anchor, labelX: anchor === 'end' ? x - row.r - 5 : x + row.r + 5, labelY: y + shape.font * 0.35 };
      });
      return [{ side: side.side, signal: { x: signal.x, y: signal.y }, items }];
    });
  }

  // The view box: the graph plus room for every purchase any signal could show, so picking one never rescales it.
  function viewBox(data, graph, people, mobile) {
    const font = (mobile ? SHAPES.mobile : SHAPES.desktop).font;
    let left = 0, top = 0, right = graph.width, bottom = graph.height;
    for (const signal of data.signals) {
      for (const side of purchases(data, graph, people, signal.id, mobile)) {
        for (const item of side.items) {
          const box = labelRect(item.text, font, item.labelX, item.labelY, item.anchor);
          left = Math.min(left, box.left, item.x - item.r);
          right = Math.max(right, box.right, item.x + item.r);
          top = Math.min(top, box.top, item.y - item.r);
          bottom = Math.max(bottom, box.bottom, item.y + item.r);
        }
      }
    }
    return [Math.floor(left), Math.floor(top), Math.ceil(right) - Math.floor(left), Math.ceil(bottom) - Math.floor(top)].join(' ');
  }

```

在 `signalSentence` 把

```js
    const shown = value === null ? '' : ' ' + formatSignal(value, signal.unit);
    return name + '：' + signal.label + shown + '，' + effects.join('；');
```

換成

```js
    const shown = value === null ? '' : ' ' + formatSignal(value, signal.unit);
    // What was bought follows the value; a signal about places says it lists nothing on purpose.
    const list = (person.items || [])[order] || [];
    const bought = signal.list_items === false ? (value === null ? '' : '（這個訊號不列品項）')
      : list.length ? '（' + list.map(([item, count]) => item + ' ×' + count).join('、') + '）' : '';
    return name + '：' + signal.label + shown + bought + '，' + effects.join('；');
```

把

```js
  const api = Object.freeze({ SHAPES, validate, traitLabel, labelRect, layout, formatSignal, traitText, signalSentence,
    cellSentence, readout, traitCount });
```

換成

```js
  const api = Object.freeze({ SHAPES, validate, traitLabel, labelRect, layout, shortName, purchases, viewBox, formatSignal,
    traitText, signalSentence, cellSentence, readout, traitCount });
```

- [ ] **Step 4: Run the trait network tests**

Run: `node --test tests/trait-network.test.cjs`
Expected: 21 tests pass

- [ ] **Step 5: Draw the purchases on the connection page**

在 `src/web/taste-comparison.html`：

把（`<style>` 裡）

```css
.t-tip{fill:var(--ink);paint-order:stroke;stroke:#101010;stroke-width:3px;stroke-linejoin:round;pointer-events:none}.detail-text{white-space:pre-line}
```

換成

```css
.t-tip{fill:var(--ink);paint-order:stroke;stroke:#101010;stroke-width:3px;stroke-linejoin:round;pointer-events:none}.detail-text{white-space:pre-line}.t-buy-line{fill:none;stroke-linecap:round;opacity:.85}.t-buy{fill-opacity:.35;stroke-width:1.2}
```

把（品味特質圖例）

```html
<span class="legend-item">空心：資料不足</span><span class="legend-hint">點選查看連線，點空白處取消</span>
```

換成

```html
<span class="legend-item">空心：資料不足</span><span class="legend-item">外圈：常買的品項（點小點出現）</span><span class="legend-hint">點選查看連線，點空白處取消</span>
```

把

```html
<div id="trait-method" hidden><p id="trait-method-text"></p></div>
```

換成

```html
<div id="trait-method" hidden><p id="trait-method-text"></p><p id="trait-graph-method"></p></div>
```

在 `prepareView` 把

```js
 $('trait-method').hidden=!available;
```

換成

```js
 $('trait-method').hidden=!available;$('trait-graph-method').hidden=!traits;
```

在 `drawTraits` 把

```js
 svg.setAttribute('viewBox',`0 0 ${graph.width} ${graph.height}`);
```

換成

```js
 // Room for every signal's purchases is kept from the start, so picking a signal never rescales the graph.
 svg.setAttribute('viewBox',TraitNetwork.viewBox(network,graph,both,mobile));
```

把

```js
 const lines=el('g'),middles=el('g'),dots=el('g'),labels=el('g'),tips=el('g'),view={graph,links:[],cells:[],signals:[],traits:[],tips,pinned:[],hover:null};
```

換成

```js
 const lines=el('g'),middles=el('g'),dots=el('g'),labels=el('g'),outer=el('g',{class:'t-outer','aria-hidden':'true'}),tips=el('g'),view={graph,links:[],cells:[],signals:[],traits:[],outer,tips,pinned:[],hover:null};
```

把

```js
 svg.append(names,lines,middles,dots,labels,tips);traitGraph=view;clearSelection();
```

換成

```js
 svg.append(names,lines,middles,dots,labels,outer,tips);traitGraph=view;clearSelection();
```

把

```js
// A name next to a dot: a signal's name, or a trait label that had no room.
function tipText(item,text){
 const font=traitGraph.graph.font,mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width,gap=item.r===undefined?8:item.r+4;
 let x,y,anchor;
 if(mobile){x=item.x+gap;y=item.y+font*.35;anchor='start';}
 else{x=item.side==='a'?item.x-gap:item.x+gap;y=item.r===undefined?item.y+4:item.y-6;anchor=item.side==='a'?'end':'start';}
```

換成

```js
// A name next to a dot: a signal's name, or a trait label that had no room. Inward puts it on the middle side.
function tipText(item,text,inward=false){
 const font=traitGraph.graph.font,mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width,gap=item.r===undefined?8:item.r+4;
 let x,y,anchor;
 if(mobile){x=item.x+gap;y=item.y+font*.35;anchor='start';}
 else{const leftward=(item.side==='a')!==inward;x=leftward?item.x-gap:item.x+gap;y=item.r===undefined?item.y+(inward?-8:4):item.y-6;anchor=leftward?'end':'start';}
```

把

```js
function pin(item,text){const tip=tipText(item,text);traitGraph.tips.append(tip);traitGraph.pinned.push(tip);}
function clearPins(){if(!traitGraph)return;for(const tip of traitGraph.pinned)tip.remove();traitGraph.pinned=[];}
```

換成

```js
function pin(item,text,inward){const tip=tipText(item,text,inward);traitGraph.tips.append(tip);traitGraph.pinned.push(tip);}
// Pinned names and the purchases of a picked signal both go when the choice changes.
function clearPins(){if(!traitGraph)return;for(const tip of traitGraph.pinned)tip.remove();traitGraph.pinned=[];traitGraph.outer.replaceChildren();}
// The purchases behind a picked signal: a short column of dots outside it on each side, each with a line in and its name.
function showPurchases(id){
 const mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width,color={a:'#ff9aa7',b:'#9bbcff'},sides=new Set();
 for(const side of TraitNetwork.purchases(network,traitGraph.graph,traitPair(),id,mobile)){
  sides.add(side.side);
  for(const item of side.items)traitGraph.outer.append(
   el('path',{d:`M${item.x.toFixed(1)} ${item.y.toFixed(1)} L${side.signal.x.toFixed(1)} ${side.signal.y.toFixed(1)}`,class:'t-buy-line',stroke:color[side.side],'stroke-width':item.width.toFixed(2)}),
   el('circle',{cx:item.x.toFixed(1),cy:item.y.toFixed(1),r:item.r.toFixed(1),class:'t-buy',fill:color[side.side],stroke:color[side.side]}),
   el('text',{x:item.labelX.toFixed(1),y:item.labelY.toFixed(1),'text-anchor':item.anchor,class:'t-tip','font-size':traitGraph.graph.font},item.text));
 }
 return sides;
}
```

在 `selectSignal` 把

```js
 const label=network.signals.find(signal=>signal.id===id).label,[left,right]=traitPair(),names=sideNames(),parts=traitGraph.graph.result.parts;
 for(const signal of traitGraph.signals)if(signal.id===id)pin(signal,label);
```

換成

```js
 const label=network.signals.find(signal=>signal.id===id).label,[left,right]=traitPair(),names=sideNames(),parts=traitGraph.graph.result.parts;
 const bought=showPurchases(id),mobile=traitGraph.graph.width===TraitNetwork.SHAPES.mobile.width;
 // On desktop a side's purchases take the outside of its signal, so the signal's name moves to the inside.
 for(const signal of traitGraph.signals)if(signal.id===id)pin(signal,label,!mobile&&bought.has(signal.side));
```

最後，把（同一行後面還接著 `$('reset').addEventListener(...)`，只換這一段）

```js
if(network)$('trait-method-text').textContent='品味相似度是 '+TraitNetwork.traitCount(network.traits)+' 項品味特質（'+network.traits.length+' 格）的餘弦相似度，範圍 '+TraitSimilarity.signed(-1)+'～'+TraitSimilarity.signed(1)+'。每項特質由幾個消費訊號加權而成，訊號線越粗，代表這個訊號推得越多；中間每條線是那一格對分數的加減，全部加起來就是品味相似度。';
```

換成

```js
if(network){
 // The score explains both graphs; the lines and the purchases only the taste network.
 const unlisted=network.signals.filter(signal=>signal.list_items===false).map(signal=>signal.label);
 $('trait-method-text').textContent='品味相似度是 '+TraitNetwork.traitCount(network.traits)+' 項品味特質（'+network.traits.length+' 格）的餘弦相似度，範圍 '+TraitSimilarity.signed(-1)+'～'+TraitSimilarity.signed(1)+'。';
 $('trait-graph-method').textContent='每項特質由幾個消費訊號加權而成，訊號線越粗，代表這個訊號推得越多；中間每條線是那一格對分數的加減，全部加起來就是品味相似度。點一個訊號，外圈會出現最常買的品項（最多 3 個，×N 是整段期間的次數）；'+unlisted.join('、')+'這 '+unlisted.length+' 個訊號不列品項。';
}
```

- [ ] **Step 6: Rebuild and run every Node test**

Run: `python scripts/build_report.py && node --test tests/*.test.cjs`
Expected: 65 tests pass

- [ ] **Step 7: Commit**

```bash
git add src/web/trait-network.js src/web/taste-comparison.html tests/trait-network.test.cjs tests/connection-page.test.cjs invoice-insights.html
git commit -m "feat: grow the purchases behind a picked signal in a short column outside it" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: 新版連結的讀取（朋友比較頁）

`TasteProfile` 認得新版 `receipt-taste/traits-v2`（`traits` 是 `null` 或物件，原樣交出），舊版照常可讀。朋友比較頁貼上新版連結時用 `TraitNetwork.validate` 檢查品味特質；舊版、資料不足、檢查不合格、只有一邊有資料，各有說明（規格 §3）。「資料來源…」多一段連結說明，原本品項細節裡的「報告連結包含…」那段刪掉。

**Files:**
- Modify: `src/web/taste-profile.js`
- Modify: `src/web/taste-comparison.html`
- Test: `tests/taste-profile.test.cjs`、`tests/connection-page.test.cjs`、`tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Produces: `TasteProfile.traitsSchema = 'receipt-taste/traits-v2'`；`TasteProfile.validate(value)` 對新版多回傳 `traits`（`null` 或物件，未深入檢查）；`TasteProfile.fromReport(report, name, taste = null)` 一律產生新版；`TasteProfile.schema` 仍是舊版字串（`fromPair` 照舊用它）。
- Produces（連線頁）：貼上的一側存成 `profiles['import-a'|'import-b'] = { name, payload, counts, traits, missing }`，`missing` 是 `'old'`、`'thin'` 或 `null`。

- [ ] **Step 1: Write the failing `TasteProfile` tests**

在 `tests/taste-profile.test.cjs` 把

```js
 assert.deepEqual(Object.keys(p).sort(),['counts','demo','months','name','schema']);
```

換成

```js
 assert.deepEqual(Object.keys(p).sort(),['counts','demo','months','name','schema','traits']);
 assert.equal(p.schema,taste.traitsSchema);assert.equal(p.traits,null);
```

並在 `test('category comparison has defined zero overlap and volume-independent identical distributions',()=>{` 之前加上：

```js
test('a new link carries the taste traits untouched, and an old link still reads',()=>{
 const traits={vector:[0.5],pushes:[[0.5]],signals:[1],items:[[['紅茶',2]]]};
 const p=taste.fromReport(fixture,'小明',traits);
 assert.deepEqual(p.traits,traits);
 assert.deepEqual(taste.fromURL(taste.toURL(p,'https://example.test/receipt/invoice-insights.html')).traits,traits);
 const old={schema:taste.schema,name:'小明',demo:true,months:['2026-03'],counts:p.counts};
 assert.deepEqual(taste.validate(old),old);
 // An old link has no taste traits, whatever extra fields it carries.
 assert.equal('traits' in taste.validate({...old,traits}),false);
 for(const invalid of [{...p,traits:undefined},{...p,traits:[1]},{...p,traits:'x'}])assert.throws(()=>taste.validate(invalid));
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/taste-profile.test.cjs`
Expected: 2 failures

- [ ] **Step 3: Read and write new links**

在 `src/web/taste-profile.js` 把

```js
 const schema='receipt-taste/categories-v1';
 function validate(value){
  if(!value||value.schema!==schema)throw new Error('這不是支援的品味連結版本，請回報告重新產生。');
```

換成

```js
 const schema='receipt-taste/categories-v1';
 // New links add taste traits; old ones carry the category counts alone and still read.
 const traitsSchema='receipt-taste/traits-v2';
 function validate(value){
  if(!value||(value.schema!==schema&&value.schema!==traitsSchema))throw new Error('這不是支援的品味連結版本，請回報告重新產生。');
```

把

```js
  // Reconstruct an allowlist rather than passing through arbitrary source fields.
  return {schema,name:value.name.trim(),demo:value.demo,months:[...value.months].sort(),counts:[...value.counts]};
 }
 function fromReport(report,name){
```

換成

```js
  // Reconstruct an allowlist rather than passing through arbitrary source fields.
  const profile={schema:value.schema,name:value.name.trim(),demo:value.demo,months:[...value.months].sort(),counts:[...value.counts]};
  if(value.schema===traitsSchema){
   // The taste traits pass through as they are; the comparison page checks them against its own trait data.
   if(value.traits!==null&&(typeof value.traits!=='object'||Array.isArray(value.traits)))throw new Error('連結裡的品味特質格式不正確。');
   profile.traits=value.traits;
  }
  return profile;
 }
 function fromReport(report,name,taste=null){
```

把

```js
  return validate({schema,name:name.trim()||'我的偏好',demo:report.isDemo===true,months,counts});
```

換成

```js
  return validate({schema:traitsSchema,name:name.trim()||'我的偏好',demo:report.isDemo===true,months,counts,traits:taste});
```

把

```js
 const api=Object.freeze({categories,schema,validate,fromReport,fromPair,toURL,fromURL,cosine});
```

換成

```js
 const api=Object.freeze({categories,schema,traitsSchema,validate,fromReport,fromPair,toURL,fromURL,cosine});
```

- [ ] **Step 4: Run the `TasteProfile` tests**

Run: `node --test tests/taste-profile.test.cjs`
Expected: 7 tests pass

- [ ] **Step 5: Write the failing link tests on the connection page**

在 `tests/connection-page.test.cjs`：

把

```js
const { scriptsOf } = require('./built-report.cjs');

const scripts = scriptsOf('taste-page-source');
const matchScripts = scriptsOf('match-page-source');
```

換成

```js
const { html, between, templateSource, scriptsOf } = require('./built-report.cjs');

const scripts = scriptsOf('taste-page-source');
const matchScripts = scriptsOf('match-page-source');
const matchData = JSON.parse(between(templateSource('match-page-source'), 'const matchReportData = ', '</script>').trim().replace(/;$/, ''));
const exported = JSON.parse(between(html, 'const tasteExportData = ', '</script>').trim().replace(/;$/, ''));

// A taste link as the export button writes it for the demo me: the new kind with taste traits, or the old kind.
function link(schema = 'receipt-taste/traits-v2', traits = exported.taste) {
  const payload = { schema, name: '我的偏好', demo: true, months: matchData.me.months, counts: matchData.me.counts };
  if (schema === 'receipt-taste/traits-v2') payload.traits = traits;
  return 'https://example.test/invoice-insights.html#taste=' + Buffer.from(JSON.stringify(payload)).toString('base64url');
}
```

把

```js
  const context = vm.createContext({ window, document, location: window.location, URLSearchParams,
    matchMedia: () => ({ matches: false, addEventListener() {} }) });
```

換成

```js
  const context = vm.createContext({ window, document, location: window.location, URLSearchParams, atob, btoa, TextEncoder, TextDecoder,
    matchMedia: () => ({ matches: false, addEventListener() {} }) });
```

把整個測試

```js
test('the friends page opens on 小安 and 小宇 with their taste score', () => {
  const { get } = open();
  assert.equal(get('overall-score').textContent, '+80');
  assert.equal(get('summary-worst').textContent, '小安偏低甜度，小宇偏高甜度（扣 6 分）— 一個加糖，一個讓糖罐放假。');
});
```

換成

```js
test('the friends page opens on 小安 and 小宇 with their taste score', () => {
  const { get } = open();
  assert.equal(get('overall-score').textContent, '+80');
  assert.equal(get('summary-worst').textContent, '小安偏低甜度，小宇偏高甜度（扣 6 分）— 一個加糖，一個讓糖罐放假。');
  assert.equal(get('link-method').hidden, true);
});

const paste = (page, side, text) => { page.get('profile-url-' + side).value = text; fire(page.get('import-' + side), 'submit'); };

test('a new taste link draws the taste network with the purchases it carries', () => {
  const page = open();
  paste(page, 'a', link());
  assert.equal(page.get('import-status-a').textContent, '已匯入 我的偏好 · 2026-03、2026-04 · 虛構示範資料');
  assert.equal(page.get('overall-score').textContent, '+41');
  assert.equal(page.get('link-method').hidden, false);
  assert.match(page.get('link-method-text').textContent, /^品味連結包含暱稱、涵蓋月份、10 類已確認消費品項的筆數、17 項品味特質/);
  fire(findAll(page.get('network'), node => node.attrs['aria-label']?.startsWith('我的偏好的飲料甜度'))[0], 'click');
  assert.equal(findAll(page.get('network'), node => node.attrs.class === 't-buy').length, 5);
});

test('an old link, a thin report and a broken link each say why there is no taste network', () => {
  const page = open(), note = () => [page.get('views-note').hidden, page.get('views-note').textContent];
  paste(page, 'a', link('receipt-taste/categories-v1'));
  assert.equal(page.get('overall-score').textContent, '—');
  assert.equal(page.get('overall-note').textContent, '舊版連結沒有品味特質，無法計算品味相似度');
  assert.deepEqual(note(), [false, '這份連結還沒有品味特質']);
  paste(page, 'a', link(undefined, null));
  assert.equal(page.get('overall-note').textContent, '這份連結的資料還不夠，無法計算品味相似度');
  assert.deepEqual(note(), [false, '這份連結的資料還不夠算出品味特質']);
  const broken = { ...exported.taste, pushes: exported.taste.pushes.map((row, k) => (k === 0 ? [1000000, ...row.slice(1)] : row)) };
  paste(page, 'b', link(undefined, broken));
  assert.equal(page.get('import-status-b').textContent, '連結裡的品味特質不正確，請對方用新版報告重新匯出。 圖中仍保留小宇的資料。');
  fire(page.get('clear-b'), 'click');
  assert.deepEqual(note(), [false, '另一邊匯入後才能看品味特質']);
  fire(page.get('clear-a'), 'click');
  assert.deepEqual(note(), [false, '匯入兩邊的資料後才能看品味特質']);
  assert.equal(page.get('link-method').hidden, true);
});
```

- [ ] **Step 6: Run the smoke test to verify it fails**

Run: `python scripts/build_report.py && node --test tests/connection-page.test.cjs`
Expected: 3 failures（`link-method` 還不存在、新版連結被當成舊版）

- [ ] **Step 7: Read new links on the friends page**

在 `src/web/taste-comparison.html`：

把

```html
<details class="method"><summary>資料來源與相似百分比怎麼算？</summary><div id="trait-method" hidden><p id="trait-method-text"></p><p id="trait-graph-method"></p></div><div id="category-method" hidden><p>報告連結包含暱稱、涵蓋月份與 10 類已確認消費品項的筆數，同一張發票的同一品項只算一次，不計折扣、贈品及待確認分類。沒有店家、品名、單筆日期、金額或發票號碼，但摘要仍可被取得連結的人讀取；編碼並非加密。</p><p>分類模式
```

換成

```html
<details class="method"><summary>資料來源與相似百分比怎麼算？</summary><div id="link-method" hidden><p id="link-method-text"></p></div><div id="trait-method" hidden><p id="trait-method-text"></p><p id="trait-graph-method"></p></div><div id="category-method" hidden><p>分類模式
```

（這一段在同一行，只換開頭到「分類模式」為止；後面的文字照舊。）

在 `prepareView` 把

```js
 $('views-note').hidden=available||!hasBoth();
```

換成

```js
 $('views-note').hidden=available;$('views-note').textContent=traitNote();
 $('link-method').hidden=!loadedSides().some(side=>keyFor(side).startsWith('import-'));
```

把

```js
function currentView(){return traitPair()?chosenView:'items';}
```

換成

```js
function currentView(){return traitPair()?chosenView:'items';}
// The reason, left side first, that two loaded people have no taste network: an old link or a report too thin for one.
function missingReason(){return loadedSides().map(side=>profiles[keyFor(side)].missing).find(Boolean)||'old';}
// Why the taste network button is off: a side is still empty, or a pasted link carries no taste traits.
function traitNote(){
 const loaded=loadedSides().length;
 if(!loaded)return '匯入兩邊的資料後才能看品味特質';
 if(loaded<2)return '另一邊匯入後才能看品味特質';
 return missingReason()==='thin'?'這份連結的資料還不夠算出品味特質':'這份連結還沒有品味特質';
}
```

在 `draw` 的大字說明裡把

```js
hasBoth()?(both?'兩人共同的特質太少，無法計算品味相似度':'舊版連結沒有品味特質，無法計算品味相似度'):
```

換成

```js
hasBoth()?(both?'兩人共同的特質太少，無法計算品味相似度':missingReason()==='thin'?'這份連結的資料還不夠，無法計算品味相似度':'舊版連結沒有品味特質，無法計算品味相似度'):
```

在 `importProfile` 把

```js
  else{const payload=TasteProfile.fromURL(text);key='import-'+side;profiles[key]={name:payload.name,payload,counts:payload.counts};}
```

換成

```js
  else{
   const payload=TasteProfile.fromURL(text);
   // An old link has no taste traits and a thin report sends none; anything else passes the same check as a match.
   const missing=payload.schema===TasteProfile.schema?'old':payload.traits===null?'thin':null;
   let traits=null;
   if(!missing&&network){try{traits=TraitNetwork.validate(payload.traits,network);}catch{throw new Error('連結裡的品味特質不正確，請對方用新版報告重新匯出。');}}
   key='import-'+side;profiles[key]={name:payload.name,payload,counts:payload.counts,traits,missing:missing||(traits?null:'old')};
  }
```

最後把

```js
if(network){
 // The score explains both graphs; the lines and the purchases only the taste network.
```

換成

```js
$('link-method-text').textContent='品味連結包含暱稱、涵蓋月份、'+TasteProfile.categories.length+' 類已確認消費品項的筆數、'+(network?TraitNetwork.traitCount(network.traits)+' 項':'')+'品味特質、各消費訊號的彙總值（例如每餐平均花費、每月 3C 花費、每月次數），以及每個訊號最常買的品名；不包含店名、行政區、地址、日期、單筆金額或發票號碼。品名裡的地名已拿掉，住宿只寫「旅館住宿」。舊版連結只有暱稱、月份與 10 類筆數。拿到連結的人都讀得到這些內容；編碼並非加密。';
if(network){
 // The score explains both graphs; the lines and the purchases only the taste network.
```

在 `tests/test_build_report.py` 把

```python
            self.assertIn("同一張發票的同一品項只算一次", comparison)
```

換成

```python
            self.assertIn("品味連結包含暱稱", comparison)
```

- [ ] **Step 8: Rebuild and run everything**

Run: `python scripts/build_report.py && node --test tests/*.test.cjs && python -m unittest discover -s tests`
Expected: 68 tests pass；74 tests OK

- [ ] **Step 9: Commit**

```bash
git add src/web/taste-profile.js src/web/taste-comparison.html tests/taste-profile.test.cjs tests/connection-page.test.cjs tests/test_build_report.py invoice-insights.html
git commit -m "feat: read new taste links with their taste traits on the friends page" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: 匯出按鈕與面板

打開「匯出我的品味連結」：新版連結帶「我」的品味特質與品項；面板照實說明連結內容（數字由程式產生），預覽列多「· 17 項品味特質」，下面列出「朋友會看到這些品名」（規格 §6）。

**Files:**
- Create: `tests/taste-export.test.cjs`
- Modify: `src/web/taste-export.js`、`src/web/invoice-insights.html`、`src/web/styles.css`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Consumes: Task 5 的 `tasteExportData`、Task 8 的 `TasteProfile.fromReport(report, name, taste)`。
- Produces: 主頁新元素 `#taste-export-about`（面板說明，由 `taste-export.js` 填入）與 `#taste-export-names`（品名清單）。

- [ ] **Step 1: Write the failing tests**

新增 `tests/taste-export.test.cjs`：

```js
// Runs the export button of the built report against a few fake elements: the link it writes and what it says.
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { html, between } = require('./built-report.cjs');

const source = name => between(html, `<script data-source="${name}">`, '</script>');
const exported = JSON.parse(source('taste-export-data.js').split('const tasteExportData = ')[1].trim().replace(/;$/, ''));

// Load the scripts the export needs, in the report's order, with my taste traits or without them.
function open({ taste = exported.taste } = {}) {
  const nodes = new Map();
  const get = id => {
    if (!nodes.has(id)) nodes.set(id, { id, value: '', textContent: '', hidden: true, listeners: {}, attrs: {},
      setAttribute(key, value) { this.attrs[key] = value; }, removeAttribute(key) { delete this.attrs[key]; },
      addEventListener(type, callback) { (this.listeners[type] ||= []).push(callback); }, focus() {}, select() {} });
    return nodes.get(id);
  };
  get('taste-nickname').value = '我的偏好';
  const context = vm.createContext({ document: { getElementById: get }, URL, btoa, TextEncoder,
    location: { href: 'https://example.test/receipt/invoice-insights.html', protocol: 'https:' } });
  const data = "'use strict';\nconst tasteExportData = " + JSON.stringify({ ...exported, taste }) + ';\n';
  for (const code of [source('report-data.js'), source('taste-profile.js'), data, source('taste-export.js')]) vm.runInContext(code, context);
  return get;
}
const click = node => { for (const callback of node.listeners.click || []) callback({}); };
const decode = url => JSON.parse(Buffer.from(url.split('#taste=')[1], 'base64url').toString('utf8'));

test('the export button is ready and its panel says what a link carries', () => {
  assert.match(html, /<button id="export-taste" type="button">匯出我的品味連結<\/button>/);
  assert.doesNotMatch(html, /功能準備中/);
  assert.match(html, /<h2>分享品味，從一個連結開始。<\/h2>/);
});

test('the export writes a new taste link with my taste traits and lists the names friends will see', () => {
  const get = open();
  assert.match(get('taste-export-about').textContent, /^連結包含暱稱、月份、10 類消費筆數、17 項品味特質、各消費訊號的彙總值/);
  click(get('export-taste'));
  assert.equal(get('taste-export-preview').textContent, '虛構示範 · 2026-03、2026-04 · 97 筆已分類品項 · 17 項品味特質');
  assert.equal(get('taste-export-names').textContent, '朋友會看到這些品名（16 個）：蔬食餐盒、番茄燉飯、蔬菜咖哩、綜合蔬菜箱、有機蔬菜、'
    + '半糖冬瓜青茶、百香果茶、花果茶、燕麥餅、焦糖布丁、花生豆花、市區接駁票、體適能體驗票、旅館住宿、環保清潔劑、無線滑鼠');
  const url = get('taste-link').value, payload = decode(url);
  assert.ok(url.length > 1500 && url.length < 12000, String(url.length));
  assert.equal(payload.schema, 'receipt-taste/traits-v2');
  assert.deepEqual(payload.traits, exported.taste);
  assert.equal(get('taste-open-link').href, url);
});

test('a report too thin for taste traits exports the category counts and says so', () => {
  const get = open({ taste: null });
  click(get('export-taste'));
  assert.match(get('taste-export-preview').textContent, / · 97 筆已分類品項 · 品味特質資料不足$/);
  assert.equal(get('taste-export-names').textContent, '這份報告的資料還不夠算出品味特質，朋友只能看品項細節。');
  assert.equal(decode(get('taste-link').value).traits, null);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/taste-export.test.cjs`
Expected: 3 failures（按鈕仍是停用）

- [ ] **Step 3: Export the taste traits**

在 `src/web/taste-export.js` 把

```js
 const panel=get('taste-export-panel'),output=get('taste-link'),notice=get('taste-export-status');
 function generate(){
  const profile=TasteProfile.fromReport(expenseReportData,get('taste-nickname').value);
  output.value=TasteProfile.toURL(profile,location.href);
  get('taste-export-preview').textContent=`${profile.demo?'虛構示範':'這份報告'} · ${profile.months.join('、')} · ${profile.counts.reduce((a,b)=>a+b,0)} 筆已分類品項。`;
```

換成

```js
 const panel=get('taste-export-panel'),output=get('taste-link'),notice=get('taste-export-status');
 // My taste traits come with the report build; a page opened without them exports the category counts alone.
 const exported=typeof tasteExportData==='undefined'?{traitCount:0,taste:null}:tasteExportData;
 get('taste-export-about').textContent='連結包含暱稱、月份、'+TasteProfile.categories.length+' 類消費筆數、'+(exported.traitCount?exported.traitCount+' 項':'')
  +'品味特質、各消費訊號的彙總值（例如每餐平均花費、每月 3C 花費、每月次數），以及每個訊號最常買的品名；不包含店名、行政區、地址、日期、單筆金額或發票號碼。'
  +'品名裡的地名會拿掉，住宿只寫「旅館住宿」。拿到連結的人都讀得到這些內容；連結沒有加密。';
 // Every purchase name a friend will see, in signal order, each once.
 function sharedNames(taste){const names=[];for(const list of taste.items)for(const [name] of list||[])if(!names.includes(name))names.push(name);return names;}
 function generate(){
  const taste=exported.taste,profile=TasteProfile.fromReport(expenseReportData,get('taste-nickname').value,taste);
  output.value=TasteProfile.toURL(profile,location.href);
  get('taste-export-preview').textContent=`${profile.demo?'虛構示範':'這份報告'} · ${profile.months.join('、')} · ${profile.counts.reduce((a,b)=>a+b,0)} 筆已分類品項 · ${taste?exported.traitCount+' 項品味特質':'品味特質資料不足'}`;
  const names=taste?sharedNames(taste):[];
  get('taste-export-names').textContent=!taste?'這份報告的資料還不夠算出品味特質，朋友只能看品項細節。':names.length?`朋友會看到這些品名（${names.length} 個）：${names.join('、')}`:'連結裡沒有品名。';
```

- [ ] **Step 4: Open the button and reword the panel**

在 `src/web/invoice-insights.html` 把

```html
 <div class="taste-actions"><a class="taste-primary" id="compare-friends" href="#friends">比較跟朋友品味差多少 ↗</a><a id="find-matches" href="#match">找到同好 ↗</a><button id="export-taste" type="button" disabled title="功能準備中">匯出我的品味連結</button></div>
 <p class="taste-caption">把消費偏好帶到朋友比較頁，或到「找到同好」看看誰和你最合拍。品味連結匯出功能準備中。</p>
 <div id="taste-export-panel" class="taste-export-panel" hidden>
  <div class="taste-export-heading"><div><h2>分享偏好，從一個連結開始。</h2><p>只分享暱稱、月份與各類消費筆數，不包含店家、品名、發票號碼或金額。取得連結的人可以讀取這些摘要；連結沒有加密。</p></div></div>
```

換成

```html
 <div class="taste-actions"><a class="taste-primary" id="compare-friends" href="#friends">比較跟朋友品味差多少 ↗</a><a id="find-matches" href="#match">找到同好 ↗</a><button id="export-taste" type="button">匯出我的品味連結</button></div>
 <p class="taste-caption">把消費偏好帶到朋友比較頁，或到「找到同好」看看誰和你最合拍；也可以匯出你的品味連結，傳給朋友比較。</p>
 <div id="taste-export-panel" class="taste-export-panel" hidden>
  <div class="taste-export-heading"><div><h2>分享品味，從一個連結開始。</h2><p id="taste-export-about"></p></div></div>
```

把

```html
  <p id="taste-export-preview"></p><label class="taste-link-label" for="taste-link">你的品味連結</label>
```

換成

```html
  <p id="taste-export-preview"></p><p id="taste-export-names"></p><label class="taste-link-label" for="taste-link">你的品味連結</label>
```

把

```html
<p class="taste-caption">涵蓋報告所有月份，不受目前畫面月份影響。依正金額、分類已確認的品項筆數計算，同一張發票的同一品項只算一次；折扣、贈品與待確認分類不計入。這是分類偏好摘要，還無法分辨甜度或餡料。</p>
```

換成

```html
<p class="taste-caption">涵蓋報告所有月份，不受目前畫面月份影響。筆數依正金額、分類已確認的品項計算，同一張發票的同一品項只算一次；折扣、贈品與待確認分類不計入。品味特質與品名和「找到同好」用的是同一份資料。</p>
```

在 `src/web/styles.css` 把

```css
#taste-export-status{color:#f2c2c4}
```

換成

```css
#taste-export-status{color:#f2c2c4}#taste-export-names{color:#ddd9d1;border-left:2px solid #ef8588;padding-left:12px;margin:0 0 16px}
```

- [ ] **Step 5: Rebuild and run every Node test**

Run: `python scripts/build_report.py && node --test tests/*.test.cjs`
Expected: 71 tests pass

- [ ] **Step 6: Commit**

```bash
git add src/web/taste-export.js src/web/invoice-insights.html src/web/styles.css tests/taste-export.test.cjs invoice-insights.html
git commit -m "feat: export a taste link with my taste traits and the names friends will see" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: 配對頁文案、README、`.gitignore`

配對頁的隱私說明照實改寫（規格 §7）；頁首那句搬到 `MatchFilter.intro`，資料不足時不寫「點一個人，看你們的連線圖。」；README 的連結段落（規格 §8）；`.gitignore` 排除根目錄的私人 `report-data.js`。

**Files:**
- Modify: `src/web/match-filter.js`、`src/web/match.html`、`README.md`、`.gitignore`
- Test: `tests/match-filter.test.cjs`、`tests/test_build_report.py`
- Regenerate: `invoice-insights.html`

**Interfaces:**
- Produces: `MatchFilter.intro(data, ready) -> string`（`data` 要有 `population`、`isDemo`）。

- [ ] **Step 1: Write the failing test**

在 `tests/match-filter.test.cjs` 把

```js
const { RANGES, pick, phrase, reasons, mine, view } = require('../src/web/match-filter.js');
```

換成

```js
const { RANGES, pick, phrase, reasons, mine, view, intro } = require('../src/web/match-filter.js');
```

並在檔案最後加上：

```js

test('the line under the title only asks to pick someone when there is a list to pick from', () => {
  assert.equal(intro({ population: 40, isDemo: true }, true), '配對對象是 40 位虛構示範用戶。「我」也是虛構示範資料。點一個人，看你們的連線圖。');
  assert.equal(intro({ population: 40, isDemo: false }, false), '配對對象是 40 位虛構示範用戶。你的品味特質來自這份私人報告，只存在這個檔案裡。');
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/match-filter.test.cjs`
Expected: 1 failure，`intro is not a function`

- [ ] **Step 3: Move the line into `MatchFilter`**

在 `src/web/match-filter.js` 把

```js
  const api = Object.freeze({ RANGES, scored, pick, words, phrase, reasons, mine, status, view });
```

換成

```js
  // The line under the title: who the matches are, whose taste mine is, and a nudge to pick someone when there is a list.
  function intro(data, ready) {
    return '配對對象是 ' + data.population + ' 位虛構示範用戶。'
      + (data.isDemo ? '「我」也是虛構示範資料。' : '你的品味特質來自這份私人報告，只存在這個檔案裡。')
      + (ready ? '點一個人，看你們的連線圖。' : '');
  }

  const api = Object.freeze({ RANGES, scored, pick, words, phrase, reasons, mine, status, view, intro });
```

在 `src/web/match.html` 把

```js
  $('match-note').textContent = '配對對象是 ' + data.population + ' 位虛構示範用戶。'
    + (data.isDemo ? '「我」也是虛構示範資料。' : '你的品味特質來自這份私人報告，只存在這個檔案裡。') + '點一個人，看你們的連線圖。';
```

換成

```js
  $('match-note').textContent = MatchFilter.intro(data, first.ready);
```

並把

```js
    make('p', '此配對頁與連線圖只用行政區、品味特質，以及各消費訊號的彙總值（例如每餐平均花費、每月次數），不顯示店名、品名、日期或單筆金額。'
```

換成

```js
    make('p', '此配對頁與連線圖只用行政區、10 類消費筆數、品味特質、各消費訊號的彙總值（例如每餐平均花費、每月 3C 花費、每月次數），'
      + '以及每個訊號最常買的品名；不顯示店名、地址、日期或單筆金額。品名裡的地名已拿掉，住宿只寫「旅館住宿」。'
```

（下一行的 `+ (data.isDemo ? '' : '這份私人報告的其他頁面仍有完整交易明細，分享整份檔案就會一併分享。')` 與 `+ '配對對象皆為虛構示範用戶。'));` 照舊。）

在 `tests/test_build_report.py` 把

```python
            self.assertIn("此配對頁與連線圖只用行政區、品味特質", match_page)
```

換成

```python
            self.assertIn("此配對頁與連線圖只用行政區、10 類消費筆數、品味特質", match_page)
```

- [ ] **Step 4: Reword the README**

在 `README.md` 的「與朋友比較偏好」：把

```markdown
報告上方可點「比較跟朋友品味差多少」開啟品項示範，預設以左側小安、右側小宇進行比較，兩側網址欄會自動填入示範人物。「匯出我的品味連結」目前只保留按鈕，暫不開放點選。到[朋友比較畫面](https://lee851104.github.io/receipt/invoice-insights.html#friends)貼上兩人的連結；只匯入一人時先顯示自己的分布，兩人到齊後顯示連線與相似百分比。點「返回消費洞察」即可回到同一檔案內的報告。

連結只包含暱稱、報告涵蓋月份及 10 類已確認品項的筆數，不含店家、品名、單筆日期、金額或發票號碼。依正金額品項逐筆計數，排除折扣、贈品及待確認分類，並涵蓋全部月份。資料放在網址片段（URL Fragment）內，不上傳至伺服器；這不是加密，取得完整連結的人可以讀取摘要。公開示範版匯出的仍是虛構資料。
```

換成

```markdown
報告上方可點「比較跟朋友品味差多少」開啟品項示範，預設以左側小安、右側小宇進行比較，兩側網址欄會自動填入示範人物。按「匯出我的品味連結」會產生你的品味連結，面板會列出朋友會看到的品名，可以先檢查再分享；按「帶到朋友比較頁」會把你放在左側，直接和示範的小宇比較。到[朋友比較畫面](https://lee851104.github.io/receipt/invoice-insights.html#friends)貼上兩人的連結；只匯入一人時先顯示自己的分布，兩人都有品味特質時顯示品味特質連線圖與品味相似度。點「返回消費洞察」即可回到同一檔案內的報告。

品味連結包含暱稱、涵蓋月份、10 類已確認品項的筆數、17 項品味特質、各消費訊號的彙總值（例如每餐平均花費、每月 3C 花費、每月次數），以及每個訊號最常買的品名；不包含店名、行政區、地址、日期、單筆金額或發票號碼。品名裡的地名會拿掉，住宿只寫「旅館住宿」，長途交通只寫交通方式。舊版連結只有暱稱、月份與 10 類筆數，仍可貼上，但只能看品項細節。資料放在網址片段（URL Fragment）內，不上傳至伺服器；這不是加密，取得完整連結的人可以讀取這些內容。公開示範版匯出的仍是虛構資料。
```

把

```markdown
本機 `file:` 連結不能讓朋友直接開啟你的電腦檔案。示範時直接傳送 `invoice-insights.html` 即可；對方下載後可離線操作報告與比較畫面。線上示範也使用同一個整合檔案。匯出按鈕目前仍停用；已有的摘要連結可貼入比較畫面讀取。
```

換成

```markdown
本機 `file:` 連結不能讓朋友直接開啟你的電腦檔案。示範時直接傳送 `invoice-insights.html` 即可；對方下載後可離線操作報告與比較畫面，再把你的完整連結貼進比較畫面。線上示範也使用同一個整合檔案。
```

- [ ] **Step 5: Keep the private report data out of Git**

在 `.gitignore` 把

```text
# Local report containing real purchases
/invoice-insights-private.html
```

換成

```text
# Local report containing real purchases
/invoice-insights-private.html
/report-data.js
```

Run: `git check-ignore -v report-data.js && git status --short`
Expected: 第一行是 `.gitignore:…:/report-data.js	report-data.js`；`git status` 不再列出 `report-data.js`。

- [ ] **Step 6: Rebuild and run everything**

Run: `python scripts/build_report.py && node --test tests/*.test.cjs && python -m unittest discover -s tests`
Expected: 三行輸出同「試做結果」；72 tests pass；74 tests OK

- [ ] **Step 7: Commit**

```bash
git add src/web/match-filter.js src/web/match.html tests/match-filter.test.cjs tests/test_build_report.py README.md .gitignore invoice-insights.html
git commit -m "feat: word the privacy notes for the new links and keep the private report data out of Git" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: 最終驗證與交接（由主控執行，不交給子代理）

- [ ] **Step 1: 全部測試**

Run: `python -m unittest discover -s tests`
Expected: 74 tests OK

Run: `node --test tests/*.test.cjs`
Expected: 72 tests pass

- [ ] **Step 2: 產生結果可重現、只動到預期的檔案**

Run: `python scripts/build_report.py && git status --short`
Expected: 輸出同「試做結果」的三行；`git status` 沒有任何變動（根目錄的 `report-data.js` 已被忽略）。

- [ ] **Step 3: 瀏覽器檢查**

主控用無頭 Chrome（DevTools 協定）實際操作 `invoice-insights.html`，逐項截圖確認規格 §10：

- 主頁：「匯出我的品味連結」可按；預覽列與品名清單（16 個，含「旅館住宿」）同「試做結果」；按「帶到朋友比較頁」，左側是我的偏好、右側小宇，大字 +41；右側換成小林、小安各是 +27、+14。
- 我的偏好 × 小宇：點「飲料甜度」兩側長出品項點（左 3 個、右 2 個）；點「住宿」左側是「旅館住宿 ×2」；點「常去店家」沒有品項點、說明列寫「（這個訊號不列品項）」；Esc、點空白處、「顯示全部連線」都會收起品項點。
- 配對頁：名單與第②輪相同；點手搖學生 B 大字 +71，點「飲料甜度」右側是冬瓜青茶 ×10、黑糖珍珠鮮奶 ×8、珍珠奶茶 ×6；隱私說明是新的文字。
- 貼舊版連結：大字「—」、按鈕旁「這份連結還沒有品味特質」；貼 `traits` 被改壞的連結：拒收、保留原本的資料。
- 視窗寬 375：品項點與名稱都在圖內，圖沒有變窄。
- 消費回顧照常：3 月 50 筆、4 月 53 筆。

- [ ] **Step 4: 核對規格**

規格已在寫計畫時同步了「與規格原稿不同的地方」。若最終驗證的數字與規格 §10 不同，先查原因，再更新 §10。

- [ ] **Step 5: 更新交接文件**

`docs/superpowers/handoffs/2026-10-08-taste-traits-stage1.md`：
- 「目前進度與下一步」：第③輪標成「完成」；下一步是「第二段合併」（由使用者決定何時合併到 `main`）。「新對話怎麼接」改成先讀「第二段第③輪」。
- 「第二段第③輪」一節改成完成紀錄：規格、計畫、commit 範圍、測試數、瀏覽器實測結果、與規格不同的地方，以及「已知、暫不處理（第③輪）」：README「與朋友比較偏好」裡「目前比較分類比例的餘弦相似度…」那段仍是第②輪以前的寫法；品名規則抓不到單一店家的名字與清單外的地名；手機版品項點的線很長。
- 「第②輪要記得」第 1～4 項標成已完成，第 5 項（真實資料校準）留著。

```bash
git add docs/superpowers/handoffs/2026-10-08-taste-traits-stage1.md
git commit -m "docs: record round 3 of stage 2 in the handoff note" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

（Step 4 若改了規格，把規格檔也加進同一個 commit。）

- [ ] **Step 6: 回報使用者**

回報 Task 1～10 的 commit、測試結果與截圖。不要 push、不要合併。
