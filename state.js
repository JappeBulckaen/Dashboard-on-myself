// Single source of truth for the current view. Kept deliberately tiny —
// render.js reads it, modal.js writes to it via api.js then triggers a reload.
let kpis = [];
let editingId = null;
