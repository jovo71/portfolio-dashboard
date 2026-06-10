#!/bin/bash
# ============================================================
# Installatiescript zonder Docker — Portfolio Dashboard
# Voor gebruik in Proxmox LXC containers
# ============================================================
set -e

APP_DIR="/opt/portfolio-dashboard"
WEBHOOK_PORT="9000"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║   Portfolio Dashboard — Installatie      ║"
echo "║   (zonder Docker, voor LXC containers)   ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── 1. Systeem bijwerken ──────────────────────────────────
echo "▶ Systeem bijwerken..."
apt-get update -qq
apt-get install -y -qq git curl python3 python3-pip python3-venv nodejs npm nginx

# ── 2. Nieuwere Node.js installeren ──────────────────────
echo "▶ Node.js 20 installeren..."
curl -fsSL https://deb.nodesource.com/setup_20.x | bash -
apt-get install -y nodejs

# ── 3. Repository klonen ──────────────────────────────────
echo "▶ Repository klonen..."
if [ -d "$APP_DIR" ]; then
    echo "  Map bestaat al, git pull uitvoeren..."
    git -C "$APP_DIR" pull origin main
else
    git clone https://github.com/jovo71/portfolio-dashboard.git "$APP_DIR"
fi

# ── 4. Inloggegevens instellen ────────────────────────────
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

# ── 5. Backend installeren ────────────────────────────────
echo ""
echo "▶ Backend (Python) installeren..."
cd "$APP_DIR/backend"
python3 -m venv venv
source venv/bin/activate
pip install -q -r requirements.txt
deactivate

# Systemd service voor backend
cat > /etc/systemd/system/portfolio-backend.service << EOF
[Unit]
Description=Portfolio Dashboard Backend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=$APP_DIR/backend
Environment="DATABASE_URL=sqlite:////opt/portfolio-dashboard/data/portfolio.db"
Environment="SECRET_KEY=$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
Environment="UPDATE_TIME_1=08:00"
Environment="UPDATE_TIME_2=13:00"
Environment="AUTH_CONFIG_PATH=$APP_DIR/config/auth.yaml"
ExecStart=$APP_DIR/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

mkdir -p /opt/portfolio-dashboard/data
systemctl daemon-reload
systemctl enable portfolio-backend
systemctl start portfolio-backend
echo "✓ Backend gestart op poort 8000"

# ── 6. Frontend bouwen ────────────────────────────────────
echo ""
echo "▶ Frontend bouwen..."
cd "$APP_DIR/frontend"
npm ci --silent
npm run build
echo "✓ Frontend gebouwd"

# ── 7. Nginx instellen ────────────────────────────────────
echo ""
echo "▶ Nginx instellen..."
cat > /etc/nginx/sites-available/portfolio << 'EOF'
server {
    listen 80;
    server_name _;
    root /opt/portfolio-dashboard/frontend/dist;
    index index.html;

    location / {
        try_files $uri $uri/ /index.html;
    }

    location /api/ {
        proxy_pass http://127.0.0.1:8000/api/;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
EOF

ln -sf /etc/nginx/sites-available/portfolio /etc/nginx/sites-enabled/
rm -f /etc/nginx/sites-enabled/default
systemctl restart nginx
systemctl enable nginx
echo "✓ Nginx geconfigureerd"

# ── 8. Webhook service installeren ───────────────────────
echo ""
echo "▶ Webhook server installeren..."
WEBHOOK_SECRET=$(python3 -c "import secrets; print(secrets.token_hex(32))")

cat > /etc/systemd/system/portfolio-webhook.service << EOF
[Unit]
Description=GitHub Webhook Server
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/bin/python3 $APP_DIR/webhook/webhook_server.py
Restart=always
RestartSec=5
Environment="WEBHOOK_SECRET=$WEBHOOK_SECRET"
Environment="APP_DIR=$APP_DIR"
Environment="WEBHOOK_PORT=$WEBHOOK_PORT"
Environment="BRANCH=main"

[Install]
WantedBy=multi-user.target
EOF

# Webhook update script aanpassen (geen Docker)
cat > "$APP_DIR/webhook/deploy.sh" << 'DEPLOY'
#!/bin/bash
cd /opt/portfolio-dashboard
git pull origin main

# Backend herstarten
systemctl restart portfolio-backend

# Frontend opnieuw bouwen
cd /opt/portfolio-dashboard/frontend
npm ci --silent
npm run build

systemctl restart nginx
echo "Deploy klaar!"
DEPLOY
chmod +x "$APP_DIR/webhook/deploy.sh"

systemctl daemon-reload
systemctl enable portfolio-webhook
systemctl start portfolio-webhook
echo "✓ Webhook service gestart op poort $WEBHOOK_PORT"

# ── 9. Voorbeelddata laden ────────────────────────────────
echo ""
read -p "▶ Voorbeelddata laden? (j/n) [n]: " SEED
if [[ "$SEED" == "j" || "$SEED" == "J" ]]; then
    cd "$APP_DIR/backend"
    source venv/bin/activate
    python seed_data.py
    deactivate
    echo "✓ Voorbeelddata geladen"
fi

# ── Samenvatting ──────────────────────────────────────────
IP=$(hostname -I | awk '{print $1}')

echo ""
echo "╔══════════════════════════════════════════════════════╗"
echo "║   ✅ Installatie voltooid!                           ║"
echo "╠══════════════════════════════════════════════════════╣"
echo "║                                                      ║"
printf "║   Dashboard:  http://%-32s║\n" "$IP"
printf "║   API docs:   http://%-32s║\n" "$IP:8000/docs"
echo "║                                                      ║"
echo "║   Webhook URL voor GitHub:                          ║"
printf "║   http://%-43s║\n" "$IP:$WEBHOOK_PORT/webhook"
echo "║                                                      ║"
echo "║   Webhook Secret (bewaar dit!):                     ║"
printf "║   %-51s║\n" "$WEBHOOK_SECRET"
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
