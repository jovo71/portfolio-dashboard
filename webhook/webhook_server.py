#!/usr/bin/env python3
"""
GitHub Webhook Server voor automatische deployments.
Luistert naar push events van GitHub en voert het deploy-script uit
(git pull, frontend bouwen en de systemd-services herstarten).
"""
import hmac
import hashlib
import subprocess
import logging
import os
from http.server import HTTPServer, BaseHTTPRequestHandler

# Configuratie
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "verander-dit-geheim")
APP_DIR = os.getenv("APP_DIR", "/opt/portfolio-dashboard")
PORT = int(os.getenv("WEBHOOK_PORT", "9000"))
BRANCH = os.getenv("BRANCH", "main")

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        logging.FileHandler("/var/log/webhook.log"),
        logging.StreamHandler(),
    ]
)
log = logging.getLogger(__name__)


def verify_signature(payload: bytes, signature: str) -> bool:
    """Controleer of het verzoek echt van GitHub komt."""
    expected = "sha256=" + hmac.new(
        WEBHOOK_SECRET.encode(), payload, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


def deploy():
    """Voer het native deploy-script uit (git pull, frontend bouwen, services herstarten)."""
    log.info("Deploy gestart...")
    deploy_script = os.path.join(APP_DIR, "webhook", "deploy.sh")
    log.info(f"Uitvoeren: {deploy_script}")
    result = subprocess.run(
        ["bash", deploy_script], capture_output=True, text=True
    )
    if result.stdout:
        log.info(result.stdout)
    if result.stderr:
        log.warning(result.stderr)
    if result.returncode != 0:
        log.error(f"Deploy-script mislukt met code {result.returncode}")
        return False
    log.info("Deploy succesvol afgerond!")
    return True


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        if self.path != "/webhook":
            self.send_response(404)
            self.end_headers()
            return

        length = int(self.headers.get("Content-Length", 0))
        payload = self.rfile.read(length)

        # Handtekening controleren
        signature = self.headers.get("X-Hub-Signature-256", "")
        if not verify_signature(payload, signature):
            log.warning("Ongeldige handtekening — verzoek afgewezen")
            self.send_response(403)
            self.end_headers()
            self.wfile.write(b"Verboden")
            return

        # Alleen reageren op push events
        event = self.headers.get("X-GitHub-Event", "")
        if event != "push":
            self.send_response(200)
            self.end_headers()
            self.wfile.write(b"Genegeerd")
            return

        self.send_response(200)
        self.end_headers()
        self.wfile.write(b"Deploy gestart")

        deploy()

    def log_message(self, format, *args):
        log.info(f"{self.address_string()} - {format % args}")


if __name__ == "__main__":
    log.info(f"Webhook server gestart op poort {PORT}")
    log.info(f"App map: {APP_DIR}")
    log.info(f"Branch: {BRANCH}")
    server = HTTPServer(("0.0.0.0", PORT), WebhookHandler)
    server.serve_forever()
