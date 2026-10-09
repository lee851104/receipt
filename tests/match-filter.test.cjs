const { test } = require('node:test');
const assert = require('node:assert/strict');
const { RANGES, pick, phrase, reasons, mine, view } = require('../src/web/match-filter.js');

const MINUS = String.fromCharCode(0x2212);
const traits = [
  { id: 'spend', name: '省錢 ↔ 享受', kind: 'two_sided', ends: ['省錢', '享受'] },
  { id: 'sweet', name: '低甜度 ↔ 高甜度', kind: 'two_sided', ends: ['低甜度', '高甜度'] },
  { id: 'travel', name: '待在生活圈 ↔ 常出遊', kind: 'two_sided', ends: ['待在生活圈', '常出遊'] },
  { id: 'routine', name: '固定習慣 ↔ 喜歡嘗鮮', kind: 'two_sided', ends: ['固定習慣', '喜歡嘗鮮'] },
  { id: 'meals', name: '快速解決 ↔ 好好吃飯', kind: 'two_sided', ends: ['快速解決', '好好吃飯'] },
  { id: 'cooking', name: '外食 ↔ 自己煮', kind: 'two_sided', ends: ['外食', '自己煮'] },
  { id: 'pets_cat', name: '有養寵物（貓）', kind: 'level', habit: '養貓' },
];
const model = { cells: traits.map(trait => ({ id: trait.id, kind: trait.kind, weight: 1 })), shrink: 0.25, min_shared_two_sided: 5 };
const settings = { min_score: 0.3, opposite_score: 0.1, top: 5, min_items: 20 };
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

test('the match list keeps people at +30% or more, strongest first, ties by name, five at most', () => {
  const entries = [entry('F', 0.31), entry('B', 0.6), entry('A', 0.6), entry('C', 0.45), entry('D', 0.3), entry('E', 0.9),
    entry('G', 0.29), entry('H', -0.5)];
  const result = pick(entries, settings, false, null);
  assert.equal(result.eligible, 6);
  assert.equal(result.within, 6);
  assert.deepEqual(names(result.shown), ['E', 'A', 'B', 'C', 'F']);
});

test('the opposite list keeps people at −10% or less, most opposite first', () => {
  const entries = [entry('A', -0.1), entry('B', -0.5), entry('C', -0.09), entry('D', 0.8), entry('E', -0.5)];
  const result = pick(entries, settings, true, null);
  assert.equal(result.eligible, 3);
  assert.deepEqual(names(result.shown), ['B', 'E', 'A']);
});

test('the bar is the printed whole percentage: +30% is in and +29% is out, likewise −10% and −9%', () => {
  const entries = [entry('A', 0.2966), entry('B', 0.2949), entry('C', -0.0951), entry('D', -0.0949)];
  assert.deepEqual(names(pick(entries, settings, false, null).shown), ['A']);
  assert.deepEqual(names(pick(entries, settings, true, null).shown), ['C']);
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
  assert.equal(phrase(traits[1], 1, 0.4), '都偏高甜度');
  assert.equal(phrase(traits[1], -0.3, -1), '都偏低甜度');
  assert.equal(phrase(traits[2], 0.61, -0.19), '你偏常出遊，對方偏待在生活圈');
  assert.equal(phrase(traits[6], 0.4, 0.7), '都有養貓的紀錄');
  assert.equal(phrase({ kind: 'level', habit: '3C' }, 0.3, 0.5), '都有 3C 的紀錄');
  // The connection page names both people instead of 你 and 對方, spacing a Latin letter from the Chinese after it.
  assert.equal(phrase(traits[2], 0.61, -0.19, ['小安', '手搖學生 A']), '小安偏常出遊，手搖學生 A 偏待在生活圈');
});

test('the most and least alike cells come from the largest and smallest parts, or nothing', () => {
  const me = [0.5, 1, 0.6, 0.2, 0.1, 0, 0.4];
  const alike = { name: 'A', vector: [0.4, 1, -0.2, 0.3, 0.1, 0.2, 0.5] };
  assert.deepEqual(reasons({ person: alike, parts: [0.05, 0.3, -0.04, 0.02, 0.003, 0, 0.06] }, me, traits),
    { alike: '都偏高甜度', unlike: '你偏常出遊，對方偏待在生活圈' });
  assert.deepEqual(reasons({ person: alike, parts: [0.05, null, 0.01, 0, 0, 0, 0] }, me, traits), { alike: '都偏享受', unlike: null });
  const opposite = { name: 'B', vector: [-0.4, -0.6, 0, 0, 0, 0, 0] };
  assert.deepEqual(reasons({ person: opposite, parts: [-0.05, -0.2, 0, 0, 0, 0, 0] }, me, traits),
    { alike: null, unlike: '你偏高甜度，對方偏低甜度' });
});

test('my traits list up to three leanings past 0.2, then the habits on record', () => {
  assert.deepEqual(mine([0.25, 1, -1, 0.65, 0.1, -0.19, 0.4], traits),
    { lean: '偏高甜度・偏待在生活圈・偏喜歡嘗鮮', habits: '也有養貓的紀錄' });
  assert.deepEqual(mine([0.1, 0, 0, 0, 0, 0, 0.3], traits), { lean: '', habits: '也有養貓的紀錄' });
  assert.deepEqual(mine([0.1, -0.1, 0, 0.05, null, 0, 0], traits), { lean: '品味特質還不明顯', habits: '' });
  assert.deepEqual(mine(null, traits), { lean: '資料還不夠，看不出品味特質', habits: '' });
});

test('the page lists matches, and opposites only when asked', () => {
  const shown = view(data, { range: null, opposite: false });
  assert.equal(shown.ready, true);
  assert.deepEqual(shown.mine, { lean: '偏享受・偏高甜度・偏常出遊', habits: '也有養貓的紀錄' });
  assert.equal(shown.note, '你的生活圈：高雄市苓雅區');
  assert.ok(shown.ranges.every(option => !option.disabled));
  assert.equal(shown.match.status, '1 位品味相似度 +30% 以上。');
  const [first] = shown.match.cards;
  assert.deepEqual([first.name, first.score, first.percent, first.opposite, first.place, first.alike, first.unlike],
    ['測試甲', '+87%', 87, false, '高雄市苓雅區', '都偏享受', null]);
  assert.equal(shown.opposite, null);
  const both = view(data, { range: null, opposite: true });
  assert.equal(both.opposite.status, '1 位品味相似度 ' + MINUS + '10% 以下。');
  const [other] = both.opposite.cards;
  assert.deepEqual([other.name, other.score, other.percent, other.opposite, other.alike, other.unlike],
    ['測試乙', MINUS + '70%', -70, true, '都有養貓的紀錄', '你偏享受，對方偏省錢']);
});

test('the page explains an empty distance, missing home districts, nobody close and thin data', () => {
  assert.equal(view(data, { range: 0, opposite: true }).opposite.status,
    '這個距離內沒有品味相似度 ' + MINUS + '10% 以下的人，試試放寬距離。');
  assert.equal(view({ ...data, people: [{ ...data.people[0], distance: 3 }] }, { range: 0, opposite: false }).match.status,
    '這個距離內沒有品味相似度 +30% 以上的人，試試放寬距離。');
  const homeless = view({ ...data, me: { ...data.me, areas: [] } }, { range: 0, opposite: false });
  assert.equal(homeless.note, '看不出你的生活圈，只能選「不限」。');
  assert.deepEqual(homeless.ranges.map(option => option.disabled), [false, true, true, true]);
  assert.equal(homeless.match.status, '1 位品味相似度 +30% 以上。');
  const nobody = view({ ...data, people: [data.people[2], data.people[3]] }, { range: null, opposite: true });
  assert.equal(nobody.match.status, '目前沒有品味夠相似的人（+30% 以上）。');
  assert.equal(nobody.opposite.status, '目前沒有和你明顯相反的人（' + MINUS + '10% 以下）。');
  const many = view({ ...data, people: ['A', 'B', 'C', 'D', 'E', 'F', 'G'].map(name => ({ ...data.people[0], name })) },
    { range: null, opposite: false });
  assert.equal(many.match.status, '7 位品味相似度 +30% 以上，顯示前 5 位。');
  assert.equal(many.match.cards.length, 5);
  assert.deepEqual(view({ ...data, me: { ...data.me, vector: null } }, { range: null, opposite: false }), {
    ready: false, mine: { lean: '資料還不夠，看不出品味特質', habits: '' },
    thin: '你的資料還不夠（有效品項少於 20 筆），先累積更多發票，再來找同好。' });
});
