"""
Settings Router — Persistent storage for AI and RAG configurations.
"""

import structlog
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Any

from app.database.postgres import get_session, SystemSettings

logger = structlog.get_logger()

router = APIRouter(prefix="/api/settings", tags=["Settings"])


class SettingsUpdate(BaseModel):
    key: str
    value: Any


@router.get("/")
async def get_all_settings():
    """Get all persistent system settings."""
    try:
        session = get_session()
        records = session.query(SystemSettings).all()
        session.close()
        return {r.key: r.value for r in records}
    except Exception as e:
        logger.error("get_settings_error", error=str(e))
        return {}


@router.get("/{key}")
async def get_setting(key: str):
    """Get a specific setting by key."""
    session = get_session()
    record = session.query(SystemSettings).filter(SystemSettings.key == key).first()
    session.close()
    if not record:
        raise HTTPException(status_code=404, detail="Setting not found")
    return record.value


@router.post("/")
async def save_setting(update: SettingsUpdate):
    """Save or update a system setting."""
    try:
        session = get_session()
        record = session.query(SystemSettings).filter(SystemSettings.key == update.key).first()
        
        if record:
            record.value = update.value
        else:
            record = SystemSettings(key=update.key, value=update.value)
            session.add(record)
            
        session.commit()
        session.close()
        logger.info("setting_saved", key=update.key)
        return {"status": "ok"}
    except Exception as e:
        logger.error("save_setting_error", error=str(e))
        raise HTTPException(status_code=500, detail=str(e))
