/* Pure review state transitions; shared by offline HTML and Node tests. */
const ReviewCore = (() => {
  const valid = value => Number.isInteger(value) && value >= 0 && value < 10;
  function choose(row, category) {
    row.category = valid(category) ? category : null;
    row.review_status = 'model_pending';
  }
  function confirm(row, category, checked) {
    choose(row, category);
    if (checked && valid(category)) row.review_status = 'human_confirmed';
  }
  function confirmedRows(rows) {
    return rows.filter(row => row.review_status === 'human_confirmed' && valid(row.category)).map(row => ({
      id: row.id, name: row.name, category: row.category, source: 'real',
      review_status: 'human_confirmed', name_only_context_needed: row.name_only_context_needed === true,
      label_method: 'model_assisted_human_review'
    }));
  }
  function safeJson(value) {
    return JSON.stringify(value).replace(/</g, '\\u003c').replace(/\u2028/g, '\\u2028').replace(/\u2029/g, '\\u2029');
  }
  return {choose, confirm, confirmedRows, safeJson};
})();
if (typeof module !== 'undefined') module.exports = ReviewCore;
