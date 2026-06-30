#!/bin/bash
# ============================================================
# Native deploy-script voor de Portfolio Dashboard LXC.
# Haalt de nieuwste code op, bouwt de frontend en herstart
# de services. Wordt aangeroepen vanuit de "Bijwerken"-knop
# in het dashboard (via systemd-run) of handmatig.
# ============================================================
set -e

APP_DIR="${APP_DIR:-/opt/portfolio-dashboard}"
BRANCH="${BRANCH:-main}"

echo "[deploy] Nieuwste code ophalen (git pull origin $BRANCH)..."
git -C "$APP_DIR" pull origin "$BRANCH"

echo "[deploy] Backend dependencies bijwerken..."
"$APP_DIR/backend/venv/bin/pip" install -q -r "$APP_DIR/backend/requirements.txt"

echo "[deploy] Frontend bouwen..."
cd "$APP_DIR/frontend"
npm ci --silent
npm run build

echo "[deploy] Backend herstarten..."
# Marker achterlaten zodat de backend bij het opstarten een
# "deploy voltooid"-logregel met de nieuwe versie kan schrijven.
mkdir -p "$APP_DIR/data"
touch "$APP_DIR/data/.deploy_completed"
systemctl restart portfolio-backend

echo "[deploy] Nginx herstarten..."
systemctl restart nginx

echo "[deploy] Klaar!"
