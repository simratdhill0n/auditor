# Database service - local stand-in until Person 3 wires DynamoDB
"""Store and fetch analysis history.
I used temperory local memory for the testing puposes, you can change this as this is required from your part
"""

from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timezone
from threading import Lock
from uuid import uuid4

_lock = Lock()
_analyses: list[dict] = []


def clear_all() -> None:
    """Test helper — wipe in-memory history."""
    with _lock:
        _analyses.clear()


def save_analysis(
    *,
    user_id: str,
    prompt: str,
    analysis: str,
    keyword: str | None = None,
    dataset_id: str | None = None,
    datasets_used: list | dict | None = None,
) -> dict:
    """Persist one analysis and return the saved record."""
    if not user_id or not str(user_id).strip():
        raise ValueError("user_id is required")
    if not prompt or not str(prompt).strip():
        raise ValueError("prompt is required")
    if analysis is None:
        raise ValueError("analysis is required")

    record = {
        "id": str(uuid4()),
        "user_id": str(user_id).strip(),
        "prompt": str(prompt).strip(),
        "analysis": analysis,
        "keyword": keyword,
        "dataset_id": dataset_id,
        "datasets_used": deepcopy(datasets_used) if datasets_used is not None else [],
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    with _lock:
        _analyses.append(record)
        return deepcopy(record)


def get_user_history(user_id: str, limit: int = 20) -> list[dict]:
    """Return a user's analyses, newest first."""
    if not user_id or not str(user_id).strip():
        raise ValueError("user_id is required")

    uid = str(user_id).strip()
    limit = max(int(limit), 0)

    with _lock:
        
        rows = [deepcopy(row) for row in reversed(_analyses) if row["user_id"] == uid]

    return rows[:limit]
