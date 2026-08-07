# Datasets route - Person 2
"""GET /api/datasets/search — search Open Canada datasets by keyword."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.canada_api import search_datasets

datasets_bp = Blueprint("datasets", __name__)


def _normalize_dataset(item: dict) -> dict:
    org = item.get("organization") or {}
    if not isinstance(org, dict):
        org = {}
    return {
        "id": item.get("id"),
        "name": item.get("name"),
        "title": item.get("title"),
        "notes": item.get("notes"),
        "organization": org.get("title") or org.get("name"),
        "metadata_created": item.get("metadata_created"),
        "metadata_modified": item.get("metadata_modified"),
    }


@datasets_bp.get("/api/datasets/search")
def search():
    keyword = (request.args.get("q") or request.args.get("keyword") or "").strip()
    if not keyword:
        return jsonify({
            "success": False,
            "error": "Query parameter 'q' (or 'keyword') is required",
        }), 400

    try:
        limit = int(request.args.get("limit", 10))
    except (TypeError, ValueError):
        return jsonify({"success": False, "error": "'limit' must be an integer"}), 400

    if limit < 1 or limit > 50:
        return jsonify({"success": False, "error": "'limit' must be between 1 and 50"}), 400

    response = search_datasets(keyword, limit=limit)
    if not response.success:
        return jsonify({"success": False, "error": response.error}), 502

    datasets = [
        _normalize_dataset(item)
        for item in (response.result or [])
        if isinstance(item, dict)
    ]

    return jsonify({
        "success": True,
        "keyword": keyword,
        "count": len(datasets),
        "datasets": datasets,
    }), 200
