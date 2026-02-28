#!/bin/bash
# Launch script for Greenhouse Digital Twin
# Run this from the project root directory

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
BACKEND_DIR="${PROJECT_ROOT}/backend"
FRONTEND_DIR="${PROJECT_ROOT}/frontend"
ENGINE_BUILD="${BACKEND_DIR}/src/digital_twin/engine/build"
PYTHON_GUI="${FRONTEND_DIR}/python_gui"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color
BOLD='\033[1m'

print_header() {
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}     ${GREEN}🌱 Greenhouse Digital Twin Platform${NC}                    ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

get_broker_ip() {
    # Get the primary IP address (not localhost)
    # Try different methods for compatibility
    
    # Method 1: hostname -I (most Linux systems)
    if command -v hostname &> /dev/null; then
        IP=$(hostname -I 2>/dev/null | awk '{print $1}')
        if [ -n "$IP" ]; then
            echo "$IP"
            return
        fi
    fi
    
    # Method 2: ip route
    if command -v ip &> /dev/null; then
        IP=$(ip route get 1 2>/dev/null | awk '{print $7; exit}')
        if [ -n "$IP" ]; then
            echo "$IP"
            return
        fi
    fi
    
    # Method 3: ifconfig
    if command -v ifconfig &> /dev/null; then
        IP=$(ifconfig 2>/dev/null | grep -Eo 'inet (addr:)?([0-9]*\.){3}[0-9]*' | grep -Eo '([0-9]*\.){3}[0-9]*' | grep -v '127.0.0.1' | head -1)
        if [ -n "$IP" ]; then
            echo "$IP"
            return
        fi
    fi
    
    # Fallback
    echo "127.0.0.1"
}

check_mosquitto() {
    if systemctl is-active --quiet mosquitto 2>/dev/null; then
        return 0
    elif pgrep -x mosquitto > /dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

start_mosquitto() {
    echo -e "${YELLOW}Starting Mosquitto MQTT broker...${NC}"
    
    if command -v systemctl &> /dev/null; then
        sudo systemctl start mosquitto 2>/dev/null || {
            echo -e "${YELLOW}systemctl failed, trying direct start...${NC}"
            mosquitto -d 2>/dev/null || {
                echo -e "${RED}Failed to start mosquitto. Install with: sudo apt install mosquitto${NC}"
                return 1
            }
        }
    else
        mosquitto -d 2>/dev/null || {
            echo -e "${RED}Failed to start mosquitto${NC}"
            return 1
        }
    fi
    
    sleep 1
    return 0
}

print_broker_info() {
    BROKER_IP=$(get_broker_ip)
    BROKER_PORT="1883"
    
    echo ""
    echo -e "${CYAN}╔════════════════════════════════════════════════════════════╗${NC}"
    echo -e "${CYAN}║${NC}  ${BOLD}📡 MQTT BROKER CONFIGURATION FOR NODES${NC}                    ${CYAN}║${NC}"
    echo -e "${CYAN}╠════════════════════════════════════════════════════════════╣${NC}"
    echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}   ${GREEN}Broker IP:${NC}   ${BOLD}${BROKER_IP}${NC}"
    echo -e "${CYAN}║${NC}   ${GREEN}Broker Port:${NC} ${BOLD}${BROKER_PORT}${NC}"
    echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}   ${YELLOW}Use this in your ESP32/Pico firmware:${NC}                   ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}   ${BLUE}// ESP32 (Arduino)${NC}                                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}   const char* mqtt_server = \"${BROKER_IP}\";               "
    echo -e "${CYAN}║${NC}   const int mqtt_port = ${BROKER_PORT};                              "
    echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}   ${BLUE}# Raspberry Pi Pico (MicroPython)${NC}                       ${CYAN}║${NC}"
    echo -e "${CYAN}║${NC}   MQTT_BROKER = \"${BROKER_IP}\"                            "
    echo -e "${CYAN}║${NC}   MQTT_PORT = ${BROKER_PORT}                                         "
    echo -e "${CYAN}║${NC}                                                            ${CYAN}║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════════════════════════════╝${NC}"
    echo ""
}

setup_environment() {
    # Check if virtual environment exists
    if [ ! -d "${BACKEND_DIR}/venv" ]; then
        echo -e "${YELLOW}Creating virtual environment...${NC}"
        python3 -m venv "${BACKEND_DIR}/venv"
    fi

    # Activate venv
    source "${BACKEND_DIR}/venv/bin/activate"

    # Check dependencies
    echo -e "${YELLOW}Checking dependencies...${NC}"
    pip install paho-mqtt matplotlib numpy -q

    # Check if C++ engine is built
    if ! ls "${ENGINE_BUILD}/twin_engine_py"*.so 1> /dev/null 2>&1; then
        echo ""
        echo -e "${YELLOW}C++ engine not found. Building...${NC}"
        cd "${BACKEND_DIR}/src/digital_twin/engine"
        bash build.sh
    fi

    # Set PYTHONPATH
    export PYTHONPATH="${ENGINE_BUILD}:${BACKEND_DIR}/src/digital_twin/engine/python:${PYTHONPATH}"
}

print_header

# Check and start Mosquitto
echo -e "${YELLOW}Checking MQTT broker...${NC}"
if check_mosquitto; then
    echo -e "${GREEN}✓ Mosquitto is running${NC}"
else
    echo -e "${YELLOW}Mosquitto not running. Attempting to start...${NC}"
    if start_mosquitto; then
        echo -e "${GREEN}✓ Mosquitto started successfully${NC}"
    else
        echo -e "${RED}✗ Could not start Mosquitto. Some features may not work.${NC}"
    fi
fi

# Print broker info for nodes
print_broker_info

# Setup Python environment
setup_environment

# Launch options
echo ""
echo -e "${BOLD}Select launch option:${NC}"
echo -e "  ${GREEN}1)${NC} Dashboard only (connect to real sensor nodes)"
echo -e "  ${GREEN}2)${NC} Dashboard + Simulator (for testing without nodes)"
echo -e "  ${GREEN}3)${NC} Simulator only (no GUI)"
echo -e "  ${GREEN}4)${NC} Train PINNs model"
echo -e "  ${GREEN}5)${NC} Generate PINNs training data"
echo ""
read -p "Enter choice [1]: " choice
choice=${choice:-1}

case $choice in
    1)
        echo ""
        echo -e "${GREEN}Launching Dashboard...${NC}"
        echo -e "${YELLOW}Waiting for sensor data from nodes...${NC}"
        cd "${PYTHON_GUI}"
        python dashboard.py
        ;;
    2)
        echo ""
        echo -e "${GREEN}Launching Dashboard + Simulator...${NC}"
        echo -e "${YELLOW}(Simulator provides fake sensor data for testing)${NC}"
        cd "${PYTHON_GUI}"
        python dashboard.py &
        DASHBOARD_PID=$!
        sleep 2
        echo ""
        echo -e "${CYAN}Starting MQTT Simulator...${NC}"
        python "${SCRIPT_DIR}/mqtt_simulator.py" --interval 3
        # When simulator stops, ask if we should stop dashboard
        echo ""
        read -p "Stop dashboard? [Y/n]: " stop_dashboard
        if [[ ! "$stop_dashboard" =~ ^[Nn] ]]; then
            kill $DASHBOARD_PID 2>/dev/null || true
        fi
        ;;
    3)
        echo ""
        echo -e "${GREEN}Starting MQTT Simulator...${NC}"
        echo -e "${YELLOW}(Run dashboard separately if needed)${NC}"
        read -p "Interval in seconds [3]: " interval
        interval=${interval:-3}
        read -p "Duration in seconds (0=indefinite) [0]: " duration
        duration=${duration:-0}
        
        if [ "$duration" -eq 0 ]; then
            python "${SCRIPT_DIR}/mqtt_simulator.py" --interval $interval
        else
            python "${SCRIPT_DIR}/mqtt_simulator.py" --interval $interval --duration $duration
        fi
        ;;
    4)
        echo ""
        echo -e "${GREEN}Training PINNs model...${NC}"
        read -p "Epochs [2000]: " epochs
        epochs=${epochs:-2000}
        read -p "Device (cpu/cuda) [cpu]: " device
        device=${device:-cpu}
        
        cd "${BACKEND_DIR}/src/digital_twin/pinns/training"
        python train.py --epochs $epochs --device $device
        ;;
    5)
        echo ""
        echo -e "${GREEN}Generating PINNs training data...${NC}"
        cd "${BACKEND_DIR}/src/digital_twin/pinns/data"
        python data_generator.py
        ;;
    *)
        echo -e "${RED}Invalid choice${NC}"
        exit 1
        ;;
esac
