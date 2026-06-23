"""Systeemstatus API endpoints."""
import os
import time
import subprocess

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import SystemLog
from app.services.price_service import get_stats
from app.services.scheduler import is_running

router = APIRouter()

APP_DIR = os.getenv("APP_DIR", "/opt/portfolio-dashboard")
BRANCH = os.getenv("BRANCH", "main")


@router.get("/status")
def get_system_status(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Systeem- en schedulerstatus."""
    stats = get_stats()
    
    last_log = (
        db.query(SystemLog)
        .order_by(SystemLog.timestamp.desc())
        .first()
    )
    
    recent_logs = (
        db.query(SystemLog)
        .order_by(SystemLog.timestamp.desc())
        .limit(20)
        .all()
    )
    
    return {
        "scheduler_running": is_running(),
        "last_update": stats.get("last_update"),
        "successful_updates": stats.get("successful_updates", 0),
        "failed_updates": stats.get("failed_updates", 0),
        "api_status": "online",
        "last_log": {
            "timestamp": last_log.timestamp,
            "event_type": last_log.event_type,
            "message": last_log.message,
        } if last_log else None,
        "recent_logs": [
            {
                "timestamp": log.timestamp,
                "event_type": log.event_type,
                "message": log.message,
            }
            for log in recent_logs
        ],
    }


def _git(*args: str, timeout: int = 30) -> subprocess.CompletedProcess:
    """Voer een git-commando uit binnen de app-map."""
    return subprocess.run(
        ["git", "-C", APP_DIR, *args],
        capture_output=True, text=True, timeout=timeout,
    )


@router.get("/version")
def get_version(user: str = Depends(get_current_user)):
    """Huidige versie en of er een update beschikbaar is op de remote."""
    try:
        current = _git("rev-parse", "--short", "HEAD").stdout.strip()
        # Haal de laatste remote-status op zonder iets te wijzigen
        _git("fetch", "origin", BRANCH, timeout=30)
        behind = _git("rev-list", "--count", f"HEAD..origin/{BRANCH}").stdout.strip()
        last_msg = _git("log", "-1", "--pretty=%s").stdout.strip()
        return {
            "current_commit": current,
            "branch": BRANCH,
            "commits_behind": int(behind) if behind.isdigit() else 0,
            "update_available": behind.isdigit() and int(behind) > 0,
            "last_commit_message": last_msg,
        }
    except (subprocess.SubprocessError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Versiecontrole mislukt: {e}")


@router.post("/deploy")
def trigger_deploy(db: Session = Depends(get_db), user: str = Depends(get_current_user)):
    """Start een deploy: haalt nieuwe code op, bouwt de frontend en herstart de services.

    Wordt als losse systemd-unit gestart (systemd-run) zodat het script de
    herstart van de backend zelf overleeft.
    """
    deploy_script = os.path.join(APP_DIR, "webhook", "deploy.sh")
    if not os.path.exists(deploy_script):
        raise HTTPException(status_code=500, detail=f"Deploy-script niet gevonden: {deploy_script}")

    # Logregel vastleggen vóór de herstart, zodat deze in SQLite bewaard blijft.
    try:
        current = _git("rev-parse", "--short", "HEAD").stdout.strip()
    except (subprocess.SubprocessError, OSError):
        current = "onbekend"
    log = SystemLog(
        event_type="deploy_started",
        message=f"Systeemupdate gestart via dashboard (huidige versie: {current})",
        details=f"door gebruiker: {user}",
    )
    db.add(log)
    db.commit()

    unit_name = f"portfolio-deploy-{int(time.time())}"
    try:
        result = subprocess.run(
            ["systemd-run", "--unit", unit_name, "--collect", "bash", deploy_script],
            capture_output=True, text=True, timeout=15,
        )
    except (subprocess.SubprocessError, OSError) as e:
        raise HTTPException(status_code=500, detail=f"Deploy starten mislukt: {e}")

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=f"Deploy starten mislukt: {result.stderr.strip()}")

    return {"status": "started", "unit": unit_name}
