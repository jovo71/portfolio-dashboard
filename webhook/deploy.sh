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

echo "[deploy] Frontend bouwen..."
cd "$APP_DIR/frontend"
npm ci --silent
npm run build

echo "[deploy] Backend herstarten..."
systemctl restart portfolio-backend

echo "[deploy] Nginx herstarten..."
systemctl restart nginx

echo "[deploy] Klaar!"
