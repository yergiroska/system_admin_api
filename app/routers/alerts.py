from fastapi import APIRouter, Request, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.database import get_db
from datetime import datetime
import logging
import asyncio

logger = logging.getLogger("system-admin-api")
router = APIRouter(prefix="/alerts", tags=["Alerts"])


@router.post("/webhook")
async def receive_alert(request: Request, db: Session = Depends(get_db)):
    body = await request.json()

    for alert in body.get("alerts", []):
        status = alert.get("status", "unknown")
        alert_name = alert.get("labels", {}).get("alertname", "unknown")
        severity = alert.get("labels", {}).get("severity", "info")
        message = alert.get("annotations", {}).get("summary", "Sin mensaje")
        fired_at_str = alert.get("startsAt", None)

        fired_at = None
        if fired_at_str:
            try:
                fired_at = datetime.fromisoformat(fired_at_str.replace("Z", "+00:00"))
            except:
                fired_at = datetime.now()

        db.execute(
            text("""
                 INSERT INTO alerts (alert_name, status, severity, message, fired_at)
                 VALUES (:alert_name, :status, :severity, :message, :fired_at)
                 """),
            {
                "alert_name": alert_name,
                "status": status,
                "severity": severity,
                "message": message,
                "fired_at": fired_at
            }
        )

    db.commit()
    logger.info(f"Alerta recibida: {body.get('title', 'sin título')}")

    return {"status": "ok"}

@router.get("/test-latency")
async def test_latency():
    await asyncio.sleep(3)  # Simula 1 segundo de latencia
    return {"message": "respuesta lenta"}