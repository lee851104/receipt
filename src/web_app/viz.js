/* The pictures: avatars, the score ring, the side-by-side taste chart, the shared habits, the "why this score" bars
 * and one person's taste. Plain HTML and SVG, sized by CSS, so they read on a phone and in both themes. */
(function (root) {
  'use strict';
  const {h, s, L} = root.Taste;
  let meta = null;
  const traitById = id => meta.traits.find(trait => trait.id === id);

  /** A round photo, or the person's emoji (or first letter) on their own color. */
  function avatar(person, size = 48, extra = '') {
    const box = h('span', {class: ['avatar', extra], 'aria-hidden': 'true'});
    box.style.setProperty('--size', size + 'px');
    box.style.setProperty('--hue', L.hue(person.user_id));
    if (person.photo) box.append(h('img', {src: person.photo, alt: '', loading: 'lazy', decoding: 'async', draggable: 'false'}));
    else box.append(h('span', {class: 'avatar-emoji'}, person.emoji || Array.from(person.name || '?')[0]));
    return box;
  }

  /** The big picture of a card: the photo, or a soft gradient with the emoji large. */
  function cover(person) {
    const box = h('div', {class: 'cover'});
    box.style.setProperty('--hue', L.hue(person.user_id));
    if (person.photo) box.append(h('img', {src: person.photo, alt: person.name + ' 的照片', draggable: 'false', decoding: 'async'}));
    else box.append(h('span', {class: 'cover-emoji', 'aria-hidden': 'true'}, person.emoji || Array.from(person.name || '?')[0]),
      h('span', {class: 'cover-pattern', 'aria-hidden': 'true'}));
    return box;
  }

  /** The score as a ring: its length is how strong, pink for alike, violet for opposite. */
  function ring(percent, band, {size = 112, caption = true, animate = true} = {}) {
    const radius = 50, length = 2 * Math.PI * radius;
    const amount = percent === null || percent === undefined ? 0 : Math.min(100, Math.abs(percent)) / 100;
    const tone = band ? band.tone : 'neutral';
    const arc = s('circle', {class: 'ring-arc', cx: 60, cy: 60, r: radius, 'stroke-dasharray': length.toFixed(2),
      'stroke-dashoffset': (animate ? length : length * (1 - amount)).toFixed(2), transform: 'rotate(-90 60 60)'});
    const number = h('span', {class: 'ring-number'}, animate ? '0%' : L.signedPercent(percent));
    const box = h('div', {class: ['ring', 'tone-' + tone], style: {width: size + 'px', height: size + 'px'},
      role: 'img', 'aria-label': '品味相似度 ' + L.signedPercent(percent) + (band ? '，' + band.label : '')},
    s('svg', {viewBox: '0 0 120 120', 'aria-hidden': 'true'}, s('circle', {class: 'ring-track', cx: 60, cy: 60, r: radius}), arc),
    h('div', {class: 'ring-text', 'aria-hidden': 'true'}, number, caption && band ? h('span', {class: 'ring-caption'}, band.label) : null));
    if (animate && percent !== null && percent !== undefined) {
      const still = root.matchMedia && root.matchMedia('(prefers-reduced-motion: reduce)').matches;
      requestAnimationFrame(() => requestAnimationFrame(() => {
        arc.setAttribute('stroke-dashoffset', (length * (1 - amount)).toFixed(2));
        if (still) { number.textContent = L.signedPercent(percent); return; }
        const began = performance.now();
        const step = moment => {
          const done = Math.min(1, (moment - began) / 900), eased = 1 - Math.pow(1 - done, 3);
          number.textContent = L.signedPercent(Math.round(percent * eased));
          if (done < 1) requestAnimationFrame(step);
        };
        requestAnimationFrame(step);
      }));
    } else if (percent === null || percent === undefined) number.textContent = '—';
    return box;
  }

  /** A small score pill: +82% in the card's tone. */
  function pill(percent, band) {
    return h('span', {class: ['score-pill', 'tone-' + (band ? band.tone : 'neutral')]}, L.signedPercent(percent));
  }

  function badges(person) {
    return h('div', {class: 'badges'},
      person.source === 'invoice' ? h('span', {class: 'badge badge-verified', title: '品味由真實發票算出'}, '✓ 發票認證') : null,
      person.source === 'quiz' ? h('span', {class: 'badge badge-quiz', title: '品味來自問卷自評'}, '問卷自評') : null,
      person.is_demo ? h('span', {class: 'badge badge-demo', title: '虛構的示範帳號'}, '示範') : null);
  }

  /** "🥤 低甜度" chips for what two people share. */
  function sharedChips(alike, limit = 3) {
    return h('div', {class: 'chips'}, alike.slice(0, limit).map(entry => {
      const trait = traitById(entry.trait);
      return h('span', {class: 'chip chip-alike'}, h('span', {'aria-hidden': 'true'}, trait ? trait.emoji : '•'), entry.word);
    }));
  }

  const STATUS = {alike: '一致', differ: '相反', neutral: '有人在中間', unknown: '資料不足'};
  const ORDER = {alike: 0, differ: 1, neutral: 2, unknown: 3};
  const place = value => ((value + 1) / 2 * 100).toFixed(1) + '%';

  /** Two people on every two-sided trait: a track from one end to the other, a pink dot for me and a blue one for
   * them, joined by a line that is green when we lean the same way and orange when we lean apart. */
  function compareChart(rows, theirName) {
    const compared = L.compare(meta.traits, rows).filter(row => row.trait.kind === 'two_sided')
      .sort((a, b) => ORDER[a.status] - ORDER[b.status]);
    const list = h('ul', {class: 'cmp-list'});
    for (const row of compared) {
      const known = row.status !== 'unknown';
      const track = h('div', {class: 'cmp-track', 'aria-hidden': 'true'}, h('i', {class: 'cmp-mid'}));
      if (known) {
        const low = Math.min(row.mine, row.theirs), high = Math.max(row.mine, row.theirs);
        track.append(h('i', {class: 'cmp-link', style: {left: place(low), width: ((high - low) / 2 * 100).toFixed(1) + '%'}}),
          h('i', {class: 'cmp-dot them', style: {left: place(row.theirs)}}), h('i', {class: 'cmp-dot me', style: {left: place(row.mine)}}));
      } else {
        if (row.mine !== null) track.append(h('i', {class: 'cmp-dot me', style: {left: place(row.mine)}}));
        if (row.theirs !== null) track.append(h('i', {class: 'cmp-dot them', style: {left: place(row.theirs)}}));
      }
      const mine = L.lean(row.trait, row.mine), theirs = L.lean(row.trait, row.theirs);
      list.append(h('li', {class: ['cmp-row', 'status-' + row.status],
        'aria-label': row.trait.name + '：你' + mine.word + '，' + theirName + theirs.word + '，' + STATUS[row.status]},
      h('div', {class: 'cmp-head'}, h('span', {class: 'cmp-emoji', 'aria-hidden': 'true'}, row.trait.emoji),
        h('span', {class: 'cmp-name'}, row.trait.short), h('span', {class: 'cmp-tag'}, STATUS[row.status])),
      h('div', {class: 'cmp-line'}, h('span', {class: 'cmp-end'}, row.trait.ends[0]), track, h('span', {class: 'cmp-end cmp-end-right'}, row.trait.ends[1]))));
    }
    return h('div', {class: 'cmp'}, legend(theirName), list);
  }

  function legend(theirName) {
    return h('div', {class: 'legend', 'aria-hidden': 'true'}, h('span', {class: 'legend-item'}, h('i', {class: 'dot dot-me'}), '你'),
      h('span', {class: 'legend-item'}, h('i', {class: 'dot dot-them'}), theirName),
      h('span', {class: 'legend-item'}, h('i', {class: 'bar bar-alike'}), '方向一致'),
      h('span', {class: 'legend-item'}, h('i', {class: 'bar bar-differ'}), '方向相反'));
  }

  const HABIT_STATE = {both: '你們都有', mine: '只有你', theirs: '只有對方', none: '都沒有', unknown: '資料不足'};
  /** The eight habits as tiles: lit for both, half-lit for one of us. */
  function habitGrid(rows) {
    const compared = L.compare(meta.traits, rows).filter(row => row.trait.kind === 'level');
    return h('ul', {class: 'habits'}, compared.map(row => h('li', {class: ['habit', 'habit-' + row.status],
      'aria-label': row.trait.habit + '：' + HABIT_STATE[row.status]},
    h('span', {class: 'habit-emoji', 'aria-hidden': 'true'}, row.trait.emoji), h('span', {class: 'habit-name'}, row.trait.habit),
    h('span', {class: 'habit-state'}, HABIT_STATE[row.status]))));
  }

  /** Each trait's share of the score as a bar from the middle: right and pink adds, left and violet takes away. */
  function contributionBars(contributions, percent, limit = 7) {
    const top = contributions.slice(0, limit);
    const widest = Math.max(0.0001, ...top.map(row => Math.abs(row.part)));
    const list = h('ul', {class: 'why-list'});
    for (const row of top) {
      const trait = traitById(row.trait), points = Math.round(row.part * 100);
      const bar = h('i', {class: ['why-bar', row.part >= 0 ? 'why-plus' : 'why-minus'],
        style: {width: (Math.abs(row.part) / widest * 50).toFixed(1) + '%'}});
      list.append(h('li', {class: 'why-row', 'aria-label': (trait.short || trait.habit) + (points >= 0 ? ' 加 ' : ' 減 ') + Math.abs(points) + ' 分'},
        h('span', {class: 'why-name'}, h('span', {'aria-hidden': 'true'}, trait.emoji + ' '), trait.short || trait.habit),
        h('span', {class: 'why-track', 'aria-hidden': 'true'}, h('i', {class: 'why-zero'}), bar),
        h('span', {class: ['why-points', points >= 0 ? 'plus' : 'minus']}, (points > 0 ? '+' : points < 0 ? '−' : '') + Math.abs(points))));
    }
    const rest = contributions.slice(limit).reduce((sum, row) => sum + row.part, 0);
    return h('div', {class: 'why'}, list,
      h('p', {class: 'why-total'}, contributions.length > limit ? '其他 ' + (contributions.length - limit) + ' 項合計 ' +
        (rest >= 0 ? '+' : '−') + Math.abs(Math.round(rest * 100)) + '，' : '', '全部加起來 = ', h('strong', null, L.signedPercent(percent))));
  }

  /** One person's taste: where they sit on each two-sided trait, then their habits. */
  function tasteChart(vector) {
    const values = vector || meta.traits.map(() => null);
    const list = h('ul', {class: 'cmp-list solo'});
    meta.traits.forEach((trait, index) => {
      if (trait.kind !== 'two_sided') return;
      const value = values[index], word = L.lean(trait, value);
      const track = h('div', {class: 'cmp-track', 'aria-hidden': 'true'}, h('i', {class: 'cmp-mid'}));
      if (value !== null) {
        const from = Math.min(0, value), to = Math.max(0, value);
        track.append(h('i', {class: 'cmp-fill', style: {left: place(from), width: ((to - from) / 2 * 100).toFixed(1) + '%'}}),
          h('i', {class: 'cmp-dot me', style: {left: place(value)}}));
      }
      list.append(h('li', {class: ['cmp-row', value === null ? 'status-unknown' : 'status-solo'], 'aria-label': trait.name + '：' + word.word},
        h('div', {class: 'cmp-head'}, h('span', {class: 'cmp-emoji', 'aria-hidden': 'true'}, trait.emoji),
          h('span', {class: 'cmp-name'}, trait.short), h('span', {class: 'cmp-tag'}, word.word)),
        h('div', {class: 'cmp-line'}, h('span', {class: 'cmp-end'}, trait.ends[0]), track, h('span', {class: 'cmp-end cmp-end-right'}, trait.ends[1]))));
    });
    const habits = h('ul', {class: 'habits solo'}, meta.traits.map((trait, index) => {
      if (trait.kind !== 'level') return null;
      const value = values[index], word = L.lean(trait, value);
      return h('li', {class: ['habit', value === null ? 'habit-unknown' : 'habit-level-' + word.strength], 'aria-label': trait.habit + '：' + word.word},
        h('span', {class: 'habit-emoji', 'aria-hidden': 'true'}, trait.emoji), h('span', {class: 'habit-name'}, trait.habit),
        h('span', {class: 'habit-state'}, word.word));
    }));
    return h('div', {class: 'taste-chart'}, list, h('h4', {class: 'subhead'}, '生活習慣'), habits);
  }

  /** The one-line reading of a comparison: how many traits point the same way. */
  function agreementLine(rows) {
    const summary = L.agreement(L.compare(meta.traits, rows));
    if (!summary.comparable) return '你們的資料還不夠多，暫時比較不出來。';
    let text = summary.comparable + ' 項生活取向裡，你們有 ' + summary.alike + ' 項方向一致';
    if (summary.differ) text += '、' + summary.differ + ' 項剛好相反';
    if (summary.habits.length) text += '，也都' + summary.habits.slice(0, 3).map(trait => trait.habit).join('、');
    return text + '。';
  }

  root.TasteViz = {setMeta: value => { meta = value; }, traitById, avatar, cover, ring, pill, badges, sharedChips,
    compareChart, habitGrid, contributionBars, tasteChart, agreementLine};
})(globalThis);
