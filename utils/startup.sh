#!/usr/bin/env bash
# ATC Development Startup Script
# Configures worktree-specific environment for Docker
#
# Features:
#   - Calculates COMPOSE_PROJECT_NAME from sanitized git branch name
#   - Finds lowest available PORT_OFFSET (0-5) not in use by Docker
#   - Persists values to .env for docker-compose
#   - Reuses existing .env values on subsequent runs

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[0;33m'
NC='\033[0m' # No Color

# Change to project root (script directory's parent)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
cd "$PROJECT_ROOT"

echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${BLUE}ATC Development Startup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Check if .env exists and has our values already set
ENV_FILE=".env"
EXISTING_PORT_OFFSET=""
EXISTING_PROJECT_NAME=""

if [[ -f "$ENV_FILE" ]]; then
    # Read existing values
    EXISTING_PORT_OFFSET=$(grep -E "^PORT_OFFSET=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)
    EXISTING_PROJECT_NAME=$(grep -E "^COMPOSE_PROJECT_NAME=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)
fi

# AC-11-env: If .env already has values, use them without re-running
if [[ -n "$EXISTING_PORT_OFFSET" && -n "$EXISTING_PROJECT_NAME" ]]; then
    echo -e "${GREEN}Using existing .env configuration:${NC}"
    echo "  COMPOSE_PROJECT_NAME=${EXISTING_PROJECT_NAME}"
    echo "  PORT_OFFSET=${EXISTING_PORT_OFFSET}"
    echo ""
    export PORT_OFFSET="$EXISTING_PORT_OFFSET"
    export COMPOSE_PROJECT_NAME="$EXISTING_PROJECT_NAME"
    echo -e "${GREEN}✓ Environment ready${NC}"
    exit 0
fi

echo -e "${YELLOW}Calculating new environment configuration...${NC}"
echo ""

# AC-5: Calculate COMPOSE_PROJECT_NAME from sanitized git branch name
# - Remove 'vk/' prefix if present
# - Escape special characters for docker-compose compatibility
BRANCH_NAME=$(git branch --show-current 2>/dev/null || echo "main")
COMPOSE_PROJECT_NAME=$(echo "$BRANCH_NAME" | sed 's|^vk/||' | sed 's|[^a-zA-Z0-9_-]|_|g')

echo "Branch: $BRANCH_NAME"
echo "Project name: $COMPOSE_PROJECT_NAME"

# AC-6: Calculate PORT_OFFSET as first available offset (0-5) not in use
# Scan Docker containers for ports matching pattern ^[0-5][0-9]{4}$
# Our port pattern is: ${PORT_OFFSET}XXXX (e.g., 05432, 18000, 23000)

# Get all ports currently in use by docker containers
used_ports=$(docker ps -q 2>/dev/null | xargs -r -n1 docker port 2>/dev/null | sed -nE 's/.*:([0-9]+)$/\1/p' | sort -n || true)

# Extract port offsets from ports that match our pattern
# Valid patterns: 0XXXX, 1XXXX, 2XXXX, 3XXXX, 4XXXX, 5XXXX
used_offsets=$(echo "$used_ports" | sed -nE 's/^([0-5])[0-9]{4}$/\1/p' | sort -u || true)

# Also check for ports 6XXXX+ which would indicate offset 0 is causing issues
# (since 6XXXX exceeds valid range but might be from other services)

if [[ -n "$used_offsets" ]]; then
    echo "Used port offsets: $(echo $used_offsets | tr '\n' ' ')"
else
    echo "No port offsets currently in use"
fi

# Find the lowest available port offset in the valid range (0-5)
PORT_OFFSET=""
for offset in {0..5}; do
    if ! echo "$used_offsets" | grep -q "^${offset}$"; then
        PORT_OFFSET=$offset
        break
    fi
done

# AC-7: Exit with error if all port offsets (0-5) are in use
if [[ -z "$PORT_OFFSET" ]]; then
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}ERROR: No available port offsets (0-5 all in use)${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Used offsets: $(echo $used_offsets | tr '\n' ' ')"
    echo ""
    echo "To free up a port offset, stop containers from another worktree:"
    echo "  docker compose down"
    exit 1
fi

# AC-9: Exit with error if calculated port would exceed 65535
# With PORT_OFFSET in range 0-5 and base ports like 5432, 8000, 3000
# Maximum port would be 55432 (offset 5 + 5432) which is safe
# However, we validate just in case base ports change
MAX_BASE_PORT=5432  # Highest base port we use
MAX_CALCULATED_PORT=$((PORT_OFFSET * 10000 + MAX_BASE_PORT))

if [[ $MAX_CALCULATED_PORT -gt 65535 ]]; then
    echo ""
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}ERROR: Calculated port would exceed 65535${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "PORT_OFFSET=$PORT_OFFSET would result in port $MAX_CALCULATED_PORT"
    exit 1
fi

echo "Selected PORT_OFFSET: $PORT_OFFSET"
echo ""

# Update or create .env file with calculated values
if [[ -f "$ENV_FILE" ]]; then
    # Set up trap to ensure .env.bak is always cleaned up
    trap 'rm -f .env.bak 2>/dev/null || true' EXIT

    # Ensure .env ends with a newline before appending
    if [[ -n "$(tail -c 1 "$ENV_FILE" 2>/dev/null)" ]]; then
        echo "" >> "$ENV_FILE"
    fi

    # Update or add COMPOSE_PROJECT_NAME
    if grep -q "^COMPOSE_PROJECT_NAME=" "$ENV_FILE"; then
        sed -i.bak "s/^COMPOSE_PROJECT_NAME=.*/COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}/" "$ENV_FILE"
        rm -f .env.bak
    else
        echo "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" >> "$ENV_FILE"
    fi

    # Update or add PORT_OFFSET
    if grep -q "^PORT_OFFSET=" "$ENV_FILE"; then
        sed -i.bak "s/^PORT_OFFSET=.*/PORT_OFFSET=${PORT_OFFSET}/" "$ENV_FILE"
        rm -f .env.bak
    else
        echo "PORT_OFFSET=${PORT_OFFSET}" >> "$ENV_FILE"
    fi

    echo -e "${GREEN}Updated .env with configuration${NC}"
else
    # Create new .env file from .env.example if it exists
    if [[ -f ".env.example" ]]; then
        cp .env.example "$ENV_FILE"
        echo "COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}" >> "$ENV_FILE"
        echo "PORT_OFFSET=${PORT_OFFSET}" >> "$ENV_FILE"
        echo -e "${GREEN}Created .env from .env.example${NC}"
    else
        # Create minimal .env
        cat > "$ENV_FILE" << EOF
# ATC Development Environment Configuration
# Auto-generated by utils/startup.sh

COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}
PORT_OFFSET=${PORT_OFFSET}
EOF
        echo -e "${GREEN}Created new .env file${NC}"
    fi
fi

# Export for current shell session
export PORT_OFFSET
export COMPOSE_PROJECT_NAME

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Environment configured${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo "  COMPOSE_PROJECT_NAME=${COMPOSE_PROJECT_NAME}"
echo "  PORT_OFFSET=${PORT_OFFSET}"
echo ""
echo "Port mappings:"
echo "  PostgreSQL: ${PORT_OFFSET}5432"
echo "  Backend:    ${PORT_OFFSET}8000"
echo "  Frontend:   ${PORT_OFFSET}3000"
echo "  Nginx:      ${PORT_OFFSET}80"
echo ""
