const test = require('node:test');
const assert = require('node:assert/strict');
const core = require('./review_core.js');
const row = () => ({id:'dummy',name:'虛構茶',category:null,source:'real',suggested_category:1,review_status:'model_pending',name_only_context_needed:false});
test('all predictions are excluded until explicit confirmation', () => {
  assert.deepEqual(core.confirmedRows([row()]), []);
});
test('explicit review exports the corrected class, never the suggested class', () => {
  const value = row();
  core.confirm(value, 2, true);
  assert.equal(core.confirmedRows([value])[0].category, 2);
  assert.equal(core.confirmedRows([value])[0].review_status, 'human_confirmed');
  assert.equal(core.confirmedRows([value])[0].source, 'real');
  core.choose(value, 3);
  assert.deepEqual(core.confirmedRows([value]), []);
});
test('undecided and invalid values cannot be confirmed', () => {
  for (const value of [10, -1, null, NaN, '1', true]) {
    const item = row();
    core.confirm(item, value, true);
    assert.deepEqual(core.confirmedRows([item]), []);
  }
});
test('uncheck revokes confirmation and context survives export', () => {
  const item = row();
  item.name_only_context_needed = true;
  core.confirm(item, 1, true);
  assert.equal(core.confirmedRows([item])[0].name_only_context_needed, true);
  core.confirm(item, 1, false);
  assert.deepEqual(core.confirmedRows([item]), []);
});
test('JSON script data escapes closing tags and preserves text', () => {
  const item = {name:'</script><script>evil()</script>'};
  const safe = core.safeJson(item);
  assert.ok(!safe.includes('<'));
  assert.deepEqual(JSON.parse(safe), item);
});
