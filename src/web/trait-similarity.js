/* Taste-vector similarity, mirrored from src/receipt/similarity.py; both run tests/fixtures/similarity-cases.json. */
(function (root) {
  'use strict';
  const NOT_COMPARABLE = Object.freeze({ comparable: false, score: null, parts: null });
  function compare(mine, theirs, model) {
    if (!mine || !theirs) return { ...NOT_COMPARABLE };
    const cells = model.cells;
    const shared = mine.map((value, index) => index).filter(index => mine[index] !== null && theirs[index] !== null);
    if (shared.filter(index => cells[index].kind === 'two_sided').length < model.min_shared_two_sided) return { ...NOT_COMPARABLE };
    const norm = values => Math.sqrt(shared.reduce((sum, index) => sum + cells[index].weight * values[index] ** 2, 0));
    const denominator = norm(mine) * norm(theirs) + model.shrink;
    const parts = mine.map(() => null);
    for (const index of shared) parts[index] = cells[index].weight * mine[index] * theirs[index] / denominator;
    return { comparable: true, score: shared.reduce((sum, index) => sum + parts[index], 0), parts };
  }
  // Whole percentage, rounding halves up like percent() in similarity.py.
  const percent = score => Math.floor(score * 100 + 0.5);
  const api = Object.freeze({ compare, percent });
  if (typeof module !== 'undefined' && module.exports) module.exports = api; else root.TraitSimilarity = api;
})(globalThis);
