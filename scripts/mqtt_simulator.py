#!/usr/bin/env python3
"""
MQTT Data Simulator for Greenhouse Digital Twin

Simulates realistic sensor data for testing:
- 4 soil moisture sensors (pico1/moisture1, pico1/moisture2, pico2/moisture1, pico2/moisture2)
- BME280 environmental sensor (pico1/bme280)
- NPK sensor (esp32/npk)

Usage:
    python mqtt_simulator.py [--broker HOST] [--port PORT] [--interval SECONDS]
    
Example:
    python mqtt_simulator.py --interval 2
"""

import paho.mqtt.client as mqtt
import time
import random
import math
import argparse
from datetime import datetime


class GreenhouseSimulator:
    """Simulates realistic greenhouse sensor data with temporal patterns."""
    
    def __init__(self, broker: str = "127.0.0.1", port: int = 1883):
        self.broker = broker
        self.port = port
        self.client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
        
        # Base values for sensors
        self.moisture_base = [55.0, 50.0, 48.0, 52.0]  # 4 zones
        self.temp_base = 25.0
        self.humidity_base = 65.0
        self.pressure_base = 1013.25
        
        # NPK base values (mg/kg)
        self.npk_base = {'n': 45, 'p': 35, 'k': 40}
        
        # Time tracking for daily patterns
        self.start_time = time.time()
        
        # Irrigation events (simulate watering)
        self.last_irrigation = [0, 0, 0, 0]  # Time since last irrigation per zone
        
    def connect(self):
        """Connect to MQTT broker."""
        try:
            self.client.connect(self.broker, self.port)
            self.client.loop_start()
            print(f"✅ Connected to MQTT broker at {self.broker}:{self.port}")
            return True
        except Exception as e:
            print(f"❌ Failed to connect: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from MQTT broker."""
        self.client.loop_stop()
        self.client.disconnect()
        print("Disconnected from MQTT broker")
    
    def get_time_of_day_factor(self) -> float:
        """Get a factor based on simulated time of day (0-24h cycle in 2 minutes)."""
        elapsed = time.time() - self.start_time
        # Complete day cycle every 120 seconds for faster simulation
        hour = (elapsed % 120) / 5  # 0-24 range
        # Peak temperature at noon (hour=12), minimum at midnight (hour=0)
        return math.sin((hour - 6) * math.pi / 12)  # -1 to 1
    
    def simulate_moisture(self, zone: int) -> float:
        """
        Simulate soil moisture with:
        - Base level per zone
        - Random walk
        - Evaporation during day
        - Occasional irrigation spikes
        """
        base = self.moisture_base[zone]
        
        # Time-based evaporation (more during day)
        tod_factor = self.get_time_of_day_factor()
        evaporation = max(0, tod_factor * 0.3)  # 0-0.3% loss during peak day
        
        # Random walk
        random_change = random.gauss(0, 0.5)
        
        # Occasional irrigation (5% chance each reading)
        irrigation = 0
        if random.random() < 0.05:
            irrigation = random.uniform(5, 15)
            print(f"  💧 Zone {zone+1}: Irrigation event (+{irrigation:.1f}%)")
        
        # Update base
        self.moisture_base[zone] = max(20, min(95, 
            base - evaporation + random_change + irrigation
        ))
        
        return round(self.moisture_base[zone], 1)
    
    def simulate_bme280(self) -> tuple:
        """
        Simulate BME280 environmental data:
        - Temperature: 15-35°C with daily cycle
        - Humidity: 40-90% (inversely related to temp)
        - Pressure: 1000-1025 hPa with slow drift
        """
        tod_factor = self.get_time_of_day_factor()
        
        # Temperature: base ± 8°C based on time of day
        temp = self.temp_base + tod_factor * 8 + random.gauss(0, 0.5)
        temp = max(15, min(38, temp))
        
        # Humidity: inversely related to temperature
        humidity = self.humidity_base - tod_factor * 15 + random.gauss(0, 2)
        humidity = max(35, min(95, humidity))
        
        # Pressure: slow random walk
        self.pressure_base += random.gauss(0, 0.1)
        self.pressure_base = max(1000, min(1030, self.pressure_base))
        pressure = round(self.pressure_base, 1)
        
        return round(temp, 1), round(humidity, 1), pressure
    
    def simulate_npk(self) -> dict:
        """
        Simulate NPK sensor with:
        - Slow drift
        - Occasional spikes (fertilizer application)
        """
        npk = {}
        for key in ['n', 'p', 'k']:
            base = self.npk_base[key]
            # Random walk
            self.npk_base[key] += random.gauss(0, 0.5)
            self.npk_base[key] = max(10, min(100, self.npk_base[key]))
            npk[key] = int(self.npk_base[key])
        
        return npk
    
    def publish_all(self):
        """Publish all sensor data to MQTT topics."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        
        # Moisture sensors
        topics_data = []
        for i in range(4):
            moisture = self.simulate_moisture(i)
            if i < 2:
                topic = f"pico1/moisture{i+1}"
            else:
                topic = f"pico2/moisture{i-1}"
            self.client.publish(topic, str(moisture))
            topics_data.append(f"M{i+1}={moisture}%")
        
        # BME280
        temp, humidity, pressure = self.simulate_bme280()
        bme_payload = f"{temp},{humidity},{pressure}"
        self.client.publish("pico1/bme280", bme_payload)
        
        # NPK
        npk = self.simulate_npk()
        import json
        self.client.publish("esp32/npk", json.dumps(npk))
        
        print(f"[{timestamp}] {' | '.join(topics_data)} | T={temp}°C H={humidity}% | NPK: N={npk['n']} P={npk['p']} K={npk['k']}")
    
    def run(self, interval: float = 3.0, duration: float = None):
        """
        Run the simulator.
        
        Args:
            interval: Seconds between readings
            duration: Total duration in seconds (None = indefinite)
        """
        if not self.connect():
            return
        
        print(f"\n🌱 Greenhouse Sensor Simulator Started")
        print(f"   Interval: {interval}s | Duration: {duration or 'indefinite'}s")
        print(f"   Topics: pico1/moisture1-2, pico2/moisture1-2, pico1/bme280, esp32/npk")
        print("-" * 70)
        
        start = time.time()
        try:
            while True:
                self.publish_all()
                time.sleep(interval)
                
                if duration and (time.time() - start) >= duration:
                    print(f"\n⏱️ Duration reached ({duration}s)")
                    break
                    
        except KeyboardInterrupt:
            print("\n\n⛔ Stopped by user")
        finally:
            self.disconnect()


def main():
    parser = argparse.ArgumentParser(
        description="Simulate MQTT sensor data for Greenhouse Digital Twin"
    )
    parser.add_argument("--broker", default="127.0.0.1", help="MQTT broker address")
    parser.add_argument("--port", type=int, default=1883, help="MQTT broker port")
    parser.add_argument("--interval", type=float, default=3.0, help="Seconds between readings")
    parser.add_argument("--duration", type=float, default=None, help="Total duration (default: indefinite)")
    
    args = parser.parse_args()
    
    simulator = GreenhouseSimulator(broker=args.broker, port=args.port)
    simulator.run(interval=args.interval, duration=args.duration)


if __name__ == "__main__":
    main()
