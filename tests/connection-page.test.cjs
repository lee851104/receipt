// Runs the connection page from the built report against a small fake DOM, so its main paths stay covered.
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');

const between = (text, start, end) => {
  const from = text.indexOf(start) + start.length;
  return text.slice(from, text.indexOf(end, from));
};
const unescapeHtml = text => [['&lt;', '<'], ['&gt;', '>'], ['&quot;', '"'], ['&#x27;', "'"], ['&amp;', '&']]
  .reduce((result, [entity, character]) => result.split(entity).join(character), text);
const html = fs.readFileSync(path.join(__dirname, '..', 'invoice-insights.html'), 'utf8');
const scriptsOf = template => [...unescapeHtml(between(html, `<template id="${template}">`, '</template>'))
  .matchAll(/<script\b[^>]*>([\s\S]*?)<\/script>/g)].map(match => match[1]);
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
  const [mine] = findAll(get('network'), node => node.attrs['aria-label']?.startsWith('你的飲料甜度'));
  fire(mine, 'click');
  assert.equal(get('detail').textContent.split('\n')[0], '你：飲料甜度 約 8 分糖，往「高甜度」推 0.61');
});

test('the friends page opens on 小安 and 小宇 with their taste score', () => {
  const { get } = open();
  assert.equal(get('overall-score').textContent, '+80');
  assert.equal(get('summary-worst').textContent, '小安偏低甜度，小宇偏高甜度（扣 6 分）— 一個加糖，一個讓糖罐放假。');
});
