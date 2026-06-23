#!/bin/bash
# ============================================================
# Installatiescript zonder Docker — Portfolio Dashboard
# Voor gebruik in Proxmox LXC containers
# ============================================================
set -e

APP_DIR="/opt/portfolio-dashboard"

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

# ── 8. Deploy-script activeren ───────────────────────────
# Updates worden via de "App bijwerken"-knop in het dashboard
# gestart (pull vanaf de LXC). Er is geen inkomende webhook
# nodig — dat werkt toch niet achter NAT op een privé-IP.
echo ""
echo "▶ Deploy-script activeren..."
chmod +x "$APP_DIR/webhook/deploy.sh"
echo "✓ Deploy via dashboard-knop beschikbaar"

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
echo "║   Updaten: log in op het dashboard en klik op       ║"
echo "║   'App bijwerken' op de pagina Systeemstatus.       ║"
echo "║   De LXC haalt dan zelf de nieuwste code op.        ║"
echo "║                                                      ║"
echo "╚══════════════════════════════════════════════════════╝"
echo ""
