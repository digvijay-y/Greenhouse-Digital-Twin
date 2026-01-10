// Greenhouse Digital Twin - Dashboard JavaScript

// Configuration
const API_BASE_URL = 'http://localhost:8000/api';
const REFRESH_INTERVAL = 5000; // 5 seconds

// State
let autoMode = false;
let sensorData = {
    moisture1: 50, moisture2: 55, moisture3: 48, moisture4: 52,
    temperature: 25, humidity: 60, pressure: 1013,
    n: 45, p: 30, k: 60
};

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
    updateClock();
    initHeatmap();
    initHistoryChart();
    setupEventListeners();
    startDataPolling();
});

// Update clock every second
function updateClock() {
    const now = new Date();
    document.getElementById('current-time').textContent = 
        now.toLocaleString('en-IN', { 
            dateStyle: 'medium', 
            timeStyle: 'medium' 
        });
    setTimeout(updateClock, 1000);
}

// Initialize the heatmap (Digital Twin visualization)
function initHeatmap() {
    const gridSize = 10;
    const z = generateMoistureGrid(gridSize);
    
    const data = [{
        z: z,
        type: 'heatmap',
        colorscale: [
            [0, '#d73027'],    // Dry - Red
            [0.25, '#fc8d59'], // Low - Orange
            [0.5, '#fee08b'],  // Medium - Yellow
            [0.75, '#91cf60'], // Good - Light Green
            [1, '#1a9850']     // Wet - Green
        ],
        zmin: 0,
        zmax: 100,
        colorbar: {
            title: 'Moisture %',
            titleside: 'right'
        }
    }];
    
    const layout = {
        title: 'Real-Time Moisture Distribution',
        xaxis: { title: 'Greenhouse Width (m)', tickvals: [0, 5, 9], ticktext: ['0', '5', '10'] },
        yaxis: { title: 'Greenhouse Length (m)', tickvals: [0, 5, 9], ticktext: ['0', '5', '10'] },
        margin: { t: 50, b: 50, l: 60, r: 50 }
    };
    
    Plotly.newPlot('twin-heatmap', data, layout, { responsive: true });
}

// Generate moisture grid using interpolation (like Twin.m)
function generateMoistureGrid(size) {
    const grid = [];
    const m1 = sensorData.moisture1;
    const m2 = sensorData.moisture2;
    const m3 = sensorData.moisture3;
    const m4 = sensorData.moisture4;
    
    for (let i = 0; i < size; i++) {
        const row = [];
        for (let j = 0; j < size; j++) {
            // Bilinear interpolation from 4 corner sensors
            const x = j / (size - 1);
            const y = i / (size - 1);
            
            const top = m1 * (1 - x) + m2 * x;
            const bottom = m3 * (1 - x) + m4 * x;
            const value = top * (1 - y) + bottom * y;
            
            row.push(Math.round(value * 10) / 10);
        }
        grid.push(row);
    }
    return grid;
}

// Initialize history chart
function initHistoryChart() {
    const now = new Date();
    const times = [];
    const values = { m1: [], m2: [], m3: [], m4: [] };
    
    // Generate dummy historical data
    for (let i = 24; i >= 0; i--) {
        const time = new Date(now - i * 3600000);
        times.push(time.toLocaleTimeString('en-IN', { hour: '2-digit', minute: '2-digit' }));
        values.m1.push(50 + Math.random() * 20);
        values.m2.push(55 + Math.random() * 15);
        values.m3.push(48 + Math.random() * 18);
        values.m4.push(52 + Math.random() * 16);
    }
    
    const data = [
        { x: times, y: values.m1, name: 'Zone 1', type: 'scatter', mode: 'lines' },
        { x: times, y: values.m2, name: 'Zone 2', type: 'scatter', mode: 'lines' },
        { x: times, y: values.m3, name: 'Zone 3', type: 'scatter', mode: 'lines' },
        { x: times, y: values.m4, name: 'Zone 4', type: 'scatter', mode: 'lines' }
    ];
    
    const layout = {
        showlegend: true,
        legend: { orientation: 'h', y: -0.2 },
        xaxis: { title: 'Time' },
        yaxis: { title: 'Moisture %', range: [0, 100] },
        margin: { t: 20, b: 60, l: 50, r: 20 }
    };
    
    Plotly.newPlot('history-chart', data, layout, { responsive: true });
}

// Update dashboard with new sensor data
function updateDashboard(data) {
    sensorData = { ...sensorData, ...data };
    
    // Update sensor displays
    document.getElementById('temp').textContent = sensorData.temperature?.toFixed(1) || '--';
    document.getElementById('humidity').textContent = sensorData.humidity?.toFixed(1) || '--';
    document.getElementById('pressure').textContent = sensorData.pressure?.toFixed(0) || '--';
    
    document.getElementById('moisture1').textContent = sensorData.moisture1?.toFixed(1) || '--';
    document.getElementById('moisture2').textContent = sensorData.moisture2?.toFixed(1) || '--';
    document.getElementById('moisture3').textContent = sensorData.moisture3?.toFixed(1) || '--';
    document.getElementById('moisture4').textContent = sensorData.moisture4?.toFixed(1) || '--';
    
    document.getElementById('npk-n').textContent = sensorData.n || '--';
    document.getElementById('npk-p').textContent = sensorData.p || '--';
    document.getElementById('npk-k').textContent = sensorData.k || '--';
    
    // Update heatmap
    const newZ = generateMoistureGrid(10);
    Plotly.restyle('twin-heatmap', { z: [newZ] });
    
    // Update timestamp
    document.getElementById('last-update').textContent = new Date().toLocaleTimeString();
}

// Setup event listeners
function setupEventListeners() {
    // Auto mode toggle
    document.getElementById('autoMode').addEventListener('click', () => {
        autoMode = !autoMode;
        const btn = document.getElementById('autoMode');
        const modeSpan = document.getElementById('mode');
        
        if (autoMode) {
            btn.textContent = '🛑 Stop Auto';
            btn.classList.replace('btn-success', 'btn-danger');
            modeSpan.textContent = 'Auto';
            modeSpan.classList.replace('bg-primary', 'bg-success');
        } else {
            btn.textContent = '🤖 Auto Mode';
            btn.classList.replace('btn-danger', 'btn-success');
            modeSpan.textContent = 'Manual';
            modeSpan.classList.replace('bg-success', 'bg-primary');
        }
    });
    
    // Valve controls
    ['valve1', 'valve2', 'valve3'].forEach((id, index) => {
        document.getElementById(id).addEventListener('change', (e) => {
            const action = e.target.checked ? 'ON' : 'OFF';
            console.log(`Valve ${index + 1}: ${action}`);
            // TODO: Send MQTT command
            // fetch(`${API_BASE_URL}/valve/${index + 1}`, { method: 'POST', body: JSON.stringify({ action }) });
        });
    });
}

// Start polling for data updates
function startDataPolling() {
    // Simulate data updates (replace with actual API calls)
    setInterval(() => {
        // Simulate sensor readings with slight variations
        const newData = {
            moisture1: sensorData.moisture1 + (Math.random() - 0.5) * 2,
            moisture2: sensorData.moisture2 + (Math.random() - 0.5) * 2,
            moisture3: sensorData.moisture3 + (Math.random() - 0.5) * 2,
            moisture4: sensorData.moisture4 + (Math.random() - 0.5) * 2,
            temperature: 25 + (Math.random() - 0.5) * 3,
            humidity: 60 + (Math.random() - 0.5) * 10,
            n: Math.floor(40 + Math.random() * 20),
            p: Math.floor(25 + Math.random() * 15),
            k: Math.floor(55 + Math.random() * 20)
        };
        
        updateDashboard(newData);
    }, REFRESH_INTERVAL);
}

// TODO: Implement actual API calls
async function fetchSensorData() {
    try {
        const response = await fetch(`${API_BASE_URL}/sensors/latest`);
        const data = await response.json();
        updateDashboard(data);
    } catch (error) {
        console.error('Failed to fetch sensor data:', error);
        document.getElementById('mqtt-status').textContent = 'Disconnected';
        document.getElementById('mqtt-status').classList.replace('bg-success', 'bg-danger');
    }
}
