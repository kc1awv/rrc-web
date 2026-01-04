#!/usr/bin/env bash

# RRC Web Client startup script
# This script helps run the RRC Web Client with common options

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Default values
PORT=8080
LOG_LEVEL="INFO"
CONFIG_FILE=""

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_warn() {
    echo -e "${YELLOW}[WARN]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to show usage
usage() {
    cat << EOF
RRC Web Client Startup Script

Usage: $0 [OPTIONS]

Options:
    -p, --port PORT         Set the server port (default: 8080)
    -c, --config FILE       Use alternate config file
    -d, --debug             Enable debug logging
    -v, --verbose           Enable verbose logging
    -h, --help              Show this help message

Environment Variables:
    RRC_WEB_PORT        Override server port
    RRC_WEB_CONFIG      Override config file path
    RRC_LOG_LEVEL           Set logging level (DEBUG, INFO, WARNING, ERROR)

Examples:
    $0                      # Run with default settings
    $0 -d                   # Run with debug logging
    $0 -p 9090              # Run on port 9090
    $0 -c /path/to/config   # Use custom config file

EOF
    exit 0
}

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case $1 in
        -p|--port)
            PORT="$2"
            shift 2
            ;;
        -c|--config)
            CONFIG_FILE="$2"
            shift 2
            ;;
        -d|--debug)
            LOG_LEVEL="DEBUG"
            shift
            ;;
        -v|--verbose)
            LOG_LEVEL="INFO"
            shift
            ;;
        -h|--help)
            usage
            ;;
        *)
            print_error "Unknown option: $1"
            usage
            ;;
    esac
done

if ! command -v python3 &> /dev/null; then
    print_error "Python 3 is not installed. Please install Python 3.11 or newer."
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
REQUIRED_VERSION="3.11"

if [ "$(printf '%s\n' "$REQUIRED_VERSION" "$PYTHON_VERSION" | sort -V | head -n1)" != "$REQUIRED_VERSION" ]; then
    print_error "Python $REQUIRED_VERSION or newer is required. Found Python $PYTHON_VERSION"
    exit 1
fi

if ! python3 -c "import RNS" 2>/dev/null; then
    print_error "Reticulum (RNS) is not installed."
    print_info "Install with: pip install rns"
    exit 1
fi

if ! python3 -c "import rrc_web" 2>/dev/null; then
    print_error "rrc_web is not installed."
    print_info "Install with: pip install -e ."
    print_info "From directory: $(dirname "$0")"
    exit 1
fi

export RRC_WEB_PORT="$PORT"
export RRC_LOG_LEVEL="$LOG_LEVEL"

if [ -n "$CONFIG_FILE" ]; then
    export RRC_WEB_CONFIG="$CONFIG_FILE"
fi

print_info "Starting RRC Web Client..."
print_info "Port: $PORT"
print_info "Log Level: $LOG_LEVEL"

if [ -n "$CONFIG_FILE" ]; then
    print_info "Config: $CONFIG_FILE"
fi

print_info ""
print_info "The browser will open automatically at http://localhost:$PORT"
print_info "Press Ctrl+C to stop the server"
print_info ""

python3 -m rrc_web.main
