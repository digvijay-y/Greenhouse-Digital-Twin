#ifndef WHATIF_SIMULATOR_HPP
#define WHATIF_SIMULATOR_HPP

#include <vector>
#include <array>
#include <string>
#include <cmath>
#include <chrono>

namespace digital_twin {

/**
 * @brief Single time point in simulation
 */
struct SimulationPoint {
    double time_hours;      // Hours from start
    double moisture;        // Moisture percentage (0-100)
    
    SimulationPoint(double t = 0.0, double m = 50.0) 
        : time_hours(t), moisture(m) {}
};

/**
 * @brief Simulation results for one zone
 */
struct ZoneSimulation {
    std::string zone_id;
    std::vector<SimulationPoint> data;
    
    // Statistics
    double initial_moisture;
    double final_moisture;
    double min_moisture;
    double max_moisture;
    double avg_moisture;
    
    void compute_stats();
};

/**
 * @brief Complete simulation results for all zones
 */
struct SimulationResult {
    std::array<ZoneSimulation, 4> zones;
    
    // Simulation parameters (for reference)
    double ambient_temperature;
    double watering_amount_ml;
    double watering_frequency_hours;
    int duration_hours;
    double time_step_hours;
    
    // Metadata
    int total_watering_events;
    double total_water_used_ml;
};

/**
 * @brief What-If Simulation Engine
 * 
 * Simulates soil moisture evolution based on:
 * 1. Evaporation - exponential decay dependent on temperature
 * 2. Irrigation - instant moisture increase at regular intervals
 * 
 * Model equations:
 * - Evaporation: M(t+dt) = M(t) * exp(-k * dt)
 *   where k = k_base * (1 + 0.03 * (T - 25))
 * - Irrigation: M += gain, where gain = (water_ml / 100) * 5
 */
class WhatIfSimulator {
public:
    /**
     * @brief Construct simulator with default parameters
     * 
     * @param base_decay_constant k value at 25°C (default: 0.02 per hour)
     * @param moisture_gain_per_100ml Moisture % increase per 100ml water
     */
    WhatIfSimulator(double base_decay_constant = 0.02,
                    double moisture_gain_per_100ml = 5.0);
    
    /**
     * @brief Run simulation for all 4 zones
     * 
     * @param initial_moisture Array of 4 current moisture values [zone1, zone2, zone3, zone4]
     * @param ambient_temperature Temperature in °C
     * @param watering_amount_ml Water volume per irrigation event
     * @param watering_frequency_hours Hours between watering
     * @param duration_hours Total simulation duration (default: 72)
     * @param time_step_hours Simulation resolution (default: 0.5)
     * @return SimulationResult Complete results for all zones
     */
    SimulationResult simulate(
        const std::array<double, 4>& initial_moisture,
        double ambient_temperature,
        double watering_amount_ml,
        double watering_frequency_hours,
        int duration_hours = 72,
        double time_step_hours = 0.5
    );
    
    /**
     * @brief Simulate single zone
     */
    ZoneSimulation simulate_zone(
        const std::string& zone_id,
        double initial_moisture,
        double ambient_temperature,
        double watering_amount_ml,
        double watering_frequency_hours,
        int duration_hours,
        double time_step_hours
    );
    
    /**
     * @brief Calculate temperature-adjusted decay constant
     * 
     * k(T) = k_base * (1 + 0.03 * (T - 25))
     * At 25°C: k = k_base
     * At 35°C: k = k_base * 1.30 (30% faster evaporation)
     * At 15°C: k = k_base * 0.70 (30% slower evaporation)
     */
    double calculate_decay_constant(double temperature) const;
    
    /**
     * @brief Convert watering amount to moisture gain
     * 
     * gain = (water_ml / 100) * gain_factor
     */
    double calculate_moisture_gain(double watering_amount_ml) const;
    
    // Setters for model parameters
    void set_base_decay_constant(double k) { base_decay_constant_ = k; }
    void set_moisture_gain_factor(double g) { moisture_gain_per_100ml_ = g; }
    
    // Getters
    double get_base_decay_constant() const { return base_decay_constant_; }
    double get_moisture_gain_factor() const { return moisture_gain_per_100ml_; }
    
private:
    double base_decay_constant_;
    double moisture_gain_per_100ml_;
    
    // Clamp moisture to valid range
    static double clamp_moisture(double m) {
        return std::max(0.0, std::min(100.0, m));
    }
};

/**
 * @brief Convenience function for simple predictions
 * 
 * Returns predicted moisture values after specified hours
 */
std::array<double, 4> predict_moisture(
    const std::array<double, 4>& current_moisture,
    double temperature,
    double watering_ml,
    double watering_freq_hours,
    double predict_hours
);

} // namespace digital_twin

#endif // WHATIF_SIMULATOR_HPP
