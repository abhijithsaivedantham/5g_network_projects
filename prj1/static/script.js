document.addEventListener('DOMContentLoaded', function() {
    const form = document.getElementById('simulation-form');
    const resultsSection = document.getElementById('results-section');
    const metricsTableBody = document.getElementById('metrics-table-body');
    
    const plotCountProgressionImg = document.getElementById('plot-count-progression');
    const plotBufferOccupancyImg = document.getElementById('plot-buffer-occupancy');
    const plotCountProgressionAlt = document.getElementById('plot-count-progression-alt');
    const plotBufferOccupancyAlt = document.getElementById('plot-buffer-occupancy-alt');

    const spinner = document.getElementById('spinner');
    const errorMessageDiv = document.getElementById('error-message');
    const runButton = document.getElementById('run-simulation-btn');

    form.addEventListener('submit', async function(event) {
        event.preventDefault();
        
        resultsSection.style.display = 'block';
        spinner.style.display = 'block';
        errorMessageDiv.style.display = 'none';
        metricsTableBody.innerHTML = ''; // Clear previous metrics
        plotCountProgressionImg.style.display = 'none';
        plotBufferOccupancyImg.style.display = 'none';
        plotCountProgressionAlt.style.display = 'none';
        plotBufferOccupancyAlt.style.display = 'none';
        runButton.disabled = true;
        runButton.textContent = 'Running...';

        const formData = new FormData(form);

        try {
            const response = await fetch('/run_simulation', {
                method: 'POST',
                body: formData
            });

            const data = await response.json();
            spinner.style.display = 'none';

            if (data.success) {
                displayMetrics(data.metrics);
                displayPlots(data.plots);
            } else {
                errorMessageDiv.textContent = 'Error: ' + (data.error || 'Unknown error occurred.');
                errorMessageDiv.style.display = 'block';
            }

        } catch (error) {
            spinner.style.display = 'none';
            errorMessageDiv.textContent = 'Network or server error: ' + error.message;
            errorMessageDiv.style.display = 'block';
            console.error('Simulation request failed:', error);
        } finally {
            runButton.disabled = false;
            runButton.textContent = 'Run Simulation';
        }
    });

    function displayMetrics(metrics) {
        const friendlyNames = {
            "total_sdu_sent": "Total SDUs Sent by TX",
            "tx_next_final": "TX_NEXT (Final)",
            "delivered_sdu_count": "SDUs Delivered by RX",
            "rx_deliv_final": "RX_DELIV (Final)",
            "rx_next_final": "RX_NEXT (Final)",
            "buffered_final": "PDUs in RX Buffer (Final)",
            "discarded_duplicates": "RX Discarded (Duplicate)",
            "discarded_old": "RX Discarded (Old/Out of Window)",
            "discarded_corrupted": "RX Discarded (Corrupted)",
            "out_of_order_deliveries": "RX Out-of-Order Deliveries (t-Reordering)",
            "channel_lost": "Channel: Packets Lost",
            "channel_duplicated": "Channel: Packets Duplicated",
            "channel_corrupted": "Channel: Packets Corrupted",
            "channel_reorder_events": "Channel: Reordering Events",
            "simulation_duration": "Simulation Duration"
        };

        for (const key in metrics) {
            if (metrics.hasOwnProperty(key)) {
                const row = metricsTableBody.insertRow();
                const cell1 = row.insertCell();
                const cell2 = row.insertCell();
                cell1.textContent = friendlyNames[key] || key;
                cell2.textContent = metrics[key];
            }
        }
    }

    function displayPlots(plots) {
        if (plots.count_progression) {
            plotCountProgressionImg.src = 'data:image/png;base64,' + plots.count_progression;
            plotCountProgressionImg.style.display = 'block';
        } else {
            plotCountProgressionAlt.style.display = 'block';
        }

        if (plots.buffer_occupancy) {
            plotBufferOccupancyImg.src = 'data:image/png;base64,' + plots.buffer_occupancy;
            plotBufferOccupancyImg.style.display = 'block';
        } else {
            plotBufferOccupancyAlt.style.display = 'block';
        }
    }
});