#ifndef DIGITAL_TWIN_ENGINE_HPP
#define DIGITAL_TWIN_ENGINE_HPP

/**
 * @file digital_twin_engine.hpp
 * @brief Main header that includes all Digital Twin Engine components
 * 
 * Greenhouse Digital Twin Engine
 * ==============================
 * 
 * A high-performance C++ engine for greenhouse environment simulation.
 * 
 * Components:
 * -----------
 * 1. LaplaceSolver - 2D moisture distribution using Laplace equation
 * 2. WhatIfSimulator - Future moisture prediction with evaporation/irrigation models
 * 
 * Usage Example (C++):
 * -------------------
 * ```cpp
 * #include "digital_twin_engine.hpp"
 * 
 * using namespace digital_twin;
 * 
 * // Compute moisture distribution
 * auto grid = compute_moisture_distribution(80, 60, 45, 55, 100);
 * 
 * // Run what-if simulation
 * WhatIfSimulator sim;
 * auto result = sim.simulate(
 *     {80.0, 60.0, 45.0, 55.0},  // Current moisture
 *     28.0,                       // Temperature °C
 *     150.0,                      // Water amount ml
 *     12.0,                       // Watering every 12 hours
 *     72,                         // Simulate 72 hours
 *     0.5                         // 30-minute time steps
 * );
 * ```
 * 
 * Usage Example (Python with bindings):
 * ------------------------------------
 * ```python
 * import twin_engine_py as te
 * 
 * # Compute moisture distribution
 * grid = te.compute_moisture_distribution(80, 60, 45, 55, 100)
 * 
 * # Run what-if simulation
 * sim = te.WhatIfSimulator()
 * result = sim.simulate([80, 60, 45, 55], 28.0, 150.0, 12.0, 72, 0.5)
 * ```
 * 
 * @author Greenhouse Digital Twin Project
 * @version 1.0.0
 */

#include "laplace_solver.hpp"
#include "whatif_simulator.hpp"

namespace digital_twin {

/**
 * @brief Engine version information
 */
struct EngineVersion {
    static constexpr int MAJOR = 1;
    static constexpr int MINOR = 0;
    static constexpr int PATCH = 0;
    
    static std::string as_string() {
        return std::to_string(MAJOR) + "." + 
               std::to_string(MINOR) + "." + 
               std::to_string(PATCH);
    }
};

/**
 * @brief Get engine version string
 */
inline std::string get_version() {
    return EngineVersion::as_string();
}

/**
 * @brief Print engine info to stdout
 */
inline void print_info() {
    std::printf("Digital Twin Engine v%s\n", get_version().c_str());
    std::printf("Components:\n");
    std::printf("  - LaplaceSolver: 2D moisture distribution\n");
    std::printf("  - WhatIfSimulator: Future prediction engine\n");
}

} // namespace digital_twin

#endif // DIGITAL_TWIN_ENGINE_HPP
