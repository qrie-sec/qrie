#!/bin/bash
# Git Subtree Sync Helper
# Usage: ./tools/git-sync.sh [pull|push] [infra|ui|lp|all]

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

cd "$REPO_ROOT"

# Remote configurations
declare -A REMOTES=(
    ["infra"]="infra-origin"
    ["ui"]="ui-origin"
    ["lp"]="lp-origin"
)

declare -A PREFIXES=(
    ["infra"]="qrie-infra"
    ["ui"]="qrie-ui"
    ["lp"]="qrie-lp"
)

declare -A BRANCHES=(
    ["infra"]="main"
    ["ui"]="main"
    ["lp"]="main"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

usage() {
    echo "Usage: $0 [pull|push] [infra|ui|lp|all]"
    echo ""
    echo "Examples:"
    echo "  $0 pull ui          # Pull changes from qrie-ui repo"
    echo "  $0 push infra       # Push qrie-infra changes to its repo"
    echo "  $0 push all         # Push all components to their repos"
    echo "  $0 pull all         # Pull all components from their repos"
    exit 1
}

sync_component() {
    local action=$1
    local component=$2
    local remote=${REMOTES[$component]}
    local prefix=${PREFIXES[$component]}
    local branch=${BRANCHES[$component]}

    echo -e "${YELLOW}==> ${action^}ing $component ($prefix)...${NC}"

    if [ "$action" = "pull" ]; then
        git subtree pull --prefix="$prefix" "$remote" "$branch" --squash
    elif [ "$action" = "push" ]; then
        git subtree push --prefix="$prefix" "$remote" "$branch"
    fi

    echo -e "${GREEN}✓ $component ${action} complete${NC}"
    echo ""
}

# Parse arguments
ACTION=$1
COMPONENT=$2

if [ -z "$ACTION" ] || [ -z "$COMPONENT" ]; then
    usage
fi

if [ "$ACTION" != "pull" ] && [ "$ACTION" != "push" ]; then
    echo -e "${RED}Error: Action must be 'pull' or 'push'${NC}"
    usage
fi

# Check for uncommitted changes
if [ "$ACTION" = "pull" ] && [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Error: You have uncommitted changes. Commit or stash them first.${NC}"
    exit 1
fi

# Sync components
if [ "$COMPONENT" = "all" ]; then
    for comp in infra ui lp; do
        sync_component "$ACTION" "$comp"
    done
else
    if [ -z "${REMOTES[$COMPONENT]}" ]; then
        echo -e "${RED}Error: Unknown component '$COMPONENT'${NC}"
        echo "Valid components: infra, ui, lp, all"
        exit 1
    fi
    sync_component "$ACTION" "$COMPONENT"
fi

echo -e "${GREEN}✓ All sync operations complete${NC}"

if [ "$ACTION" = "pull" ]; then
    echo -e "${YELLOW}Don't forget to push to monorepo: git push origin main${NC}"
fi
