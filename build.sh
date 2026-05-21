#!/usr/bin/env bash
# Cloud build script — runs on Railway / Render / any Linux host.
# Builds the React frontend and outputs it into backend/static/,
# then installs Python dependencies.
set -e

echo "──────────────────────────────────────"
echo " Step 1/3  Frontend (React + Vite)"
echo "──────────────────────────────────────"
cd frontend
npm install
npm run build          # outputs to ../backend/static  (see vite.config.js)
cd ..

echo "──────────────────────────────────────"
echo " Step 2/3  Backend (Python deps)"
echo "──────────────────────────────────────"
cd backend
python3 -m pip install -r requirements.txt

echo "──────────────────────────────────────"
echo " Step 3/3  Playwright (Chromium)"
echo "──────────────────────────────────────"
playwright install chromium --with-deps

echo ""
echo "Build complete. Static files are in backend/static/"
ls -lh static/
