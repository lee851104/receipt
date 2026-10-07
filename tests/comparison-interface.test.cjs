const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const { test } = require('node:test');
const root = path.join(__dirname, '..');

function setup(inlineOnly = false) {
  const nodes = new Map();
  function element() {
    return {
      innerHTML: '', textContent: '', value: '', dataset: {}, style: {}, attrs: {},
      events: {}, children: [], classList: { toggle() {} },
      append(child) { this.children.push(child); },
      setAttribute(key, value) { this.attrs[key] = value; },
      addEventListener(name, callback) { this.events[name] = callback; },
      querySelectorAll() { return []; },
    };
  }
  const frames = [];
  const chapters = [0, 1, 2].map(index => { const el = element(); el.dataset.chapter = String(index); return el; });
  const metrics = ['count', 'amount'].map(metric => { const el = element(); el.dataset.rhythmMetric = metric; return el; });
  const buttons = ['actual', 'demo'].map(source => {
    const button = element();
    button.dataset.compareSource = source;
    return button;
  });
  const document = {
    getElementById(id) { if (!nodes.has(id)) nodes.set(id, element()); return nodes.get(id); },
    createElement: element,
    querySelectorAll(selector) { return selector === '[data-compare-source]' ? buttons : selector === '.chapter' ? chapters : selector === '[data-rhythm-metric]' ? metrics : []; },
    addEventListener() {},
  };
  const context = vm.createContext({ document, matchMedia: () => ({ matches: true }), requestAnimationFrame(callback) { frames.push(callback); } });
  const html = fs.readFileSync(path.join(root, 'invoice-insights.html'), 'utf8');
  for (const match of html.matchAll(/<script\b([^>]*)>([\s\S]*?)<\/script>/g)) {
    const source = /\bsrc="([^"]+)"/.exec(match[1]);
    if (source && inlineOnly) continue;
    vm.runInContext(source ? fs.readFileSync(path.join(root, source[1]), 'utf8') : match[2], context);
  }
  return { nodes, buttons, chapters, metrics, frames, run: code => vm.runInContext(code, context) };
}

test('standalone HTML loads both months without external scripts', () => {
  const { nodes } = setup(true);
  assert.equal(nodes.get('total')?.textContent, 'NT$ 8,095');
  assert.match(nodes.get('data-notice').textContent, /虛構示範資料/);
  assert.match(nodes.get('report-tag').textContent, /虛構示範/);
  assert.match(nodes.get('audit-rows').innerHTML, /<td>高雄市苓雅區<\/td>/);
  assert.match(nodes.get('report-source').textContent, /與行政區，不嵌入原始號碼、統編或完整地址/);
  assert.doesNotMatch(nodes.get('compare-source-note').textContent, /真實發票/);
  nodes.get('insights-month').events.change({ target: { value: '2026-03' } });
  assert.equal(nodes.get('total').textContent, 'NT$ 7,910');
});

test('initial view uses April and compares fictional sport purchases against March', () => {
  const { nodes } = setup();
  assert.match(nodes.get('compare-months').innerHTML, /6<small>次/);
  assert.doesNotMatch(nodes.get('compare-months').innerHTML, /尚無資料/);
  assert.match(nodes.get('compare-specs').innerHTML, /540/);
  assert.match(nodes.get('compare-takeaway').innerHTML, /多花 180 元/);
  assert.equal(nodes.get('total').textContent, 'NT$ 8,095');
  assert.equal(nodes.get('compare-current-heading').textContent, '本月 · 4 月');
  assert.equal(nodes.get('time').textContent, '00:05 / 00:18');
  assert.equal(nodes.get('timeline').max, '18');
});

test('source button and item selector update every category and item without corrupting personal data', () => {
  const { nodes, buttons, run } = setup();
  const original = run('JSON.stringify(current)');
  for (const button of buttons) {
    button.events.click();
    assert.equal(button.attrs['aria-pressed'], 'true');
    for (let i = 0; i < run('comparisonSelections.length'); i++) {
      nodes.get('compare-item').value = String(i);
      nodes.get('compare-item').events.change();
      assert.ok(nodes.get('compare-caption').textContent.includes(run(`comparisonSelections[${i}].label`)));
      assert.doesNotMatch(nodes.get('compare-specs').innerHTML, /NaN|Infinity|undefined/);
      if (button.dataset.compareSource === 'demo') {
        assert.match(nodes.get('compare-source-note').textContent, /兩個月皆為模擬資料/);
        assert.doesNotMatch(nodes.get('compare-months').innerHTML, /尚無資料/);
      }
    }
  }
  buttons[0].events.click();
  assert.doesNotMatch(nodes.get('compare-months').innerHTML, /尚無資料/);
  assert.equal(run('JSON.stringify(current)'), original);
});


test('month switch refreshes totals, calendars, weekdays, clouds, audits and comparison', () => {
  const { nodes, chapters, metrics } = setup();
  const selector = nodes.get('insights-month');
  for (const key of ['2026-03', '2026-04', '2026-03', '2026-04']) {
    selector.events.change({ target: { value: key } });
    const march = key === '2026-03';
    assert.equal(nodes.get('total').textContent, march ? 'NT$ 7,910' : 'NT$ 8,095');
    assert.match(nodes.get('audit-summary').textContent, march ? /50 筆/ : /53 筆/);
    assert.match(nodes.get('report-source').textContent, march ? /虛構示範資料（3 月）/ : /虛構示範資料（4 月）/);
    assert.equal((nodes.get('rhythm-chart').innerHTML.match(/class="weekend-band"/g) || []).length, march ? 9 : 8);
    assert.equal((nodes.get('rhythm-chart').innerHTML.match(/class="radial-label/g) || []).length, march ? 31 : 30);
    assert.match(nodes.get('category-cloud').innerHTML, march ? /正餐<small>13 次/ : /飲品<small>12 次/);
    assert.match(nodes.get('compare-source-note').textContent, march ? /2 月尚無資料/ : /3 月已載入/);
    chapters[1].onclick();
    assert.match(nodes.get('insight-title').innerHTML, /住宿/);
    chapters[2].onclick();
    assert.match(nodes.get('routine-amount').innerHTML, march ? /360/ : /540/);
    metrics[1].onclick();
    assert.match(nodes.get('rhythm-chart').innerHTML, march ? />7,910<\/text>/ : />8,095<\/text>/);
  }
});

test('switching months retires the previous animation and preserves selected item', () => {
  const { nodes, frames } = setup();
  nodes.get('compare-item').value = '1';
  nodes.get('compare-item').events.change();
  const oldFrame = frames[0];
  nodes.get('insights-month').events.change({ target: { value: '2026-03' } });
  const queued = frames.length;
  oldFrame(1000);
  assert.equal(frames.length, queued);
  assert.equal(nodes.get('compare-item').value, '1');
  assert.match(nodes.get('compare-caption').textContent, /飲品/);
});
