const ACCENTS = ['var(--blue-1)', 'var(--blue-2)', 'var(--blue-3)', 'var(--blue-4)'];

function ringMarkup(score, accent, size = 88){
  const radius = 34;
  const circumference = 2 * Math.PI * radius;
  const progress = score === null ? 0 : Math.max(0, Math.min(100, score));
  const offset = circumference * (1 - progress / 100);
  const label = score === null
    ? 'No score available'
    : `${Math.round(score)} percent progress`;
  return `
    <div class="ring-wrap domain-ring" style="--ring-size:${size}px" role="img" aria-label="${label} score">
      <svg width="${size}" height="${size}" viewBox="0 0 80 80" aria-hidden="true">
        <circle class="ring-track" cx="40" cy="40" r="${radius}"></circle>
        <circle class="ring-progress" cx="40" cy="40" r="${radius}"
          stroke="${accent}"
          stroke-dasharray="${circumference}"
          stroke-dashoffset="${offset}"></circle>
      </svg>
      <div class="ring-pct">${score === null ? '—' : `${Math.round(score)}%`}</div>
    </div>`;
}

function formatNum(value){
  const num = Number(value);
  return Number.isInteger(num) ? num : num.toFixed(1);
}

function escapeHtml(value){
  const div = document.createElement('div');
  div.textContent = value == null ? '' : String(value);
  return div.innerHTML;
}

function formatMonth(month){
  if (!month) return 'Monthly progress';
  const [year, monthNumber] = month.split('-').map(Number);
  return new Intl.DateTimeFormat(undefined, { month: 'long', year: 'numeric' })
    .format(new Date(year, monthNumber - 1, 1));
}

function formatChange(change, label){
  if (change === null || change === undefined) {
    return `<span class="trend-item trend-muted">Δ ${label}: —</span>`;
  }
  const rounded = Math.round(change);
  const sign = rounded > 0 ? '+' : '';
  const state = rounded > 0 ? 'trend-up' : rounded < 0 ? 'trend-down' : 'trend-flat';
  return `<span class="trend-item ${state}">Δ ${label}: ${sign}${rounded}%</span>`;
}

function renderSkeleton(){
  const grid = document.getElementById('domainGrid');
  grid.innerHTML = '';
  for (let i = 0; i < 6; i++){
    const card = document.createElement('div');
    card.className = 'domain-card skeleton';
    card.innerHTML = `
      <div class="skeleton-line" style="width:46%;"></div>
      <div class="domain-card-body">
        <div class="skeleton-line skeleton-ring"></div>
        <div class="domain-card-copy">
          <div class="skeleton-line" style="width:70%;"></div>
          <div class="skeleton-line" style="width:52%;"></div>
        </div>
      </div>`;
    grid.appendChild(card);
  }
}

function setStatus(message, isError = false){
  const element = document.getElementById('statusBanner');
  element.replaceChildren();
  if (!message){
    element.style.display = 'none';
    return;
  }
  element.style.display = 'flex';
  element.className = `status-banner${isError ? ' error' : ''}`;
  const dot = document.createElement('span');
  dot.className = 'status-dot';
  const text = document.createElement('span');
  text.textContent = message;
  element.append(dot, text);
}

async function loadKpis(){
  renderSkeleton();
  setStatus(API_BASE ? '' : 'Using mock data — set API_BASE to connect your FastAPI backend.');
  try {
    [domains, kpis] = await Promise.all([api.listDomains(), api.list()]);
    domainSummaries = await Promise.all(
      domains.map(domain => api.getDomainSummary(domain.id))
    );
    render();
  } catch (err){
    console.error(err);
    kpis = [];
    domains = [];
    domainSummaries = [];
    render();
    setStatus(`Couldn't load the dashboard: ${err.message}`, true);
  }
}

function render(){
  const overview = document.getElementById('overviewView');
  const detail = document.getElementById('domainDetailView');
  const selectedDomain = domains.find(domain => domain.id === selectedDomainId);
  const hasSelection = Boolean(selectedDomain);
  overview.hidden = hasSelection;
  detail.hidden = !hasSelection;
  if (hasSelection){
    renderDomainDetail(selectedDomain);
  } else {
    selectedDomainId = null;
    renderDomainOverview();
  }
}

function renderDomainOverview(){
  const grid = document.getElementById('domainGrid');
  grid.replaceChildren();
  const summariesById = new Map(
    domainSummaries.map(summary => [summary.id, summary])
  );
  const period = domainSummaries.find(summary => summary.last_completed_month);
  document.getElementById('overviewPeriod').textContent = period
    ? `Last completed month · ${formatMonth(period.last_completed_month)}`
    : '';

  domains.forEach((domain, index) => {
    const summary = summariesById.get(domain.id);
    const score = summary?.score_percent ?? null;
    const kpiCount = summary?.kpis?.length ?? 0;
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'domain-card';
    card.setAttribute('aria-label', `Open ${domain.name}`);
    card.innerHTML = `
      <div class="domain-card-top">
        <span class="domain-name">${escapeHtml(domain.name)}</span>
        <span class="domain-chevron" aria-hidden="true">›</span>
      </div>
      <div class="domain-card-body">
        ${ringMarkup(score, ACCENTS[index % ACCENTS.length])}
        <div class="domain-card-copy">
          <span class="domain-score-caption">${score === null ? 'No score yet' : 'Monthly score'}</span>
          <span class="domain-kpi-count">${kpiCount} ${kpiCount === 1 ? 'KPI' : 'KPIs'}</span>
          <div class="domain-trends">
            ${formatChange(summary?.year_over_year_change_pp, 'YoY')}
            ${formatChange(summary?.month_over_month_change_pp, 'MoM')}
          </div>
        </div>
      </div>`;
    card.addEventListener('click', () => {
      selectedDomainId = domain.id;
      render();
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });
    grid.appendChild(card);
  });
}

function renderDomainDetail(domain){
  const summary = domainSummaries.find(item => item.id === domain.id);
  const summaryKpis = new Map((summary?.kpis || []).map(kpi => [kpi.id, kpi]));
  const domainKpis = kpis.filter(kpi => kpi.domain_id === domain.id);
  document.getElementById('detailTitle').textContent = domain.name;
  document.getElementById('detailPeriod').textContent = summary?.last_completed_month
    ? `Current KPI values · monthly score for ${formatMonth(summary.last_completed_month)}`
    : 'Current KPI values · no completed-month score yet';
  const scoreElement = document.getElementById('detailScore');
  scoreElement.innerHTML = summary?.score_percent == null
    ? '<span class="detail-score-value">—</span><span class="detail-score-label">No score yet</span>'
    : `<span class="detail-score-value">${Math.round(summary.score_percent)}%</span>
       <span class="detail-score-label">Monthly score</span>
       <span class="detail-score-trends">
         ${formatChange(summary.year_over_year_change_pp, 'YoY')}
         ${formatChange(summary.month_over_month_change_pp, 'MoM')}
       </span>`;

  const grid = document.getElementById('kpiGrid');
  grid.replaceChildren();
  domainKpis.forEach((kpi, index) => {
    const card = document.createElement('article');
    card.className = 'kpi-card';
    const summaryKpi = summaryKpis.get(kpi.id);
    if (kpi.tracking_mode === 'checkin') {
      renderCheckinKpiCard(card, kpi, summaryKpi, index);
      grid.appendChild(card);
      return;
    }
    const score = !kpi.has_value
      ? null
      : (kpi.direction === 'at_most'
        ? (kpi.value <= 0 ? 100 : Math.min(100, kpi.target / kpi.value * 100))
        : Math.min(100, kpi.value / kpi.target * 100));
    card.innerHTML = `
      <div class="kpi-top">
        <div>
          <span class="kpi-name">${escapeHtml(kpi.name)}</span>
          <div class="kpi-domain">${escapeHtml(kpi.domain_name)}</div>
        </div>
        <button class="kpi-menu-btn" type="button" aria-label="Edit ${escapeHtml(kpi.name)}" data-id="${escapeHtml(kpi.id)}">&#8942;</button>
      </div>
      <div class="kpi-body">
        ${ringMarkup(score, ACCENTS[index % ACCENTS.length], 62)}
        <div>
          <div class="kpi-value">${kpi.has_value ? formatNum(kpi.value) : '—'}${kpi.has_value && kpi.unit ? ` <span class="kpi-unit">${escapeHtml(kpi.unit)}</span>` : ''}</div>
          <div class="kpi-target">${kpi.direction === 'at_most' ? 'at most ' : 'of '}${formatNum(kpi.target)} ${escapeHtml(kpi.unit || '')}${kpi.direction === 'at_most' ? '' : ' target'}</div>
        </div>
      </div>`;
    card.querySelector('.kpi-menu-btn').addEventListener('click', () => openModal(kpi.id));
    grid.appendChild(card);
  });

  if (!domainKpis.length){
    const empty = document.createElement('p');
    empty.className = 'empty-state';
    empty.textContent = 'No KPIs in this domain yet. Add one to start tracking progress.';
    grid.appendChild(empty);
  }
}

function renderCheckinKpiCard(card, kpi, summaryKpi, index){
  const today = new Date().toISOString().slice(0, 10);
  const history = summaryKpi?.checkin_history || [];
  const todayEntry = history.find(entry => entry.date === today);
  const todayStatus = !todayEntry?.scheduled
    ? 'Not scheduled today'
    : !todayEntry.recorded
      ? 'Waiting for today’s check-in'
      : `Today: ${todayEntry.met ? 'Yes' : 'No'}`;
  const historyDots = history.map(entry => {
    const status = !entry.scheduled
    ? 'checkin-not-scheduled'
    : entry.recorded
    ? (entry.met ? 'checkin-yes' : 'checkin-no')
    : (entry.date < today ? 'checkin-missed' : 'checkin-pending');
    const description = !entry.scheduled
    ? 'Not scheduled'
    : entry.recorded
    ? (entry.met ? 'Yes, target met' : 'No, target not met')
    : (entry.date < today ? 'Missed check-in, counts as No' : 'Check-in due today');
    return `<span class="checkin-day ${status}" title="${entry.date}: ${description}" aria-label="${entry.date}: ${description}"></span>`;
  }).join('');
  const firstHistoryDay = history[0]
    ? new Date(`${history[0].date}T00:00:00`).getDay()
    : 1;
  const historyOffset = firstHistoryDay === 0 ? 6 : firstHistoryDay - 1;
  const historyPadding = Array.from({ length: historyOffset }, () =>
    '<span class="checkin-day-placeholder" aria-hidden="true"></span>'
  ).join('');

  card.innerHTML = `
    <div class="kpi-top">
      <div>
        <span class="kpi-name">${escapeHtml(kpi.name)}</span>
        <div class="kpi-domain">${escapeHtml(kpi.domain_name)} · Yes / No</div>
      </div>
      <button class="kpi-menu-btn" type="button" aria-label="Edit ${escapeHtml(kpi.name)}" data-id="${escapeHtml(kpi.id)}">&#8942;</button>
    </div>
    <div class="kpi-body">
      ${ringMarkup(summaryKpi?.period_score_percent ?? null, ACCENTS[index % ACCENTS.length], 62)}
      <div class="checkin-target">
        <div class="kpi-target">Target: ${formatNum(kpi.target)} ${escapeHtml(kpi.unit || '')}</div>
        <div class="checkin-today">${todayStatus}</div>
      </div>
    </div>
    <div class="checkin-history-label">Recent scheduled check-ins · last 5 weeks</div>
    <div class="checkin-weekdays" aria-hidden="true">
      <span>M</span><span>T</span><span>W</span><span>T</span><span>F</span><span>S</span><span>S</span>
    </div>
    <div class="checkin-history" role="group" aria-label="Check-in history for ${escapeHtml(kpi.name)}">${historyPadding}${historyDots}</div>
    <div class="checkin-actions" ${todayEntry?.scheduled ? '' : 'hidden'}>
      <button class="checkin-button yes" type="button" data-met="true">Yes</button>
      <button class="checkin-button no" type="button" data-met="false">No</button>
      <span class="checkin-action-hint">Record or correct today’s answer</span>
    </div>`;
  card.querySelector('.kpi-menu-btn').addEventListener('click', () => openModal(kpi.id));
  card.querySelectorAll('.checkin-button').forEach(button => {
    button.addEventListener('click', async () => {
      button.disabled = true;
      try {
        await api.setCheckin(kpi.id, today, button.dataset.met === 'true');
        await loadKpis();
      } catch (error) {
        console.error(error);
        setStatus(`Check-in failed: ${error.message}`, true);
      } finally {
        button.disabled = false;
      }
    });
  });
}

document.getElementById('backToOverview').addEventListener('click', () => {
  selectedDomainId = null;
  render();
});
document.getElementById('addKpiBtn').addEventListener('click', () => openModal(null));
