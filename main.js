function setGreeting(){
  const h = new Date().getHours();
  const g = h < 12 ? 'Good morning' : h < 18 ? 'Good afternoon' : 'Good evening';
  document.getElementById('greeting').textContent = g;
  document.getElementById('today').textContent = new Date().toLocaleDateString(undefined, { weekday: 'long', day: 'numeric',  month: 'short' });
}

// main.js loads last, after api.js / state.js / render.js / modal.js have
// defined everything it depends on. `defer` guarantees DOM is parsed and
// scripts have run in source order, so it's safe to call these directly here.
setGreeting();
loadKpis();
