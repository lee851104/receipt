'use strict';

// Demo records are isolated from the personal report and never used by its charts.
const comparisonItems = [...new Map(Object.values(reportMonths).flatMap(month => month.rows).map(row => [
  row.category + ':' + row.name, { category: row.category, name: row.name },
])).values()];
// Keep the comparison taxonomy aligned with the future classifier output.
// "待確認" is a review status, not a consumption tag.
const comparisonSelections = categories
  .map((category, index) => ({ category: index, label: category.name }))
  .filter(selection => selection.label !== '待確認');
const comparisonData = { actual: {}, demo: {} };
function refreshComparisonMonths() {
  const currentMonth = reportMonths[selectedMonthKey];
  const date = new Date(currentMonth.year, currentMonth.monthNumber - 2, 1);
  const previousKey = date.getFullYear() + '-' + String(date.getMonth() + 1).padStart(2, '0');
  const previousMonth = reportMonths[previousKey] || {
    year: date.getFullYear(), monthNumber: date.getMonth() + 1,
    month: date.getFullYear() + ' 年 ' + (date.getMonth() + 1) + ' 月',
    days: new Date(date.getFullYear(), date.getMonth() + 1, 0).getDate(), rows: null,
  };
  comparisonData.actual = { previous: previousMonth, current: currentMonth };
  function demoMonth(month, newer) {
    const rows = comparisonItems.flatMap((item, index) => Array.from({ length: newer ? (index + 2) % 5 : index % 4 }, (_, occurrence) => ({
      ...item, day: 1 + (index * 3 + occurrence * 7) % month.days,
      invoice: 'DEMO-' + month.monthNumber + '-' + index + '-' + occurrence,
      amount: 30 + index * 8 + (newer ? 5 : 0),
    })));
    return { ...month, rows };
  }
  comparisonData.demo = { previous: demoMonth(previousMonth, false), current: demoMonth(currentMonth, true) };
  comparisonSource = 'actual';
  renderComparison();
}
let comparisonSource = 'actual';
const comparisonMetrics = [
  { key: 'amount', label: '消費金額', unit: '元', currency: true },
  { key: 'count', label: '消費次數', unit: '次' },
  { key: 'days', label: '有消費的日子', unit: '天' },
  { key: 'average', label: '平均每次金額', unit: '元', currency: true, decimal: true },
  { key: 'daily', label: '整月每日平均', unit: '元', currency: true, decimal: true },
];
const comparisonNumber = (value, decimal = false) => value.toLocaleString('zh-TW', {
  minimumFractionDigits: decimal ? 1 : 0,
  maximumFractionDigits: decimal ? 1 : 0,
});
function comparisonDelta(delta, metric) {
  if (!delta) return '—<small>無法比較</small>';
  if (delta.absolute === 0) return '持平';
  const absolute = (delta.absolute > 0 ? '+' : '−') + comparisonNumber(Math.abs(delta.absolute), metric.decimal) + ' ' + metric.unit;
  const percent = delta.percent === null ? '上月為 0，不計增減率' :
    (delta.percent > 0 ? '+' : '−') + comparisonNumber(Math.abs(delta.percent), true) + '%';
  return absolute + '<small>' + percent + '</small>';
}
function comparisonCard(month, stats, selection, isCurrent) {
  const name = isCurrent ? '本月' : '上月';
  const matching = month.rows?.filter(row => row.category === selection.category) ?? [];
  const dailyAmounts = Array.from({ length: month.days }, (_, i) =>
    matching.filter(row => row.day === i + 1).reduce((value, row) => value + row.amount, 0));
  // The strip marks purchase days, not amount, so the two months have equal visual weight.
  const strip = stats ? '<div class="month-days" aria-hidden="true">' + dailyAmounts.map(amount =>
    '<span style="height:' + (amount > 0 ? '30' : '3') + 'px;opacity:' + (amount > 0 ? '1' : '.25') + '"></span>').join('') +
    '</div><div class="month-caption">每一格一天 · 有消費的日子亮起</div>' :
    '<div class="month-empty">尚未載入這個月的發票</div>';
  return '<article class="month-card' + (isCurrent ? ' current-month' : '') + '"><span class="month-tag">' + name + '</span>' +
    '<h3>' + (month.monthNumber + ' 月') + '</h3><div class="month-caption">' + month.month + ' · ' + month.days + ' 天</div>' +
    '<div class="month-emblem"><span>' + (stats ? stats.count + '<small>次</small>' : '—') + '</span></div>' +
    '<div class="month-amount">' + (stats ? '<small>NT$</small>' + comparisonNumber(stats.amount) : '尚無資料') + '</div>' +
    '<div class="month-caption">' + (comparisonSource === 'demo' ? '模擬消費金額' : '發票涵蓋金額') + '</div>' + strip + '</article>';
}
function renderComparison() {
  const selection = comparisonSelections[Number($('compare-item').value)];
  const dataset = comparisonData[comparisonSource];
  const result = MonthlyComparison.compare(dataset.previous, dataset.current, selection);
  const demo = comparisonSource === 'demo';
  document.querySelectorAll('[data-compare-source]').forEach(button =>
    button.setAttribute('aria-pressed', String(button.dataset.compareSource === comparisonSource)));
  $('compare-source-note').className = 'compare-source' + (demo ? ' demo' : '');
  $('compare-source-note').textContent = demo ?
    '示範模式：兩個月皆為模擬資料，僅展示比較功能，不代表你的實際消費。' :
    '我的資料：' + dataset.current.month + '已載入；' + dataset.previous.month + (dataset.previous.rows ? '已載入。以下為真實發票比較。' : '尚無資料，不計增減。');
  $('compare-previous-heading').textContent = '上月 · ' + dataset.previous.monthNumber + ' 月';
  $('compare-current-heading').textContent = '本月 · ' + dataset.current.monthNumber + ' 月';
  $('compare-period-note').textContent = '本次比較：' + dataset.current.month + '對' + dataset.previous.month + '。同一張發票、同一標籤計 1 次付費消費；平均每次金額不等於商品單價。每日平均按各月實際天數計算，類別金額包含同類折抵。缺月不當成零，沒有紀錄不代表沒有消費。';
  $('compare-months').innerHTML = comparisonCard(dataset.previous, result.previous, selection, false) +
    comparisonCard(dataset.current, result.current, selection, true);
  $('compare-caption').textContent = selection.label + ' · ' + (demo ? '模擬資料比較' : '我的月度比較');
  $('compare-specs').innerHTML = comparisonMetrics.map(metric => {
    function value(stats) {
      if (!stats) return '—<small>尚無資料</small>';
      if (stats[metric.key] === null) return '—<small>無付費紀錄</small>';
      return (metric.currency ? 'NT$ ' : '') + comparisonNumber(stats[metric.key], metric.decimal) + (metric.currency ? '' : ' ' + metric.unit);
    }
    return '<tr><th scope="row">' + metric.label + '</th><td>' + value(result.previous) + '</td><td>' + value(result.current) + '</td><td>' + comparisonDelta(result.delta[metric.key], metric) + '</td></tr>';
  }).join('');
  let title, description;
  if (!result.previous || !result.current) {
    title = '選好了「' + selection.label + '」，等上個月的自己到齊。';
    description = '目前可看 ' + dataset.current.month + '數字；缺少 ' + dataset.previous.month + '資料，還不能判斷增加或減少。';
  } else {
    const change = result.delta.amount.absolute;
    title = '「' + selection.label + '」' + (change === 0 ? '，兩個月花費相同。' :
      '，這個月' + (change > 0 ? '多' : '少') + '花 ' + comparisonNumber(Math.abs(change)) + ' 元。');
    description = '消費紀錄從 ' + result.previous.count + ' 次變成 ' + result.current.count + ' 次。' +
      dataset.previous.monthNumber + ' 月 ' + dataset.previous.days + ' 天、' + dataset.current.monthNumber + ' 月 ' + dataset.current.days + ' 天，也可以對照每日平均，分辨月份長度的影響。';
  }
  $('compare-takeaway').innerHTML = '<strong>' + escapeHTML(title) + '</strong><p>' + escapeHTML(description) + '</p>';
}
$('compare-item').innerHTML = comparisonSelections.map((selection, i) =>
  '<option value="' + i + '">' + escapeHTML(selection.label) + '</option>').join('');
$('compare-item').value = String(Math.max(0, comparisonSelections.findIndex(selection => selection.category === 4)));
$('compare-item').addEventListener('change', renderComparison);
document.querySelectorAll('[data-compare-source]').forEach(button => button.addEventListener('click', () => {
  comparisonSource = button.dataset.compareSource;
  renderComparison();
}));
refreshComparisonMonths();
