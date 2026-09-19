#!/usr/bin/env bash
# Build script for Render deployment
# This runs during the "Build Command" phase

set -o errexit  # exit on error

echo "==> Installing Python dependencies..."
pip install --upgrade pip
pip install -r requirements.txt

echo "==> Building React frontend..."
cd frontend
npm install
npm run build
cd ..

echo "==> Build complete!"
