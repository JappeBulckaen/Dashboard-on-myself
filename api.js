// ---------- Constants ----------
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

function cryptoId(){
  return Math.random().toString(36).slice(2, 10);
}
