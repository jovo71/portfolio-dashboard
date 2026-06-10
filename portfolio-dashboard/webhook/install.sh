#!/bin/bash
# ============================================================
# InstallatieScript — Portfolio Dashboard op Proxmox
# Uitvoeren als root op uw Ubuntu VM/LXC
# Gebruik: bash install.sh
# ============================================================
set -e

REPO_URL="https://github.com/jovo71/portfolio-dashboard.git"
APP_DIR="/opt/portfolio-dashboard"
WEBHOOK_DIR="/opt/webhook"
WEBHOOK_PORT="9000"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Portfolio Dashboard — Installatie      ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Systeem bijwerken ──────────────────────────────────
echo "▶ Systeem bijwerken..."
apt-get update -qq
apt-get install -y -qq git curl python3 python3-pip

# ── 2. Docker installeren ─────────────────────────────────
if ! command -v docker &> /dev/null; then
    echo "▶ Docker installeren..."
    curl -fsSL https://get.docker.com | sh
    systemctl enable docker
    systemctl start docker
else
    echo "✓ Docker al geïnstalleerd"
fi

# ── 3. Repository klonen ──────────────────────────────────
echo "▶ Repository klonen..."
if [ -d "$APP_DIR" ]; then
    echo "  Map bestaat al, git pull uitvoeren..."
    git -C "$APP_DIR" pull origin main
else
    git clone "$REPO_URL" "$APP_DIR"
fi

# ── 4. Configuratie instellen ─────────────────────────────
echo ""
echo "▶ Inloggegevens instellen..."
mkdir -p "$APP_DIR/config"

read -p "  Gebruikersnaam dashboard [admin]: " USERNAME
USERNAME=${USERNAME:-admin}

read -s -p "  Wachtwoord dashboard: " PASSWORD
echo ""

cat > "$APP_DIR/config/auth.yaml" << EOF
username: $USERNAME
password: $PASSWORD
EOF
echo "✓ Inloggegevens opgeslagen"

# ── 5. Webhook secret genereren ───────────────────────────
WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")
echo ""
echo "▶ Webhook geheim gegenereerd"

# ── 6. Webhook server installeren ────────────────────────
echo "▶ Webhook server installeren..."
mkdir -p "$WEBHOOK_DIR"
cp "$APP_DIR/webhook/webhook_server.py" "$WEBHOOK_DIR/"

# Systemd service aanmaken
cat > /etc/systemd/system/portfolio-webhook.service << EOF
[Unit]
Description=GitHub Webhook Server voor Portfolio Dashboard
After=network.target docker.service
Requires=docker.service

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 $WEBHOOK_DIR/webhook_server.py
Restart=always
RestartSec=5
Environment="WEBHOOK_SECRET=$WEBHOOK_SECRET"
Environment="APP_DIR=$APP_DIR"
Environment="WEBHOOK_PORT=$WEBHOOK_PORT"
Environment="BRANCH=main"

[Install]
WantedBy=multi-user.target
EOF

systemctl daemon-reload
systemctl enable portfolio-webhook
systemctl start portfolio-webhook
echo "✓ Webhook service actief"

# ── 7. Applicatie starten ─────────────────────────────────
echo "▶ Portfolio Dashboard starten..."
cd "$APP_DIR"
docker compose up -d
echo "✓ Applicatie gestart"

# ── 8. Voorbeelddata laden (optioneel) ────────────────────
echo ""
read -p "▶ Voorbeelddata laden? (j/n) [n]: " SEED
if [[ "$SEED" == "j" || "$SEED" == "J" ]]; then
    docker compose exec backend python seed_data.py
    echo "✓ Voorbeelddata geladen"
fi

# ── Samenvatting ──────────────────────────────────────────
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅ Installatie voltooid!                           ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
echo "║   Dashboard:  http://$IP                      "
echo "║   API docs:   http://$IP:8000/docs             "
echo "║                                                      ║"
echo "║   Webhook URL voor GitHub:                          ║"
echo "║   http://$IP:$WEBHOOK_PORT/webhook              "
echo "║                                                      ║"
echo "║   Webhook Secret (bewaar dit!):                     ║"
echo "║   $WEBHOOK_SECRET  "
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
echo "Stel de webhook in op GitHub:"
echo "  Repository → Settings → Webhooks → Add webhook"
echo "  Payload URL: http://$IP:$WEBHOOK_PORT/webhook"
echo "  Content type: application/json"
echo "  Secret: $WEBHOOK_SECRET"
echo "  Event: Just the push event"
echo ""
