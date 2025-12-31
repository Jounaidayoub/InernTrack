#!/usr/bin/bash
set -e

echo "Installing dependencies..."
python -m pip install -r requirements.txt

echo "Running internship sync pipeline..."
PYTHONPATH=. python -m src.main