"""Systeemstatus API endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.database import get_db
from app.auth import get_current_user
from app.models import SystemLog
from app.services.price_service import get_stats
from app.services.scheduler import is_running

router = APIRouter()


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
