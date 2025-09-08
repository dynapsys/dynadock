#!/usr/bin/env bash
# Bumps version, builds, commits, tags, and publishes to PyPI.
set -euo pipefail

# Define colors for output
RED='\033[0;31m'
YELLOW='\033[0;33m'
GREEN='\033[0;32m'
NC='\033[0m' # No Color

# --- Pre-flight checks ---
if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then
    echo -e "${RED}Not on main branch. Please switch to main before publishing.${NC}"
    exit 1
fi

if [ -n "$(git status --porcelain)" ]; then
    echo -e "${RED}Git working directory is not clean. Please commit or stash changes.${NC}"
    git status --porcelain
    exit 1
fi

# --- Version bump ---
echo -e "${YELLOW}Bumping patch version...${NC}"
CURRENT_VERSION=$(awk -F\" '/^__version__/ {print $2}' src/dynadock/__init__.py)
NEW_VERSION=$(echo "$CURRENT_VERSION" | awk -F. -v OFS=. '{$3++; print}')

echo "Bumping version from $CURRENT_VERSION to $NEW_VERSION"
sed -i "s/__version__ = \"$CURRENT_VERSION\"/__version__ = \"$NEW_VERSION\"/" src/dynadock/__init__.py
sed -i "s/version = \"$CURRENT_VERSION\"/version = \"$NEW_VERSION\"/" pyproject.toml

# --- Build and check distribution ---
echo -e "${YELLOW}Building and checking distribution...${NC}"
make build-dist
make check-dist

# --- Git operations ---
NEW_VERSION_TAG="v$NEW_VERSION"
echo -e "${YELLOW}Committing version bump...${NC}"
git commit -am "chore: Bump version to $NEW_VERSION_TAG"

echo -e "${YELLOW}Tagging new version $NEW_VERSION_TAG...${NC}"
git tag "$NEW_VERSION_TAG"

echo -e "${YELLOW}Pushing commit and tags...${NC}"
git push && git push --tags

# --- PyPI Upload ---
echo -e "${YELLOW}Publishing to PyPI...${NC}"
uv run --with twine twine upload dist/*

echo -e "${GREEN}✓ Successfully published version $NEW_VERSION to PyPI!${NC}"
