// Runs the connection page from the built report against a small fake DOM, so its main paths stay covered.
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const { html, between, templateSource, scriptsOf, embedded } = require('./built-report.cjs');

const scripts = scriptsOf('taste-page-source');
const matchScripts = scriptsOf('match-page-source');
const matchData = embedded('match-page-source', 'matchReportData');
const exported = JSON.parse(between(html, 'const tasteExportData = ', '</script>').trim().replace(/;$/, ''));

// A taste link as the export button writes it for the demo me: the new kind with taste traits, or the old kind.
function link(schema = 'receipt-taste/traits-v2', traits = exported.taste) {
  const payload = { schema, name: '我的偏好', demo: true, months: matchData.me.months, counts: matchData.me.counts };
  if (schema === 'receipt-taste/traits-v2') payload.traits = traits;
  return 'https://example.test/invoice-insights.html#taste=' + Buffer.from(JSON.stringify(payload)).toString('base64url');
}

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
// The score badge and the glow drawn between the fans, with the attributes the tests read.
function scoreMarkOf(network) {
  const [badge] = findAll(network, node => node.attrs.class === 't-score'), [glow] = findAll(network, node => node.attrs.class === 't-glow');
  const [box] = findAll(badge, node => node.tag === 'rect'), [number] = findAll(badge, node => node.attrs.class === 't-score-number');
  const [gradient] = findAll(glow, node => node.tag === 'radialGradient'), [stop] = findAll(glow, node => node.tag === 'stop');
  const [ellipse] = findAll(glow, node => node.tag === 'ellipse');
  return { badge, glow, box, gradient, ellipse, texts: findAll(badge, node => node.tag === 'text').map(node => node.textContent),
    number: number.attrs.fill, frame: box.attrs.stroke, stop: stop.attrs['stop-opacity'] };
}

// Click a card on the built match page, or on its list of opposites, and keep the pair it hands to the connection page.
function pairFromMatchList(index, { opposite = false } = {}) {
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  let pair = null;
  const window = { frameElement: { id: 'match-frame' } };
  window.parent = { ReceiptPages: { showConnection: chosen => { pair = chosen; }, showReport() {} } };
  const context = vm.createContext({ window, document: { getElementById: get, createElement: tag => element(tag) } });
  for (const source of matchScripts) vm.runInContext(source, context);
  if (opposite) fire(get('show-opposites'), 'change', { target: { checked: true } });
  const card = get(opposite ? 'opposite-list' : 'match-list').children[index];
  fire(card, 'click');
  return { name: card.title, pair };
}

// Load the page as the report would: in the connection frame with a chosen pair, or on its own as the friends page.
// `phone` is a narrow window; `standalone` leaves out the trait data, as when the page is opened outside the report.
function open({ pair = null, phone = false, standalone = false } = {}) {
  const nodes = new Map();
  const get = id => { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); };
  const singles = { '.toolbar': element(), '.detail': element(), '.method': element(), 'header .brand': element() };
  const lists = { '.summary-case': [element(), element()], '.import-title-row, .imports': [element(), element()], '[data-demo-side]': [] };
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
  const context = vm.createContext({ window, document, location: window.location, URLSearchParams, atob, btoa, TextEncoder, TextDecoder,
    matchMedia: () => ({ matches: phone, addEventListener() {} }) });
  for (const source of standalone ? scripts.filter(code => !code.includes('const traitNetworkData')) : scripts) vm.runInContext(source, context);
  return { get, calls, singles };
}

test('a match opens on the taste network with its score in the middle, glowing as strongly as the match', () => {
  const chosen = pairFromMatchList(0);
  assert.equal(chosen.name, '查看你和手搖學生 B的連線圖');
  const { get, calls } = open({ pair: chosen.pair });
  const network = get('network');
  assert.equal(get('overall-score').textContent, '+71');
  assert.equal(get('overall-note').textContent, '依 17 項品味特質計算 · 虛構示範');
  assert.equal(get('scope').textContent, '17 項品味特質 · 46 個訊號');
  assert.equal(findAll(network, node => node.attrs.class === 't-link').length, 85);
  const cells = findAll(network, node => node.attrs.class === 't-cell');
  assert.equal(cells.length, 15);
  assert.equal(get('summary-best').textContent, '都偏好好吃飯（加 32 分）— 吃飯這件事，從不將就。');
  // The same score sits between the fans, green because it adds up to alike, over a glow as strong as the match.
  const mark = scoreMarkOf(network);
  assert.deepEqual(mark.texts, ['品味相似度', '+71%']);
  assert.deepEqual([mark.number, mark.frame, mark.stop], ['#5eeac7', '#5eeac7', '0.46']);
  // The badge and glow only decorate: hidden from screen readers, over the middle lines and under the dots, letting
  // clicks through to the lines beneath them.
  assert.deepEqual([mark.badge.attrs['aria-hidden'], mark.glow.attrs['aria-hidden']], ['true', 'true']);
  assert.equal(mark.ellipse.attrs.fill, `url(#${mark.gradient.attrs.id})`);
  const layers = network.children, middles = layers.findIndex(layer => findAll(layer, node => node.attrs.class === 't-cell').length);
  assert.ok(layers[0] === mark.glow && layers.indexOf(mark.badge) === middles + 1, 'glow first, badge right after the middle lines');
  assert.ok(templateSource('taste-page-source').includes('.t-glow,.t-score{pointer-events:none}'));
  // The cells that decide the score are bright; the ones that add almost nothing fade.
  const opacity = cells.map(cell => Number(cell.attrs.opacity));
  assert.ok(Math.max(...opacity) === 1 && Math.min(...opacity) < 0.5, opacity.join(' '));
  assert.equal(get('return-report').textContent, '← 返回配對清單');
  fire(get('return-report'), 'click');
  assert.deepEqual(calls, ['showMatches']);
});

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
  // Clearing the choice puts every middle line back at its own brightness.
  for (const cell of findAll(network, node => node.attrs.class === 't-cell')) assert.equal(Number(cell.style.opacity).toFixed(2), cell.attrs.opacity);
  pick('你，低甜度 ↔ 高甜度');
  assert.equal(bought(), 0);
});

test('an opposite match shows its score in orange with hardly any glow, and phones put the badge between the groups', () => {
  const chosen = pairFromMatchList(0, { opposite: true });
  assert.equal(chosen.name, '查看你和省錢上班族 D的連線圖');
  const { get } = open({ pair: chosen.pair }), mark = scoreMarkOf(get('network'));
  assert.deepEqual([mark.texts[1], mark.number, mark.frame, mark.stop], [get('overall-score').textContent + '%', '#ffb65c', '#ffb65c', '0.08']);
  const phone = scoreMarkOf(open({ pair: pairFromMatchList(0).pair, phone: true }).get('network'));
  assert.deepEqual([phone.box.attrs.x, phone.box.attrs.y, phone.box.attrs.width], ['200', '360', '200']);
});

test('opened outside the report, the page says where to open it instead of blaming the link', () => {
  const { get } = open({ standalone: true });
  assert.equal(get('views-note').textContent, '請從報告開啟這一頁，才看得到品味特質圖');
  assert.equal(get('overall-note').textContent, '請從報告開啟這一頁，才算得出品味相似度');
  assert.equal(get('network').getAttribute('hidden'), '');
});

// Desktop writes both names along the top, so nothing a click adds may reach into that band.
test('whichever signal is picked, its name and its purchases stay below the names along the top', () => {
  const { top, font } = require('../src/web/trait-network.js').SHAPES.desktop;
  const { get } = open({ pair: pairFromMatchList(0).pair });
  const network = get('network');
  const signals = findAll(network, node => node.attrs.class === 't-hit' && node.children.some(child => child.attrs.class === 't-signal'));
  assert.equal(signals.length, 92);
  const names = () => findAll(network, node => node.attrs.class === 't-tip' && !node.textContent.includes('×')).length;
  for (const signal of signals) {
    fire(signal, 'mouseenter');
    fire(signal, 'click');
    // The signal's name shows once on each side: the name the pointer brought up is gone, and coming back brings none.
    assert.equal(names(), 2);
    fire(signal, 'mouseleave');
    fire(signal, 'mouseenter');
    assert.equal(names(), 2);
    for (const name of findAll(network, node => node.attrs.class === 't-tip')) assert.ok(Number(name.attrs.y) - font >= top, name.textContent);
    for (const dot of findAll(network, node => node.attrs.class === 't-buy')) assert.ok(Number(dot.attrs.cy) - Number(dot.attrs.r) >= top);
  }
});

test('the friends page opens on 小安 and 小宇 with their taste score', () => {
  const { get, singles } = open();
  assert.equal(get('overall-score').textContent, '+80');
  assert.equal(get('summary-worst').textContent, '小安偏低甜度，小宇偏高甜度（扣 6 分）— 一個加糖，一個讓糖罐放假。');
  assert.equal(get('link-method').hidden, true);
  assert.deepEqual([get('network').getAttribute('hidden'), singles['.detail'].hidden, get('views-note').hidden], [null, false, true]);
});

test('the friends page keeps no item view: no tabs, no demo items, no case links', () => {
  const page = templateSource('taste-page-source');
  for (const gone of ['data-view', '品項細節', 'demoItems', 'id="category"', "get('case')"]) assert.ok(!page.includes(gone), gone);
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
  // Without taste traits on both sides the graph's place holds only the reason: no graph, toolbar, detail line or legend.
  const graph = () => [page.get('network').getAttribute('hidden'), page.singles['.toolbar'].hidden, page.singles['.detail'].hidden,
    page.get('trait-legend').hidden];
  paste(page, 'a', link('receipt-taste/categories-v1'));
  assert.equal(page.get('overall-score').textContent, '—');
  assert.equal(page.get('overall-note').textContent, '舊版連結沒有品味特質，無法計算品味相似度');
  assert.deepEqual(note(), [false, '這份連結還沒有品味特質']);
  assert.deepEqual(graph(), ['', true, true, true]);
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
  // A link with taste traits and a friend bring the graph back.
  paste(page, 'a', link());
  paste(page, 'b', 'demo://yu');
  assert.deepEqual(graph(), [null, false, false, false]);
  assert.equal(page.get('views-note').hidden, true);
});

// The friends page quietly drops a friend whose data fails the check, so this test is what notices one.
test('everyone the report embeds passes the check the graph runs before drawing', () => {
  const TN = require('../src/web/trait-network.js');
  const network = embedded('taste-page-source', 'traitNetworkData');
  const people = [['我', matchData.me], ...matchData.people.map(person => [person.name, person]), ...Object.entries(network.friends)];
  assert.equal(people.length, 44);
  for (const [name, person] of people) assert.doesNotThrow(() => TN.validate(person, network), name);
});
