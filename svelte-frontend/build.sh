#!/bin/bash
# Build script for frontend

set -e

echo "Building frontend..."

cd "$(dirname "$0")"

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
    echo "Installing dependencies..."
    npm install
fi

# Build the production bundle
echo "Building production bundle..."
npm run build

echo "Build complete! Output is in ../rrc_web/static-svelte/"
