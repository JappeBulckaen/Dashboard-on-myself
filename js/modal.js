const overlay = document.getElementById('overlay');
const form = document.getElementById('kpiForm');
const modalTitle = document.getElementById('modalTitle');
const deleteBtn = document.getElementById('deleteBtn');
const trackingModeSelect = document.getElementById('fTrackingMode');
const cadenceSelect = document.getElementById('fCadence');

function localDateString(date = new Date()){
  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  return `${year}-${month}-${day}`;
}

function updateTrackingFields(){
  const isCheckin = trackingModeSelect.value === 'checkin';
  document.getElementById('cadenceField').hidden = !isCheckin;
  document.getElementById('scheduleStartField').hidden = !isCheckin;
  document.getElementById('weekdayField').hidden = !isCheckin || cadenceSelect.value !== 'biweekly';
  document.getElementById('directionField').hidden = isCheckin;
  document.getElementById('currentValueField').hidden = isCheckin;
  document.getElementById('trackingHint').textContent = isCheckin
    ? 'Each scheduled check-in records whether you met this target. Missed past check-ins count as No.'
    : 'Progress ring fills based on current value vs. target.';
}

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
  domainSelect.value = k ? k.domain_id : (selectedDomainId || '');
  trackingModeSelect.value = k ? (k.tracking_mode || 'numeric') : 'numeric';
  trackingModeSelect.disabled = Boolean(k);
  cadenceSelect.value = k?.checkin_cadence || 'daily';
  document.getElementById('fScheduleStart').value = k?.schedule_start_date || localDateString();
  document.querySelectorAll('input[name="fWeekday"]').forEach(input => {
    input.checked = (k?.schedule_weekdays || []).includes(Number(input.value));
  });
  if (k?.checkin_cadence === 'biweekly' && !(k.schedule_weekdays || []).length) {
    document.querySelector('input[name="fWeekday"][value="0"]').checked = true;
  }
  updateTrackingFields();
  document.getElementById('fDirection').value = k ? k.direction : 'at_least';
  document.getElementById('fValue').value = k && k.has_value ? k.value : '';
  document.getElementById('fTarget').value = k ? k.target : '';
  document.getElementById('fUnit').value = k ? (k.unit || '') : '';
  deleteBtn.style.display = k ? 'inline-block' : 'none';
  overlay.classList.add('open');
  document.getElementById('fName').focus();
}

trackingModeSelect.addEventListener('change', updateTrackingFields);
cadenceSelect.addEventListener('change', updateTrackingFields);

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
  const tracking_mode = trackingModeSelect.value;
  const checkin_cadence = cadenceSelect.value;
  const schedule_start_date = document.getElementById('fScheduleStart').value;
  const schedule_weekdays = [...document.querySelectorAll('input[name="fWeekday"]:checked')]
    .map(input => Number(input.value));

  if (!name || !domain_id || !Number.isFinite(target)
      || (tracking_mode === 'numeric' && value !== null && !Number.isFinite(value))
      || (tracking_mode === 'checkin' && !schedule_start_date)
      || (tracking_mode === 'checkin' && checkin_cadence === 'biweekly' && !schedule_weekdays.length)) {
    if (tracking_mode === 'checkin' && checkin_cadence === 'biweekly' && !schedule_weekdays.length) {
      setStatus('Choose at least one weekday for a biweekly check-in.', true);
    }
    return;
  }

  const saveBtn = form.querySelector('.btn-primary');
  saveBtn.disabled = true;
  saveBtn.textContent = 'Saving…';

  try {
    if (editingId){
      // NB: `value` is not sent — it's server-derived from ingested facts,
      // never edited directly from the dashboard config UI.
      const payload = { name, target, domain_id, direction, unit };
      if (tracking_mode === 'checkin') {
        payload.checkin_cadence = checkin_cadence;
        payload.schedule_start_date = schedule_start_date;
        payload.schedule_weekdays = checkin_cadence === 'biweekly'
          ? schedule_weekdays
          : null;
      }
      await api.update(editingId, payload);
    } else {
      const payload = { name, target, domain_id, direction, unit, tracking_mode };
      if (tracking_mode === 'checkin') {
        payload.checkin_cadence = checkin_cadence;
        payload.schedule_start_date = schedule_start_date;
        if (checkin_cadence === 'biweekly') payload.schedule_weekdays = schedule_weekdays;
      } else if (value !== null) {
        payload.value = value;
      }
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
