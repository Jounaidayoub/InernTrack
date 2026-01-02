#!/usr/bin/bash
set -e

# Get the project root directory (parent of scripts/)
PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$PROJECT_ROOT"

echo "Running backup..."
make backup

echo "Running scrape..."
make scrape
