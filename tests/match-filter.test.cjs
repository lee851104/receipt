const { test } = require('node:test');
const assert = require('node:assert/strict');
const { recommend } = require('../src/web/match-filter.js');

const thresholds = { taste: 0.8, taste_same_area: 0.7 };
const people = [
  { name: 'A', taste: 80, areas: [] },
  { name: 'B', taste: 79, areas: ['高雄市苓雅區'] },
  { name: 'C', taste: 70, areas: ['高雄市苓雅區'] },
  { name: 'D', taste: 69, areas: ['高雄市苓雅區'] },
  { name: 'E', taste: 75, areas: ['臺北市信義區'] },
];
const names = list => list.map(person => person.name);

test('without a confirmed area only the higher bar applies', () => {
  assert.deepEqual(names(recommend(people, [], thresholds)), ['A']);
});

test('a confirmed shared area lowers the bar to 70%', () => {
  assert.deepEqual(names(recommend(people, ['高雄市苓雅區'], thresholds)), ['A', 'B', 'C']);
});

test('an area that nobody shares changes nothing', () => {
  assert.deepEqual(names(recommend(people, ['高雄市新興區'], thresholds)), ['A']);
});
