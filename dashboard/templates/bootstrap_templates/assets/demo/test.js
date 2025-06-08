const ctx = document.getElementById('temperatureChart').getContext('2d');
        const temperatureChart = new Chart(ctx, {
            type: 'line',
            data: {
                labels: [
                    {% for entry in data %}
                        "{{ entry.time_stamp }}",
                    {% endfor %}
                ],
                datasets: [
                    {
                        label: 'Current Temp (°F)',
                        data: [
                            {% for entry in data %}
                                {{ entry.current_temp }},
                            {% endfor %}
                        ],
                        borderColor: 'rgba(255, 99, 132, 1)',
                        backgroundColor: 'rgba(255, 99, 132, 0.2)',
                        borderWidth: 2,
                        tension: 0.4
                    },
                    {
                        label: 'Set Temp (°F)',
                        data: [
                            {% for entry in data %}
                                {{ entry.set_temp }},
                            {% endfor %}
                        ],
                        borderColor: 'rgba(54, 162, 235, 1)',
                        backgroundColor: 'rgba(54, 162, 235, 0.2)',
                        borderWidth: 2,
                        tension: 0.4
                    }
                ]
            },
            options: {
                responsive: true,
                plugins: {
                    legend: {
                        display: true,
                        position: 'top',
                    },
                    tooltip: {
                        enabled: true
                    }
                },
                scales: {
                    x: {
                        title: {
                            display: true,
                            text: 'Time Stamp',
                            color: '#333'
                        },
                        ticks: {
                            autoSkip: true,
                            maxTicksLimit: 10
                        }
                    },
                    y: {
                        title: {
                            display: true,
                            text: 'Temperature (°F)',
                            color: '#333'
                        },
                        beginAtZero: false
                    }
                }
            }
        });