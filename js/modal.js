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
