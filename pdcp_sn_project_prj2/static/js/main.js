document.addEventListener('DOMContentLoaded', () => {
    // --- DOM Elements ---
    const runButton = document.getElementById('run-button');
    const resetButton = document.getElementById('reset-button');
    const tamperToggle = document.getElementById('tamper-toggle');
    const tamperStatus = document.getElementById('tamper-status');

    const txLogBox = document.getElementById('tx-log');
    const channelLogBox = document.getElementById('channel-log');
    const rxLogBox = document.getElementById('rx-log');

    const txColumn = document.getElementById('tx-column');
    const channelColumn = document.getElementById('channel-column');
    const rxColumn = document.getElementById('rx-column');
    
    const arrow1 = document.getElementById('arrow1');
    const arrow2 = document.getElementById('arrow2');

    const resultsArea = document.getElementById('results-area');
    const resultKey = document.getElementById('result-key');
    const resultBearer = document.getElementById('result-bearer');
    const resultSent = document.getElementById('result-sent');
    const resultDelivered = document.getElementById('result-delivered');
    const resultDiscarded = document.getElementById('result-discarded');
    const resultStatus = document.getElementById('result-status');

    // --- Initial State ---
    const initialPlaceholders = {
        tx: txLogBox.innerHTML,
        channel: channelLogBox.innerHTML,
        rx: rxLogBox.innerHTML
    };

    // --- Event Listeners ---
    tamperToggle.addEventListener('change', () => {
        if (tamperToggle.checked) {
            tamperStatus.textContent = 'ON';
            tamperStatus.className = 'status-text-on';
        } else {
            tamperStatus.textContent = 'OFF';
            tamperStatus.className = 'status-text-off';
        }
    });

    runButton.addEventListener('click', runSimulation);
    resetButton.addEventListener('click', resetSimulation);

    // --- Functions ---
    function resetSimulation() {
        runButton.disabled = false;
        runButton.innerHTML = '<i class="fa-solid fa-play"></i> Run Simulation';

        txLogBox.innerHTML = initialPlaceholders.tx;
        channelLogBox.innerHTML = initialPlaceholders.channel;
        rxLogBox.innerHTML = initialPlaceholders.rx;
        
        [txColumn, channelColumn, rxColumn].forEach(col => col.classList.remove('active'));
        [arrow1, arrow2].forEach(arrow => arrow.classList.remove('visible'));

        resultsArea.classList.add('hidden');
    }

    async function runSimulation() {
        resetSimulation();
        runButton.disabled = true;
        runButton.innerHTML = '<i class="fa-solid fa-spinner fa-spin"></i> Processing...';
        
        try {
            const response = await fetch('/run_simulation', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    tamper: tamperToggle.checked
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP error! status: ${response.status}`);
            }

            const data = await response.json();
            await animateLog(data.log);
            displayResults(data.results);

        } catch (error) {
            console.error("Simulation failed:", error);
            channelLogBox.innerHTML = `<div class="log-entry log-fail"><strong>Error:</strong> Failed to run simulation. Check console.</div>`;
        } finally {
            runButton.innerHTML = '<i class="fa-solid fa-play"></i> Run Simulation';
            runButton.disabled = false;
        }
    }

    const sleep = (ms) => new Promise(resolve => setTimeout(resolve, ms));

    async function animateLog(log) {
        txLogBox.innerHTML = '';
        channelLogBox.innerHTML = '';
        rxLogBox.innerHTML = '';

        for (const entry of log) {
            let logHtml = '';
            
            switch (entry.event) {
                case 'tx_protect':
                    txColumn.classList.add('active');
                    logHtml = `
                        <div class="log-entry log-info">
                            <strong>Packet #${entry.sdu_id} Sent</strong><br>
                            COUNT: <span class="mono">${entry.count}</span><br>
                            MAC-I: <span class="mono mac">${entry.mac_i}</span>
                        </div>`;
                    txLogBox.innerHTML += logHtml;
                    await sleep(500);
                    txColumn.classList.remove('active');
                    arrow1.classList.add('visible');
                    break;
                
                case 'channel_ok':
                    channelColumn.classList.add('active');
                    logHtml = `
                        <div class="log-entry log-neutral">
                            <strong>Packet #${entry.sdu_id}</strong><br>
                            Transmission OK
                        </div>`;
                    channelLogBox.innerHTML += logHtml;
                    await sleep(500);
                    channelColumn.classList.remove('active');
                    arrow1.classList.remove('visible');
                    arrow2.classList.add('visible');
                    break;
                
                case 'channel_tamper':
                    channelColumn.classList.add('active');
                    logHtml = `
                        <div class="log-entry log-tamper">
                            <strong><i class="fa-solid fa-skull-crossbones"></i> PACKET #${entry.sdu_id} TAMPERED!</strong><br>
                            ${entry.detail}
                        </div>`;
                    channelLogBox.innerHTML += logHtml;
                    await sleep(1000); // Longer pause for effect
                    channelColumn.classList.remove('active');
                    arrow1.classList.remove('visible');
                    arrow2.classList.add('visible');
                    break;

                case 'rx_verify_pass':
                    rxColumn.classList.add('active');
                    logHtml = `
                        <div class="log-entry log-pass">
                            <strong><i class="fa-solid fa-check-circle"></i> Packet #${entry.sdu_id} VERIFIED</strong><br>
                            Rcvd MAC: <span class="mono mac">${entry.received_mac}</span><br>
                            Calc X-MAC: <span class="mono mac">${entry.calculated_x_mac}</span><br>
                            <strong>Status: ${entry.status}</strong>
                        </div>`;
                    rxLogBox.innerHTML += logHtml;
                    await sleep(500);
                    rxColumn.classList.remove('active');
                    arrow2.classList.remove('visible');
                    break;

                case 'rx_verify_fail':
                    rxColumn.classList.add('active');
                    logHtml = `
                        <div class="log-entry log-fail">
                            <strong><i class="fa-solid fa-times-circle"></i> Packet #${entry.sdu_id} FAILED</strong><br>
                            Rcvd MAC: <span class="mono mac">${entry.received_mac}</span><br>
                            Calc X-MAC: <span class="mono mac">${entry.calculated_x_mac}</span><br>
                            <strong>Status: ${entry.status} & DISCARDED</strong>
                        </div>`;
                    rxLogBox.innerHTML += logHtml;
                    await sleep(1000); // Longer pause
                    rxColumn.classList.remove('active');
                    arrow2.classList.remove('visible');
                    break;
            }
            // Scroll to the new log entry
            txLogBox.scrollTop = txLogBox.scrollHeight;
            channelLogBox.scrollTop = channelLogBox.scrollHeight;
            rxLogBox.scrollTop = rxLogBox.scrollHeight;
            
            await sleep(500);
        }
    }
    
    function displayResults(results) {
        resultKey.textContent = results.integrity_key;
        resultBearer.textContent = results.bearer_id;
        resultSent.textContent = results.packets_sent;
        resultDelivered.textContent = results.packets_delivered;
        resultDiscarded.textContent = results.packets_discarded;
        
        if (results.packets_discarded > 0) {
            resultStatus.textContent = 'Attack Detected & Mitigated';
            resultStatus.style.color = 'var(--accent-red)';
        } else {
            resultStatus.textContent = 'All Packets Securely Delivered';
            resultStatus.style.color = 'var(--accent-green)';
        }

        resultsArea.classList.remove('hidden');
    }
});