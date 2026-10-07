/* The final recommendation rule, shared by the match page and its tests. */
(function (root) {
  'use strict';
  const whole = value => Math.round(value * 100);
  function recommend(candidates, confirmedAreas, thresholds) {
    const chosen = new Set(confirmedAreas);
    return candidates.filter(candidate => candidate.taste >= whole(thresholds.taste)
      || (candidate.taste >= whole(thresholds.taste_same_area) && candidate.areas.some(area => chosen.has(area))));
  }
  const api = Object.freeze({ recommend });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.MatchFilter = api;
})(globalThis);
