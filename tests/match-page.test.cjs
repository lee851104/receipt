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

test('the demo lists the three sweet-toothed students and two coffee lovers', () => {
  const shown = view(data, { range: null, opposite: false });
  assert.equal(shown.match.status, '14 位品味相似度 +30% 以上，顯示前 5 位。');
  assert.deepEqual(summary(shown.match.cards), [['手搖學生 B', '+71%'], ['手搖學生 A', '+71%'], ['手搖學生 C', '+67%'],
    ['咖啡上班族 D', '+40%'], ['咖啡上班族 E', '+40%']]);
  const [first, , , fourth] = shown.match.cards;
  assert.deepEqual([first.alike, first.unlike, first.place], ['都偏好好吃飯', null, '高雄市苓雅區']);
  assert.deepEqual([fourth.alike, fourth.unlike, fourth.place], ['都偏好好吃飯', '你偏省錢，對方偏享受', '臺北市信義區']);
  assert.deepEqual(shown.mine, { lean: '偏好好吃飯・偏避開連假・偏高甜度', habits: '也有運動、生活小物、3C 的紀錄' });
  assert.equal(shown.note, '你的生活圈：高雄市苓雅區、高雄市新興區');
});

test('within the same district all five students remain', () => {
  const shown = view(data, { range: 0, opposite: false });
  assert.equal(shown.match.status, '5 位品味相似度 +30% 以上。');
  assert.deepEqual(summary(shown.match.cards), [['手搖學生 B', '+71%'], ['手搖學生 A', '+71%'], ['手搖學生 C', '+67%'],
    ['手搖學生 D', '+32%'], ['手搖學生 E', '+32%']]);
  assert.equal(shown.match.cards[3].unlike, '你偏高甜度，對方偏低甜度');
});

test('the opposite list is the thrifty office workers', () => {
  const shown = view(data, { range: null, opposite: true });
  assert.equal(shown.opposite.status, '6 位品味相似度 ' + MINUS + '10% 以下，顯示前 5 位。');
  assert.deepEqual(summary(shown.opposite.cards), [['省錢上班族 D', MINUS + '12%'], ['省錢上班族 E', MINUS + '12%'],
    ['省錢上班族 C', MINUS + '11%'], ['省錢上班族 A', MINUS + '11%'], ['省錢上班族 B', MINUS + '11%']]);
  assert.ok(shown.opposite.cards.every(card => card.alike === '都偏省錢' && card.unlike === '你偏高甜度，對方偏低甜度'));
  // They pass 同一區 through their second home district, so the card shows that one.
  assert.ok(shown.opposite.cards.every(card => card.place === '高雄市苓雅區'));
});
