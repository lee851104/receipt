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
  assert.equal(shown.match.status, '3 位品味相似度 +30% 以上。');
});

test('the opposite list is the five thrifty office workers', () => {
  const shown = view(data, { range: null, opposite: true });
  assert.equal(shown.opposite.status, '8 位品味相似度 ' + MINUS + '30% 以下，顯示前 5 位。');
  assert.deepEqual(summary(shown.opposite.cards), [['省錢上班族 E', MINUS + '42%'], ['省錢上班族 B', MINUS + '41%'],
    ['省錢上班族 A', MINUS + '41%'], ['省錢上班族 D', MINUS + '41%'], ['省錢上班族 C', MINUS + '41%']]);
  assert.ok(shown.opposite.cards.every(card => card.alike === '都偏省錢' && card.unlike === '你偏香甜，對方偏清爽'));
});
