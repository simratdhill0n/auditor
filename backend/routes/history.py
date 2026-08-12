# History route - Person 2
"""GET /api/history — return a user's past analyses."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.db_service import get_user_history

history_bp = Blueprint("history", __name__)


@history_bp.get("/api/history")
def history():
    user_id = (request.args.get("user_id") or "").strip()
    if not user_id:
        return jsonify({
            "success": False,
            "error": "Query parameter 'user_id' is required",
        }), 400

    try:
        limit = int(request.args.get("limit", 20))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "'limit' must be an integer"}), 400

    if limit < 1 or limit > 100:
        return jsonify({"success": False, "error": "'limit' must be between 1 and 100"}), 400

    try:
        items = get_user_history(user_id, limit=limit)
    except ValueError as exc:
        return jsonify({"success": False, "error": str(exc)}), 400
    except Exception:  # noqa: BLE001 — surface unexpected store failures
        return jsonify({"success": False, "error": "Could not load history"}), 500

    return jsonify({
        "success": True,
        "user_id": user_id,
        "count": len(items),
        "history": items,
    }), 200
