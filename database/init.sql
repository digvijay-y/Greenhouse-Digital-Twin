-- Greenhouse Digital Twin Database Schema

-- Sensor data table (real-time readings)
CREATE TABLE IF NOT EXISTS sensor_data (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    temperature REAL,
    humidity REAL,
    pressure REAL,
    moisture1 REAL,
    moisture2 REAL,
    moisture3 REAL,
    moisture4 REAL,
    n_value INTEGER,
    p_value INTEGER,
    k_value INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Irrigation events log
CREATE TABLE IF NOT EXISTS irrigation_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    zone INTEGER NOT NULL,
    valve_id INTEGER NOT NULL,
    action TEXT NOT NULL,  -- 'ON' or 'OFF'
    duration_seconds INTEGER,
    trigger_source TEXT,   -- 'auto', 'manual', 'schedule'
    moisture_before REAL,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Crop configuration
CREATE TABLE IF NOT EXISTS crops (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    stage TEXT NOT NULL,   -- 'Initial', 'Medium', 'Final'
    min_moisture REAL,
    max_moisture REAL,
    min_n INTEGER,
    min_p INTEGER,
    min_k INTEGER,
    days_in_stage INTEGER,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Alerts and anomalies
CREATE TABLE IF NOT EXISTS alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp TEXT NOT NULL,
    alert_type TEXT NOT NULL,  -- 'low_moisture', 'sensor_fault', 'connection_lost'
    severity TEXT NOT NULL,    -- 'info', 'warning', 'critical'
    message TEXT,
    resolved BOOLEAN DEFAULT FALSE,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes for faster queries
CREATE INDEX IF NOT EXISTS idx_sensor_timestamp ON sensor_data(timestamp);
CREATE INDEX IF NOT EXISTS idx_irrigation_timestamp ON irrigation_events(timestamp);
CREATE INDEX IF NOT EXISTS idx_alerts_resolved ON alerts(resolved);
