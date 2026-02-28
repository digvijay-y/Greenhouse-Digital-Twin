/**
 * @file test_engine.cpp
 * @brief Test suite for Digital Twin Engine
 * 
 * Validates:
 * 1. Laplace solver produces expected moisture distribution
 * 2. What-If simulator behaves correctly
 * 3. Edge cases are handled properly
 */

#include <iostream>
#include <iomanip>
#include <cassert>
#include <cmath>
#include "digital_twin_engine.hpp"

using namespace digital_twin;

// Test helpers
#define TEST(name) void name(); \
    struct name##_registrar { name##_registrar() { std::cout << "Running: " #name << std::endl; name(); std::cout << "  PASSED" << std::endl; } } name##_instance; \
    void name()

#define ASSERT_NEAR(a, b, tol) \
    if (std::abs((a) - (b)) > (tol)) { \
        std::cerr << "FAILED: " << #a << " = " << (a) << " not near " << #b << " = " << (b) << std::endl; \
        std::exit(1); \
    }

#define ASSERT_TRUE(cond) \
    if (!(cond)) { \
        std::cerr << "FAILED: " << #cond << std::endl; \
        std::exit(1); \
    }

// ============================================
// Grid2D Tests
// ============================================
TEST(test_grid_creation) {
    Grid2D grid(10, 10, 50.0);
    ASSERT_TRUE(grid.rows() == 10);
    ASSERT_TRUE(grid.cols() == 10);
    ASSERT_NEAR(grid(5, 5), 50.0, 0.001);
}

TEST(test_grid_access) {
    Grid2D grid(10, 10, 0.0);
    grid(3, 4) = 75.5;
    ASSERT_NEAR(grid(3, 4), 75.5, 0.001);
}

TEST(test_grid_to_2d_vector) {
    Grid2D grid(5, 5, 25.0);
    auto vec = grid.to_2d_vector();
    ASSERT_TRUE(vec.size() == 5);
    ASSERT_TRUE(vec[0].size() == 5);
    ASSERT_NEAR(vec[2][2], 25.0, 0.001);
}

// ============================================
// LaplaceSolver Tests
// ============================================
TEST(test_laplace_uniform_bc) {
    // With uniform boundary conditions, interior should be uniform
    BoundaryConditions bc(50.0, 50.0, 50.0, 50.0);
    LaplaceSolver solver(20, 20);
    Grid2D result = solver.solve(bc);
    
    // Center should be 50
    ASSERT_NEAR(result(10, 10), 50.0, 0.1);
}

TEST(test_laplace_gradient) {
    // Linear gradient from left (0) to right (100)
    // Top: 0 to 100, Bottom: 0 to 100
    BoundaryConditions bc(0.0, 100.0, 0.0, 100.0);
    LaplaceSolver solver(50, 50);
    Grid2D result = solver.solve(bc);
    
    // Middle of grid should be ~50 (allow some tolerance for Laplace solution)
    ASSERT_NEAR(result(25, 25), 50.0, 5.0);
    
    // Left side should be low
    ASSERT_TRUE(result(25, 5) < 25.0);
    
    // Right side should be high
    ASSERT_TRUE(result(25, 45) > 75.0);
}

TEST(test_laplace_corners) {
    BoundaryConditions bc(80.0, 60.0, 45.0, 55.0);
    LaplaceSolver solver(100, 100);
    Grid2D result = solver.solve(bc);
    
    // Corners should match boundary conditions
    ASSERT_NEAR(result(0, 0), 80.0, 0.1);
    ASSERT_NEAR(result(0, 99), 60.0, 0.1);
    ASSERT_NEAR(result(99, 0), 45.0, 0.1);
    ASSERT_NEAR(result(99, 99), 55.0, 0.1);
}

TEST(test_laplace_convergence) {
    BoundaryConditions bc(80.0, 20.0, 30.0, 70.0);
    LaplaceSolver solver(100, 100, 1e-5, 5000);
    solver.solve(bc);
    
    std::cout << "    Iterations: " << solver.get_last_iterations() 
              << ", Residual: " << solver.get_last_residual() << std::endl;
    
    ASSERT_TRUE(solver.get_last_residual() < 1e-4);
}

// ============================================
// WhatIfSimulator Tests
// ============================================
TEST(test_whatif_decay_constant) {
    WhatIfSimulator sim(0.02);  // k_base = 0.02
    
    // At 25°C, k should equal base
    ASSERT_NEAR(sim.calculate_decay_constant(25.0), 0.02, 0.001);
    
    // At 35°C, k should be 30% higher
    ASSERT_NEAR(sim.calculate_decay_constant(35.0), 0.026, 0.001);
    
    // At 15°C, k should be 30% lower
    ASSERT_NEAR(sim.calculate_decay_constant(15.0), 0.014, 0.001);
}

TEST(test_whatif_moisture_gain) {
    WhatIfSimulator sim(0.02, 5.0);  // 5% per 100ml
    
    ASSERT_NEAR(sim.calculate_moisture_gain(100.0), 5.0, 0.001);
    ASSERT_NEAR(sim.calculate_moisture_gain(200.0), 10.0, 0.001);
    ASSERT_NEAR(sim.calculate_moisture_gain(50.0), 2.5, 0.001);
}

TEST(test_whatif_no_watering) {
    // Without watering, moisture should only decay
    WhatIfSimulator sim;
    auto result = sim.simulate(
        {80.0, 80.0, 80.0, 80.0},  // Start at 80%
        25.0,                       // 25°C
        100.0,                      // 100ml (irrelevant)
        1000.0,                     // Never water (freq > duration)
        24,                         // 24 hours
        0.5
    );
    
    // After 24 hours of evaporation at k=0.02, expect ~61%
    // M = 80 * exp(-0.02 * 24) = 80 * 0.619 = 49.5
    double expected = 80.0 * std::exp(-0.02 * 24.0);
    ASSERT_NEAR(result.zones[0].final_moisture, expected, 1.0);
}

TEST(test_whatif_regular_watering) {
    WhatIfSimulator sim;
    auto result = sim.simulate(
        {50.0, 50.0, 50.0, 50.0},
        25.0,
        100.0,      // 100ml -> 5% gain
        12.0,       // Water every 12 hours
        48,         // 48 hours
        0.5
    );
    
    // Should have 4 watering events (48/12 = 4)
    ASSERT_TRUE(result.total_watering_events == 4);
    
    // Final moisture should be positive
    ASSERT_TRUE(result.zones[0].final_moisture > 0);
    ASSERT_TRUE(result.zones[0].final_moisture <= 100);
}

TEST(test_whatif_statistics) {
    WhatIfSimulator sim;
    auto result = sim.simulate(
        {70.0, 60.0, 50.0, 40.0},
        28.0,
        150.0,
        8.0,
        72,
        0.5
    );
    
    // Check statistics are computed
    for (const auto& zone : result.zones) {
        ASSERT_TRUE(zone.min_moisture >= 0);
        ASSERT_TRUE(zone.max_moisture <= 100);
        ASSERT_TRUE(zone.avg_moisture > 0);
        ASSERT_TRUE(zone.data.size() > 0);
    }
}

// ============================================
// Convenience Function Tests
// ============================================
TEST(test_compute_moisture_distribution) {
    auto grid = compute_moisture_distribution(80.0, 60.0, 45.0, 55.0, 50);
    
    ASSERT_TRUE(grid.size() == 50);
    ASSERT_TRUE(grid[0].size() == 50);
    
    // Check corners
    ASSERT_NEAR(grid[0][0], 80.0, 0.1);
    ASSERT_NEAR(grid[0][49], 60.0, 0.1);
}

TEST(test_predict_moisture) {
    auto predictions = predict_moisture(
        {80.0, 60.0, 45.0, 55.0},
        25.0,
        100.0,
        12.0,
        24.0
    );
    
    ASSERT_TRUE(predictions.size() == 4);
    
    // All predictions should be valid percentages
    for (double p : predictions) {
        ASSERT_TRUE(p >= 0 && p <= 100);
    }
}

// ============================================
// Main
// ============================================
int main() {
    std::cout << "\n======================================" << std::endl;
    std::cout << "Digital Twin Engine Test Suite" << std::endl;
    std::cout << "Version: " << get_version() << std::endl;
    std::cout << "======================================\n" << std::endl;
    
    // Tests run automatically via static initialization
    
    std::cout << "\n======================================" << std::endl;
    std::cout << "All tests passed!" << std::endl;
    std::cout << "======================================\n" << std::endl;
    
    return 0;
}
