// Single source of truth for the current view; KPI objects match the mock/API response shape.
// render.js reads this state, while modal.js saves changes through api.js and reloads it.
let kpis = [];
let editingId = null;
