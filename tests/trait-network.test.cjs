const { test } = require('node:test');
const assert = require('node:assert/strict');
const TN = require('../src/web/trait-network.js');
const { percent, signed } = require('../src/web/trait-similarity.js');

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
const me = { vector: [0.7, 1, null, 0.375], pushes: [[0.61, 0.09], [0, 1], [null, null], [0.375]], signals: [0.8333, 0.1429, 0, 1, null, 5],
  items: [[['半糖冬瓜青茶', 7], ['百香果茶', 7], ['花果茶', 7]], [['燕麥餅', 4]], [], [['蔬食餐盒', 5]], [], [['體適能體驗票', 10]]] };
const them = { vector: [0.94, 0.82, 0.5, 0.2], pushes: [[0.8, 0.14], [-0.18, 1], [-0.1, 0.6], [0.2]], signals: [1, 0.2, 0.36, 1, 0.1, 2],
  items: [[['冬瓜青茶', 10], ['黑糖珍珠鮮奶', 8]], [['肉桂捲', 6]], [['鮪魚飯糰', 9]], [['石鍋拌飯', 5]], [['即期便當', 2]], [['體適能體驗票', 4]]] };
const light = { ...them, vector: [-0.58, 0.82, 0.5, 0], pushes: [[-0.5, -0.08], [-0.18, 1], [-0.1, 0.6], [0]] };
const shownRects = side => side.traits.filter(trait => trait.labelShown)
  .map(trait => TN.labelRect(trait.label, TN.SHAPES.desktop.font, trait.labelX, trait.labelY, trait.labelAnchor));
const overlap = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

test('validate keeps well-formed taste data and refuses anything else', () => {
  const copy = TN.validate(me, data);
  assert.deepEqual(copy, me);
  assert.notEqual(copy.vector, me.vector);
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
  for (const person of broken) assert.throws(() => TN.validate(person, data), /品味資料不正確/);
});

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
  // A value that prints as 0.00 leans nowhere.
  assert.equal(TN.traitLabel(traits[0], -0.004), '甜度');
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
  assert.equal(TN.traitText(traits[0], 0.004), '0.00');
});

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
  // With room to spare a column stands exactly `across` out, centred on its signal, its rows `step` apart.
  const { across, step } = TN.SHAPES.desktop.item, at = items => items.map(item => [item.x.toFixed(3), item.y.toFixed(3)]);
  const spot = (x, ...ys) => ys.map(y => [x.toFixed(3), y.toFixed(3)]);
  assert.deepEqual(at(mine.items), spot(signal.x - across, signal.y - step, signal.y, signal.y + step));
  assert.deepEqual(at(theirs.items), spot(theirs.signal.x + across, theirs.signal.y - step / 2, theirs.signal.y + step / 2));
  // Phones stand my column in the band above the top fan and theirs in the band below the bottom one.
  const phone = TN.layout(data, me, them, true), { beyond, step: row } = TN.SHAPES.mobile.item;
  const [up, down] = TN.purchases(data, phone, [me, them], 'sugar_mean', true);
  assert.deepEqual(up.items.map(item => item.y), [-beyond - 2 * row, -beyond - row, -beyond]);
  assert.deepEqual(down.items.map(item => item.y), [phone.height + beyond, phone.height + beyond + row]);
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
  assert.equal(TN.viewBox(data, TN.layout(data, me, them, true), [bare(me), bare(them)], true), '0 0 600 820');
});

test('on desktop every column of purchases finds room clear of the names along the top, the dots and the trait labels', () => {
  const { embedded } = require('./built-report.cjs');
  const network = embedded('taste-page-source', 'traitNetworkData'), match = embedded('match-page-source', 'matchReportData');
  const { top, font, item: { across } } = TN.SHAPES.desktop;
  const dot = (x, y, r) => ({ left: x - r, right: x + r, top: y - r, bottom: y + r });
  let columns = 0;
  // A side's columns depend only on that side's person, so drawing each person on both sides covers everyone.
  for (const person of [match.me, ...match.people, ...Object.values(network.friends)].map(other => TN.validate(other, network))) {
    const graph = TN.layout(network, person, person, false);
    for (const signal of network.signals) {
      for (const column of TN.purchases(network, graph, [person, person], signal.id, false)) {
        const side = graph.sides.find(entry => entry.side === column.side);
        const taken = [...side.signals.map(entry => dot(entry.x, entry.y, 3)), ...side.traits.map(trait => dot(trait.x, trait.y, trait.r)),
          ...shownRects(side)];
        for (const item of column.items) {
          const marks = [TN.labelRect(item.text, font, item.labelX, item.labelY, item.anchor), dot(item.x, item.y, item.r)];
          assert.ok(marks.every(mark => mark.top >= top && !taken.some(box => overlap(box, mark))), `${signal.id} ${item.text}`);
          // However far it moved, the column still stands outside its signal.
          assert.ok(Math.abs(item.x - column.signal.x) > across - 0.001, `${signal.id} ${item.text}`);
        }
        columns++;
      }
    }
  }
  assert.equal(columns, 1092);
});

test('the overall match sits in the middle of the graph: its score in a badge, and a glow that grows with it', () => {
  const mark = TN.scoreMark(TN.layout(data, me, them, false), false);
  assert.deepEqual([mark.x, mark.y, mark.text, mark.tone, mark.glow], [600, 325, '+83%', 'positive', 0.5]);
  const phone = TN.scoreMark(TN.layout(data, me, them, true), true);
  assert.deepEqual([phone.x, phone.y], [300, 410]);
  assert.ok(phone.labelY < phone.y && phone.numberY > phone.y);
  // The glow follows how far the score is from zero; the colour, which side of zero it falls on.
  const at = score => TN.scoreMark({ result: { comparable: true, score } }, false);
  assert.deepEqual([at(-0.12).text, at(-0.12).tone, at(-0.12).glow.toFixed(3)], [signed(-0.12), 'negative', '0.078']);
  assert.deepEqual([at(0.004).text, at(0.004).tone, at(0.004).glow.toFixed(4)], ['0%', 'zero', '0.0026']);
  // Two people with too little in common get no badge, as the big number shows —.
  const nobody = { ...me, vector: [null, null, null, null], pushes: [[null, null], [null, null], [null, null], [null]] };
  assert.equal(TN.scoreMark(TN.layout(data, me, nobody, false), false), null);
});

test('a middle line is as bright as the points it adds or takes, up to ten', () => {
  assert.deepEqual([0, 0.05, -0.1, 0.35].map(part => TN.cellOpacity(part).toFixed(2)), ['0.30', '0.60', '1.00', '1.00']);
});

test('a long purchase name is cut to ten letters on the graph', () => {
  assert.equal(TN.shortName('半糖冬瓜青茶'), '半糖冬瓜青茶');
  assert.equal(TN.shortName('測'.repeat(10)), '測'.repeat(10));
  assert.equal(TN.shortName('測'.repeat(11)), '測'.repeat(9) + '…');
  // Letters, not UTF-16 units: a character outside the basic plane still counts once.
  assert.equal(TN.shortName('𠮷'.repeat(10)), '𠮷'.repeat(10));
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
  // A part that rounds to 0 points neither adds nor takes away.
  assert.equal(TN.cellSentence(data, 3, me, them, ['你', '對方'], 0.004), '「運動投入」這一格：你 0.38、對方 0.20，不加也不扣');
  // Both leaning to the left end read the left line.
  const lowMe = { ...me, vector: [-0.6, 1, null, 0.375] }, lowThem = { ...them, vector: [-0.5, 0.82, 0.5, 0.2] };
  const low = TN.layout(data, lowMe, lowThem, false).result;
  assert.equal(TN.cellSentence(data, 0, lowMe, lowThem, ['你', '對方'], low.parts[0]),
    '「低甜度 ↔ 高甜度」這一格：你偏低甜度 0.60、對方偏低甜度 0.50，加 ' + percent(low.parts[0]) + ' 分 — 無糖派，清爽到底。');
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
  // A cell that rounds to 0 points is neither the most alike nor the most apart.
  assert.deepEqual(TN.readout(data, me, them, ['你', '對方'], { comparable: true, score: 0.004, parts: [0.004, null, null, -0.004] }),
    { alike: '沒有加分的特質 — 共同話題還在找。', unlike: '沒有扣分的特質 — 難得這麼合拍。' });
});

test('cats and dogs count as one trait', () => {
  assert.equal(TN.traitCount([{ id: 'a' }, { id: 'b', group: 'pets' }, { id: 'c', group: 'pets' }]), 2);
});
