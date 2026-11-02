// Gráficos del ERP (Chart.js) con la identidad de Blancos Aromáticos
Chart.defaults.font.family = "'Manrope', system-ui, sans-serif";
Chart.defaults.font.weight = 600;
Chart.defaults.color = '#7b858f';
Chart.defaults.borderColor = '#ecebe5';

const COLOR_LINEA = { Desinfectante: '#6b58d3', ECO: '#5f9221' };
const colorDe = nombre => Object.entries(COLOR_LINEA).find(([k]) => nombre.includes(k))?.[1] || '#0e6b5b';

function graficoSemanal(id, datos) {
  const series = Object.entries(datos.series).map(([nombre, valores]) => ({
    label: nombre, data: valores, backgroundColor: colorDe(nombre), borderRadius: 6, borderSkipped: false, maxBarThickness: 34,
  }));
  new Chart(document.getElementById(id), {
    type: 'bar',
    data: { labels: datos.etiquetas, datasets: series },
    options: {
      responsive: true,
      plugins: { legend: { display: false }, tooltip: { padding: 10, cornerRadius: 8, callbacks: { title: i => 'Semana del ' + i[0].label } } },
      scales: {
        x: { stacked: true, grid: { display: false }, border: { display: false }, ticks: { maxRotation: 0, autoSkip: true } },
        y: { stacked: true, beginAtZero: true, border: { display: false }, ticks: { maxTicksLimit: 5 }, title: { display: true, text: 'unidades de 1 L' } },
      },
    },
  });
}

function graficoSensor(canvas, url, intervaloMs) {
  const grafico = new Chart(canvas, {
    type: 'line',
    data: { labels: [], datasets: [
      { label: 'valor', data: [], borderColor: '#0e6b5b', backgroundColor: 'rgba(14,107,91,.08)', fill: true, tension: .35, pointRadius: 0, borderWidth: 2 },
      { label: 'mín', data: [], borderColor: '#bb3a33', borderDash: [4, 4], pointRadius: 0, borderWidth: 1 },
      { label: 'máx', data: [], borderColor: '#bb3a33', borderDash: [4, 4], pointRadius: 0, borderWidth: 1 },
    ] },
    options: { animation: false, plugins: { legend: { display: false } }, scales: { x: { ticks: { maxTicksLimit: 3, maxRotation: 0, autoSkip: true }, grid: { display: false } }, y: { border: { display: false }, ticks: { maxTicksLimit: 4 } } } },
  });
  const valorEl = document.querySelector(`[data-valor-de="${canvas.id}"]`);
  const ordenEl = document.querySelector(`[data-orden-de="${canvas.id}"]`);
  const tarjeta = canvas.closest('.sensor');
  async function actualizar() {
    try {
      const d = await (await fetch(url)).json();
      grafico.data.labels = d.etiquetas;
      grafico.data.datasets[0].data = d.valores;
      grafico.data.datasets[1].data = d.min === null ? [] : d.valores.map(() => d.min);
      grafico.data.datasets[2].data = d.max === null ? [] : d.valores.map(() => d.max);
      grafico.update();
      if (valorEl && d.ultima !== null) {
        valorEl.textContent = d.ultima.toFixed(d.unidad === 'und' ? 0 : 2);
        const fuera = (d.min !== null && d.ultima < d.min) || (d.max !== null && d.ultima > d.max);
        valorEl.classList.toggle('text-danger', fuera);
        tarjeta?.classList.toggle('fuera', fuera);
      }
      if (ordenEl) ordenEl.textContent = d.orden || 'sin orden activa';
    } catch (e) { /* sin conexión: se reintenta en el próximo ciclo */ }
  }
  actualizar();
  setInterval(actualizar, intervaloMs);
}
