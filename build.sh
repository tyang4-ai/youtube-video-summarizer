#!/bin/bash
set -e
cd frontend && npm install && npm run build
mkdir -p ../backend/app/static
cp -r dist/* ../backend/app/static/
echo "Frontend built and copied to backend/app/static/"
