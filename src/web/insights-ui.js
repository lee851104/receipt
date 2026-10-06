'use strict';

const isDemoReport = expenseReportData.isDemo === true;
const reportMonths = expenseReportData.months;
const categories = expenseReportData.categories;
let selectedMonthKey = Object.keys(reportMonths).sort().at(-1);
let current = reportMonths[selectedMonthKey].rows;
const $ = id => document.getElementById(id);
const sum = rows => rows.reduce((value, row) => value + row.amount, 0);
const number = value => Math.round(value).toLocaleString('zh-TW');
const money = value => 'NT$ ' + number(value);
const escapeHTML = value => String(value).replace(/[&<>"']/g, char => ({
  '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
}[char]));
let insightGeneration = 0;
let rhythmMetric = 'count';

function renderInsights(key, autoplay = false) {
  if (!reportMonths[key]) return;
  selectedMonthKey = key;
  const month = reportMonths[key];
  current = month.rows;
  const generation = ++insightGeneration;
  const mm = String(month.monthNumber).padStart(2, '0');
  const dateLabel = day => mm + ' / ' + String(day).padStart(2, '0');
  const dateInfo = day => {
    const weekday = new Date(month.year, month.monthNumber - 1, day).getDay();
    return { weekday: '週' + '日一二三四五六'[weekday], weekend: weekday === 0 || weekday === 6 };
  };
  const totals = rows => categories.map((_, index) => sum(rows.filter(row => row.category === index)));
  const paid = current.filter(row => row.amount > 0);
  const zeroCount = current.filter(row => row.amount === 0).length;
  const discounts = -sum(current.filter(row => row.amount < 0));
  const total = sum(current), daysInMonth = month.days;
  const currTotals = totals(current);
  const invoices = [...new Set(current.map(row => row.invoice))];
  const activeDays = new Set(current.map(row => row.day)).size;
  const daily = Array.from({ length: daysInMonth }, (_, index) => {
    const rows = current.filter(row => row.day === index + 1), values = totals(rows);
    return { day: index + 1, amount: sum(rows), count: new Set(rows.map(row => row.invoice)).size,
      category: values.indexOf(Math.max(...values)) };
  });
  const topDays = daily.filter(day => day.count).sort((a, b) => b.amount - a.amount).slice(0, 3);
  const peak = topDays[0];
  const topAmount = topDays.reduce((value, day) => value + day.amount, 0);
  const topShare = total ? topAmount / total * 100 : 0;
  const largestCategory = currTotals.indexOf(Math.max(...currTotals));
  const largestShare = total ? currTotals[largestCategory] / total * 100 : 0;
  const sports = paid.filter(row => row.category === 4);
  const sportDays = [...new Set(sports.map(row => row.day))];
  const sportCount = new Set(sports.map(row => row.invoice)).size;
  const gaps = sportDays.slice(1).map((day, index) => day - sportDays[index]);
  const frequency = categories.map((category, index) => {
    const records = paid.filter(row => row.category === index);
    return { ...category, index, count: new Set(records.map(row => row.invoice)).size,
      amount: currTotals[index], days: [...new Set(records.map(row => row.day))] };
  }).filter(category => category.count > 0).sort((a, b) => b.count - a.count || a.index - b.index);

  $('insights-month').value = key;
  $('insights-source-label').textContent = isDemoReport ? '虛構示範 · 消費洞察' : '你的消費洞察';
  $('report-tag').textContent = month.month + (isDemoReport ? '・虛構示範' : '・個人報告');
  $('data-notice').textContent = isDemoReport ? '虛構示範資料：店家、品項、日期與金額皆為合成，僅供功能展示。' : '私人消費報告：本檔包含真實消費明細，請自行決定分享對象。';
  $('report-period').innerHTML = '<small>本期觀察區間</small>' + month.year + '.' + mm + '.01 — ' + mm + '.' + month.days;
  $('total').textContent = money(total);
  $('total-change').textContent = current.length + ' 筆明細 · 含 ' + zeroCount + ' 筆零元' + (discounts ? ' · 已扣折抵 ' + number(discounts) + ' 元' : '');
  $('records').innerHTML = invoices.length + '<small>張</small>';
  $('active-days').innerHTML = activeDays + '<small>/ ' + daysInMonth + ' 天</small>';
  $('highlight-stat').textContent = frequency.slice(0, 2).map(category => category.name).join('與');
  $('drink-stat').textContent = frequency.slice(0, 2).map(category => category.name + ' ' + category.count + ' 次').join(' · ');
  $('legend').innerHTML = categories.filter((_, index) => currTotals[index] !== 0).map(category => '<span style="--color:' + category.color + '">' + category.name + '</span>').join('');
  $('audit-summary').textContent = '查看分類明細與計算方式 · ' + current.length + ' 筆品項';
  $('audit-description').textContent = '依品名與賣方人工分類，尚未接模型。飲品含酒類；不明品項標示待確認。餐廳服務費列其他服務，餐廳折扣與點數折抵列正餐並扣除；不分攤至個別品名。零元明細保留供核對，消費次數只計付費紀錄。';
  $('audit-rows').innerHTML = current.map(row => '<tr><td>' + dateLabel(row.day) + '</td><td>' + row.invoice + '</td><td>' + escapeHTML(row.merchant) + '</td><td>' + escapeHTML(row.name) + '</td><td' + (row.provisional ? ' class="provisional"' : '') + '>' + categories[row.category].name + (row.provisional ? '（暫定）' : '') + '</td><td class="numeric">' + row.quantity + '</td><td class="numeric">' + number(row.amount) + '</td></tr>').join('');
  $('report-source').textContent = '目前洞察來源：' + month.source + '。金額依明細加總，已含負數折抵；發票張數按號碼去重。沒有紀錄不代表沒有消費。頁面只保留匿名發票代碼，不嵌入原始號碼、統編或地址。';

  const calendar = $('calendar');
  calendar.innerHTML = '';
  ['一', '二', '三', '四', '五', '六', '日'].forEach((value, index) => {
    const el = document.createElement('div');
    el.className = 'weekday' + (index >= 5 ? ' weekend' : ''); el.textContent = value; calendar.append(el);
  });
  const offset = (new Date(month.year, month.monthNumber - 1, 1).getDay() + 6) % 7;
  const weekRows = Math.ceil((offset + daysInMonth) / 7);
  calendar.style.gridTemplateRows = '20px repeat(' + weekRows + ',1fr)';
  for (let index = 0; index < weekRows * 7; index++) {
    const el = document.createElement('div'), data = daily[index - offset];
    if (!data) { el.className = 'day empty'; calendar.append(el); continue; }
    const date = dateInfo(data.day);
    el.className = 'day' + (data.count ? '' : ' no-record') + (date.weekend ? ' weekend' : '');
    el.dataset.day = data.day;
    el.title = dateLabel(data.day) + '（' + date.weekday + '）：' + (data.count ? money(data.amount) + ' · ' + data.count + ' 張發票' : '本檔無紀錄');
    el.setAttribute('aria-label', el.title);
    const diameter = peak?.amount > 0 ? Math.sqrt(Math.max(0, data.amount) / peak.amount) * 32 : 0;
    el.innerHTML = '<span class="day-label">' + String(data.day).padStart(2, '0') + '</span>' + (data.count ? '<span class="bubble" style="width:' + diameter + 'px;height:' + diameter + 'px;background:' + categories[data.category].color + '"></span>' : '') + '<span class="day-total">' + (data.count ? number(data.amount) : '—') + '</span>';
    calendar.append(el);
  }
  const visibleCategories = categories.map((category, index) => ({ ...category, index })).filter(category => currTotals[category.index] !== 0);
  $('stacks').innerHTML = visibleCategories.map(category => '<div class="category-row"><span>' + category.name + '</span><div class="category-track"><i id="stack-' + category.index + '" style="background:' + category.color + '"></i></div><span class="numeric" id="amount-' + category.index + '">0</span></div>').join('');
  $('routine').innerHTML = '<div class="routine-top"><div class="routine-label">重複出現的品項<br><strong>運動票券</strong></div><div class="routine-running" id="routine-amount">0<small>元累積</small></div></div><div class="ticket-strip">' + sports.map(row => '<div class="ticket pending" data-day="' + row.day + '"><div class="ticket-date">' + dateLabel(row.day) + '</div><span class="ticket-icon" aria-hidden="true"></span><div class="ticket-money">$' + row.amount + '</div><div class="ticket-caption">1 張發票</div></div>').join('') + '</div><div class="routine-foot">卡片依日期排序，等寬排列，不代表等長時間間隔。<br>' + (gaps.length ? '相鄰日期間隔：' + gaps.join('、') + ' 天。' : '目前不足兩個日期，無法計算間隔。') + '</div>';

  const scenes = [
    { title: '這個月的支出，集中在哪幾天？', subtitle: '圓的面積代表當日淨額；顏色代表當日金額最高的類別。', note: '「—」表示本檔無紀錄。' + month.month + '共 ' + daysInMonth + ' 天；紫色日期為週末。', value: topShare.toFixed(0), unit: '%', headline: '最高的 ' + topDays.length + ' 個日期，<br>占本月 ' + topShare.toFixed(0) + '% 支出。', body: topDays.length ? month.monthNumber + ' 月 ' + topDays.map(day => day.day).join('、') + ' 日合計 ' + money(topAmount) + '。最高一天為 ' + dateLabel(peak.day) + '，共 ' + money(peak.amount) + '。' : '本月沒有資料。', bottom: '<strong>' + activeDays + ' 天有紀錄，' + (daysInMonth - activeDays) + ' 天沒有紀錄。</strong><br>僅描述發票涵蓋的消費。' },
    { title: '拆到品項，看見支出的組成。', subtitle: '品項歸類後逐日累積，長度代表類別淨額。', note: '含折扣與點數折抵；明細金額已包含數量，不重複乘算。', value: largestShare.toFixed(0), unit: '%', headline: categories[largestCategory].name + '，是本月<br>最大的支出類別。', body: categories[largestCategory].name + '共 ' + money(currTotals[largestCategory]) + '，占 ' + largestShare.toFixed(1) + '%。' + (discounts ? '全月已扣除折抵 ' + money(discounts) + '。' : '同一張發票可包含多種類別。'), bottom: '<strong>分類採人工判讀。</strong><br>不明品項保留暫定標記，可由下方明細核對。' },
    { title: '有些習慣，不靠金額也能被看見。', subtitle: '同一品項沿日期出現，呈現交易的重複性。', note: '票券紀錄代表購買行為，無法確認實際入場或運動時長。', value: sportCount, unit: '張', headline: '運動票券，<br>在 ' + sportDays.length + ' 個日期出現。', body: '本月共有 ' + sportCount + ' 張運動類發票，累積 ' + money(sum(sports)) + '，占本月 ' + (total ? sum(sports) / total * 100 : 0).toFixed(1) + '%。', bottom: '<strong>頻繁出現，不一定是高額支出。</strong><br>往下選擇「運動」標籤，跟上個月比較。' },
  ];
  let position = autoplay ? 0 : 11.99, playing = autoplay, speed = 1, lastTime = null, activeScene = -1, lastDay = -1;
  function updatePlay() {
    $('play').textContent = playing ? 'Ⅱ' : '▶'; $('play').setAttribute('aria-label', playing ? '暫停動畫' : '播放動畫');
    $('play-state').textContent = playing ? '正在播放' : position >= 36 ? '播放完畢' : '已暫停';
  }
  function render() {
    const index = Math.min(2, Math.floor(position / 12));
    const day = Math.min(daysInMonth, Math.floor(Math.min(1, (position - index * 12) / 10) * daysInMonth) + 1);
    if (index !== activeScene) {
      activeScene = index; lastDay = -1;
      const scene = scenes[index];
      document.querySelectorAll('.scene').forEach((el, i) => el.hidden = i !== index);
      document.querySelectorAll('.chapter').forEach((el, i) => { el.classList.toggle('active', i === index); el.setAttribute('aria-current', i === index ? 'step' : 'false'); });
      $('scene-title').textContent = scene.title; $('scene-subtitle').textContent = scene.subtitle; $('chart-note').textContent = scene.note;
      $('insight-number').innerHTML = scene.value + '<small>' + scene.unit + '</small>';
      $('insight-title').innerHTML = scene.headline; $('insight-body').textContent = scene.body; $('insight-bottom').innerHTML = scene.bottom;
    }
    if (day !== lastDay) {
      lastDay = day; $('date-badge').textContent = dateLabel(day);
      if (index === 0) document.querySelectorAll('.day[data-day]').forEach(el => { el.classList.toggle('future', Number(el.dataset.day) > day); el.classList.toggle('current', Number(el.dataset.day) === day); });
      if (index === 1) visibleCategories.forEach(category => {
        const amount = sum(current.filter(row => row.category === category.index && row.day <= day));
        $('amount-' + category.index).textContent = number(amount);
        $('stack-' + category.index).style.width = Math.max(0, amount) / Math.max(1, ...currTotals) * 100 + '%';
      });
      if (index === 2) {
        document.querySelectorAll('.ticket').forEach(el => el.classList.toggle('pending', Number(el.dataset.day) > day));
        $('routine-amount').innerHTML = number(sum(sports.filter(row => row.day <= day))) + '<small>元累積</small>';
      }
    }
    $('timeline').value = position; $('time').textContent = '00:' + String(Math.floor(position)).padStart(2, '0') + ' / 00:36';
  }
  function tick(now) {
    if (generation !== insightGeneration) return;
    if (lastTime !== null && playing) { position = Math.min(36, position + (now - lastTime) / 1000 * speed); if (position >= 36) { playing = false; updatePlay(); } render(); }
    lastTime = now; requestAnimationFrame(tick);
  }
  $('play').onclick = () => { if (position >= 36) position = 0; playing = !playing; lastTime = null; render(); updatePlay(); };
  $('replay').onclick = () => { position = 0; playing = true; lastTime = null; render(); updatePlay(); };
  $('timeline').oninput = event => { position = Number(event.target.value); playing = false; render(); updatePlay(); };
  $('speed').textContent = '1×'; $('speed').setAttribute('aria-label', '播放速度 1 倍');
  $('speed').onclick = () => { speed = speed === 1 ? 1.5 : speed === 1.5 ? 2 : 1; $('speed').textContent = speed + '×'; $('speed').setAttribute('aria-label', '播放速度 ' + speed + ' 倍'); };
  $('finish').onclick = () => { position = activeScene * 12 + 11.99; playing = false; render(); updatePlay(); };
  document.querySelectorAll('.chapter').forEach(el => el.onclick = () => { position = Number(el.dataset.chapter) * 12 + (playing ? 0 : 11.99); lastTime = null; render(); updatePlay(); });
  document.onvisibilitychange = () => { if (document.hidden) { playing = false; updatePlay(); } lastTime = null; };
  render(); updatePlay(); requestAnimationFrame(tick);

  const largestFrequency = Math.max(1, ...frequency.map(category => category.count));
  $('category-cloud').innerHTML = frequency.map(category => '<button class="cloud-word" data-category="' + category.index + '" style="--word-color:' + category.color + ';--word-size:' + (20 + 52 * category.count / largestFrequency) + '" aria-pressed="false" aria-label="' + category.name + '，' + category.count + ' 次消費">' + category.name + '<small>' + category.count + ' 次</small></button>').join('');
  function showCategory(index) {
    const category = frequency.find(item => item.index === index);
    if (!category) return;
    document.querySelectorAll('.cloud-word').forEach(button => button.setAttribute('aria-pressed', String(Number(button.dataset.category) === index)));
    $('cloud-detail').innerHTML = '<strong>' + category.name + ' · ' + category.count + ' 次 · ' + money(category.amount) + '</strong><p>出現在 ' + category.days.length + ' 個日期，金額含同類折抵。</p><div class="date-chips">' + category.days.map(day => '<span>' + dateLabel(day) + '</span>').join('') + '</div>';
  }
  document.querySelectorAll('.cloud-word').forEach(button => button.onclick = () => showCategory(Number(button.dataset.category)));
  if (frequency.length) showCategory(frequency[0].index);

  const point = (radius, angle) => [190 + radius * Math.sin(angle * Math.PI / 180), 190 - radius * Math.cos(angle * Math.PI / 180)];
  function wedge(start, end, outer, inner = 42) {
    const a = point(inner, start), b = point(outer, start), c = point(outer, end), d = point(inner, end);
    return 'M ' + a.join(' ') + ' L ' + b.join(' ') + ' A ' + outer + ' ' + outer + ' 0 0 1 ' + c.join(' ') + ' L ' + d.join(' ') + ' A ' + inner + ' ' + inner + ' 0 0 0 ' + a.join(' ') + ' Z';
  }
  function renderRhythm() {
    const maximum = Math.max(1, ...daily.map(day => day[rhythmMetric]));
    const unit = rhythmMetric === 'count' ? '次' : '元';
    $('rhythm-month').textContent = month.month;
    $('rhythm-description').textContent = '把 ' + month.monthNumber + ' 月排成一個圓，從上方 1 日順時針閱讀。長條長度代表' + (rhythmMetric === 'count' ? '消費次數。' : '折抵後的消費金額。');
    document.querySelectorAll('[data-rhythm-metric]').forEach(button => button.setAttribute('aria-pressed', String(button.dataset.rhythmMetric === rhythmMetric)));
    let markup = '<title>' + month.month + '消費分布</title>';
    [42, 96, 150].forEach(radius => markup += '<circle class="radial-guide" cx="190" cy="190" r="' + radius + '" stroke-dasharray="2 5"/>');
    daily.forEach((day, index) => {
      const angle = index / daysInMonth * 360, step = 360 / daysInMonth, date = dateInfo(day.day);
      const label = dateLabel(day.day) + '（' + date.weekday + (date.weekend ? '・週末' : '') + '）';
      const a = point(42, angle), b = point(150, angle);
      markup += '<line class="radial-guide" x1="' + a[0] + '" y1="' + a[1] + '" x2="' + b[0] + '" y2="' + b[1] + '"/>';
      if (day[rhythmMetric] > 0) markup += '<path class="radial-bar" data-bucket="' + index + '" tabindex="0" role="img" aria-label="' + label + '，' + day.count + ' 次，' + money(day.amount) + '" d="' + wedge(angle + 1, angle + step - 1, 42 + 108 * day[rhythmMetric] / maximum) + '"><title>' + label + ' · ' + day.count + ' 次 · ' + money(day.amount) + '</title></path>';
      if (date.weekend) markup += '<path class="weekend-band" d="' + wedge(angle + 1, angle + step - 1, 159, 154) + '"><title>' + label + '</title></path>';
      const labelPoint = point(175, angle + step / 2);
      markup += '<text class="radial-label' + (date.weekend ? ' weekend' : '') + '" x="' + labelPoint[0] + '" y="' + labelPoint[1] + '">' + day.day + '</text>';
    });
    markup += '<text class="radial-center" x="190" y="189">' + number(daily.reduce((value, day) => value + day[rhythmMetric], 0)) + '</text><text class="radial-caption" x="190" y="210">本月 · ' + unit + '</text>';
    $('rhythm-chart').innerHTML = markup;
    $('rhythm-chart').setAttribute('aria-label', month.month + '消費分布，紫色外圈為週末');
    $('rhythm-note').textContent = '同日發票合併；金額已含折抵。最外圈為 ' + number(maximum) + ' ' + unit + '；沒有長條表示本檔無紀錄。';
    $('rhythm-rows').innerHTML = daily.map(day => { const date = dateInfo(day.day); return '<tr><td' + (date.weekend ? ' class="weekend-date"' : '') + '>' + dateLabel(day.day) + '（' + date.weekday + (date.weekend ? '・週末' : '') + '）</td><td class="numeric">' + day.count + '</td><td class="numeric">' + number(day.amount) + '</td></tr>'; }).join('');
    const best = daily.reduce((a, b) => b[rhythmMetric] > a[rhythmMetric] ? b : a);
    const showBucket = day => $('rhythm-detail').innerHTML = dateLabel(day.day) + '（' + dateInfo(day.day).weekday + '） · ' + day.count + ' 次 · ' + money(day.amount) + '<small>點選或聚焦長條，查看當日紀錄</small>';
    showBucket(best);
    $('rhythm-chart').querySelectorAll('[data-bucket]').forEach(bar => { bar.onmouseenter = bar.onfocus = bar.onclick = () => showBucket(daily[Number(bar.dataset.bucket)]); });
  }
  document.querySelectorAll('[data-rhythm-metric]').forEach(button => button.onclick = () => { rhythmMetric = button.dataset.rhythmMetric; renderRhythm(); });
  renderRhythm();
}

$('insights-month').innerHTML = Object.keys(reportMonths).sort().reverse().map(key => '<option value="' + key + '">' + reportMonths[key].month + '</option>').join('');
$('insights-month').addEventListener('change', event => {
  renderInsights(event.target.value);
  if (typeof refreshComparisonMonths === 'function') refreshComparisonMonths();
});
renderInsights(selectedMonthKey, !matchMedia('(prefers-reduced-motion: reduce)').matches);
