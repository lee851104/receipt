/* Who the match page shows and what it says, shared by the page and its tests. */
(function (root) {
  'use strict';
  const RANGES = ['同一區', '同縣市', '同地區', '不限'];
  const PLACES = ['同一區', '同縣市', '同地區', '其他地區'];
  const whole = value => Math.round(value * 100);
  function recommend(candidates, maxDistance, thresholds) {
    const strong = candidates.filter(candidate => candidate.score >= whole(thresholds.match));
    if (strong.length) return strong;
    if (maxDistance === null) return [];
    return candidates.filter(candidate => candidate.score >= whole(thresholds.nearby) && candidate.distance <= maxDistance);
  }
  function view(data, maxDistance) {
    const { settings, me, candidates } = data;
    const { thresholds, top_matches: top } = settings;
    const blank = { status: '', note: '', options: [], cards: [], empty: '' };
    const cards = (list, withPlace) => list.slice(0, top)
      .map(candidate => ({ candidate, place: withPlace ? PLACES[candidate.distance] : null }));
    if (!me.ready) {
      return { ...blank, empty: '資料不足，還不能配對：需要至少 ' + settings.category_min_items + ' 筆已分類品項（目前 '
        + me.item_count + ' 筆），以及品牌、葷素紀錄或消費檔次其中一項。多掃幾張發票再看看。' };
    }
    const strong = recommend(candidates, null, thresholds);
    if (strong.length) {
      return { ...blank, cards: cards(strong, false), status: strong.length + ' 位配對分數 ' + whole(thresholds.match) + '% 以上'
        + (strong.length > top ? '，顯示前 ' + top + ' 位' : '') + '。' };
    }
    if (!candidates.some(candidate => candidate.score >= whole(thresholds.nearby))) {
      return { ...blank, empty: '目前沒有夠相似的人，多掃幾張發票再看看。' };
    }
    const options = RANGES.map((label, level) => {
      const count = recommend(candidates, level, thresholds).length;
      return { level, label, count, disabled: count === 0 };
    });
    return {
      ...blank, options,
      status: '目前沒有 ' + whole(thresholds.match) + '% 以上的人。放寬到 ' + whole(thresholds.nearby) + '%，要找多遠？',
      note: me.areas.length ? '以你的常消費地區為準：' + me.areas.join('、') + '。' : '推測不出你的常消費地區，只能選「不限」。',
      cards: maxDistance === null ? [] : cards(recommend(candidates, maxDistance, thresholds), true),
    };
  }
  const api = Object.freeze({ recommend, view });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.MatchFilter = api;
})(globalThis);
