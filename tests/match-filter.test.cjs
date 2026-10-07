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
