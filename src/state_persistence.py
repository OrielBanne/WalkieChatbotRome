"""Persist and restore app state across browser refreshes."""

import json
import os
from pathlib import Path
from typing import Optional
from src.agents.models import Itinerary
from src.logging_config import get_logger

logger = get_logger(__name__)

STATE_DIR = Path("sessions")
STATE_FILE_PREFIX = "app_state_user_"


def _state_path(user_id: str) -> Path:
    STATE_DIR.mkdir(exist_ok=True)
    return STATE_DIR / f"{STATE_FILE_PREFIX}{user_id}.json"


def save_app_state(user_id: str, planned_itinerary: Optional[Itinerary],
                   visited_places: list, messages: list):
    """Save critical app state to disk, keyed by user_id so it survives session rotation."""
    try:
        data = {
            "visited_places": visited_places,
            "messages": messages,
            "planned_itinerary": planned_itinerary.model_dump(mode="json") if planned_itinerary else None,
        }
        path = _state_path(user_id)
        path.write_text(json.dumps(data, default=str), encoding="utf-8")
    except Exception as e:
        logger.warning(f"Failed to save app state: {e}")


def load_app_state(user_id: str) -> Optional[dict]:
    """Load app state from disk. Returns dict with keys or None."""
    try:
        path = _state_path(user_id)
        if not path.exists():
            return None
        data = json.loads(path.read_text(encoding="utf-8"))
        # Rehydrate itinerary
        if data.get("planned_itinerary"):
            data["planned_itinerary"] = Itinerary.model_validate(data["planned_itinerary"])
        return data
    except Exception as e:
        logger.warning(f"Failed to load app state: {e}")
        return None
