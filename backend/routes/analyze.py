# Analyze route - Person 2
"""POST /api/analyze — search Canada data and ask DeepSeek for an analysis."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.canada_api import get_dataset_details, search_datasets
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


def _build_data_context(
    *,
    keyword: str,
    dataset_id: str | None,
    limit: int,
) -> tuple[list[dict] | dict | None, str | None]:
    """Fetch Canada API context. Returns (context, error)."""
    if dataset_id:
        details = get_dataset_details(dataset_id)
        if not details.success:
            return None, details.error
        if not isinstance(details.result, dict):
            return None, "Unexpected dataset details shape"
        return _trim_dataset(details.result), None

    search = search_datasets(keyword, limit=limit)
    if not search.success:
        return None, search.error

    datasets = [
        _trim_dataset(item)
        for item in (search.result or [])
        if isinstance(item, dict)
    ]
    return datasets, None


@analyze_bp.post("/api/analyze")
def analyze():
    if not request.is_json:
        return jsonify({
            "success": False,
            "error": "Content-Type must be application/json",
        }), 400

    body = request.get_json(silent=True)
    if body is None and request.data:
        return jsonify({"success": False, "error": "Invalid JSON body"}), 400
    body = body or {}
    user_id = str(body.get("user_id") or "").strip()
    prompt = str(body.get("prompt") or body.get("question") or "").strip()
    keyword = str(body.get("keyword") or prompt).strip()
    dataset_id = str(body.get("dataset_id") or "").strip() or None

    if not user_id:
        return jsonify({"success": False, "error": "'user_id' is required"}), 400
    if not prompt:
        return jsonify({
            "success": False,
            "error": "'prompt' (or 'question') is required",
        }), 400

    try:
        limit = int(body.get("limit", 5))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "'limit' must be an integer"}), 400

    if limit < 1 or limit > 20:
        return jsonify({"success": False, "error": "'limit' must be between 1 and 20"}), 400

    data_context, canada_error = _build_data_context(
        keyword=keyword,
        dataset_id=dataset_id,
        limit=limit,
    )
    if canada_error:
        return jsonify({"success": False, "error": canada_error}), 502

    llm = ask_llm(prompt, data_context=data_context)
    if not llm.success:
        return jsonify({"success": False, "error": llm.error}), 502

    datasets_used = data_context if isinstance(data_context, list) else [data_context]
    saved = False
    record_id = None
    try:
        record = save_analysis(
            user_id=user_id,
            prompt=prompt,
            analysis=llm.content,
            keyword=keyword if not dataset_id else None,
            dataset_id=dataset_id,
            datasets_used=datasets_used,
        )
        saved = True
        record_id = record["id"]
    except Exception:
        # Analysis still succeeds even if persistence fails
        saved = False

    return jsonify({
        "success": True,
        "id": record_id,
        "user_id": user_id,
        "prompt": prompt,
        "keyword": keyword if not dataset_id else None,
        "dataset_id": dataset_id,
        "datasets_used": datasets_used,
        "analysis": llm.content,
        "saved": saved,
    }), 200
