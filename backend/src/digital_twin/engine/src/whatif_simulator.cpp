/**
 * @file whatif_simulator.cpp
 * @brief Implementation of What-If simulation engine
 * 
 * Simulates soil moisture evolution based on:
 * - Evaporation (temperature-dependent exponential decay)
 * - Irrigation (periodic moisture addition)
 */

#include "whatif_simulator.hpp"
#include <algorithm>
#include <numeric>

namespace digital_twin {

// ============================================
// ZoneSimulation Implementation
// ============================================

void ZoneSimulation::compute_stats() {
    if (data.empty()) {
        initial_moisture = final_moisture = min_moisture = max_moisture = avg_moisture = 0.0;
        return;
    }
    
    initial_moisture = data.front().moisture;
    final_moisture = data.back().moisture;
    
    min_moisture = data[0].moisture;
    max_moisture = data[0].moisture;
    double sum = 0.0;
    
    for (const auto& point : data) {
        min_moisture = std::min(min_moisture, point.moisture);
        max_moisture = std::max(max_moisture, point.moisture);
        sum += point.moisture;
    }
    
    avg_moisture = sum / data.size();
}

// ============================================
// WhatIfSimulator Implementation
// ============================================

WhatIfSimulator::WhatIfSimulator(double base_decay_constant,
                                 double moisture_gain_per_100ml)
    : base_decay_constant_(base_decay_constant),
      moisture_gain_per_100ml_(moisture_gain_per_100ml) {}

double WhatIfSimulator::calculate_decay_constant(double temperature) const {
    // k(T) = k_base * (1 + 0.03 * (T - 25))
    // At 25°C: k = k_base (reference)
    // At 35°C: k = k_base * 1.30 (30% faster evaporation)
    // At 15°C: k = k_base * 0.70 (30% slower evaporation)
    return base_decay_constant_ * (1.0 + 0.03 * (temperature - 25.0));
}

double WhatIfSimulator::calculate_moisture_gain(double watering_amount_ml) const {
    // gain = (water_ml / 100) * gain_factor
    // Example: 100ml water -> 5% moisture increase (with default factor)
    return (watering_amount_ml / 100.0) * moisture_gain_per_100ml_;
}

ZoneSimulation WhatIfSimulator::simulate_zone(
    const std::string& zone_id,
    double initial_moisture,
    double ambient_temperature,
    double watering_amount_ml,
    double watering_frequency_hours,
    int duration_hours,
    double time_step_hours) {
    
    ZoneSimulation result;
    result.zone_id = zone_id;
    
    // Calculate model parameters
    double k = calculate_decay_constant(ambient_temperature);
    double moisture_gain = calculate_moisture_gain(watering_amount_ml);
    
    // Calculate number of steps
    int num_steps = static_cast<int>(duration_hours / time_step_hours);
    result.data.reserve(num_steps + 1);
    
    // Initial state
    double current_moisture = clamp_moisture(initial_moisture);
    result.data.emplace_back(0.0, current_moisture);
    
    double time_since_watering = 0.0;
    
    // Simulation loop
    for (int step = 1; step <= num_steps; ++step) {
        double t = step * time_step_hours;
        time_since_watering += time_step_hours;
        
        // 1. Apply evaporation: M(t+dt) = M(t) * exp(-k * dt)
        current_moisture *= std::exp(-k * time_step_hours);
        
        // 2. Check for watering event
        if (time_since_watering >= watering_frequency_hours) {
            current_moisture += moisture_gain;
            time_since_watering = 0.0;
        }
        
        // 3. Clamp to valid range
        current_moisture = clamp_moisture(current_moisture);
        
        // 4. Record data point
        result.data.emplace_back(t, current_moisture);
    }
    
    // Compute statistics
    result.compute_stats();
    
    return result;
}

SimulationResult WhatIfSimulator::simulate(
    const std::array<double, 4>& initial_moisture,
    double ambient_temperature,
    double watering_amount_ml,
    double watering_frequency_hours,
    int duration_hours,
    double time_step_hours) {
    
    SimulationResult result;
    
    // Store parameters
    result.ambient_temperature = ambient_temperature;
    result.watering_amount_ml = watering_amount_ml;
    result.watering_frequency_hours = watering_frequency_hours;
    result.duration_hours = duration_hours;
    result.time_step_hours = time_step_hours;
    
    // Calculate total watering events
    result.total_watering_events = static_cast<int>(duration_hours / watering_frequency_hours);
    result.total_water_used_ml = result.total_watering_events * watering_amount_ml * 4; // 4 zones
    
    // Simulate each zone
    const std::array<std::string, 4> zone_ids = {"zone1", "zone2", "zone3", "zone4"};
    
    for (size_t i = 0; i < 4; ++i) {
        result.zones[i] = simulate_zone(
            zone_ids[i],
            initial_moisture[i],
            ambient_temperature,
            watering_amount_ml,
            watering_frequency_hours,
            duration_hours,
            time_step_hours
        );
    }
    
    return result;
}

// ============================================
// Convenience Functions
// ============================================

std::array<double, 4> predict_moisture(
    const std::array<double, 4>& current_moisture,
    double temperature,
    double watering_ml,
    double watering_freq_hours,
    double predict_hours) {
    
    WhatIfSimulator sim;
    auto result = sim.simulate(
        current_moisture,
        temperature,
        watering_ml,
        watering_freq_hours,
        static_cast<int>(predict_hours),
        0.5  // 30-minute steps
    );
    
    std::array<double, 4> predictions;
    for (size_t i = 0; i < 4; ++i) {
        predictions[i] = result.zones[i].final_moisture;
    }
    
    return predictions;
}

} // namespace digital_twin
