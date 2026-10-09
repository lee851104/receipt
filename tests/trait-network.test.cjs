const { test } = require('node:test');
const assert = require('node:assert/strict');
const TN = require('../src/web/trait-network.js');
const { percent } = require('../src/web/trait-similarity.js');

// Four traits and six signals are enough to exercise every rule; "quick" feeds two traits, like weekday_quick_share.
const traits = [
  { id: 'sweet', name: '低甜度 ↔ 高甜度', kind: 'two_sided', ends: ['低甜度', '高甜度'], short: '甜度', signals: ['sugar_mean', 'dessert_share'],
    lines: { both: ['無糖派，清爽到底。', '糖分補給，雙人同行。'], split: '一個加糖，一個讓糖罐放假。' } },
  { id: 'meals', name: '快速解決 ↔ 好好吃飯', kind: 'two_sided', ends: ['快速解決', '好好吃飯'], short: '吃飯', signals: ['quick', 'shop_meal'],
    lines: { both: ['五分鐘吃完，效率一百分。', '吃飯這件事，從不將就。'], split: '一個在趕路，一個在等上菜。' } },
  { id: 'motive', name: '超商：省錢 ↔ 省時', kind: 'two_sided', ends: ['為了省錢', '為了省時'], short: '超商動機', signals: ['clearance', 'quick'],
    lines: { both: ['即期區的老朋友。', '超商是續命補給站。'], split: '同一家超商，不同的理由。' } },
  { id: 'sport', name: '運動投入', kind: 'level', habit: '運動', signals: ['sport_visits'], lines: { both: '流汗也有伴。' } },
];
const data = {
  model: { cells: traits.map(trait => ({ id: trait.id, kind: trait.kind, weight: 1 })), shrink: 0.25, min_shared_two_sided: 2 },
  traits,
  signals: [{ id: 'sugar_mean', label: '飲料甜度', unit: 'sugar' }, { id: 'dessert_share', label: '甜點', unit: 'share' },
    { id: 'quick', label: '平日固定速食', unit: 'share' }, { id: 'shop_meal', label: '餐廳正餐', unit: 'share' },
    { id: 'clearance', label: '超商即期', unit: 'share' }, { id: 'sport_visits', label: '運動消費', unit: 'times_month' }],
  readout: { no_alike: '共同話題還在找。', no_unlike: '難得這麼合拍。' },
};
const me = { vector: [0.7, 1, null, 0.375], pushes: [[0.61, 0.09], [0, 1], [null, null], [0.375]], signals: [0.8333, 0.1429, 0, 1, null, 5] };
const them = { vector: [0.94, 0.82, 0.5, 0.2], pushes: [[0.8, 0.14], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, 0.2, 0.36, 1, 0.1, 2] };
const light = { ...them, vector: [-0.58, 0.82, 0.5, 0], pushes: [[-0.5, -0.08], [-0.18, 1], [-0.1, 0.6], [0]] };
const shownRects = side => side.traits.filter(trait => trait.labelShown)
  .map(trait => TN.labelRect(trait.label, TN.SHAPES.desktop.font, trait.labelX, trait.labelY, trait.labelAnchor));
const overlap = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

test('validate keeps well-formed taste data and refuses anything else', () => {
  const copy = TN.validate(me, data);
  assert.deepEqual(copy, me);
  assert.notEqual(copy.vector, me.vector);
  const broken = [
    null, { ...me, vector: me.vector.slice(1) }, { ...me, vector: [1.2, 1, null, 0.3] }, { ...me, vector: [0.7, 1, null, -0.1] },
    { ...me, vector: [NaN, 1, null, 0.3] }, { ...me, pushes: [[0.61], [0, 1], [null, null], [0.375]] },
    { ...me, pushes: [[0.61, 'x'], [0, 1], [null, null], [0.375]] }, { ...me, signals: me.signals.slice(1) },
    { ...me, signals: [Infinity, 0, 0, 1, null, 5] },
  ];
  for (const person of broken) assert.throws(() => TN.validate(person, data), /品味資料不正確/);
});

test('the layout is the same every time, left fan on the left and the first trait on top', () => {
  const graph = TN.layout(data, me, them, false);
  assert.deepEqual(TN.layout(data, me, them, false), graph);
  const [a, b] = graph.sides;
  assert.ok(a.traits.every(trait => trait.x < 430) && b.traits.every(trait => trait.x > 770));
  assert.ok(a.traits[0].y < a.traits[3].y);
  for (const side of graph.sides) side.traits.slice(1).forEach((trait, k) => assert.ok(trait.angle < side.traits[k].angle));
  assert.deepEqual([graph.width, graph.height], [1200, 640]);
});

test('a stronger trait sits further out and is bigger; a trait without data is a small hollow dot near the centre', () => {
  const [a, b] = TN.layout(data, me, them, false).sides;
  const { near, far, none, dot } = TN.SHAPES.desktop;
  assert.equal(a.traits[1].distance, far);
  assert.equal(b.traits[3].distance, near + (far - near) * 0.2);
  assert.ok(a.traits[1].r > a.traits[3].r);
  assert.deepEqual([a.traits[2].hollow, a.traits[2].distance, a.traits[2].r], [true, none, dot[0]]);
  assert.equal(b.traits[2].hollow, false);
});

test('a signal feeding two traits is one dot with a line to each, and missing pushes draw no line', () => {
  const graph = TN.layout(data, me, them, false);
  for (const side of graph.sides) assert.equal(side.signals.filter(signal => signal.id === 'quick').length, 1);
  const quick = side => graph.links.filter(link => link.side === side && link.signal === 'quick').map(link => link.trait);
  assert.deepEqual(quick('b'), [1, 2]);
  assert.deepEqual(quick('a'), [1]);
  assert.equal(graph.links.filter(link => link.side === 'a').length, 5);
  assert.ok(graph.links.every(link => /^M[\d.]+ [\d.]+ Q[\d.]+ [\d.]+ [\d.]+ [\d.]+$/.test(link.d)));
});

test('the middle lines are the cells both people have, and they add up to the score', () => {
  const graph = TN.layout(data, me, them, false);
  assert.deepEqual(graph.cells.map(cell => cell.trait), [0, 1, 3]);
  const total = graph.cells.reduce((sum, cell) => sum + cell.part, 0);
  assert.ok(Math.abs(total - graph.result.score) < 1e-12);
  assert.equal(percent(graph.result.score), 83);
});

test('phones stack the fans, the left person on top', () => {
  const graph = TN.layout(data, me, them, true);
  const [a, b] = graph.sides;
  assert.deepEqual([graph.width, graph.height], [600, 820]);
  assert.ok(a.traits.every(trait => trait.y < 290) && b.traits.every(trait => trait.y > 530));
  assert.ok(a.traits[0].x < a.traits[3].x);
});

test('one more trait spreads every direction again, without any code change', () => {
  const extra = { id: 'fun', name: '娛樂體驗', kind: 'level', habit: '娛樂', signals: ['fun_visits'], lines: { both: '看展看戲，都不缺席。' } };
  const bigger = { ...data, traits: [...traits, extra], signals: [...data.signals, { id: 'fun_visits', label: '娛樂消費', unit: 'times_month' }],
    model: { ...data.model, cells: [...data.model.cells, { id: 'fun', kind: 'level', weight: 1 }] } };
  const grow = person => ({ vector: [...person.vector, 0.5], pushes: [...person.pushes, [0.5]], signals: [...person.signals, 2] });
  const before = TN.layout(data, me, them, false).sides[0].traits, after = TN.layout(bigger, grow(me), grow(them), false).sides[0].traits;
  assert.equal(after.length, 5);
  // Neighbours move closer together and the fan still opens the same 78° either way.
  assert.ok(after[0].angle - after[1].angle < before[0].angle - before[1].angle);
  assert.ok(Math.abs(after[0].angle + after[4].angle) < 1e-12 && after[0].angle < 78 * Math.PI / 180);
  after.slice(1).forEach((trait, k) => assert.ok(trait.angle < after[k].angle));
});

test('labels never cover each other, and the strongest trait always keeps its label', () => {
  // Twenty habits at zero crowd the centre of the fan; only the one at 1.0 stands out.
  const crowd = Array.from({ length: 20 }, (_, k) => ({ id: 't' + k, name: '測試' + k, kind: 'level', habit: '測試習慣' + k,
    signals: ['s' + k], lines: { both: '測試。' } }));
  const busy = { ...data, traits: crowd, signals: crowd.map((_, k) => ({ id: 's' + k, label: '訊號' + k, unit: 'share' })),
    model: { ...data.model, cells: crowd.map(trait => ({ id: trait.id, kind: 'level', weight: 1 })), min_shared_two_sided: 0 } };
  const person = { vector: crowd.map((_, k) => (k === 7 ? 1 : 0)), pushes: crowd.map((_, k) => [k === 7 ? 1 : 0]), signals: crowd.map(() => 0) };
  const [a] = TN.layout(busy, person, person, false).sides;
  assert.equal(a.traits[7].labelShown, true);
  assert.ok(a.traits.some(trait => !trait.labelShown));
  const rects = shownRects(a);
  rects.forEach((rect, k) => rects.slice(k + 1).forEach(other => assert.ok(!overlap(rect, other))));
});

test('on phones a label hangs away from the middle of the fan, so the strongest trait keeps its label', () => {
  // Twenty habits all at 1.0: every dot sits on the outer ring, crowding its neighbours.
  const crowd = Array.from({ length: 20 }, (_, k) => ({ id: 't' + k, name: '測試' + k, kind: 'level', habit: '測試習慣' + k,
    signals: ['s' + k], lines: { both: '測試。' } }));
  const busy = { ...data, traits: crowd, signals: crowd.map((_, k) => ({ id: 's' + k, label: '訊號' + k, unit: 'share' })),
    model: { ...data.model, cells: crowd.map(trait => ({ id: trait.id, kind: 'level', weight: 1 })), min_shared_two_sided: 0 } };
  const person = { vector: crowd.map(() => 1), pushes: crowd.map(() => [1]), signals: crowd.map(() => 1) };
  for (const side of TN.layout(busy, person, person, true).sides) {
    assert.equal(side.traits[0].labelShown, true);
    const shown = side.traits.filter(trait => trait.labelShown);
    assert.ok(shown.every(trait => trait.labelAnchor === (trait.angle > 0 ? 'end' : 'start')));
    const rects = shown.map(trait => TN.labelRect(trait.label, TN.SHAPES.mobile.font, trait.labelX, trait.labelY, trait.labelAnchor));
    rects.forEach((rect, k) => rects.slice(k + 1).forEach(other => assert.ok(!overlap(rect, other))));
  }
});

test('labels name the end a trait leans to, else its short name or habit', () => {
  assert.equal(TN.traitLabel(traits[0], 0.7), '高甜度');
  assert.equal(TN.traitLabel(traits[0], -0.2), '低甜度');
  assert.equal(TN.traitLabel(traits[0], 0), '甜度');
  assert.equal(TN.traitLabel(traits[2], null), '超商動機');
  assert.equal(TN.traitLabel(traits[3], 0), '運動');
});

test('each unit reads naturally in the detail line', () => {
  assert.equal(TN.formatSignal(0.381, 'share'), '38%');
  assert.equal(TN.formatSignal(0.8333, 'sugar'), '約 8 分糖');
  assert.equal(TN.formatSignal(125, 'money'), '每餐約 NT$125');
  assert.equal(TN.formatSignal(1200, 'money_month'), '每月約 NT$1,200');
  assert.equal(TN.formatSignal(2.5, 'times_month'), '每月 2.5 次');
  assert.equal(TN.formatSignal(3, 'times_month'), '每月 3 次');
  assert.equal(TN.formatSignal(0.333, 'items_month'), '每月 0.3 件');
  assert.equal(TN.formatSignal(3, 'kinds'), '3 種');
  assert.throws(() => TN.formatSignal(1, 'stars'));
  assert.equal(TN.traitText(traits[0], 0.7), '偏高甜度 0.70');
  assert.equal(TN.traitText(traits[0], -0.58), '偏低甜度 0.58');
  assert.equal(TN.traitText(traits[0], 0), '0.00');
  assert.equal(TN.traitText(traits[3], 0.375), '0.38');
  assert.equal(TN.traitText(traits[2], null), '資料不足');
});

test('a signal sentence says its value and how far it pushed each trait it feeds', () => {
  assert.equal(TN.signalSentence(data, me, '你', 'sugar_mean'), '你：飲料甜度 約 8 分糖，往「高甜度」推 0.61');
  assert.equal(TN.signalSentence(data, them, '對方', 'quick'), '對方：平日固定速食 36%，往「快速解決」推 0.18；往「為了省時」推 0.60');
  assert.equal(TN.signalSentence(data, me, '你', 'quick'), '你：平日固定速食 0%，沒有推動「快速解決 ↔ 好好吃飯」；「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, me, '你', 'clearance'), '你：超商即期，「超商：省錢 ↔ 省時」資料不足');
  assert.equal(TN.signalSentence(data, them, '手搖學生 A', 'sport_visits'), '手搖學生 A：運動消費 每月 2 次，往「運動」推 0.20');
  const unmeasured = { ...them, pushes: [[0.8, null], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, null, 0.36, 1, 0.1, 2] };
  assert.equal(TN.signalSentence(data, unmeasured, '對方', 'dessert_share'), '對方：甜點，沒有紀錄');
});

test('a cell sentence gives both values, the points it added or took, and its line', () => {
  const alike = TN.layout(data, me, them, false).result, apart = TN.layout(data, me, light, false).result;
  assert.equal(TN.cellSentence(data, 0, me, them, ['你', '對方'], alike.parts[0]),
    '「低甜度 ↔ 高甜度」這一格：你偏高甜度 0.70、對方偏高甜度 0.94，加 ' + percent(alike.parts[0]) + ' 分 — 糖分補給，雙人同行。');
  assert.equal(TN.cellSentence(data, 0, me, light, ['小安', '小宇'], apart.parts[0]),
    '「低甜度 ↔ 高甜度」這一格：小安偏高甜度 0.70、小宇偏低甜度 0.58，扣 ' + -percent(apart.parts[0]) + ' 分 — 一個加糖，一個讓糖罐放假。');
  assert.equal(TN.cellSentence(data, 2, me, them, ['你', '對方'], null), '「超商：省錢 ↔ 省時」這一格：你資料不足，這一格不計分');
  assert.equal(TN.cellSentence(data, 2, me, me, ['你', '手搖學生 A'], null), '「超商：省錢 ↔ 省時」這一格：你和手搖學生 A 資料不足，這一格不計分');
  assert.equal(TN.cellSentence(data, 3, me, light, ['你', '對方'], 0), '「運動投入」這一格：你 0.38、對方 0.00，不加也不扣');
  assert.equal(TN.cellSentence(data, 0, me, them, ['你', '對方'], null), '「低甜度 ↔ 高甜度」這一格：兩人共同的特質太少，無法計分');
  // A number never runs into a name that ends in a Latin letter.
  assert.equal(TN.cellSentence(data, 3, me, them, ['你', '手搖學生 A'], alike.parts[3]),
    '「運動投入」這一格：你 0.38、手搖學生 A 0.20，加 ' + percent(alike.parts[3]) + ' 分 — 流汗也有伴。');
});

test('the readout names the cell that adds most and the one that takes most away', () => {
  const alike = TN.layout(data, me, them, false).result;
  assert.deepEqual(TN.readout(data, me, them, ['你', '對方'], alike), {
    alike: '都偏好好吃飯（加 ' + percent(alike.parts[1]) + ' 分）— 吃飯這件事，從不將就。',
    unlike: '沒有扣分的特質 — 難得這麼合拍。' });
  const apart = TN.layout(data, me, light, false).result;
  assert.equal(TN.readout(data, me, light, ['小安', '小宇'], apart).unlike,
    '小安偏高甜度，小宇偏低甜度（扣 ' + -percent(apart.parts[0]) + ' 分）— 一個加糖，一個讓糖罐放假。');
  const habitOnly = { ...data, model: { ...data.model, min_shared_two_sided: 0 } };
  const sporty = { vector: [null, null, null, 0.5], pushes: [[null, null], [null, null], [null, null], [0.5]], signals: [null, null, null, null, null, 4] };
  const both = TN.layout(habitOnly, sporty, sporty, false).result;
  assert.equal(TN.readout(habitOnly, sporty, sporty, ['你', '對方'], both).alike, '都有運動的紀錄（加 ' + percent(both.parts[3]) + ' 分）— 流汗也有伴。');
  assert.deepEqual(TN.readout(data, me, them, ['你', '對方'], { comparable: false, score: null, parts: null }),
    { alike: '沒有加分的特質 — 共同話題還在找。', unlike: '沒有扣分的特質 — 難得這麼合拍。' });
});

test('cats and dogs count as one trait', () => {
  assert.equal(TN.traitCount([{ id: 'a' }, { id: 'b', group: 'pets' }, { id: 'c', group: 'pets' }]), 2);
});
