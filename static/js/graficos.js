// Gráficos compartidos (Chart.js)
const PALETA = ['#0f766e', '#d97706', '#2563eb', '#9333ea', '#dc2626'];

function graficoSemanal(id, datos) {
  const series = Object.entries(datos.series).map(([nombre, valores], i) => ({
    label: nombre, data: valores, backgroundColor: PALETA[i % PALETA.length], borderRadius: 4,
  }));
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels: datos.etiquetas.map(e => 'Sem. ' + e), datasets: series },
    options: {
      responsive: true,
      plugins: { legend: { position: 'bottom' } },
      scales: { x: { stacked: true, grid: { display: false } }, y: { stacked: true, beginAtZero: true, title: { display: true, text: 'unidades' } } },
    },
  });
}

function graficoSensor(canvas, url, intervaloMs) {
  const grafico = new Chart(canvas, {
    type: 'line',
    data: { labels: [], datasets: [
      { label: 'valor', data: [], borderColor: '#0f766e', backgroundColor: 'rgba(15,118,110,.08)', fill: true, tension: .3, pointRadius: 0 },
      { label: 'mín', data: [], borderColor: '#dc2626', borderDash: [4, 4], pointRadius: 0, borderWidth: 1 },
      { label: 'máx', data: [], borderColor: '#dc2626', borderDash: [4, 4], pointRadius: 0, borderWidth: 1 },
    ] },
    options: { animation: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 6 } } } },
  });
  const valorEl = document.querySelector(`[data-valor-de="${canvas.id}"]`);
  const ordenEl = document.querySelector(`[data-orden-de="${canvas.id}"]`);
  async function actualizar() {
    try {
      const r = await fetch(url);
      const d = await r.json();
      grafico.data.labels = d.etiquetas;
      grafico.data.datasets[0].data = d.valores;
      grafico.data.datasets[1].data = d.min === null ? [] : d.valores.map(() => d.min);
      grafico.data.datasets[2].data = d.max === null ? [] : d.valores.map(() => d.max);
      grafico.update();
      if (valorEl && d.ultima !== null) {
        valorEl.textContent = d.ultima.toFixed(2);
        const fuera = (d.min !== null && d.ultima < d.min) || (d.max !== null && d.ultima > d.max);
        valorEl.classList.toggle('text-danger', fuera);
      }
      if (ordenEl) ordenEl.textContent = d.orden || 'sin orden activa';
    } catch (e) { /* sin conexión: se reintenta en el próximo ciclo */ }
  }
  actualizar();
  setInterval(actualizar, intervaloMs);
}
