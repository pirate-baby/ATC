#!/usr/bin/env bash
# ATC Development Stop/Cleanup Script
# Tears down Docker resources for the current worktree only
#
# Features:
#   - Dual-filter resource discovery (Docker labels + name patterns)
#   - Cleans up containers, networks, and volumes for current project
#   - Ensures isolation: only affects current project's resources
#   - Safe teardown that doesn't impact other running worktrees
#
# Usage:
#   ./utils/stop.sh           # Stop and clean up current project
#   ./utils/stop.sh --volumes # Also remove volumes (data loss warning)

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

# Parse arguments
REMOVE_VOLUMES=false
for arg in "$@"; do
    case $arg in
        --volumes|-v)
            REMOVE_VOLUMES=true
            ;;
        --help|-h)
            echo "Usage: $0 [OPTIONS]"
            echo ""
            echo "Stop and clean up Docker resources for the current worktree."
            echo ""
            echo "Options:"
            echo "  --volumes, -v  Also remove volumes (WARNING: data loss)"
            echo "  --help, -h     Show this help message"
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
echo -e "${BLUE}ATC Development Cleanup${NC}"
echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""

# Read COMPOSE_PROJECT_NAME from .env
ENV_FILE=".env"
COMPOSE_PROJECT_NAME=""

if [[ -f "$ENV_FILE" ]]; then
    COMPOSE_PROJECT_NAME=$(grep -E "^COMPOSE_PROJECT_NAME=" "$ENV_FILE" 2>/dev/null | cut -d= -f2 || true)
fi

if [[ -z "$COMPOSE_PROJECT_NAME" ]]; then
    echo -e "${RED}ERROR: COMPOSE_PROJECT_NAME not found in .env${NC}"
    echo ""
    echo "Run utils/startup.sh first to configure the environment."
    exit 1
fi

echo -e "Project: ${GREEN}${COMPOSE_PROJECT_NAME}${NC}"
echo ""

# AC-10: Ensure complete network isolation between compose stacks when cleaning up
# Use dual-filter approach: Docker labels (primary) + name patterns (fallback)

# Function to find resources by Docker Compose labels
find_resources_by_label() {
    local resource_type="$1"
    local label_filter="com.docker.compose.project=${COMPOSE_PROJECT_NAME}"

    case "$resource_type" in
        containers)
            docker ps -aq --filter "label=${label_filter}" 2>/dev/null || true
            ;;
        networks)
            docker network ls -q --filter "label=${label_filter}" 2>/dev/null || true
            ;;
        volumes)
            docker volume ls -q --filter "label=${label_filter}" 2>/dev/null || true
            ;;
    esac
}

# Function to find resources by name pattern (fallback)
find_resources_by_name() {
    local resource_type="$1"
    local name_pattern="^${COMPOSE_PROJECT_NAME}[-_]"

    case "$resource_type" in
        containers)
            docker ps -aq --filter "name=${COMPOSE_PROJECT_NAME}" 2>/dev/null || true
            ;;
        networks)
            docker network ls -q --filter "name=${COMPOSE_PROJECT_NAME}" 2>/dev/null || true
            ;;
        volumes)
            docker volume ls -q --filter "name=${COMPOSE_PROJECT_NAME}" 2>/dev/null || true
            ;;
    esac
}

# Function to merge and deduplicate resource lists
merge_resources() {
    local by_label="$1"
    local by_name="$2"

    # Combine, sort, and deduplicate
    echo -e "${by_label}\n${by_name}" | grep -v '^$' | sort -u || true
}

# Discover resources using dual-filter approach
echo -e "${YELLOW}Discovering resources...${NC}"

# Find containers
CONTAINERS_BY_LABEL=$(find_resources_by_label containers)
CONTAINERS_BY_NAME=$(find_resources_by_name containers)
CONTAINERS=$(merge_resources "$CONTAINERS_BY_LABEL" "$CONTAINERS_BY_NAME")

# Find networks
NETWORKS_BY_LABEL=$(find_resources_by_label networks)
NETWORKS_BY_NAME=$(find_resources_by_name networks)
NETWORKS=$(merge_resources "$NETWORKS_BY_LABEL" "$NETWORKS_BY_NAME")

# Find volumes
VOLUMES_BY_LABEL=$(find_resources_by_label volumes)
VOLUMES_BY_NAME=$(find_resources_by_name volumes)
VOLUMES=$(merge_resources "$VOLUMES_BY_LABEL" "$VOLUMES_BY_NAME")

# Count resources (handle empty strings properly)
count_lines() {
    local input="$1"
    if [[ -z "$input" ]]; then
        echo 0
    else
        echo "$input" | wc -l | tr -d ' '
    fi
}

CONTAINER_COUNT=$(count_lines "$CONTAINERS")
NETWORK_COUNT=$(count_lines "$NETWORKS")
VOLUME_COUNT=$(count_lines "$VOLUMES")

echo "  Containers: $CONTAINER_COUNT"
echo "  Networks:   $NETWORK_COUNT"
echo "  Volumes:    $VOLUME_COUNT"
echo ""

# Check if there's anything to clean up
if [[ $CONTAINER_COUNT -eq 0 && $NETWORK_COUNT -eq 0 && $VOLUME_COUNT -eq 0 ]]; then
    echo -e "${GREEN}No resources found for project '${COMPOSE_PROJECT_NAME}'${NC}"
    echo "Nothing to clean up."
    exit 0
fi

# Stop and remove containers
if [[ $CONTAINER_COUNT -gt 0 ]]; then
    echo -e "${YELLOW}Stopping containers...${NC}"

    # First try docker compose down for graceful shutdown
    if docker compose down --remove-orphans 2>/dev/null; then
        echo -e "${GREEN}✓ Containers stopped via docker compose${NC}"
    else
        # Fallback: stop containers individually
        echo "$CONTAINERS" | xargs -r docker stop 2>/dev/null || true
        echo "$CONTAINERS" | xargs -r docker rm -f 2>/dev/null || true
        echo -e "${GREEN}✓ Containers stopped individually${NC}"
    fi
fi

# Remove networks (must happen after containers are removed)
if [[ $NETWORK_COUNT -gt 0 ]]; then
    echo -e "${YELLOW}Removing networks...${NC}"

    for network in $NETWORKS; do
        # Skip default networks
        if [[ "$network" == "bridge" || "$network" == "host" || "$network" == "none" ]]; then
            continue
        fi

        if docker network rm "$network" 2>/dev/null; then
            echo "  Removed: $network"
        else
            echo -e "  ${YELLOW}Skipped: $network (may be in use)${NC}"
        fi
    done

    echo -e "${GREEN}✓ Networks cleaned up${NC}"
fi

# Remove volumes (only if --volumes flag is passed)
if [[ $VOLUME_COUNT -gt 0 ]]; then
    if [[ "$REMOVE_VOLUMES" == "true" ]]; then
        echo -e "${YELLOW}Removing volumes...${NC}"
        echo -e "${RED}WARNING: This will delete all data in these volumes!${NC}"

        for volume in $VOLUMES; do
            if docker volume rm "$volume" 2>/dev/null; then
                echo "  Removed: $volume"
            else
                echo -e "  ${YELLOW}Skipped: $volume (may be in use)${NC}"
            fi
        done

        echo -e "${GREEN}✓ Volumes removed${NC}"
    else
        echo -e "${YELLOW}Volumes preserved (use --volumes to remove)${NC}"
        echo "  Volumes:"
        for volume in $VOLUMES; do
            echo "    - $volume"
        done
    fi
fi

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}✓ Cleanup complete for project '${COMPOSE_PROJECT_NAME}'${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
