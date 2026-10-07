const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { compare, percent } = require('../src/web/trait-similarity.js');

const fixture = JSON.parse(fs.readFileSync(path.join(__dirname, 'fixtures', 'similarity-cases.json'), 'utf8'));

for (const item of fixture.cases) {
  test(item.name, () => {
    const result = compare(item.mine, item.theirs, item.model ?? fixture.model);
    assert.equal(result.comparable, item.comparable);
    if (!item.comparable) {
      assert.equal(result.score, null);
      assert.equal(result.parts, null);
      return;
    }
    assert.ok(Math.abs(result.score - item.score) < 1e-9, `${result.score} vs ${item.score}`);
    result.parts.forEach((part, index) => {
      if (item.parts[index] === null) assert.equal(part, null);
      else assert.ok(Math.abs(part - item.parts[index]) < 1e-9, `cell ${index}: ${part} vs ${item.parts[index]}`);
    });
  });
}

test('percent rounds halves up, as the Python side does', () => {
  assert.equal(percent(0.625), 63);
  assert.equal(percent(-0.355), -35);
  assert.equal(percent(0.1234), 12);
});
