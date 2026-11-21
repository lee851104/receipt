// The dating app's pure rules (src/web_app/logic.js): formatting, comparison, swipes, the quiz and error words.
const test = require('node:test');
const assert = require('node:assert/strict');
const L = require('../src/web_app/logic.js');

const traits = [
  {id: 'spend', kind: 'two_sided', ends: ['省錢', '享受'], short: '花費'},
  {id: 'sweet', kind: 'two_sided', ends: ['低甜度', '高甜度'], short: '甜度'},
  {id: 'travel', kind: 'two_sided', ends: ['待在生活圈', '常出遊'], short: '出遊'},
  {id: 'sport', kind: 'level', habit: '運動'},
  {id: 'pets_cat', kind: 'level', habit: '養貓'}
];

test('scores read as signed whole percentages', () => {
  assert.equal(L.signedPercent(82), '+82%');
  assert.equal(L.signedPercent(-45), '−45%');
  assert.equal(L.signedPercent(0), '0%');
  assert.equal(L.signedPercent(null), '—');
  assert.equal(L.signedPercent(Number.NaN), '—');
});

test('a value leans to an end, a habit to how often', () => {
  assert.deepEqual(L.lean(traits[0], 0.7), {word: '享受', strength: 3, known: true});
  assert.deepEqual(L.lean(traits[0], -0.4), {word: '省錢', strength: 2, known: true});
  assert.equal(L.lean(traits[0], 0.1).word, '剛好中間');
  assert.equal(L.lean(traits[0], null).known, false);
  assert.equal(L.lean(traits[3], 0.7).word, '常常');
  assert.equal(L.lean(traits[3], 0).word, '很少');
});

test('two people compare trait by trait', () => {
  const rows = [
    {id: 'spend', mine: 0.5, theirs: 0.6}, {id: 'sweet', mine: 0.5, theirs: -0.6}, {id: 'travel', mine: 0.05, theirs: 0.8},
    {id: 'sport', mine: 0.7, theirs: 0.7}, {id: 'pets_cat', mine: 0, theirs: null}
  ];
  const compared = L.compare(traits, rows);
  assert.deepEqual(compared.map(row => row.status), ['alike', 'differ', 'neutral', 'both', 'unknown']);
  const summary = L.agreement(compared);
  assert.deepEqual({comparable: summary.comparable, alike: summary.alike, differ: summary.differ}, {comparable: 3, alike: 1, differ: 1});
  assert.deepEqual(summary.habits.map(trait => trait.id), ['sport']);
  assert.equal(L.compare(traits, []).every(row => row.status === 'unknown'), true);
});

test('a drag likes or passes when far or quick enough, else snaps back', () => {
  assert.equal(L.swipeDecision(130, 400, 360), 'like');
  assert.equal(L.swipeDecision(-130, 400, 360), 'pass');
  assert.equal(L.swipeDecision(50, 60, 360), 'like');     // a flick
  assert.equal(L.swipeDecision(50, 400, 360), null);      // slow and short
  assert.equal(L.swipeDecision(0, 10, 360), null);
});

test('times read the way a chat shows them', () => {
  const now = new Date(2026, 10, 22, 15, 0).getTime();
  assert.equal(L.ago(new Date(now - 20 * 1000).toISOString(), now), '剛剛');
  assert.equal(L.ago(new Date(now - 5 * 60 * 1000).toISOString(), now), '5 分鐘前');
  assert.equal(L.ago(new Date(2026, 10, 22, 9, 5).toISOString(), now), '上午 9:05');
  assert.equal(L.ago(new Date(2026, 10, 21, 20, 0).toISOString(), now), '昨天');
  assert.equal(L.ago(new Date(2026, 9, 3, 20, 0).toISOString(), now), '10/3');
  assert.equal(L.clock(new Date(2026, 10, 22, 0, 7).toISOString()), '上午 12:07');
  assert.equal(L.clock(new Date(2026, 10, 22, 13, 30).toISOString()), '下午 1:30');
  assert.equal(L.dayLabel(new Date(2026, 10, 22, 1).toISOString(), now), '今天');
  assert.equal(L.dayLabel(new Date(2025, 0, 2).toISOString(), now), '2025年1月2日');
  const groups = L.byDay([{created_at: new Date(2026, 10, 21, 9).toISOString()}, {created_at: new Date(2026, 10, 22, 9).toISOString()},
    {created_at: new Date(2026, 10, 22, 10).toISOString()}], now);
  assert.deepEqual(groups.map(group => [group.day, group.messages.length]), [['昨天', 1], ['今天', 2]]);
});

test('the quiz turns into 18-style answers and back', () => {
  const vector = L.quizVector(traits, {spend: -1, sweet: 0.5}, new Set(['pets_cat']), 0.7);
  assert.deepEqual(vector, [-1, 0.5, null, 0, 0.7]);
  const state = L.quizState(traits, vector);
  assert.deepEqual(state.answers, {spend: -1, sweet: 0.5});
  assert.deepEqual([...state.habits], ['pets_cat']);
  assert.equal(L.answeredTwoSided(state.answers), 2);
  assert.deepEqual(L.quizState(traits, null), {answers: {}, habits: new Set()});
});

test('profile completion points to the next step', () => {
  const base = {missing: [], profile: {photo: null, emoji: null, bio: '', intent: null}, taste: {source: null}};
  assert.deepEqual(L.completion(base), {percent: 30, next: '品味'});
  const done = {missing: [], profile: {photo: '/p', emoji: null, bio: '喜歡咖啡和貓，也喜歡散步', intent: 'chat'}, taste: {source: 'invoice'}};
  assert.deepEqual(L.completion(done), {percent: 100, next: null});
  assert.equal(L.completion({missing: ['gender'], profile: null, taste: {source: null}}).percent, 0);
});

test('messages are trimmed and limited, birth years run youngest first', () => {
  assert.equal(L.cleanMessage('  嗨  ', 500), '嗨');
  assert.equal(L.cleanMessage('   ', 500), null);
  assert.equal(L.cleanMessage('哈'.repeat(501), 500), null);
  assert.deepEqual(L.birthYears(2026, 18, 20), [2008, 2007, 2006]);
  assert.equal(L.subtitle({age: 28, city: '臺北市'}), '28 · 臺北市');
  assert.equal(L.subtitle({age: 28, city: null}), '28');
});

test('error answers become words a person understands', () => {
  assert.equal(L.errorText(409, {detail: 'no_taste'}), '先做品味問卷或上傳發票，才能開始配對。');
  assert.equal(L.errorText(422, {detail: 'invalid_profile', message: 'birth_year: you must be 18 or older'}), '需要年滿 18 歲才能使用。');
  assert.equal(L.errorText(422, {detail: [{loc: ['body', 'bio']}, {loc: ['body', 'body']}]}), '自我介紹、訊息格式不符，請再檢查一次。');
  assert.equal(L.errorText(400, {detail: 'invalid_csv', message: 'no rows'}), '發票檔案格式不符：no rows');
  assert.equal(L.errorText(429, null), '訊息傳得太快了，休息一下再傳。');
  assert.equal(L.errorText(418, {detail: 'teapot'}), '暫時無法完成，請稍後再試。');
});

test('everyone gets a steady color', () => {
  assert.equal(L.hue(1), L.hue(1));
  assert.notEqual(L.hue(1), L.hue(2));
  assert.ok(L.hue(12345) >= 0 && L.hue(12345) < 360);
});
