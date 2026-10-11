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
