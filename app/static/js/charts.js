document.addEventListener("DOMContentLoaded", () => {
    const categoriesCtx = document.getElementById('chart-categories');
    const trendsCtx = document.getElementById('chart-trends');
    const custodyCtx = document.getElementById('chart-custody');
    const activityCtx = document.getElementById('chart-activity');

    // Only load if at least one chart canvas is present on the page
    if (categoriesCtx || trendsCtx || custodyCtx || activityCtx) {
        fetch('/dashboard/chart-data')
            .then(res => res.json())
            .then(data => {
                // Common styling variables for dark theme charts
                const gridColor = 'rgba(255, 255, 255, 0.05)';
                const textColor = '#94a3b8';
                
                // 1. Evidence Categories Chart (Doughnut)
                if (categoriesCtx) {
                    new Chart(categoriesCtx, {
                        type: 'doughnut',
                        data: {
                            labels: data.categories.labels,
                            datasets: [{
                                data: data.categories.values,
                                backgroundColor: [
                                    '#06b6d4', // Cyan
                                    '#2563eb', // Blue
                                    '#10b981', // Green
                                    '#f59e0b', // Orange
                                    '#8b5cf6', // Purple
                                    '#ec4899', // Pink
                                    '#64748b'  // Grey
                                ],
                                borderWeight: 1,
                                borderColor: '#0f172a'
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: {
                                    position: 'right',
                                    labels: { color: textColor, font: { family: 'Inter' } }
                                }
                            }
                        }
                    });
                }

                // 2. Upload Trends Chart (Line)
                if (trendsCtx) {
                    new Chart(trendsCtx, {
                        type: 'line',
                        data: {
                            labels: data.trends.labels,
                            datasets: [{
                                label: 'Evidence Uploaded',
                                data: data.trends.values,
                                borderColor: '#06b6d4',
                                backgroundColor: 'rgba(6, 182, 212, 0.1)',
                                fill: true,
                                tension: 0.3,
                                borderWidth: 2
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                x: {
                                    grid: { color: gridColor },
                                    ticks: { color: textColor }
                                },
                                y: {
                                    grid: { color: gridColor },
                                    ticks: { color: textColor, stepSize: 1 },
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }

                // 3. Custody Transfers Chart (Bar)
                if (custodyCtx) {
                    new Chart(custodyCtx, {
                        type: 'bar',
                        data: {
                            labels: data.custody.labels,
                            datasets: [{
                                label: 'Events Count',
                                data: data.custody.values,
                                backgroundColor: '#2563eb',
                                borderRadius: 4,
                                borderSkipped: false
                            }]
                        },
                        options: {
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                x: {
                                    grid: { color: gridColor },
                                    ticks: { color: textColor }
                                },
                                y: {
                                    grid: { color: gridColor },
                                    ticks: { color: textColor, stepSize: 1 },
                                    beginAtZero: true
                                }
                            }
                        }
                    });
                }

                // 4. User Activity Chart (Horizontal Bar or Radar/Polar)
                if (activityCtx) {
                    new Chart(activityCtx, {
                        type: 'bar',
                        data: {
                            labels: data.activity.labels,
                            datasets: [{
                                label: 'Audit Actions Logged',
                                data: data.activity.values,
                                backgroundColor: '#10b981',
                                borderRadius: 4
                            }]
                        },
                        options: {
                            indexAxis: 'y',
                            responsive: true,
                            maintainAspectRatio: false,
                            plugins: {
                                legend: { display: false }
                            },
                            scales: {
                                x: {
                                    grid: { color: gridColor },
                                    ticks: { color: textColor, stepSize: 5 },
                                    beginAtZero: true
                                },
                                y: {
                                    grid: { color: gridColor },
                                    ticks: { color: textColor }
                                }
                            }
                        }
                    });
                }
            })
            .catch(err => console.error("Error loading dashboard charts:", err));
    }
});
