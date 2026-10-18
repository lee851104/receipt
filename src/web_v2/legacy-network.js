/* Where the taste network draws every dot and line, and what its sentences say; the page only turns this into SVG. */
(function (root) {
  'use strict';
  const node = typeof module !== 'undefined' && module.exports;
  const similarity = node ? require('./legacy-similarity.js') : root.TraitSimilarity;
  const cards = node ? require('./legacy-match-filter.js') : root.MatchFilter;

  // Desktop puts the two fans side by side; phones stack them, the left person on top. All sizes are SVG units.
  // `item` places the purchases behind a picked signal: a column `across` from the signal on desktop (slid along or
  // stepped further out when that spot is taken), a column in a band `beyond` the fans on phones, rows `step` apart,
  // dots from dot[0] to dot[0] + dot[1] across.
  // Desktop writes the two people's names along the top, above `top`; nothing a click adds goes higher.
  // `mark` is the score badge between the fans: its size, the label and number font sizes, and the glow's radii.
  const SHAPES = Object.freeze({
    desktop: Object.freeze({ width: 1700, height: 600, centers: [[620, 300], [1080, 300]], stretch: [1.5, 0.8],
      near: 110, far: 270, none: 72, ring: 312, stagger: 14, dot: [4.5, 13], font: 22, top: 36,
      item: Object.freeze({ across: 72, step: 30, dot: [3.5, 4.5] }),
      mark: Object.freeze({ width: 212, height: 100, label: 19, number: 48, glow: [400, 250] }) }),
    mobile: Object.freeze({ width: 600, height: 820, centers: [[300, 290], [300, 530]], stretch: [1, 0.9],
      near: 70, far: 190, none: 46, ring: 228, stagger: 12, dot: [5, 11], font: 18,
      item: Object.freeze({ beyond: 30, step: 26, dot: [3, 4] }),
      mark: Object.freeze({ width: 200, height: 100, label: 17, number: 46, glow: [270, 140] }) }),
  });
  const FAN = 78 * Math.PI / 180;      // each fan opens 78° either side of straight out
  const SPREAD = 0.045;                // radians between neighbouring signals of one trait
  const SLIDES = 8;                    // half rows a purchase column may slide down or up to find room
  const REACH = 5;                     // rows a purchase column may step further out to find room
  const SIGNAL_ROOM = 4;               // a desktop signal dot's radius (3) and a little room around it
  const FULL_PART = 0.1;               // a middle line adding or taking ten points or more is drawn at full strength
  const GLOW_RATE = 0.65;              // how bright the glow between the fans gets per unit of score …
  const GLOW_MAX = 0.5;                // … up to this, so the lines stay readable over it
  const LABEL_STEPS = 3;               // a crowded label moves outwards this many times before it hides
  const PAD = 3;                       // the gap kept around every label

  // Every check a person's taste data must pass before the graph trusts it.
  function validate(person, data) {
    const fail = () => { throw new Error('品味資料不正確，請回配對清單重新選擇。'); };
    const finite = value => typeof value === 'number' && Number.isFinite(value);
    if (!person || typeof person !== 'object') fail();
    const { vector, pushes, signals, items } = person;
    if (!Array.isArray(vector) || vector.length !== data.traits.length) fail();
    if (!Array.isArray(pushes) || pushes.length !== data.traits.length) fail();
    if (!Array.isArray(signals) || signals.length !== data.signals.length) fail();
    signals.forEach(value => { if (value !== null && (!finite(value) || value < 0 || value > 1e6)) fail(); });
    const order = new Map(data.signals.map((signal, index) => [signal.id, index]));
    data.traits.forEach((trait, index) => {
      const value = vector[index], list = pushes[index], low = trait.kind === 'level' ? 0 : -1;
      if (value !== null && (!finite(value) || value < low || value > 1)) fail();
      if (!Array.isArray(list) || list.length !== trait.signals.length) fail();
      list.forEach((push, slot) => {
        if (push === null) return;
        if (!finite(push) || push < low || push > 1) fail();
        // A trait without data pushes nothing, and neither does a signal that was not measured.
        if (value === null || signals[order.get(trait.signals[slot])] === null) fail();
      });
      // The lines must add up to the trait they draw, give or take the rounding of each push.
      if (value !== null && Math.abs(list.reduce((sum, push) => sum + (push ?? 0), 0) - value) > 0.001) fail();
    });
    // Up to three purchases per signal, each a short name and the bills it is on; signals about places list none.
    if (!Array.isArray(items) || items.length !== data.signals.length) fail();
    const lists = items.map((list, index) => {
      if (data.signals[index].list_items === false) return list === null ? null : fail();
      if (!Array.isArray(list) || list.length > 3) fail();
      const seen = new Set();
      return list.map(entry => {
        if (!Array.isArray(entry) || entry.length !== 2) fail();
        const [name, count] = entry;
        if (typeof name !== 'string' || /[\u0000-\u001f\u007f]/.test(name)) fail();
        const trimmed = name.trim(), letters = Array.from(trimmed).length;
        if (letters < 1 || letters > 20 || seen.has(trimmed)) fail();
        if (!Number.isSafeInteger(count) || count < 1 || count > 10000) fail();
        seen.add(trimmed);
        return [trimmed, count];
      });
    });
    return { vector: [...vector], pushes: pushes.map(list => [...list]), signals: [...signals], items: lists };
  }

  // A value that prints as 0.00 leans nowhere, so the words treat it as 0.
  const faint = value => Math.abs(value) < 0.005;

  // The label a trait wears: the end it leans to, or its short name or habit word.
  function traitLabel(trait, value) {
    if (trait.kind === 'level') return trait.habit;
    if (value === null || faint(value)) return trait.short;
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
  function layout(data, left, right, mobile, result) {
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
    if (!result) throw new Error('缺少 API 配對結果。');
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

  // A purchase name the graph can fit: ten letters at most, cut with an ellipsis; the detail line keeps it whole.
  const shortName = name => (Array.from(name).length > 10 ? Array.from(name).slice(0, 9).join('') + '…' : name);

  // What a purchase column on desktop must not cover: the names along the top, this side's dots and its trait labels.
  function obstacles(side, shape) {
    const dot = (x, y, r) => ({ left: x - r, right: x + r, top: y - r, bottom: y + r });
    return [{ left: -Infinity, right: Infinity, top: -Infinity, bottom: shape.top },
      ...side.signals.map(signal => dot(signal.x, signal.y, SIGNAL_ROOM)),
      ...side.traits.map(trait => dot(trait.x, trait.y, trait.r)),
      ...side.traits.filter(trait => trait.labelShown)
        .map(trait => labelRect(trait.label, shape.font, trait.labelX, trait.labelY, trait.labelAnchor))];
  }

  // Everything one purchase covers on the graph: its dot and its name.
  function reach(item, font) {
    const box = labelRect(item.text, font, item.labelX, item.labelY, item.anchor);
    return { left: Math.min(box.left, item.x - item.r), right: Math.max(box.right, item.x + item.r),
      top: Math.min(box.top, item.y - item.r), bottom: Math.max(box.bottom, item.y + item.r) };
  }

  // The purchases behind one signal for each person who has any: a short column of dots outside the signal, most
  // bought first, each with a line into the signal and its name beside it. Desktop stands the column beside the
  // signal, away from the middle; phones stand it in a band above the top fan or below the bottom one.
  function purchases(data, graph, people, id, mobile) {
    const shape = mobile ? SHAPES.mobile : SHAPES.desktop, { across, beyond, step, dot } = shape.item;
    const order = data.signals.findIndex(signal => signal.id === id);
    return graph.sides.flatMap((side, k) => {
      const list = (people[k].items || [])[order] || [];
      if (!list.length) return [];
      const signal = side.signals.find(entry => entry.id === id), most = Math.max(...list.map(([, count]) => count));
      const rows = list.map(([name, count]) => ({ name, count, text: shortName(name) + ' ×' + count,
        r: dot[0] + dot[1] * count / most, width: 0.7 + 2.2 * count / most }));
      // Where the column may stand, best first: [x, y of its first row].
      let spots, anchor;
      if (mobile) {
        // The names must fit inside the phone's width; the band itself only makes the graph taller.
        const widest = Math.max(...rows.map(row => row.r + 5 + textWidth(row.text, shape.font)));
        anchor = 'start';
        spots = [[Math.min(Math.max(signal.x, 20), graph.width - widest - 8),
          side.side === 'a' ? -beyond - (rows.length - 1) * step : graph.height + beyond]];
      } else {
        // Beside the signal and centred on it when there is room; otherwise the column slides down or up half a row at
        // a time, then steps a row further out and slides again.
        const out = side.side === 'a' ? -1 : 1, centred = signal.y - (rows.length - 1) * step / 2;
        anchor = side.side === 'a' ? 'end' : 'start';
        spots = [];
        for (let far = 0; far <= REACH; far++) {
          for (let slide = 0; slide <= SLIDES; slide++) {
            for (const sign of slide ? [1, -1] : [1]) spots.push([signal.x + out * (across + far * step), centred + sign * slide * step / 2]);
          }
        }
      }
      const column = ([x, first]) => rows.map((row, slot) => {
        const y = first + slot * step;
        return { ...row, x, y, anchor, labelX: anchor === 'end' ? x - row.r - 5 : x + row.r + 5, labelY: y + shape.font * 0.35 };
      });
      const taken = mobile ? [] : obstacles(side, shape);
      const fits = items => items.every(item => !taken.some(box => overlaps(reach(item, shape.font), box)));
      const items = column(spots.find(spot => fits(column(spot))) || spots[0]);
      return [{ side: side.side, signal: { x: signal.x, y: signal.y }, items }];
    });
  }

  // The overall match drawn between the fans: the score in a badge, coloured by the side of zero it falls on, and a
  // glow that grows with how far it is from zero, so a close match reads at a glance and a distant one stays dim.
  function scoreMark(graph, mobile) {
    const { result } = graph;
    if (!result || !result.comparable) return null;
    const shape = mobile ? SHAPES.mobile : SHAPES.desktop, { mark } = shape, [[ax, ay], [bx, by]] = shape.centers;
    const x = (ax + bx) / 2, y = (ay + by) / 2, points = result.percent;
    return { x, y, width: mark.width, height: mark.height, label: mark.label, number: mark.number, radii: mark.glow,
      labelY: y - mark.height / 2 + 24, numberY: y + mark.height / 2 - 16, text: (points > 0 ? '+' : points < 0 ? '−' : '') + Math.abs(points) + '%',
      tone: points > 0 ? 'positive' : points < 0 ? 'negative' : 'zero', glow: Math.min(GLOW_MAX, Math.abs(result.score) * GLOW_RATE) };
  }

  // A middle line is as bright as the points its cell adds or takes, so the cells that decide the score stand out.
  const cellOpacity = part => (part === 0 ? 0.3 : 0.2 + 0.8 * Math.min(1, Math.abs(part) / FULL_PART));

  // The view box: the graph plus room for every purchase any signal could show, so picking one never rescales it.
  function viewBox(data, graph, people, mobile) {
    const font = (mobile ? SHAPES.mobile : SHAPES.desktop).font;
    let left = 0, top = 0, right = graph.width, bottom = graph.height;
    for (const signal of data.signals) {
      for (const side of purchases(data, graph, people, signal.id, mobile)) {
        for (const item of side.items) {
          const box = reach(item, font);
          left = Math.min(left, box.left);
          right = Math.max(right, box.right);
          top = Math.min(top, box.top);
          bottom = Math.max(bottom, box.bottom);
        }
      }
    }
    return [Math.floor(left), Math.floor(top), Math.ceil(right) - Math.floor(left), Math.ceil(bottom) - Math.floor(top)].join(' ');
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
    if (trait.kind === 'level' || faint(value)) return Math.abs(value).toFixed(2);
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
      else if (faint(push)) effects.push('沒有推動「' + trait.name + '」');
      else effects.push('往「' + (trait.kind === 'level' ? trait.habit : trait.ends[push > 0 ? 1 : 0]) + '」推 ' + Math.abs(push).toFixed(2));
    });
    const shown = value === null ? '' : ' ' + formatSignal(value, signal.unit);
    // What was bought follows the value; a signal about places says it lists nothing on purpose.
    const list = (person.items || [])[order] || [];
    const bought = signal.list_items === false ? (value === null ? '' : '（這個訊號不列品項）')
      : list.length ? '（' + list.map(([item, count]) => item + ' ×' + count).join('、') + '）' : '';
    return name + '：' + signal.label + shown + bought + '，' + effects.join('；');
  }

  // One cell of the score: both values and what it added or took away, with its line.
  function cellSentence(data, index, left, right, names, part) {
    const trait = data.traits[index], head = '「' + trait.name + '」這一格：';
    const missing = names.filter((name, k) => [left, right][k].vector[index] === null);
    if (missing.length) return head + cards.words(missing.join('和'), '資料不足，這一格不計分');
    if (part === null) return head + '兩人共同的特質太少，無法計分';
    const values = valued(names[0], traitText(trait, left.vector[index])) + '、' + valued(names[1], traitText(trait, right.vector[index]));
    // A part that rounds to 0 points neither adds nor takes away on the page.
    if (points(part) === 0) return head + values + '，不加也不扣';
    return head + values + '，' + (part > 0 ? '加 ' : '扣 ') + points(part) + ' 分 — ' + line(trait, left.vector[index], right.vector[index]);
  }

  // 臭味相投 and 背道而馳: the cell that adds the most and the one that takes the most away.
  function readout(data, left, right, names, result) {
    let best = null, worst = null;
    (result.parts || []).forEach((part, index) => {
      if (part === null || points(part) === 0) return;
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

  const api = Object.freeze({ SHAPES, validate, traitLabel, labelRect, layout, shortName, purchases, viewBox, scoreMark,
    cellOpacity, formatSignal, traitText, signalSentence, cellSentence, readout, traitCount });
  if (node) module.exports = api; else root.TraitNetwork = api;
})(globalThis);
