// The dashboard renders a fixed number of KPI slots.
const MAX_KPIS = 4;
const ACCENTS = ['var(--blue-1)', 'var(--blue-2)', 'var(--blue-3)', 'var(--blue-4)'];

// Set this to the FastAPI origin to use the server; an empty value selects the mock API.
// The server returns KPI fields including its life-domain assignment and progress direction.
// POST accepts name/target/domain_id plus optional direction/unit/value/metric_type.
// PUT accepts optional name/target/domain_id/direction/unit.
// DELETE currently returns { status: "deleted" }.
const API_BASE = 'http://127.0.0.1:8000';

const api = {
  async listDomains(){
    if (!API_BASE) return mockApi.listDomains();
    const res = await fetch(`${API_BASE}/api/domains`, { credentials: 'include' });
    if (!res.ok) throw new Error(`GET /api/domains failed: ${res.status}`);
    return res.json();
  },
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
  const mockDomains = [
    { id: 'health_fitness', key: 'health_fitness', name: 'Health & Fitness', position: 0 },
    { id: 'productivity', key: 'productivity', name: 'Productivity', position: 1 },
    { id: 'finance', key: 'finance', name: 'Finance', position: 2 },
    { id: 'relationships', key: 'relationships', name: 'Relationships', position: 3 },
    { id: 'household', key: 'household', name: 'Household', position: 4 },
    { id: 'other', key: 'other', name: 'Other', position: 5 },
  ];
  let store = [
    { id: cryptoId(), metric_type: 'strava.distance_weekly', name: 'Weekly Runs', value: 3, has_value: true, target: 5, unit: 'km', domain_id: 'health_fitness', domain_name: 'Health & Fitness', direction: 'at_least' },
    { id: cryptoId(), metric_type: 'googlefit.sleep_avg', name: 'Sleep Avg', value: 6.8, has_value: true, target: 8, unit: 'h', domain_id: 'health_fitness', domain_name: 'Health & Fitness', direction: 'at_least' },
  ];
  const delay = (ms = 250) => new Promise(r => setTimeout(r, ms));
  return {
    async listDomains(){ await delay(); return structuredClone(mockDomains); },
    async list(){ await delay(); return structuredClone(store); },
    async create(payload){
      await delay();
      const domain = mockDomains.find(x => x.id === payload.domain_id);
      const row = {
        id: cryptoId(),
        value: payload.value ?? 0,
        has_value: payload.value != null,
        ...payload,
        domain_name: domain.name
      };
      store.push(row);
      return structuredClone(row);
    },
    async update(id, payload){
      await delay();
      const row = store.find(x => x.id === id);
      if (!row) throw new Error('Not found');
      Object.assign(row, payload);
      if (payload.domain_id) {
        const domain = mockDomains.find(x => x.id === payload.domain_id);
        row.domain_name = domain.name;
      }
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
