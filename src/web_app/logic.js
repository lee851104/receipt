/* The dating app's pure rules: no DOM, so node --test can run them (tests/web-app-logic.test.cjs). */
(function (root, factory) {
  const logic = factory();
  if (typeof module === 'object' && module.exports) module.exports = logic;
  else root.TasteLogic = logic;
})(globalThis, function () {
  'use strict';

  const LEAN = 0.15;   // weaker than this is "no real preference" (src/api/dating.py uses the same)
  const HABIT = 0.3;

  const MESSAGES = {
    not_authenticated: '登入已失效，請重新登入。',
    bad_credentials: '帳號或密碼錯誤。',
    username_taken: '這個帳號已經有人使用，換一個試試。',
    profile_incomplete: '先完成個人檔案，才能開始配對。',
    no_taste: '先做品味問卷或上傳發票，才能開始配對。',
    no_city: '先在個人檔案設定所在縣市，才能用地區篩選。',
    invalid_quiz: '問卷至少要回答 5 題「二選一」的題目。',
    invalid_photo: '這張照片無法使用，請換一張 JPG 或 PNG 照片。',
    file_too_large: '檔案太大了，請換一個小一點的檔案。',
    length_required: '檔案上傳失敗，請重新選擇檔案。',
    slow_down: '訊息傳得太快了，休息一下再傳。',
    demo_user_read_only: '示範帳號可以瀏覽、配對和聊天，但不能修改資料。',
    not_found: '找不到這個人或對話，可能已經被移除。',
    self: '不能對自己這樣做喔。',
    invalid_csv: '發票檔案格式不符：',
    job_in_progress: '發票還在分析中，請稍後再試。',
    wrong_password: '密碼不正確。',
    model_unavailable: '分析模型暫時無法使用，請稍後再試。',
    invalid_report: '請選擇檢舉原因。',
    internal_error: '系統暫時出了點問題，請稍後再試。',
    no_home_area: '目前資料不足以判斷生活圈。'
  };
  const FIELDS = {username: '帳號', password: '密碼', display_name: '暱稱', bio: '自我介紹', body: '訊息',
    birth_year: '出生年', age_min: '年齡範圍', age_max: '年齡範圍', note: '補充說明', new_password: '新密碼'};

  /** The words to show for an error answer: status and the parsed JSON body. */
  function errorText(status, body) {
    const detail = body && body.detail;
    if (status === 422 && Array.isArray(detail)) {
      const names = [...new Set(detail.map(item => FIELDS[item.loc && item.loc[item.loc.length - 1]]).filter(Boolean))];
      return (names.length ? names.join('、') : '輸入的資料') + '格式不符，請再檢查一次。';
    }
    if (detail === 'invalid_profile') {
      const message = String(body.message || '');
      if (message.startsWith('birth_year')) return '需要年滿 18 歲才能使用。';
      if (message.startsWith('age_min')) return '年齡範圍的下限不能大於上限。';
      return '個人檔案有欄位格式不符，請再檢查一次。';
    }
    if (detail === 'invalid_csv') return MESSAGES.invalid_csv + (body.message || '請確認是財政部電子發票的 CSV。');
    if (typeof detail === 'string' && MESSAGES[detail]) return MESSAGES[detail];
    if (status === 413) return MESSAGES.file_too_large;
    if (status === 429) return MESSAGES.slow_down;
    return '暫時無法完成，請稍後再試。';
  }

  /** +82%, −45%, 0%, or — when there is no score. */
  function signedPercent(percent) {
    if (percent === null || percent === undefined || !Number.isFinite(percent)) return '—';
    return (percent > 0 ? '+' : percent < 0 ? '−' : '') + Math.abs(Math.round(percent)) + '%';
  }

  function side(value) { return value < 0 ? 0 : 1; }

  /** How one person sits on one trait: the end they lean to and how strongly (0 none, 1 a bit, 2 clearly, 3 very). */
  function lean(trait, value) {
    if (value === null || value === undefined) return {word: '資料不足', strength: 0, known: false};
    if (trait.kind === 'level') {
      const strength = value >= 0.6 ? 3 : value >= HABIT ? 2 : value > 0.05 ? 1 : 0;
      return {word: ['很少', '偶爾', '有時', '常常'][strength], strength, known: true};
    }
    const size = Math.abs(value);
    if (size < LEAN) return {word: '剛好中間', strength: 0, known: true};
    return {word: trait.ends[side(value)], strength: size >= 0.6 ? 3 : size >= 0.35 ? 2 : 1, known: true};
  }

  /** Each trait of two people side by side: alike, differ, neutral or unknown for two-sided traits; both, mine,
   * theirs or none for habits. rows are {id, mine, theirs} in the traits' order. */
  function compare(traits, rows) {
    const byId = new Map(rows.map(row => [row.id, row]));
    return traits.map(trait => {
      const row = byId.get(trait.id) || {mine: null, theirs: null};
      const mine = row.mine ?? null, theirs = row.theirs ?? null;
      let status;
      if (mine === null || theirs === null) status = 'unknown';
      else if (trait.kind === 'level') {
        status = mine >= HABIT && theirs >= HABIT ? 'both' : mine >= HABIT ? 'mine' : theirs >= HABIT ? 'theirs' : 'none';
      } else if (Math.abs(mine) < LEAN || Math.abs(theirs) < LEAN) status = 'neutral';
      else status = side(mine) === side(theirs) ? 'alike' : 'differ';
      return {trait, mine, theirs, status};
    });
  }

  /** "18 項裡有 N 項能比較，M 項方向一致": the counts behind the one-line summary of a comparison. */
  function agreement(compared) {
    const twoSided = compared.filter(row => row.trait.kind === 'two_sided' && row.status !== 'unknown');
    return {comparable: twoSided.length, alike: twoSided.filter(row => row.status === 'alike').length,
      differ: twoSided.filter(row => row.status === 'differ').length,
      habits: compared.filter(row => row.status === 'both').map(row => row.trait)};
  }

  /** Whether a released drag likes, passes or snaps back: far enough, or a quick flick. */
  function swipeDecision(dx, ms, width) {
    const far = Math.min(120, Math.max(60, width * 0.28));
    const speed = Math.abs(dx) / Math.max(ms, 1);
    if (dx > far || (dx > 40 && speed > 0.6)) return 'like';
    if (dx < -far || (dx < -40 && speed > 0.6)) return 'pass';
    return null;
  }

  const pad = number => String(number).padStart(2, '0');
  function clock(iso) {
    const time = new Date(iso), hours = time.getHours();
    return (hours < 12 ? '上午 ' : '下午 ') + ((hours % 12) || 12) + ':' + pad(time.getMinutes());
  }
  function sameDay(a, b) { return a.getFullYear() === b.getFullYear() && a.getMonth() === b.getMonth() && a.getDate() === b.getDate(); }
  /** 今天, 昨天, 11月20日 or 2025年11月20日 for the day separators in a chat. */
  function dayLabel(iso, now = Date.now()) {
    const time = new Date(iso), today = new Date(now), yesterday = new Date(now - 86400000);
    if (sameDay(time, today)) return '今天';
    if (sameDay(time, yesterday)) return '昨天';
    const day = (time.getMonth() + 1) + '月' + time.getDate() + '日';
    return time.getFullYear() === today.getFullYear() ? day : time.getFullYear() + '年' + day;
  }
  /** 剛剛, 5 分鐘前, 下午 3:05, 昨天 or 11/20 for the chat list. */
  function ago(iso, now = Date.now()) {
    const time = new Date(iso), seconds = (now - time.getTime()) / 1000;
    if (seconds < 60) return '剛剛';
    if (seconds < 3600) return Math.floor(seconds / 60) + ' 分鐘前';
    if (sameDay(time, new Date(now))) return clock(iso);
    if (sameDay(time, new Date(now - 86400000))) return '昨天';
    return (time.getMonth() + 1) + '/' + time.getDate();
  }

  /** A soft color for someone without a photo, the same for them everywhere. */
  function hue(id) { return ((Number(id) || 0) * 47 + 330) % 360; }

  /** How complete a profile is, 0-100, and the next thing worth doing. */
  function completion(me) {
    const profile = me && me.profile, taste = me && me.taste;
    const steps = [
      ['基本資料', !!profile && me.missing.length === 0, 30],
      ['品味', !!(taste && taste.source), 25],
      ['照片或頭像', !!(profile && (profile.photo || profile.emoji)), 15],
      ['自我介紹', !!(profile && profile.bio && profile.bio.length >= 10), 15],
      ['交友目的', !!(profile && profile.intent), 5],
      ['發票認證', !!(taste && taste.source === 'invoice'), 10]
    ];
    const percent = steps.reduce((sum, [, done, weight]) => sum + (done ? weight : 0), 0);
    const next = steps.find(([, done]) => !done);
    return {percent, next: next ? next[0] : null};
  }

  /** The quiz's 18 answers in the traits' order: two-sided answers as given (null when skipped), habits from the
   * chosen chips. */
  function quizVector(traits, answers, habits, habitValue) {
    return traits.map(trait => trait.kind === 'two_sided'
      ? (Object.prototype.hasOwnProperty.call(answers, trait.id) ? answers[trait.id] : null)
      : (habits.has(trait.id) ? habitValue : 0));
  }
  /** quizVector's inverse, so an earlier quiz fills the form again. */
  function quizState(traits, vector) {
    const answers = {}, habits = new Set();
    if (!Array.isArray(vector)) return {answers, habits};
    traits.forEach((trait, index) => {
      const value = vector[index];
      if (trait.kind === 'two_sided') { if (value !== null && value !== undefined) answers[trait.id] = value; }
      else if (value >= HABIT) habits.add(trait.id);
    });
    return {answers, habits};
  }
  function answeredTwoSided(answers) { return Object.values(answers).filter(value => value !== null).length; }

  /** The birth years someone of min to max years can pick, youngest first. */
  function birthYears(year, min, max) {
    const years = [];
    for (let age = min; age <= max; age++) years.push(year - age);
    return years;
  }

  /** A chat message as it will be sent: trimmed; null when empty or too long. */
  function cleanMessage(text, max) {
    const trimmed = String(text || '').trim();
    return trimmed && Array.from(trimmed).length <= max ? trimmed : null;
  }

  /** Messages grouped under day separators: [{day, messages}]. */
  function byDay(messages, now = Date.now()) {
    const groups = [];
    for (const message of messages) {
      const day = dayLabel(message.created_at, now);
      if (!groups.length || groups[groups.length - 1].day !== day) groups.push({day, messages: []});
      groups[groups.length - 1].messages.push(message);
    }
    return groups;
  }

  /** The person's age and city as one short line: 28 · 臺北市. */
  function subtitle(person) {
    return [person.age, person.city].filter(value => value !== null && value !== undefined && value !== '').join(' · ');
  }

  return {errorText, signedPercent, lean, compare, agreement, swipeDecision, clock, dayLabel, ago, hue, completion,
    quizVector, quizState, answeredTwoSided, birthYears, cleanMessage, byDay, subtitle, LEAN, HABIT};
});
