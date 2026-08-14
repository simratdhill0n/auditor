# Analyze route - USES AI AGENT
"""POST /api/analyze — AI Agent searches Canada data intelligently."""

from __future__ import annotations

from flask import Blueprint, jsonify, request

from services.ai_agent import get_agent
from services.db_service import save_analysis

analyze_bp = Blueprint("analyze", __name__)


@analyze_bp.post("/api/analyze")
def analyze():
    """Analyze government data using AI Agent."""
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

    try:
        agent = get_agent()
        agent_result = agent.analyze_with_data(prompt, limit=limit)
        
        if not agent_result.success:
            return jsonify({"success": False, "error": agent_result.error}), 502

        analysis_data = agent_result.result
        analysis_text = analysis_data.get("analysis", "No analysis generated")
        datasets_used = analysis_data.get("datasets", [])

        saved = False
        record_id = None
        try:
            record = save_analysis(
                user_id=user_id,
                prompt=prompt,
                analysis=analysis_text,
                keyword=None,
                dataset_id=None,
                datasets_used=datasets_used,
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
            "datasets_found": analysis_data.get("datasets_found", 0),
            "datasets_used": datasets_used,
            "analysis": analysis_text,
            "saved": saved,
            "agent_used": True,
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": f"Analysis error: {str(e)}"}), 500