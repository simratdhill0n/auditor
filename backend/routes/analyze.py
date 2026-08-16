"""POST /api/analyze — search Canada data and ask DeepSeek for analysis."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.canada_api import search_datasets
from services.db_service import save_analysis
from services.deepseek_service import ask_llm

analyze_bp = Blueprint("analyze", __name__)


def _trim_dataset(item: dict) -> dict:
    org = item.get("organization") or {}
    if not isinstance(org, dict):
        org = {}
    notes = item.get("notes") or ""
    if isinstance(notes, str) and len(notes) > 500:
        notes = notes[:500] + "..."
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "title": item.get("title"),
        "notes": notes,
        "organization": org.get("title") or org.get("name"),
    }


@analyze_bp.post("/api/analyze")
def analyze():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Content-Type must be application/json",
        }), 400

    body = request.get_json(silent=True)
    body = body or {}
    user_id = str(body.get("user_id") or "").strip()
    prompt = str(body.get("prompt") or body.get("question") or "").strip()
    keyword = str(body.get("keyword") or prompt).strip()

    if not user_id:
        return jsonify({"success": False, "error": "'user_id' is required"}), 400
    if not prompt:
        return jsonify({"success": False, "error": "'prompt' is required"}), 400

    try:
        limit = int(body.get("limit", 5))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "'limit' must be an integer"}), 400

    if limit < 1 or limit > 20:
        return jsonify({"success": False, "error": "'limit' must be between 1 and 20"}), 400

    search = search_datasets(keyword, limit=limit)
    if not search.success:
        return jsonify({"success": False, "error": search.error}), 502

    datasets = [
        _trim_dataset(item)
        for item in (search.result or [])
        if isinstance(item, dict)
    ]

    llm = ask_llm(prompt, data_context=datasets)
    if not llm.success:
        return jsonify({"success": False, "error": llm.error}), 502

    saved = False
    record_id = None
    try:
        record = save_analysis(
            user_id=user_id,
            prompt=prompt,
            analysis=llm.content,
            keyword=keyword,
            dataset_id=None,
            datasets_used=datasets,
        )
        saved = True
        record_id = record.get("id")
    except Exception:
        saved = False

    return jsonify({
        "success": True,
        "id": record_id,
        "user_id": user_id,
        "prompt": prompt,
        "datasets_used": datasets,
        "analysis": llm.content,
        "saved": saved,
    }), 200