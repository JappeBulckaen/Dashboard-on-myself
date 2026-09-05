function pct(k){
  if (!k.target) return 0;
  return Math.max(0, Math.min(1, k.value / k.target));
}

function ringMarkup(progress, accent){
  const r = 26, c = 2 * Math.PI * r;
  const offset = c * (1 - progress);
  return `
    <div class="ring-wrap">
      <svg width="62" height="62" viewBox="0 0 62 62">
        <circle class="ring-track" cx="31" cy="31" r="${r}"></circle>
        <circle class="ring-progress" cx="31" cy="31" r="${r}"
          stroke="${accent}"
          stroke-dasharray="${c}"
          stroke-dashoffset="${offset}"></circle>
      </svg>
      <div class="ring-pct">${Math.round(progress * 100)}%</div>
    </div>`;
}

function formatNum(n){
  const num = Number(n);
  return Number.isInteger(num) ? num : num.toFixed(1);
}

function escapeHtml(str){
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderSkeleton(){
  const grid = document.getElementById('kpiGrid');
  grid.innerHTML = '';
  for (let i = 0; i < MAX_KPIS; i++){
    const card = document.createElement('div');
    card.className = 'kpi-card skeleton';
    card.innerHTML = `
      <div class="skeleton-line" style="width:40%;"></div>
      <div style="display:flex; align-items:center; gap:18px;">
        <div class="skeleton-line" style="width:62px; height:62px; border-radius:50%;"></div>
        <div style="flex:1;">
          <div class="skeleton-line" style="width:60%; height:26px; margin-bottom:8px;"></div>
          <div class="skeleton-line" style="width:40%;"></div>
        </div>
      </div>`;
    grid.appendChild(card);
  }
}

function setStatus(message, isError = false){
  const el = document.getElementById('statusBanner');
  if (!message){ el.style.display = 'none'; return; }
  el.style.display = 'flex';
  el.className = `status-banner${isError ? ' error' : ''}`;
  el.innerHTML = `<span class="status-dot"></span>${message}`;
}

async function loadKpis(){
  renderSkeleton();
  setStatus(API_BASE ? '' : 'Using mock data — set API_BASE to connect your FastAPI backend.');
  try {
    kpis = await api.list();
    render();
  } catch (err){
    console.error(err);
    kpis = [];
    render();
    setStatus(`Couldn't load KPIs: ${err.message}`, true);
  }
}

function render(){
  const grid = document.getElementById('kpiGrid');
  grid.innerHTML = '';

  for (let i = 0; i < MAX_KPIS; i++){
    const k = kpis[i];
    if (k){
      const accent = ACCENTS[i % ACCENTS.length];
      const progress = pct(k);
      const card = document.createElement('div');
      card.className = 'kpi-card';
      card.innerHTML = `
        <div class="kpi-top">
          <span class="kpi-name">${escapeHtml(k.name)}</span>
          <button class="kpi-menu-btn" aria-label="Edit ${escapeHtml(k.name)}" data-id="${k.id}">&#8942;</button>
        </div>
        <div class="kpi-body">
          ${ringMarkup(progress, accent)}
          <div>
            <div class="kpi-value">${formatNum(k.value)}<span class="kpi-unit">${escapeHtml(k.unit||'')}</span></div>
            <div class="kpi-target">of ${formatNum(k.target)}${escapeHtml(k.unit||'')} target</div>
          </div>
        </div>
      `;
      card.querySelector('.kpi-menu-btn').addEventListener('click', (e) => {
        e.stopPropagation();
        openModal(k.id);
      });
      grid.appendChild(card);
    } else {
      const empty = document.createElement('button');
      empty.className = 'kpi-card kpi-empty';
      empty.innerHTML = `<span class="plus">+</span><span class="plus-label">Add KPI</span>`;
      empty.addEventListener('click', () => openModal(null));
      grid.appendChild(empty);
    }
  }
}
