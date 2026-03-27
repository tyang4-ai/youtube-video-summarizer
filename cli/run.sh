#!/bin/bash
cd "$(dirname "$0")"

# Create venv if needed
if [ ! -d ".venv" ]; then
    echo "Setting up virtual environment..."
    python -m venv .venv
    source .venv/Scripts/activate || source .venv/bin/activate
    pip install -r requirements.txt
else
    source .venv/Scripts/activate || source .venv/bin/activate
fi

python summarizer.py
