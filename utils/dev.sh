#!/usr/bin/env bash
# ATC Development Convenience Script
# Combines startup configuration and docker compose for easy development
#
# Features:
#   - Ensures environment is configured (runs startup.sh)
#   - Starts all core services via docker compose
#   - Displays the React home page URL with the correct port
#
# Usage:
#   ./utils/dev.sh              # Start development environment
#   ./utils/dev.sh --build      # Rebuild containers before starting
#   ./utils/dev.sh --detach     # Run in detached mode

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Change to project root (script directory's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

# Parse arguments
BUILD_FLAG=""
DETACH_FLAG=""
for arg in "$@"; do
    case $arg in
        --build|-b)
            BUILD_FLAG="--build"
            ;;
        --detach|-d)
            DETACH_FLAG="--detach"
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Start the ATC development environment."
            echo ""
            echo "Options:"
            echo "  --build, -b   Rebuild containers before starting"
            echo "  --detach, -d  Run containers in detached mode"
            echo "  --help, -h    Show this help message"
            exit 0
            ;;
        *)
            echo -e "${RED}Unknown argument: $arg${NC}"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}ATC Development Environment${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Step 1: Run startup.sh to ensure environment is configured
echo -e "${YELLOW}Ensuring environment is configured...${NC}"
"$SCRIPT_DIR/startup.sh"

# Read configuration from .env
ENV_FILE=".env"
if [[ ! -f "$ENV_FILE" ]]; then
    echo -e "${RED}ERROR: .env file not found after running startup.sh${NC}"
    exit 1
fi

PORT_OFFSET=$(grep -E "^PORT_OFFSET=" "$ENV_FILE" | cut -d= -f2)
COMPOSE_PROJECT_NAME=$(grep -E "^COMPOSE_PROJECT_NAME=" "$ENV_FILE" | cut -d= -f2)

if [[ -z "$PORT_OFFSET" || -z "$COMPOSE_PROJECT_NAME" ]]; then
    echo -e "${RED}ERROR: PORT_OFFSET or COMPOSE_PROJECT_NAME not found in .env${NC}"
    exit 1
fi

# Export for docker compose
export PORT_OFFSET
export COMPOSE_PROJECT_NAME

# Calculate the frontend port
FRONTEND_PORT="${PORT_OFFSET}3000"

echo ""
echo -e "${YELLOW}Starting Docker Compose services...${NC}"
echo -e "  Project: ${GREEN}${COMPOSE_PROJECT_NAME}${NC}"
echo ""

# Step 2: Start docker compose
# Build the command with optional flags
COMPOSE_CMD="docker compose up"
if [[ -n "$BUILD_FLAG" ]]; then
    COMPOSE_CMD="$COMPOSE_CMD $BUILD_FLAG"
fi
if [[ -n "$DETACH_FLAG" ]]; then
    COMPOSE_CMD="$COMPOSE_CMD $DETACH_FLAG"
fi

# Display the URL before starting (useful for detached mode)
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${CYAN}React App URL:${NC} ${GREEN}http://localhost:${FRONTEND_PORT}${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "${YELLOW}Starting services (Ctrl+C to stop)...${NC}"
echo ""

# Run docker compose
eval "$COMPOSE_CMD"
