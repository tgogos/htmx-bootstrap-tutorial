/* globals Chart:false */

(() => {
  'use strict'

  const canvas = document.getElementById('signins-chart')
  if (!canvas) {
    return
  }

  if (typeof Chart === 'undefined') {
    const note = document.createElement('p')
    note.className = 'small text-body-secondary mb-0'
    note.textContent = 'Chart.js is not loaded. The rest of this page remains usable.'
    canvas.replaceWith(note)
    return
  }

  if (window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
    Chart.defaults.animation = false
  }

  const cssVar = name => getComputedStyle(document.documentElement).getPropertyValue(name).trim()

  const palette = () => ({
    color: cssVar('--bs-body-color'),
    border: cssVar('--bs-border-color'),
    primary: cssVar('--bs-primary'),
    bodyBg: cssVar('--bs-body-bg')
  })

  const buildOptions = colors => ({
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      legend: { display: false },
      tooltip: { boxPadding: 4 }
    },
    scales: {
      x: {
        ticks: { color: colors.color },
        grid: { color: colors.border }
      },
      y: {
        beginAtZero: true,
        ticks: { color: colors.color, precision: 0 },
        grid: { color: colors.border }
      }
    }
  })

  const colors = palette()
  const chart = new Chart(canvas, {
    type: 'line',
    data: {
      labels: ['Thu', 'Fri', 'Sat', 'Sun', 'Mon', 'Tue', 'Wed'],
      datasets: [{
        label: 'Sign-ins',
        data: [18, 24, 9, 7, 31, 28, 22],
        tension: 0.15,
        fill: false,
        borderColor: colors.primary,
        backgroundColor: colors.primary,
        borderWidth: 2,
        pointBackgroundColor: colors.bodyBg,
        pointBorderColor: colors.primary,
        pointRadius: 3
      }]
    },
    options: buildOptions(colors)
  })

  const refresh = () => {
    const next = palette()
    chart.data.datasets[0].borderColor = next.primary
    chart.data.datasets[0].backgroundColor = next.primary
    chart.data.datasets[0].pointBackgroundColor = next.bodyBg
    chart.data.datasets[0].pointBorderColor = next.primary
    chart.options = buildOptions(next)
    chart.update()
  }

  window.addEventListener('admin:themechange', refresh)
})()
