/* Who the match page shows and what it says; the page and its tests share these pure functions. */
(function (root) {
  'use strict';
  const similarity = typeof module !== 'undefined' && module.exports ? require('./trait-similarity.js') : root.TraitSimilarity;
  const RANGES = Object.freeze([
    { level: null, label: '不限' }, { level: 0, label: '同一區' }, { level: 1, label: '同縣市' }, { level: 2, label: '同地區' }]);
  // Code-point order, as Python sorts names, so both sides break ties the same way.
  const byName = (a, b) => (a < b ? -1 : a > b ? 1 : 0);
  const signed = similarity.signed;

  // Everyone who can be compared with me, in the payload's order, with their score and each cell's share of it.
  function scored(data) {
    return data.people.map(person => ({ person, ...similarity.compare(data.me.vector, person.vector, data.model) }))
      .filter(entry => entry.comparable);
  }

  // The bar on one side, as the whole percentage the page prints: +30% for matches, −10% for opposites.
  const bar = (settings, opposite) => (opposite ? -settings.opposite_score : settings.min_score);

  // People past the bar on one side, then within the chosen distance; strongest first, ties by name.
  // The bar is checked on the printed whole percentage, so a card reading +30% is always on the list.
  function pick(entries, settings, opposite, range) {
    const line = similarity.percent(bar(settings, opposite));
    const eligible = entries.filter(entry => (opposite ? similarity.percent(entry.score) <= line : similarity.percent(entry.score) >= line));
    const within = eligible.filter(entry => range === null || entry.person.distance <= range)
      .sort((a, b) => (opposite ? a.score - b.score : b.score - a.score) || byName(a.person.name, b.person.name));
    return { eligible: eligible.length, within: within.length, shown: within.slice(0, settings.top) };
  }

  const end = (trait, value) => trait.ends[value > 0 ? 1 : 0];
  const latin = /[A-Za-z0-9]/;
  // Chinese next to Latin letters or digits gets a space, as the report writes 「3C 投入」.
  function words(...pieces) {
    return pieces.reduce((text, piece) => {
      const gap = text && piece && latin.test(text[text.length - 1]) !== latin.test(piece[0]);
      return text + (gap ? ' ' : '') + piece;
    }, '');
  }

  // How one cell reads on a card: a habit both have, both on one side, or opposite sides.
  function phrase(trait, mine, theirs) {
    if (trait.kind === 'level') return words('都有', trait.habit, '的紀錄');
    if (mine * theirs > 0) return '都偏' + end(trait, mine);
    return '你偏' + end(trait, mine) + '，對方偏' + end(trait, theirs);
  }

  // The cell that adds most to the score and the one that takes most away; null when there is none.
  function reasons(entry, me, traits) {
    let best = null, worst = null;
    entry.parts.forEach((part, index) => {
      if (part === null) return;
      if (part > 0 && (best === null || part > entry.parts[best])) best = index;
      if (part < 0 && (worst === null || part < entry.parts[worst])) worst = index;
    });
    const describe = index => (index === null ? null : phrase(traits[index], me[index], entry.person.vector[index]));
    return { alike: describe(best), unlike: describe(worst) };
  }

  // My three strongest two-sided leanings (at least 0.2 either way) and the habits on record.
  function mine(vector, traits) {
    if (!vector) return { lean: '資料還不夠，看不出品味特質', habits: '' };
    const leaning = traits.map((trait, index) => ({ trait, index, value: vector[index] }))
      .filter(({ trait, value }) => trait.kind === 'two_sided' && value !== null && Math.abs(value) >= 0.2)
      .sort((a, b) => Math.abs(b.value) - Math.abs(a.value) || a.index - b.index)
      .slice(0, 3).map(({ trait, value }) => '偏' + end(trait, value));
    const habits = traits.filter((trait, index) => trait.kind === 'level' && vector[index] > 0).map(trait => trait.habit);
    if (!leaning.length && !habits.length) return { lean: '品味特質還不明顯', habits: '' };
    return { lean: leaning.join('・'), habits: habits.length ? words('也有', habits.join('、'), '的紀錄') : '' };
  }

  function status(result, settings, opposite) {
    const line = signed(bar(settings, opposite)) + (opposite ? ' 以下' : ' 以上');
    if (!result.eligible) return opposite ? '目前沒有和你明顯相反的人（' + line + '）。' : '目前沒有品味夠相似的人（' + line + '）。';
    if (!result.within) return '這個距離內沒有品味相似度 ' + line + '的人，試試放寬距離。';
    return result.within + ' 位品味相似度 ' + line + (result.within > settings.top ? '，顯示前 ' + settings.top + ' 位' : '') + '。';
  }

  function card(entry, data) {
    const why = reasons(entry, data.me.vector, data.traits);
    return { person: entry.person, name: entry.person.name, score: signed(entry.score), percent: similarity.percent(entry.score),
      opposite: entry.score < 0, place: entry.person.place, alike: why.alike, unlike: why.unlike };
  }

  // Everything the page shows for a choice of distance (null for any) and whether opposites are wanted.
  function view(data, choice) {
    const { settings, me } = data;
    const profile = mine(me.vector, data.traits);
    if (!me.vector) {
      return { ready: false, mine: profile, thin: '你的資料還不夠（有效品項少於 ' + settings.min_items + ' 筆），先累積更多發票，再來找同好。' };
    }
    const entries = scored(data), located = me.areas.length > 0, range = located ? choice.range : null;
    const list = opposite => {
      const result = pick(entries, settings, opposite, range);
      return { status: status(result, settings, opposite), cards: result.shown.map(entry => card(entry, data)) };
    };
    return {
      ready: true, mine: profile,
      note: located ? '你的生活圈：' + me.areas.join('、') : '看不出你的生活圈，只能選「不限」。',
      ranges: RANGES.map(option => ({ ...option, disabled: option.level !== null && !located })),
      match: list(false), opposite: choice.opposite ? list(true) : null,
    };
  }

  const api = Object.freeze({ RANGES, scored, pick, phrase, reasons, mine, status, view });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.MatchFilter = api;
})(globalThis);
