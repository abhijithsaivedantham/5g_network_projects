// Initialize counters and chart instance in the global scope of the script.
// This state lives in the user's browser tab and is reset on page reload.
let successCount = 0;
let failCount = 0;
let eavesdropCount = 0;
let chart = null;

// This function runs once the HTML document is fully loaded.
document.addEventListener('DOMContentLoaded', () => {
    const ctx = document.getElementById('cipheringChart').getContext('2d');
    
    // Chart.js configuration
    chart = new Chart(ctx, {
        type: 'bar',
        data: {
            labels: ['Successful Decryptions', 'Failed Decryptions', 'Eavesdrop Attempts'],
            datasets: [{
                label: 'Ciphering Metrics',
                data: [successCount, failCount, eavesdropCount],
                backgroundColor: ['#34a853', '#ea4335', '#fbbc05'],
                borderColor: ['#2d8e44', '#c1362d', '#d89e04'],
                borderWidth: 1,
                borderRadius: 5
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: true,
            scales: {
                y: {
                    beginAtZero: true,
                    title: {
                        display: true,
                        text: 'Count',
                        color: '#cccccc', // Dark theme text color
                        font: { size: 14 }
                    },
                    ticks: { 
                        color: '#cccccc', // Dark theme tick color
                        stepSize: 1 
                    },
                    grid: { color: '#444444' } // Dark theme grid line color
                },
                x: {
                    title: {
                        display: true,
                        text: 'Metrics',
                        color: '#cccccc', // Dark theme text color
                        font: { size: 14 }
                    },
                    ticks: { color: '#cccccc' }, // Dark theme tick color
                    grid: { display: false } // Hide vertical grid lines for a cleaner look
                }
            },
            plugins: {
                legend: {
                    display: true,
                    labels: {
                        color: '#cccccc', // Dark theme legend text color
                        font: { size: 14 }
                    }
                },
                tooltip: {
                    backgroundColor: '#000',
                    titleColor: '#fff',
                    bodyColor: '#fff'
                }
            }
        }
    });
});

function runSimulation() {
    console.log("runSimulation called");

    const plaintext = document.getElementById('plaintext').value;
    if (!plaintext) {
        alert('Please enter some text to encrypt.');
        return;
    }

    // Show a loading state (optional but good UX)
    document.getElementById('plaintext-result').textContent = 'Simulating...';
    document.getElementById('ciphertext-result').textContent = '...';
    document.getElementById('deciphered-result').textContent = '...';
    document.getElementById('eavesdrop-result').textContent = '...';
    
    console.log("Sending request to /simulate with plaintext:", plaintext);

    // Use the Fetch API to communicate with the Flask backend
    fetch('/simulate', {
        method: 'POST',
        headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
        body: `plaintext=${encodeURIComponent(plaintext)}`
    })
    .then(response => {
        console.log("Response status:", response.status);
        if (!response.ok) {
            // If the server returns an error, show it
            return response.json().then(errorData => {
                throw new Error(errorData.error || `HTTP error! Status: ${response.status}`);
            });
        }
        return response.json();
    })
    .then(data => {
        console.log("Received data:", data);
        
        // Update the result cards with the data from the server
        document.getElementById('plaintext-result').textContent = data.plaintext;
        document.getElementById('ciphertext-result').textContent = data.ciphertext;
        document.getElementById('deciphered-result').textContent = data.deciphered;
        document.getElementById('eavesdrop-result').textContent = data.eavesdrop;

        // Update the client-side counters based on the simulation result
        if (data.deciphered !== 'Failed') {
            successCount++;
        } else {
            failCount++;
        }
        // Every simulation is an "eavesdrop attempt" in this model
        eavesdropCount++; 

        // Update the chart with the new data
        if (chart) {
            chart.data.datasets[0].data = [successCount, failCount, eavesdropCount];
            chart.update(); // Redraw the chart with the new values
        } else {
            console.error("Chart is not initialized");
        }
    })
    .catch(error => {
        console.error('Error in fetch request:', error);
        alert(`Simulation failed: ${error.message}`);
        // Reset the result cards on error
        document.getElementById('plaintext-result').textContent = '';
        document.getElementById('ciphertext-result').textContent = '';
        document.getElementById('deciphered-result').textContent = '';
        document.getElementById('eavesdrop-result').textContent = '';
    });
}