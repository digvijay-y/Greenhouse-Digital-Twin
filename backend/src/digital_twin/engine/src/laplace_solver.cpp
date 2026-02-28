/**
 * @file laplace_solver.cpp
 * @brief Implementation of Laplace equation solver for moisture distribution
 * 
 * Ported from MATLAB moisture_distribution_twin.m
 * Uses Jacobi iterative method to solve: ∇²u = 0
 */

#include "laplace_solver.hpp"
#include <algorithm>
#include <numeric>

namespace digital_twin {

// ============================================
// Grid2D Implementation
// ============================================

Grid2D::Grid2D(size_t rows, size_t cols, double initial_value)
    : rows_(rows), cols_(cols), data_(rows * cols, initial_value) {
    if (rows < 3 || cols < 3) {
        throw std::invalid_argument("Grid must be at least 3x3");
    }
}

double& Grid2D::operator()(size_t row, size_t col) {
    if (row >= rows_ || col >= cols_) {
        throw std::out_of_range("Grid index out of bounds");
    }
    return data_[row * cols_ + col];
}

double Grid2D::operator()(size_t row, size_t col) const {
    if (row >= rows_ || col >= cols_) {
        throw std::out_of_range("Grid index out of bounds");
    }
    return data_[row * cols_ + col];
}

std::vector<std::vector<double>> Grid2D::to_2d_vector() const {
    std::vector<std::vector<double>> result(rows_, std::vector<double>(cols_));
    for (size_t i = 0; i < rows_; ++i) {
        for (size_t j = 0; j < cols_; ++j) {
            result[i][j] = data_[i * cols_ + j];
        }
    }
    return result;
}

// ============================================
// LaplaceSolver Implementation
// ============================================

LaplaceSolver::LaplaceSolver(size_t nx, size_t ny, 
                             double tolerance, size_t max_iterations)
    : nx_(nx), ny_(ny), tolerance_(tolerance), max_iterations_(max_iterations),
      last_iterations_(0), last_residual_(0.0) {
    if (nx < 3 || ny < 3) {
        throw std::invalid_argument("Grid must be at least 3x3");
    }
}

void LaplaceSolver::apply_boundary_conditions(Grid2D& grid, const BoundaryConditions& bc) {
    const size_t ny = grid.rows();
    const size_t nx = grid.cols();
    
    // Top edge: linearly interpolate from top_left to top_right
    for (size_t j = 0; j < nx; ++j) {
        double t = static_cast<double>(j) / (nx - 1);
        grid(0, j) = bc.top_left * (1.0 - t) + bc.top_right * t;
    }
    
    // Bottom edge: linearly interpolate from bottom_left to bottom_right
    for (size_t j = 0; j < nx; ++j) {
        double t = static_cast<double>(j) / (nx - 1);
        grid(ny - 1, j) = bc.bottom_left * (1.0 - t) + bc.bottom_right * t;
    }
    
    // Left edge: linearly interpolate from top_left to bottom_left
    for (size_t i = 0; i < ny; ++i) {
        double t = static_cast<double>(i) / (ny - 1);
        grid(i, 0) = bc.top_left * (1.0 - t) + bc.bottom_left * t;
    }
    
    // Right edge: linearly interpolate from top_right to bottom_right
    for (size_t i = 0; i < ny; ++i) {
        double t = static_cast<double>(i) / (ny - 1);
        grid(i, nx - 1) = bc.top_right * (1.0 - t) + bc.bottom_right * t;
    }
}

double LaplaceSolver::jacobi_iteration(Grid2D& grid) {
    const size_t ny = grid.rows();
    const size_t nx = grid.cols();
    
    double max_change = 0.0;
    
    // Create copy for Jacobi iteration (read from old, write to new)
    std::vector<double> old_data = grid.data();
    
    // Update interior points using 4-point stencil
    // u_new[i,j] = 0.25 * (u[i-1,j] + u[i+1,j] + u[i,j-1] + u[i,j+1])
    for (size_t i = 1; i < ny - 1; ++i) {
        for (size_t j = 1; j < nx - 1; ++j) {
            double old_val = old_data[i * nx + j];
            
            double new_val = 0.25 * (
                old_data[(i - 1) * nx + j] +  // top
                old_data[(i + 1) * nx + j] +  // bottom
                old_data[i * nx + (j - 1)] +  // left
                old_data[i * nx + (j + 1)]    // right
            );
            
            grid(i, j) = new_val;
            
            double change = std::abs(new_val - old_val);
            max_change = std::max(max_change, change);
        }
    }
    
    return max_change;
}

Grid2D LaplaceSolver::solve(const BoundaryConditions& bc) {
    // Initialize grid with mean of boundary values
    double mean_bc = (bc.top_left + bc.top_right + bc.bottom_left + bc.bottom_right) / 4.0;
    Grid2D grid(ny_, nx_, mean_bc);
    
    // Apply boundary conditions
    apply_boundary_conditions(grid, bc);
    
    // Iterative solve
    last_iterations_ = 0;
    last_residual_ = 0.0;
    
    for (size_t iter = 0; iter < max_iterations_; ++iter) {
        double max_change = jacobi_iteration(grid);
        last_iterations_ = iter + 1;
        last_residual_ = max_change;
        
        // Check convergence
        if (max_change < tolerance_) {
            break;
        }
    }
    
    return grid;
}

// ============================================
// Convenience Functions
// ============================================

std::vector<std::vector<double>> compute_moisture_distribution(
    double moisture1, double moisture2, 
    double moisture3, double moisture4,
    size_t grid_size) {
    
    // Create boundary conditions matching MATLAB layout
    BoundaryConditions bc(moisture1, moisture2, moisture3, moisture4);
    
    // Create solver and solve
    LaplaceSolver solver(grid_size, grid_size);
    Grid2D result = solver.solve(bc);
    
    return result.to_2d_vector();
}

} // namespace digital_twin
