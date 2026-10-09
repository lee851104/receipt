/* Where the taste network draws every dot and line, and what its sentences say; the page only turns this into SVG. */
(function (root) {
  'use strict';
  const node = typeof module !== 'undefined' && module.exports;
  const similarity = node ? require('./trait-similarity.js') : root.TraitSimilarity;
  const cards = node ? require('./match-filter.js') : root.MatchFilter;

  // Desktop puts the two fans side by side; phones stack them, the left person on top. All sizes are SVG units.
  const SHAPES = Object.freeze({
    desktop: Object.freeze({ width: 1200, height: 640, centers: [[430, 325], [770, 325]], stretch: [1, 0.86],
      near: 110, far: 270, none: 72, ring: 312, stagger: 14, dot: [3.5, 9], font: 13 }),
    mobile: Object.freeze({ width: 600, height: 820, centers: [[300, 290], [300, 530]], stretch: [1, 0.9],
      near: 70, far: 190, none: 46, ring: 228, stagger: 12, dot: [5, 11], font: 18 }),
  });
  const FAN = 78 * Math.PI / 180;      // each fan opens 78° either side of straight out
  const SPREAD = 0.045;                // radians between neighbouring signals of one trait
  const LABEL_STEPS = 3;               // a crowded label moves outwards this many times before it hides
  const PAD = 3;                       // the gap kept around every label

  // Every check a person's taste data must pass before the graph trusts it.
  function validate(person, data) {
    const fail = () => { throw new Error('品味資料不正確，請回配對清單重新選擇。'); };
    const finite = value => typeof value === 'number' && Number.isFinite(value);
    if (!person || typeof person !== 'object') fail();
    const { vector, pushes, signals } = person;
    if (!Array.isArray(vector) || vector.length !== data.traits.length) fail();
    vector.forEach((value, index) => {
      const low = data.traits[index].kind === 'level' ? 0 : -1;
      if (value !== null && (!finite(value) || value < low || value > 1)) fail();
    });
    if (!Array.isArray(pushes) || pushes.length !== data.traits.length) fail();
    pushes.forEach((list, index) => {
      if (!Array.isArray(list) || list.length !== data.traits[index].signals.length
        || list.some(value => value !== null && !finite(value))) fail();
    });
    if (!Array.isArray(signals) || signals.length !== data.signals.length
      || signals.some(value => value !== null && !finite(value))) fail();
    return { vector: [...vector], pushes: pushes.map(list => [...list]), signals: [...signals] };
  }

  // The label a trait wears: the end it leans to, or its short name or habit word.
  function traitLabel(trait, value) {
    if (trait.kind === 'level') return trait.habit;
    if (value === null || value === 0) return trait.short;
    return trait.ends[value > 0 ? 1 : 0];
  }

  // Roughly how wide a label is: a full em for Chinese, a little over half for Latin letters and digits.
  const textWidth = (text, font) => Array.from(text).reduce((sum, letter) => sum + (letter.charCodeAt(0) > 0x2e80 ? 1 : 0.6), 0) * font;

  // The box a label covers, with a small gap around it, for text anchored at (x, y).
  function labelRect(text, font, x, y, anchor) {
    const width = textWidth(text, font), left = anchor === 'end' ? x - width : x;
    return { left: left - PAD, right: left + width + PAD, top: y - font - PAD, bottom: y + PAD };
  }

  const overlaps = (a, b) => a.left < b.right && b.left < a.right && a.top < b.bottom && b.top < a.bottom;

  // A point d away from a fan's centre at angle e (positive e is the first trait's side), in SVG coordinates.
  function place(shape, side, d, e) {
    const [cx, cy] = shape.centers[side === 'a' ? 0 : 1];
    const [sx, sy] = shape.stretch;
    const out = d * Math.cos(e), across = d * Math.sin(e);
    if (shape === SHAPES.mobile) return { x: cx - across * sx, y: side === 'a' ? cy - out * sy : cy + out * sy };
    return { x: side === 'a' ? cx - out * sx : cx + out * sx, y: cy - across * sy };
  }

  // Each trait's fixed angle: spread evenly in configuration order, the first at the top (on the left on phones).
  const angle = (index, count) => FAN - 2 * FAN * (index + 0.5) / count;

  // Labels go in strongest first; one that would cover a dot or another label moves outwards, then hides.
  function placeLabels(traits, shape, side) {
    const taken = traits.map(trait => ({ left: trait.x - trait.r, right: trait.x + trait.r, top: trait.y - trait.r, bottom: trait.y + trait.r }));
    const strength = trait => (trait.value === null ? -1 : Math.abs(trait.value));
    for (const trait of [...traits].sort((a, b) => strength(b) - strength(a) || a.index - b.index)) {
      trait.labelShown = false;
      for (let step = 0; step <= LABEL_STEPS && !trait.labelShown; step++) {
        const at = place(shape, side, trait.distance + step * shape.font * 1.2, trait.angle);
        let box;
        // Phones hang a label away from the middle of the fan, so moving it outwards never lands it on its own dot.
        if (shape === SHAPES.mobile && trait.angle > 0) box = { x: at.x - trait.r - 4, y: at.y + shape.font * 0.35, anchor: 'end' };
        else if (shape === SHAPES.mobile) box = { x: at.x + trait.r + 4, y: at.y + shape.font * 0.35, anchor: 'start' };
        else if (side === 'a') box = { x: at.x - trait.r - 4, y: at.y - 6, anchor: 'end' };
        else box = { x: at.x + trait.r + 4, y: at.y - 6, anchor: 'start' };
        const rect = labelRect(trait.label, shape.font, box.x, box.y, box.anchor);
        if (taken.some(other => overlaps(rect, other))) continue;
        taken.push(rect);
        Object.assign(trait, { labelShown: true, labelX: box.x, labelY: box.y, labelAnchor: box.anchor });
      }
    }
  }

  const fixed = number => number.toFixed(1);

  // Every dot and line of the graph for two people, from the trait order in data and each person's values.
  function layout(data, left, right, mobile) {
    const shape = mobile ? SHAPES.mobile : SHAPES.desktop;
    const count = data.traits.length;
    // A signal sits beside the first trait that lists it; later traits only get another line.
    const home = new Map();
    data.traits.forEach((trait, index) => trait.signals.forEach(id => { if (!home.has(id)) home.set(id, index); }));
    const sides = [['a', left], ['b', right]].map(([side, person]) => {
      const traits = data.traits.map((trait, index) => {
        const value = person.vector[index], e = angle(index, count);
        const distance = value === null ? shape.none : shape.near + (shape.far - shape.near) * Math.abs(value);
        return { index, value, angle: e, distance, hollow: value === null, label: traitLabel(trait, value),
          r: shape.dot[0] + (value === null ? 0 : shape.dot[1] * Math.abs(value)), ...place(shape, side, distance, e) };
      });
      placeLabels(traits, shape, side);
      const signals = data.signals.map((signal, order) => {
        const index = home.get(signal.id);
        const own = data.traits[index].signals.filter(id => home.get(id) === index), slot = own.indexOf(signal.id);
        const e = angle(index, count) + SPREAD * (slot - (own.length - 1) / 2);
        return { id: signal.id, order, value: person.signals[order], ...place(shape, side, shape.ring + shape.stagger * ((index + slot) % 3), e) };
      });
      return { side, traits, signals };
    });
    const links = [];
    sides.forEach((side, k) => {
      const person = k === 0 ? left : right;
      data.traits.forEach((trait, index) => trait.signals.forEach((id, slot) => {
        const push = person.pushes[index][slot];
        if (push === null) return;
        const from = side.signals.find(signal => signal.id === id), to = side.traits[index];
        const bend = side.side === 'a' ? 0.18 : -0.18;
        const mx = (from.x + to.x) / 2 + (to.y - from.y) * bend, my = (from.y + to.y) / 2 - (to.x - from.x) * bend;
        links.push({ side: side.side, signal: id, trait: index, push,
          d: `M${fixed(from.x)} ${fixed(from.y)} Q${fixed(mx)} ${fixed(my)} ${fixed(to.x)} ${fixed(to.y)}` });
      }));
    });
    const result = similarity.compare(left.vector, right.vector, data.model);
    const cells = [];
    data.traits.forEach((trait, index) => {
      const part = result.parts ? result.parts[index] : null;
      if (part === null) return;
      const a = sides[0].traits[index], b = sides[1].traits[index];
      const middle = mobile ? (a.y + b.y) / 2 : (a.x + b.x) / 2;
      const d = mobile
        ? `M${fixed(a.x)} ${fixed(a.y)} C${fixed(a.x)} ${fixed(middle)} ${fixed(b.x)} ${fixed(middle)} ${fixed(b.x)} ${fixed(b.y)}`
        : `M${fixed(a.x)} ${fixed(a.y)} C${fixed(middle)} ${fixed(a.y)} ${fixed(middle)} ${fixed(b.y)} ${fixed(b.x)} ${fixed(b.y)}`;
      cells.push({ trait: index, part, d });
    });
    return { width: shape.width, height: shape.height, font: shape.font, sides, links, cells, result };
  }

  // A measured signal as the detail line reads it.
  function formatSignal(value, unit) {
    const one = number => String(Number(number.toFixed(1)));
    const money = number => 'NT$' + Math.round(number).toLocaleString('en-US');
    switch (unit) {
      case 'share': return Math.round(value * 100) + '%';
      case 'sugar': return '約 ' + Math.round(value * 10) + ' 分糖';
      case 'money': return '每餐約 ' + money(value);
      case 'money_month': return '每月約 ' + money(value);
      case 'times_month': return '每月 ' + one(value) + ' 次';
      case 'items_month': return '每月 ' + one(value) + ' 件';
      case 'kinds': return value + ' 種';
      default: throw new Error('Unknown unit: ' + unit);
    }
  }

  // A trait's value with its direction: 偏高甜度 0.70, 0.38 for a habit, or 資料不足.
  function traitText(trait, value) {
    if (value === null) return '資料不足';
    if (trait.kind === 'level' || value === 0) return Math.abs(value).toFixed(2);
    return '偏' + trait.ends[value > 0 ? 1 : 0] + ' ' + Math.abs(value).toFixed(2);
  }

  // Which line fits a cell: both on one end, one on each end, or a habit both have.
  function line(trait, mine, theirs) {
    if (trait.kind === 'level') return trait.lines.both;
    return mine * theirs > 0 ? trait.lines.both[mine > 0 ? 1 : 0] : trait.lines.split;
  }

  const points = part => Math.abs(similarity.percent(part));

  // A name with a trait value: 你偏高甜度 0.70, 你 0.38, 手搖學生 A 0.22; a number always stands apart from the name.
  const valued = (name, text) => (/^\d/.test(text) ? name + ' ' + text : cards.words(name, text));

  // What one person's signal did: its value, and how far it pushed each trait it feeds.
  function signalSentence(data, person, name, id) {
    const order = data.signals.findIndex(signal => signal.id === id);
    const signal = data.signals[order], value = person.signals[order];
    const effects = [];
    data.traits.forEach((trait, index) => {
      const slot = trait.signals.indexOf(id);
      if (slot < 0) return;
      const push = person.pushes[index][slot];
      if (person.vector[index] === null) effects.push('「' + trait.name + '」資料不足');
      else if (push === null) effects.push('沒有紀錄');
      else if (push === 0) effects.push('沒有推動「' + trait.name + '」');
      else effects.push('往「' + (trait.kind === 'level' ? trait.habit : trait.ends[push > 0 ? 1 : 0]) + '」推 ' + Math.abs(push).toFixed(2));
    });
    const shown = value === null ? '' : ' ' + formatSignal(value, signal.unit);
    return name + '：' + signal.label + shown + '，' + effects.join('；');
  }

  // One cell of the score: both values and what it added or took away, with its line.
  function cellSentence(data, index, left, right, names, part) {
    const trait = data.traits[index], head = '「' + trait.name + '」這一格：';
    const missing = names.filter((name, k) => [left, right][k].vector[index] === null);
    if (missing.length) return head + cards.words(missing.join('和'), '資料不足，這一格不計分');
    if (part === null) return head + '兩人共同的特質太少，無法計分';
    const values = valued(names[0], traitText(trait, left.vector[index])) + '、' + valued(names[1], traitText(trait, right.vector[index]));
    if (part === 0) return head + values + '，不加也不扣';
    return head + values + '，' + (part > 0 ? '加 ' : '扣 ') + points(part) + ' 分 — ' + line(trait, left.vector[index], right.vector[index]);
  }

  // 臭味相投 and 背道而馳: the cell that adds the most and the one that takes the most away.
  function readout(data, left, right, names, result) {
    let best = null, worst = null;
    (result.parts || []).forEach((part, index) => {
      if (part === null) return;
      if (part > 0 && (best === null || part > result.parts[best])) best = index;
      if (part < 0 && (worst === null || part < result.parts[worst])) worst = index;
    });
    const say = (index, verb) => {
      const trait = data.traits[index], mine = left.vector[index], theirs = right.vector[index];
      return cards.phrase(trait, mine, theirs, names) + '（' + verb + ' ' + points(result.parts[index]) + ' 分）— ' + line(trait, mine, theirs);
    };
    return {
      alike: best === null ? '沒有加分的特質 — ' + data.readout.no_alike : say(best, '加'),
      unlike: worst === null ? '沒有扣分的特質 — ' + data.readout.no_unlike : say(worst, '扣'),
    };
  }

  // How many traits the page talks about: cats and dogs share one group, so 18 cells read as 17 traits.
  const traitCount = traits => new Set(traits.map(trait => trait.group ?? trait.id)).size;

  const api = Object.freeze({ SHAPES, validate, traitLabel, labelRect, layout, formatSignal, traitText, signalSentence,
    cellSentence, readout, traitCount });
  if (node) module.exports = api; else root.TraitNetwork = api;
})(globalThis);
