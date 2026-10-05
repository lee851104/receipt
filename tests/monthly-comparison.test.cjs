const assert = require('node:assert/strict');
const { test } = require('node:test');
const { summarize, difference, compare } = require('../monthly-comparison.js');

const rows = [
  { invoice: 'A', day: 1, category: 0, name: '飯', amount: 100 },
  { invoice: 'A', day: 1, category: 0, name: '飯', amount: 50 },
  { invoice: 'A', day: 1, category: 1, name: '茶', amount: 30 },
  { invoice: 'B', day: 2, category: 0, name: '飯', amount: 200 },
  { invoice: 'C', day: 3, category: 0, name: '贈品', amount: 0 },
];

test('category totals deduplicate invoices and exclude free items from frequency', () => {
  assert.deepEqual(summarize(rows, { category: 0 }, 31), {
    amount: 350, count: 2, days: 2, average: 175, daily: 350 / 31,
  });
});
test('item selection matches the full name and category', () => {
  assert.equal(summarize(rows, { category: 1, name: '茶' }, 31).amount, 30);
  assert.equal(summarize(rows, { category: 0, name: '茶' }, 31).amount, 0);
});
test('a missing month stays unknown, whereas a loaded empty month is zero', () => {
  assert.equal(summarize(null, { category: 0 }, 28), null);
  assert.deepEqual(summarize([], { category: 0 }, 28), {
    amount: 0, count: 0, days: 0, average: null, daily: 0,
  });
  assert.equal(difference(100, null), null);
});
test('deltas handle increase, decrease, equal and zero denominators', () => {
  assert.deepEqual(difference(150, 100), { absolute: 50, percent: 50 });
  assert.deepEqual(difference(50, 100), { absolute: -50, percent: -50 });
  assert.deepEqual(difference(0, 100), { absolute: -100, percent: -100 });
  assert.deepEqual(difference(100, 0), { absolute: 100, percent: null });
  assert.deepEqual(difference(0, 0), { absolute: 0, percent: null });
  assert.deepEqual(difference(100, 100), { absolute: 0, percent: 0 });
});
test('February and March use their own day counts', () => {
  const result = compare({ rows, days: 28 }, { rows, days: 31 }, { category: 0 });
  assert.equal(result.delta.amount.absolute, 0);
  assert.equal(result.previous.daily, 350 / 28);
  assert.equal(result.current.daily, 350 / 31);
  assert.ok(result.delta.daily.absolute < 0);
});

test('negative discounts reduce category totals without creating purchase counts', () => {
  const discounted = [...rows, { invoice: 'A', day: 1, category: 0, name: '折扣', amount: -40 }];
  assert.equal(summarize(discounted, { category: 0 }, 30).amount, 310);
  assert.equal(summarize(discounted, { category: 0 }, 30).count, 2);
  assert.equal(summarize(discounted, { category: 0, name: '飯' }, 30).amount, 350);
});
