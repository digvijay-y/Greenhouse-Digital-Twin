#ifndef LAPLACE_SOLVER_HPP
#define LAPLACE_SOLVER_HPP

#include <vector>
#include <array>
#include <cmath>
#include <stdexcept>

namespace digital_twin {

/**
 * @brief 2D Grid for moisture distribution
 * 
 * Row-major storage: grid[row][col] = grid[y][x]
 */
class Grid2D {
public:
    Grid2D(size_t rows, size_t cols, double initial_value = 50.0);
    
    // Accessors
    double& operator()(size_t row, size_t col);
    double operator()(size_t row, size_t col) const;
    
    // Dimensions
    size_t rows() const { return rows_; }
    size_t cols() const { return cols_; }
    size_t size() const { return data_.size(); }
    
    // Raw data access (for Python bindings)
    std::vector<double>& data() { return data_; }
    const std::vector<double>& data() const { return data_; }
    
    // Get as 2D vector (for Python)
    std::vector<std::vector<double>> to_2d_vector() const;
    
    // Get flattened copy
    std::vector<double> flatten() const { return data_; }
    
private:
    size_t rows_;
    size_t cols_;
    std::vector<double> data_;
};

/**
 * @brief Boundary conditions from 4 corner sensors
 * 
 * Layout:
 *   top_left (0,0) -------- top_right (0, Nx-1)
 *        |                       |
 *        |                       |
 *   bottom_left (Ny-1,0) -- bottom_right (Ny-1, Nx-1)
 */
struct BoundaryConditions {
    double top_left;      // Sensor 1 (moisture1)
    double top_right;     // Sensor 2 (moisture2)  
    double bottom_left;   // Sensor 3 (moisture3)
    double bottom_right;  // Sensor 4 (moisture4)
    
    BoundaryConditions(double tl = 50.0, double tr = 50.0, 
                       double bl = 50.0, double br = 50.0)
        : top_left(tl), top_right(tr), bottom_left(bl), bottom_right(br) {}
};

/**
 * @brief Laplace Equation Solver using Jacobi iteration
 * 
 * Solves: ∇²u = ∂²u/∂x² + ∂²u/∂y² = 0
 * 
 * This is a direct port of the MATLAB Twin.m moisture distribution model.
 * Uses 4-point boundary interpolation and iterative relaxation.
 */
class LaplaceSolver {
public:
    /**
     * @brief Construct solver with grid dimensions
     * 
     * @param nx Grid points in x-direction (width)
     * @param ny Grid points in y-direction (height)
     * @param tolerance Convergence tolerance (default: 1e-4)
     * @param max_iterations Maximum iterations (default: 1000)
     */
    LaplaceSolver(size_t nx = 100, size_t ny = 100, 
                  double tolerance = 1e-4, size_t max_iterations = 1000);
    
    /**
     * @brief Solve the Laplace equation with given boundary conditions
     * 
     * @param bc Boundary conditions from 4 sensors
     * @return Grid2D Solution grid with moisture values (0-100%)
     */
    Grid2D solve(const BoundaryConditions& bc);
    
    /**
     * @brief Apply boundary conditions to the grid edges
     * 
     * Linearly interpolates between corner sensor values along each edge.
     */
    void apply_boundary_conditions(Grid2D& grid, const BoundaryConditions& bc);
    
    /**
     * @brief Perform one Jacobi iteration
     * 
     * @param grid Current grid state
     * @return double Maximum change (for convergence check)
     */
    double jacobi_iteration(Grid2D& grid);
    
    // Getters
    size_t get_nx() const { return nx_; }
    size_t get_ny() const { return ny_; }
    size_t get_last_iterations() const { return last_iterations_; }
    double get_last_residual() const { return last_residual_; }
    
private:
    size_t nx_;
    size_t ny_;
    double tolerance_;
    size_t max_iterations_;
    
    // Stats from last solve
    size_t last_iterations_;
    double last_residual_;
};

/**
 * @brief Convenience function to compute moisture distribution
 * 
 * @param moisture1 Top-left sensor value
 * @param moisture2 Top-right sensor value
 * @param moisture3 Bottom-left sensor value
 * @param moisture4 Bottom-right sensor value
 * @param grid_size Grid resolution (default: 100x100)
 * @return std::vector<std::vector<double>> 2D moisture distribution
 */
std::vector<std::vector<double>> compute_moisture_distribution(
    double moisture1, double moisture2, 
    double moisture3, double moisture4,
    size_t grid_size = 100
);

} // namespace digital_twin

#endif // LAPLACE_SOLVER_HPP
