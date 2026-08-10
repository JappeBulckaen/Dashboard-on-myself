
  const MAX_KPIS = 4;
  const ACCENTS = ['var(--blue-1)', 'var(--blue-2)', 'var(--blue-3)', 'var(--blue-4)'];

  // ---------- API layer ----------
  // Swap API_BASE for your FastAPI deployment (Render/Railway) when live.
  // Expected contract, matching the facts-table model:
  //   GET    /api/kpis            -> [{ id, metric_type, name, value, target, unit }]
  //   POST   /api/kpis            -> body: { metric_type, name, target, unit } -> created row
  //   PUT    /api/kpis/:id        -> body: { name, target, unit }              -> updated row
  //   DELETE /api/kpis/:id        -> 204
  // `value` on GET is server-computed: latest/aggregated fact for that metric_type
  // from the normalized facts table (user_id, source_app, metric_type, value, unit, timestamp).
  // The dashboard never writes `value` directly — that only comes from connector ingestion.
  const API_BASE = ''; // e.g. 'https://your-api.onrender.com' — leave blank to force mock mode

  const api = {
    async list(){
      if (!API_BASE) return mockApi.list();
      const res = await fetch(`${API_BASE}/api/kpis`, { credentials: 'include' });
      if (!res.ok) throw new Error(`GET /api/kpis failed: ${res.status}`);
      return res.json();
    },
    async create(payload){
      if (!API_BASE) return mockApi.create(payload);
      const res = await fetch(`${API_BASE}/api/kpis`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`POST /api/kpis failed: ${res.status}`);
      return res.json();
    },
    async update(id, payload){
      if (!API_BASE) return mockApi.update(id, payload);
      const res = await fetch(`${API_BASE}/api/kpis/${id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        credentials: 'include',
        body: JSON.stringify(payload)
      });
      if (!res.ok) throw new Error(`PUT /api/kpis/${id} failed: ${res.status}`);
      return res.json();
    },
    async remove(id){
      if (!API_BASE) return mockApi.remove(id);
      const res = await fetch(`${API_BASE}/api/kpis/${id}`, { method: 'DELETE', credentials: 'include' });
      if (!res.ok) throw new Error(`DELETE /api/kpis/${id} failed: ${res.status}`);
    }
  };

  // Mock backend so the UI is fully functional before FastAPI exists.
  // Simulated network delay keeps loading states honest during dev.
  const mockApi = (() => {
    let store = [
      { id: cryptoId(), metric_type: 'strava.distance_weekly', name: 'Weekly Runs', value: 3, target: 5, unit: 'km' },
      { id: cryptoId(), metric_type: 'googlefit.sleep_avg', name: 'Sleep Avg', value: 6.8, target: 8, unit: 'h' },
    ];
    const delay = (ms = 250) => new Promise(r => setTimeout(r, ms));
    return {
      async list(){ await delay(); return structuredClone(store); },
      async create(payload){
        await delay();
        const row = { id: cryptoId(), value: 0, ...payload };
        store.push(row);
        return structuredClone(row);
      },
      async update(id, payload){
        await delay();
        const row = store.find(x => x.id === id);
        if (!row) throw new Error('Not found');
        Object.assign(row, payload);
        return structuredClone(row);
      },
      async remove(id){
        await delay();
        store = store.filter(x => x.id !== id);
      }
    };
  })();

  let kpis = [];
  let editingId = null;

  function cryptoId(){
    return Math.random().toString(36).slice(2, 10);
  }

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

  function formatNum(n){
    const num = Number(n);
    return Number.isInteger(num) ? num : num.toFixed(1);
  }

  function escapeHtml(str){
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  // ---------- Modal handling ----------
  const overlay = document.getElementById('overlay');
  const form = document.getElementById('kpiForm');
  const modalTitle = document.getElementById('modalTitle');
  const deleteBtn = document.getElementById('deleteBtn');

  function openModal(id){
    editingId = id;
    const k = id ? kpis.find(x => x.id === id) : null;
    modalTitle.textContent = k ? 'Edit KPI' : 'Add KPI';
    document.getElementById('fName').value = k ? k.name : '';
    document.getElementById('fValue').value = k ? k.value : '';
    document.getElementById('fTarget').value = k ? k.target : '';
    document.getElementById('fUnit').value = k ? (k.unit || '') : '';
    deleteBtn.style.display = k ? 'inline-block' : 'none';
    overlay.classList.add('open');
    document.getElementById('fName').focus();
  }

  function closeModal(){
    overlay.classList.remove('open');
    editingId = null;
    form.reset();
  }

  document.getElementById('cancelBtn').addEventListener('click', closeModal);
  overlay.addEventListener('click', (e) => { if (e.target === overlay) closeModal(); });
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape' && overlay.classList.contains('open')) closeModal(); });

  form.addEventListener('submit', async (e) => {
    e.preventDefault();
    const name = document.getElementById('fName').value.trim();
    const value = parseFloat(document.getElementById('fValue').value);
    const target = parseFloat(document.getElementById('fTarget').value);
    const unit = document.getElementById('fUnit').value.trim();

    if (!name || isNaN(value) || isNaN(target)) return;

    const saveBtn = form.querySelector('.btn-primary');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Saving…';

    try {
      if (editingId){
        // NB: `value` is not sent — it's server-derived from ingested facts,
        // never edited directly from the dashboard config UI.
        await api.update(editingId, { name, target, unit });
      } else {
        if (kpis.length >= MAX_KPIS) return;
        await api.create({ name, target, unit, value, metric_type: 'manual.custom' });
      }
      closeModal();
      await loadKpis();
    } catch (err){
      console.error(err);
      setStatus(`Save failed: ${err.message}`, true);
    } finally {
      saveBtn.disabled = false;
      saveBtn.textContent = 'Save';
    }
  });

  deleteBtn.addEventListener('click', async () => {
    deleteBtn.disabled = true;
    try {
      await api.remove(editingId);
      closeModal();
      await loadKpis();
    } catch (err){
      console.error(err);
      setStatus(`Delete failed: ${err.message}`, true);
    } finally {
      deleteBtn.disabled = false;
    }
  });

  // ---------- Greeting + date ----------
  function setGreeting(){
    const h = new Date().getHours();
    const g = h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
    document.getElementById('greeting').textContent = g;
    document.getElementById('today').textContent = new Date().toLocaleDateString(undefined, { weekday: 'long', month: 'short', day: 'numeric' });
  }

  setGreeting();
  loadKpis();
