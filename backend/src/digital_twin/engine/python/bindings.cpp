/**
 * @file bindings.cpp
 * @brief Python bindings for Digital Twin Engine using pybind11
 * 
 * Creates a Python module 'twin_engine_py' with:
 * - Grid2D class
 * - LaplaceSolver class
 * - WhatIfSimulator class
 * - Convenience functions
 */

#include <pybind11/pybind11.h>
#include <pybind11/stl.h>
#include <pybind11/numpy.h>

#include "digital_twin_engine.hpp"

namespace py = pybind11;
using namespace digital_twin;

// Helper to convert Grid2D to numpy array
py::array_t<double> grid_to_numpy(const Grid2D& grid) {
    auto result = py::array_t<double>({grid.rows(), grid.cols()});
    auto buf = result.mutable_unchecked<2>();
    
    for (size_t i = 0; i < grid.rows(); ++i) {
        for (size_t j = 0; j < grid.cols(); ++j) {
            buf(i, j) = grid(i, j);
        }
    }
    
    return result;
}

// Helper to convert simulation data to dict
py::dict simulation_point_to_dict(const SimulationPoint& p) {
    py::dict d;
    d["time_hours"] = p.time_hours;
    d["moisture"] = p.moisture;
    return d;
}

py::dict zone_simulation_to_dict(const ZoneSimulation& z) {
    py::dict d;
    d["zone_id"] = z.zone_id;
    d["initial_moisture"] = z.initial_moisture;
    d["final_moisture"] = z.final_moisture;
    d["min_moisture"] = z.min_moisture;
    d["max_moisture"] = z.max_moisture;
    d["avg_moisture"] = z.avg_moisture;
    
    // Convert data points
    py::list data_list;
    for (const auto& point : z.data) {
        data_list.append(simulation_point_to_dict(point));
    }
    d["data"] = data_list;
    
    // Also provide separate lists for easy plotting
    py::list times, moistures;
    for (const auto& point : z.data) {
        times.append(point.time_hours);
        moistures.append(point.moisture);
    }
    d["times"] = times;
    d["moistures"] = moistures;
    
    return d;
}

py::dict simulation_result_to_dict(const SimulationResult& r) {
    py::dict d;
    
    // Parameters
    d["ambient_temperature"] = r.ambient_temperature;
    d["watering_amount_ml"] = r.watering_amount_ml;
    d["watering_frequency_hours"] = r.watering_frequency_hours;
    d["duration_hours"] = r.duration_hours;
    d["time_step_hours"] = r.time_step_hours;
    d["total_watering_events"] = r.total_watering_events;
    d["total_water_used_ml"] = r.total_water_used_ml;
    
    // Zones
    py::dict zones;
    for (size_t i = 0; i < 4; ++i) {
        zones[r.zones[i].zone_id.c_str()] = zone_simulation_to_dict(r.zones[i]);
    }
    d["zones"] = zones;
    
    return d;
}

PYBIND11_MODULE(twin_engine_py, m) {
    m.doc() = R"pbdoc(
        Digital Twin Engine - Python Bindings
        =====================================
        
        High-performance C++ engine for greenhouse environment simulation.
        
        Modules:
        --------
        - LaplaceSolver: 2D moisture distribution using Laplace equation
        - WhatIfSimulator: Future moisture prediction
        
        Quick Start:
        -----------
        >>> import twin_engine_py as te
        >>> 
        >>> # Compute moisture distribution
        >>> grid = te.compute_moisture_distribution(80, 60, 45, 55)
        >>> 
        >>> # Run what-if simulation
        >>> sim = te.WhatIfSimulator()
        >>> result = sim.simulate([80, 60, 45, 55], 28.0, 150.0, 12.0)
    )pbdoc";

    // Version info
    m.def("get_version", &get_version, "Get engine version string");
    m.def("print_info", &print_info, "Print engine information");

    // ========================================
    // BoundaryConditions
    // ========================================
    py::class_<BoundaryConditions>(m, "BoundaryConditions",
        "Boundary conditions from 4 corner sensors")
        .def(py::init<double, double, double, double>(),
             py::arg("top_left") = 50.0,
             py::arg("top_right") = 50.0,
             py::arg("bottom_left") = 50.0,
             py::arg("bottom_right") = 50.0)
        .def_readwrite("top_left", &BoundaryConditions::top_left)
        .def_readwrite("top_right", &BoundaryConditions::top_right)
        .def_readwrite("bottom_left", &BoundaryConditions::bottom_left)
        .def_readwrite("bottom_right", &BoundaryConditions::bottom_right)
        .def("__repr__", [](const BoundaryConditions& bc) {
            return "BoundaryConditions(tl=" + std::to_string(bc.top_left) +
                   ", tr=" + std::to_string(bc.top_right) +
                   ", bl=" + std::to_string(bc.bottom_left) +
                   ", br=" + std::to_string(bc.bottom_right) + ")";
        });

    // ========================================
    // Grid2D
    // ========================================
    py::class_<Grid2D>(m, "Grid2D", "2D grid for moisture distribution")
        .def(py::init<size_t, size_t, double>(),
             py::arg("rows"), py::arg("cols"), py::arg("initial_value") = 50.0)
        .def("rows", &Grid2D::rows)
        .def("cols", &Grid2D::cols)
        .def("size", &Grid2D::size)
        .def("get", [](const Grid2D& g, size_t i, size_t j) { return g(i, j); },
             py::arg("row"), py::arg("col"), "Get value at (row, col)")
        .def("set", [](Grid2D& g, size_t i, size_t j, double v) { g(i, j) = v; },
             py::arg("row"), py::arg("col"), py::arg("value"), "Set value at (row, col)")
        .def("to_list", &Grid2D::to_2d_vector, "Convert to 2D Python list")
        .def("flatten", &Grid2D::flatten, "Get as flattened 1D list")
        .def("to_numpy", [](const Grid2D& g) { return grid_to_numpy(g); },
             "Convert to NumPy array")
        .def("__repr__", [](const Grid2D& g) {
            return "Grid2D(" + std::to_string(g.rows()) + "x" + 
                   std::to_string(g.cols()) + ")";
        });

    // ========================================
    // LaplaceSolver
    // ========================================
    py::class_<LaplaceSolver>(m, "LaplaceSolver",
        R"pbdoc(
        Laplace Equation Solver for moisture distribution.
        
        Solves: ∇²u = 0 with 4-point boundary conditions.
        Uses Jacobi iterative method.
        
        Example:
        --------
        >>> solver = te.LaplaceSolver(100, 100)
        >>> bc = te.BoundaryConditions(80, 60, 45, 55)
        >>> grid = solver.solve(bc)
        >>> grid.to_numpy()  # Returns NumPy array
        )pbdoc")
        .def(py::init<size_t, size_t, double, size_t>(),
             py::arg("nx") = 100,
             py::arg("ny") = 100,
             py::arg("tolerance") = 1e-4,
             py::arg("max_iterations") = 1000)
        .def("solve", &LaplaceSolver::solve,
             py::arg("boundary_conditions"),
             "Solve Laplace equation with given boundary conditions")
        .def("solve_from_sensors", 
             [](LaplaceSolver& self, double m1, double m2, double m3, double m4) {
                 BoundaryConditions bc(m1, m2, m3, m4);
                 return self.solve(bc);
             },
             py::arg("moisture1"), py::arg("moisture2"),
             py::arg("moisture3"), py::arg("moisture4"),
             "Solve directly from 4 sensor values")
        .def("solve_to_numpy",
             [](LaplaceSolver& self, double m1, double m2, double m3, double m4) {
                 BoundaryConditions bc(m1, m2, m3, m4);
                 Grid2D grid = self.solve(bc);
                 return grid_to_numpy(grid);
             },
             py::arg("moisture1"), py::arg("moisture2"),
             py::arg("moisture3"), py::arg("moisture4"),
             "Solve and return as NumPy array")
        .def_property_readonly("nx", &LaplaceSolver::get_nx)
        .def_property_readonly("ny", &LaplaceSolver::get_ny)
        .def_property_readonly("last_iterations", &LaplaceSolver::get_last_iterations,
             "Number of iterations in last solve")
        .def_property_readonly("last_residual", &LaplaceSolver::get_last_residual,
             "Final residual from last solve");

    // ========================================
    // WhatIfSimulator
    // ========================================
    py::class_<WhatIfSimulator>(m, "WhatIfSimulator",
        R"pbdoc(
        What-If Simulation Engine for future moisture prediction.
        
        Simulates moisture evolution based on:
        - Evaporation (temperature-dependent decay)
        - Irrigation events (periodic moisture addition)
        
        Example:
        --------
        >>> sim = te.WhatIfSimulator()
        >>> result = sim.simulate(
        ...     [80, 60, 45, 55],  # Current moisture values
        ...     28.0,               # Temperature (°C)
        ...     150.0,              # Water amount (ml)
        ...     12.0,               # Watering frequency (hours)
        ...     72,                 # Simulation duration (hours)
        ...     0.5                 # Time step (hours)
        ... )
        >>> result['zones']['zone1']['final_moisture']
        )pbdoc")
        .def(py::init<double, double>(),
             py::arg("base_decay_constant") = 0.02,
             py::arg("moisture_gain_per_100ml") = 5.0)
        .def("simulate",
             [](WhatIfSimulator& self,
                const std::vector<double>& initial_moisture,
                double ambient_temperature,
                double watering_amount_ml,
                double watering_frequency_hours,
                int duration_hours,
                double time_step_hours) {
                 
                 if (initial_moisture.size() != 4) {
                     throw std::invalid_argument("initial_moisture must have 4 values");
                 }
                 
                 std::array<double, 4> moisture_arr;
                 std::copy_n(initial_moisture.begin(), 4, moisture_arr.begin());
                 
                 auto result = self.simulate(
                     moisture_arr,
                     ambient_temperature,
                     watering_amount_ml,
                     watering_frequency_hours,
                     duration_hours,
                     time_step_hours
                 );
                 
                 return simulation_result_to_dict(result);
             },
             py::arg("initial_moisture"),
             py::arg("ambient_temperature"),
             py::arg("watering_amount_ml"),
             py::arg("watering_frequency_hours"),
             py::arg("duration_hours") = 72,
             py::arg("time_step_hours") = 0.5,
             "Run what-if simulation for all 4 zones")
        .def("calculate_decay_constant", &WhatIfSimulator::calculate_decay_constant,
             py::arg("temperature"),
             "Calculate temperature-adjusted decay constant")
        .def("calculate_moisture_gain", &WhatIfSimulator::calculate_moisture_gain,
             py::arg("watering_amount_ml"),
             "Calculate moisture gain from watering amount")
        .def_property("base_decay_constant",
             &WhatIfSimulator::get_base_decay_constant,
             &WhatIfSimulator::set_base_decay_constant)
        .def_property("moisture_gain_factor",
             &WhatIfSimulator::get_moisture_gain_factor,
             &WhatIfSimulator::set_moisture_gain_factor);

    // ========================================
    // Convenience Functions
    // ========================================
    m.def("compute_moisture_distribution",
          [](double m1, double m2, double m3, double m4, size_t grid_size) {
              auto result = compute_moisture_distribution(m1, m2, m3, m4, grid_size);
              
              // Convert to numpy
              auto arr = py::array_t<double>({grid_size, grid_size});
              auto buf = arr.mutable_unchecked<2>();
              for (size_t i = 0; i < grid_size; ++i) {
                  for (size_t j = 0; j < grid_size; ++j) {
                      buf(i, j) = result[i][j];
                  }
              }
              return arr;
          },
          py::arg("moisture1"), py::arg("moisture2"),
          py::arg("moisture3"), py::arg("moisture4"),
          py::arg("grid_size") = 100,
          R"pbdoc(
          Compute moisture distribution from 4 sensor values.
          
          Parameters:
          -----------
          moisture1 : float
              Top-left sensor (Zone 1)
          moisture2 : float
              Top-right sensor (Zone 2)
          moisture3 : float
              Bottom-left sensor (Zone 3)
          moisture4 : float
              Bottom-right sensor (Zone 4)
          grid_size : int, optional
              Grid resolution (default: 100)
          
          Returns:
          --------
          numpy.ndarray
              2D moisture distribution array
          )pbdoc");

    m.def("predict_moisture",
          [](const std::vector<double>& current_moisture,
             double temperature,
             double watering_ml,
             double watering_freq_hours,
             double predict_hours) {
              
              if (current_moisture.size() != 4) {
                  throw std::invalid_argument("current_moisture must have 4 values");
              }
              
              std::array<double, 4> moisture_arr;
              std::copy_n(current_moisture.begin(), 4, moisture_arr.begin());
              
              auto result = predict_moisture(
                  moisture_arr, temperature, watering_ml, 
                  watering_freq_hours, predict_hours
              );
              
              return std::vector<double>(result.begin(), result.end());
          },
          py::arg("current_moisture"),
          py::arg("temperature"),
          py::arg("watering_ml"),
          py::arg("watering_freq_hours"),
          py::arg("predict_hours"),
          R"pbdoc(
          Quick prediction of moisture values after specified hours.
          
          Parameters:
          -----------
          current_moisture : list
              Current moisture values [zone1, zone2, zone3, zone4]
          temperature : float
              Ambient temperature (°C)
          watering_ml : float
              Water amount per irrigation (ml)
          watering_freq_hours : float
              Hours between watering events
          predict_hours : float
              Hours into the future to predict
          
          Returns:
          --------
          list
              Predicted moisture values [zone1, zone2, zone3, zone4]
          )pbdoc");
}
