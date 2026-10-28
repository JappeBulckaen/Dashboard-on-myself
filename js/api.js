// Set this to the FastAPI origin to use the server; an empty value selects the mock API.
// The server returns KPI fields including domain assignment and numeric/check-in tracking.
// POST accepts the tracking mode and schedule in addition to numeric KPI fields.
// Check-in answers use POST /api/kpis/{id}/checkins with a date and Yes/No result.
// PUT accepts KPI fields and check-in schedule updates.
// DELETE currently returns { status: "deleted" }.
const API_BASE = 'http://127.0.0.1:8000';

const api = {
  async listDomains(){
    if (!API_BASE) return mockApi.listDomains();
    const res = await fetch(`${API_BASE}/api/domains`, { credentials: 'include' });
    if (!res.ok) throw new Error(`GET /api/domains failed: ${res.status}`);
    return res.json();
  },
  async getDomainSummary(id){
    if (!API_BASE) return mockApi.getDomainSummary(id);
    const res = await fetch(`${API_BASE}/api/domains/${id}/summary`, { credentials: 'include' });
    if (!res.ok) throw new Error(`GET /api/domains/${id}/summary failed: ${res.status}`);
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
  async setCheckin(id, checkinDate, met){
    if (!API_BASE) return mockApi.setCheckin(id, checkinDate, met);
    const res = await fetch(`${API_BASE}/api/kpis/${id}/checkins`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      credentials: 'include',
      body: JSON.stringify({ date: checkinDate, met })
    });
    if (!res.ok) throw new Error(`POST /api/kpis/${id}/checkins failed: ${res.status}`);
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
    async getDomainSummary(id){
      await delay();
      const domain = mockDomains.find(x => x.id === id);
      if (!domain) throw new Error('Life domain not found');
      const currentDate = new Date();
      const today = new Date(
        currentDate.getFullYear(),
        currentDate.getMonth(),
        currentDate.getDate()
      );
      const lastMonthStart = new Date(today.getFullYear(), today.getMonth() - 1, 1);
      const thisMonthStart = new Date(today.getFullYear(), today.getMonth(), 1);
      const dateString = date => `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-${String(date.getDate()).padStart(2, '0')}`;
      const isScheduled = (kpi, date) => {
        const start = kpi.schedule_start_date
          ? new Date(`${kpi.schedule_start_date}T00:00:00`)
          : today;
        if (date < start) return false;
        if (kpi.checkin_cadence === 'daily') return true;
        if (kpi.checkin_cadence === 'weekdays') return date.getDay() > 0 && date.getDay() < 6;
        if (kpi.checkin_cadence === 'biweekly') {
          const weeks = Math.floor((date - start) / (7 * 24 * 60 * 60 * 1000));
          return weeks % 2 === 0 && (kpi.schedule_weekdays || []).includes((date.getDay() + 6) % 7);
        }
        return false;
      };
      const domainKpis = store
        .filter(kpi => kpi.domain_id === id)
        .map(kpi => {
          if (kpi.tracking_mode === 'checkin') {
            const answers = kpi.checkin_history || [];
            const expected = [];
            for (let day = new Date(lastMonthStart); day < thisMonthStart; day.setDate(day.getDate() + 1)) {
              if (isScheduled(kpi, day)) expected.push(dateString(day));
            }
            const yesCount = expected.filter(day => answers.some(answer => answer.date === day && answer.met)).length;
            const history = [];
            for (let offset = 34; offset >= 0; offset--) {
              const day = new Date(today);
              day.setDate(day.getDate() - offset);
              const checkinDate = dateString(day);
              const answer = answers.find(entry => entry.date === checkinDate);
              history.push({
                date: checkinDate,
                scheduled: isScheduled(kpi, day),
                met: answer?.met ?? null,
                recorded: Boolean(answer)
              });
            }
            return {
              ...kpi,
              value: 0,
              has_value: false,
              checkin_history: history,
              period_score_percent: expected.length ? yesCount / expected.length * 100 : null
            };
          }
          const ratio = kpi.direction === 'at_most'
            ? (kpi.value <= 0 ? 1 : kpi.target / kpi.value)
            : kpi.value / kpi.target;
          const score = kpi.has_value
            ? Math.max(0, Math.min(1, ratio)) * 100
            : null;
          return { ...kpi, period_score_percent: score };
        });
      const scores = domainKpis
        .map(kpi => kpi.period_score_percent)
        .filter(score => score !== null);
      return {
        ...domain,
        last_completed_month: `${lastMonthStart.getFullYear()}-${String(lastMonthStart.getMonth() + 1).padStart(2, '0')}`,
        score_percent: scores.length
          ? scores.reduce((sum, score) => sum + score, 0) / scores.length
          : null,
        month_over_month_change_pp: null,
        year_over_year_change_pp: null,
        kpis: domainKpis
      };
    },
    async list(){ await delay(); return structuredClone(store); },
    async create(payload){
      await delay();
      const domain = mockDomains.find(x => x.id === payload.domain_id);
      const row = {
        id: cryptoId(),
        value: payload.value ?? 0,
        has_value: payload.value != null,
        schedule_weekdays: [],
        checkin_history: [],
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
    async setCheckin(id, checkinDate, met){
      await delay();
      const row = store.find(x => x.id === id);
      if (!row || row.tracking_mode !== 'checkin') throw new Error('Check-in KPI not found');
      row.checkin_history ||= [];
      const existing = row.checkin_history.find(entry => entry.date === checkinDate);
      if (existing) {
        existing.met = met;
        existing.recorded = true;
      } else {
        row.checkin_history.push({ date: checkinDate, met, recorded: true });
      }
      return { date: checkinDate, met, recorded: true };
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
