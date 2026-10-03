// The dashboard renders a fixed number of KPI slots.
const MAX_KPIS = 4;
const ACCENTS = ['var(--blue-1)', 'var(--blue-2)', 'var(--blue-3)', 'var(--blue-4)'];

// Set this to the FastAPI origin to use the server; an empty value selects the mock API.
// The server returns KPI fields { id, metric_type, name, value, target, unit }.
// POST accepts name/target plus optional unit/value/metric_type; PUT accepts name/target/unit.
// DELETE currently returns { status: "deleted" }.
const API_BASE = 'http://127.0.0.1:8000';

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

// Keep temporary dashboard data in memory until API_BASE is configured.
// The simulated delay makes loading states visible during development.
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
  // Mock records only need short IDs; persisted backend records use UUIDs.
  return Math.random().toString(36).slice(2, 10);
}
