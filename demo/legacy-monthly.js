'use strict';

// Shared calculation rules for the browser and the automated checks.
(function (root) {
  function summarize(rows, selection, monthDays) {
    if (rows === null) return null;
    const selected = rows.filter(row =>
      row.category === selection.category &&
      (selection.name === undefined || row.name === selection.name)
    );
    const paid = selected.filter(row => row.amount > 0);
    const amount = selected.reduce((total, row) => total + row.amount, 0);
    const count = new Set(paid.map(row => row.invoice)).size;
    return {
      amount,
      count,
      days: new Set(paid.map(row => row.day)).size,
      average: count ? amount / count : null,
      daily: amount / monthDays,
    };
  }

  function difference(current, previous) {
    if (current === null || previous === null) return null;
    return {
      absolute: current - previous,
      percent: previous === 0 ? null : (current - previous) / previous * 100,
    };
  }

  function compare(previousMonth, currentMonth, selection) {
    const previous = summarize(previousMonth.rows, selection, previousMonth.days);
    const current = summarize(currentMonth.rows, selection, currentMonth.days);
    const delta = Object.fromEntries(['amount', 'count', 'days', 'average', 'daily']
      .map(key => [key, difference(current?.[key] ?? null, previous?.[key] ?? null)]));
    return { previous, current, delta };
  }

  const api = { summarize, difference, compare };
  root.MonthlyComparison = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})(globalThis);
