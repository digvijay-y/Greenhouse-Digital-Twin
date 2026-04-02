#!/bin/bash
# PINN Training Launcher for Greenhouse Moisture Prediction
# Run this from the project root directory
# 
# Usage:
#   ./scripts/train_pinn.sh              # Default: 2000 epochs on GPU/CPU auto
#   ./scripts/train_pinn.sh --epochs 5000 --device cuda
#   ./scripts/train_pinn.sh --help

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="${PROJECT_ROOT}/backend"
VENV_DIR="${BACKEND_DIR}/venv"
VENV_PYTHON="${VENV_DIR}/bin/python"
PINNS_DIR="${BACKEND_DIR}/src/digital_twin/pinns"
TRAINING_DIR="${PINNS_DIR}/training"
DATA_DIR="${PINNS_DIR}/data"
CHECKPOINT_DIR="${TRAINING_DIR}/checkpoints"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
NC='\033[0m' # No Color
BOLD='\033[1m'

# Default parameters
EPOCHS=2000
LEARNING_RATE="1e-3"
LAMBDA_PDE="0.1"
DEVICE=""
KAGGLE_CSV=""
KAGGLE_RATIO="0.3"
SKIP_DATA_GEN=false
GENERATE_ONLY=false
SHOW_HELP=false

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}     ${GREEN}🌱 PINN Training for Moisture Prediction${NC}             ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

print_help() {
    echo -e "${BOLD}Usage:${NC}"
    echo "  ./scripts/train_pinn.sh [OPTIONS]"
    echo ""
    echo -e "${BOLD}Options:${NC}"
    echo "  --epochs EPOCHS              Training epochs (default: 2000)"
    echo "  --lr LR                      Learning rate (default: 1e-3)"
    echo "  --lambda-pde WEIGHT          PDE loss weight (default: 0.1)"
    echo "  --device DEVICE              'cpu' or 'cuda' (default: auto-detect)"
    echo "  --kaggle-csv PATH            Optional Kaggle CSV path for hybrid training"
    echo "  --kaggle-ratio VALUE         Kaggle fraction in mixed data [0,1] (default: 0.3)"
    echo "  --skip-data-gen              Skip data generation if files exist"
    echo "  --generate-only              Only generate data, don't train"
    echo "  --help                       Show this message"
    echo ""
    echo -e "${BOLD}Examples:${NC}"
    echo "  ./scripts/train_pinn.sh                              # Default settings"
    echo "  ./scripts/train_pinn.sh --epochs 5000 --device cuda  # 5000 epochs on GPU"
    echo "  ./scripts/train_pinn.sh --generate-only              # Only create datasets"
    echo "  ./scripts/train_pinn.sh --skip-data-gen --epochs 3000  # Retrain with existing data"
    echo "  ./scripts/train_pinn.sh --kaggle-csv ~/Downloads/data.csv --kaggle-ratio 0.3"
    echo ""
}

parse_args() {
    while [[ $# -gt 0 ]]; do
        case $1 in
            --epochs)
                EPOCHS="$2"
                shift 2
                ;;
            --lr)
                LEARNING_RATE="$2"
                shift 2
                ;;
            --lambda-pde)
                LAMBDA_PDE="$2"
                shift 2
                ;;
            --device)
                DEVICE="$2"
                shift 2
                ;;
            --kaggle-csv)
                KAGGLE_CSV="$2"
                shift 2
                ;;
            --kaggle-ratio)
                KAGGLE_RATIO="$2"
                shift 2
                ;;
            --skip-data-gen)
                SKIP_DATA_GEN=true
                shift
                ;;
            --generate-only)
                GENERATE_ONLY=true
                shift
                ;;
            --help)
                SHOW_HELP=true
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_help
                exit 1
                ;;
        esac
    done
}

check_environment() {
    # Verify venv exists
    if [ ! -d "${VENV_DIR}" ]; then
        echo -e "${RED}❌ Virtual environment not found at ${VENV_DIR}${NC}"
        echo -e "${YELLOW}Run ./scripts/launch.sh first to set up the environment${NC}"
        exit 1
    fi

    if [ ! -x "${VENV_PYTHON}" ]; then
        echo -e "${RED}❌ Python executable not found${NC}"
        exit 1
    fi

    # Verify PyTorch is installed
    if ! "${VENV_PYTHON}" -c "import torch" 2>/dev/null; then
        echo -e "${RED}❌ PyTorch not installed in virtual environment${NC}"
        echo -e "${YELLOW}Installing PyTorch...${NC}"
        "${VENV_PYTHON}" -m pip install torch -q --upgrade
    fi
}

detect_device() {
    local device_choice="$1"
    
    # If device explicitly set, use it
    if [ -n "$device_choice" ] && [ "$device_choice" != "auto" ]; then
        echo "$device_choice"
        return
    fi
    
    # Auto-detect: check CUDA availability
    local cuda_available=$("${VENV_PYTHON}" -c "import torch; print('yes' if torch.cuda.is_available() else 'no')" 2>/dev/null || echo "no")
    
    if [ "$cuda_available" = "yes" ]; then
        echo "cuda"
    else
        echo "cpu"
    fi
}

show_device_info() {
    local device="$1"
    
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Device Information${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    
    if [ "$device" = "cuda" ]; then
        echo -e "  ${GREEN}Device:${NC} CUDA (GPU) ✓"
        echo ""
        echo -e "  ${BOLD}GPU Details:${NC}"
        "${VENV_PYTHON}" -c "
import torch
if torch.cuda.is_available():
    print('    GPU Name:', torch.cuda.get_device_name(0))
    print('    Compute Capability:', torch.cuda.get_device_capability(0))
    print('    VRAM Available:', round(torch.cuda.get_device_properties(0).total_memory / 1e9, 2), 'GB')
"
        echo ""
        echo -e "  ${YELLOW}Expected training time: 3-5 minutes (2000 epochs)${NC}"
    else
        echo -e "  ${YELLOW}Device:${NC} CPU"
        echo ""
        echo -e "  ${YELLOW}ℹ️  GPU not available - training will be slower${NC}"
        echo -e "  Expected training time: 30-40 minutes (2000 epochs)"
        echo ""
        echo -e "  To use GPU:"
        echo "    1. Install CUDA for your GPU"
        echo "    2. Reinstall PyTorch with CUDA support:"
        echo "       pip install torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cu118"
    fi
    echo ""
}

setup_directories() {
    # Create checkpoint directory
    mkdir -p "${CHECKPOINT_DIR}"
    echo -e "${GREEN}✓ Checkpoint directory ready: ${CHECKPOINT_DIR}${NC}"
}

generate_data() {
    local skip_if_exists="$1"
    
    # Check if data already exists
    if [ "$skip_if_exists" = true ] && [ -f "${DATA_DIR}/train_data.npz" ]; then
        echo -e "${GREEN}✓ Training data already exists, skipping generation${NC}"
        return 0
    fi
    
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}📊 Data Generation${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    cd "${DATA_DIR}"
    "${VENV_PYTHON}" data_generator.py
    
    # Verify data was generated
    if [ ! -f "${DATA_DIR}/train_data.npz" ]; then
        echo -e "${RED}❌ Data generation failed${NC}"
        exit 1
    fi
    
    echo -e "${GREEN}✓ Data generation complete${NC}"
}

show_training_config() {
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}Training Configuration${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  ${MAGENTA}Epochs:${NC}              $EPOCHS"
    echo -e "  ${MAGENTA}Learning Rate:${NC}      $LEARNING_RATE"
    echo -e "  ${MAGENTA}PDE Loss Weight:${NC}    $LAMBDA_PDE"
    echo -e "  ${MAGENTA}Device:${NC}             $(echo $DEVICE | tr '[:lower:]' '[:upper:]')"
    if [ -n "$KAGGLE_CSV" ]; then
        echo -e "  ${MAGENTA}Kaggle CSV:${NC}         $KAGGLE_CSV"
        echo -e "  ${MAGENTA}Kaggle Ratio:${NC}       $KAGGLE_RATIO"
    fi
    echo ""
    echo -e "  Physics Configuration:"
    echo -e "    λ_pde = $LAMBDA_PDE (PDE residual weight)"
    echo -e "    λ_bc  = 1.0 (boundary condition weight)"
    echo -e "    λ_ic  = 0.5 (initial condition weight)"
    echo ""
    echo -e "  Model Architecture:"
    echo -e "    Input:  4D (x, y, t, T)"
    echo -e "    Hidden: [64, 128, 128, 64]"
    echo -e "    Output: 1D (soil moisture %)"
    echo ""
}

run_training() {
    local device="$1"
    
    echo ""
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}🚀 Starting Training${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    
    cd "${TRAINING_DIR}"

    local cmd="${VENV_PYTHON} train.py --epochs ${EPOCHS} --lr ${LEARNING_RATE} --lambda-pde ${LAMBDA_PDE} --device ${device} --kaggle-ratio ${KAGGLE_RATIO}"
    if [ -n "$KAGGLE_CSV" ]; then
        cmd+=" --kaggle-csv \"${KAGGLE_CSV}\""
    fi
    
    echo -e "${YELLOW}Command:${NC} $cmd"
    echo ""
    
    # Run training
    eval "$cmd"
    
    # Check if training completed successfully
    if [ $? -eq 0 ]; then
        echo ""
        echo -e "${GREEN}╔════════════════════════════════════════════════════════════╗${NC}"
        echo -e "${GREEN}║${NC}          ${BOLD}✅ Training Completed Successfully!${NC}             ${GREEN}║${NC}"
        echo -e "${GREEN}╚════════════════════════════════════════════════════════════╝${NC}"
        echo ""
        
        # List saved checkpoints
        echo -e "${BOLD}Saved Checkpoints:${NC}"
        ls -lh "${CHECKPOINT_DIR}"/*.pt 2>/dev/null || echo "  (No .pt files found)"
        
        echo ""
        echo -e "${BOLD}Next Steps:${NC}"
        echo "  1. Visualize results: Open ${CHECKPOINT_DIR}/training_results.png"
        echo "  2. Evaluate model:   ${VENV_PYTHON} train.py --eval ${CHECKPOINT_DIR}/moisture_pinn.pt"
        echo "  3. Use in inference: See integration documentation"
        echo ""
    else
        echo -e "${RED}❌ Training failed${NC}"
        exit 1
    fi
}

show_summary() {
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BOLD}📋 Summary${NC}"
    echo -e "${CYAN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo -e "  Data Directory:          ${DATA_DIR}"
    echo -e "  Checkpoint Directory:    ${CHECKPOINT_DIR}"
    echo -e "  Training Log:            Available in console output above"
    echo ""
    echo -e "${GREEN}✓ Ready to train PINN model${NC}"
    echo ""
}

# ============================================================================
# Main execution
# ============================================================================

print_header

# Parse command-line arguments
parse_args "$@"

if [ -n "$KAGGLE_CSV" ] && [ ! -f "$KAGGLE_CSV" ]; then
    echo -e "${RED}❌ Kaggle CSV not found: $KAGGLE_CSV${NC}"
    exit 1
fi

# Show help and exit if requested
if [ "$SHOW_HELP" = true ]; then
    print_help
    exit 0
fi

# Check environment
check_environment

# Define DEVICE (auto-detect or use specified)
DEVICE=$(detect_device "$DEVICE")

# Show device info
show_device_info "$DEVICE"

# Setup directories
setup_directories

# Generate data or skip
if [ "$GENERATE_ONLY" = true ]; then
    generate_data false
    show_summary
    exit 0
else
    generate_data "$SKIP_DATA_GEN"
fi

# Show training configuration
show_training_config

# Run training
run_training "$DEVICE"

echo ""
