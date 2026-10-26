const overlay = document.getElementById('overlay');
const form = document.getElementById('kpiForm');
const modalTitle = document.getElementById('modalTitle');
const deleteBtn = document.getElementById('deleteBtn');

// Open a blank form for a new KPI or preload the selected KPI for editing.
function openModal(id){
  editingId = id;
  const k = id ? kpis.find(x => x.id === id) : null;
  modalTitle.textContent = k ? 'Edit KPI' : 'Add KPI';
  document.getElementById('fName').value = k ? k.name : '';
  const domainSelect = document.getElementById('fDomain');
  domainSelect.replaceChildren(...domains.map(domain => {
    const option = document.createElement('option');
    option.value = domain.id;
    option.textContent = domain.name;
    return option;
  }));
  domainSelect.value = k ? k.domain_id : '';
  document.getElementById('fDirection').value = k ? k.direction : 'at_least';
  document.getElementById('fValue').value = k && k.has_value ? k.value : '';
  document.getElementById('fTarget').value = k ? k.target : '';
  document.getElementById('fUnit').value = k ? (k.unit || '') : '';
  deleteBtn.style.display = k ? 'inline-block' : 'none';
  overlay.classList.add('open');
  document.getElementById('fName').focus();
}

// Clear edit state and form values whenever the dialog closes.
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
  // Read and normalize form values before sending the request.
  const name = document.getElementById('fName').value.trim();
  const domain_id = document.getElementById('fDomain').value;
  const direction = document.getElementById('fDirection').value;
  const rawValue = document.getElementById('fValue').value.trim();
  const value = rawValue === '' ? null : parseFloat(rawValue);
  const target = parseFloat(document.getElementById('fTarget').value);
  const unit = document.getElementById('fUnit').value.trim();

  if (!name || !domain_id || (value !== null && !Number.isFinite(value)) || !Number.isFinite(target)) return;

  const saveBtn = form.querySelector('.btn-primary');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';

  try {
    if (editingId){
      // NB: `value` is not sent — it's server-derived from ingested facts,
      // never edited directly from the dashboard config UI.
      await api.update(editingId, { name, target, domain_id, direction, unit });
    } else {
      // Keep the UI's four-card limit in sync with the available dashboard slots.
      if (kpis.length >= MAX_KPIS) return;
      const payload = { name, target, domain_id, direction, unit };
      if (value !== null) payload.value = value;
      await api.create(payload);
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
