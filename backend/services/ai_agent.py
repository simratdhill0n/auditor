"""AI Agent - Intelligent API interaction and data fetching."""

import json
import logging
from typing import Any, Optional

import requests

from services.deepseek_service import ask_llm

logger = logging.getLogger(__name__)


class AuditResult:
    """Result wrapper for agent operations."""

    def __init__(self, success: bool, result: Any = None, error: str = None):
        self.success = success
        self.result = result
        self.error = error


class APIAgent:
    """AI Agent that learns from API documentation and makes intelligent calls."""

    def __init__(self):
        self.base_url = "https://open.canada.ca/data/api"
        self.session = requests.Session()

    def _search_datasets(self, query: str, limit: int = 5) -> AuditResult:
        """Search CKAN API for datasets."""
        try:
            url = f"{self.base_url}/3/action/package_search"
            params = {
                "q": query,
                "rows": min(limit, 10),
                "sort": "metadata_modified desc",
            }

            response = self.session.get(url, params=params, timeout=10)
            response.raise_for_status()

            data = response.json()
            if not data.get("success"):
                return AuditResult(
                    False, error=f"CKAN API error: {data.get('error', 'Unknown')}"
                )

            records = data.get("result", {}).get("records", [])
            return AuditResult(success=True, result=records)

        except requests.Timeout:
            return AuditResult(False, error="CKAN API timeout")
        except requests.RequestException as e:
            return AuditResult(False, error=f"API connection error: {str(e)}")
        except Exception as e:
            return AuditResult(False, error=f"Search error: {str(e)}")

    def analyze_with_data(self, user_query: str, limit: int = 5) -> AuditResult:
        """Complete analysis pipeline: search → analyze."""
        try:
            search_results = self._search_datasets(user_query, limit)
            if not search_results.success:
                return search_results

            datasets = search_results.result or []
            if not datasets:
                return AuditResult(False, error="No datasets found")

            datasets_info = []
            for ds in datasets[:5]:
                datasets_info.append({
                    "title": ds.get("title", "Untitled"),
                    "name": ds.get("name", ""),
                    "notes": ds.get("notes", "")[:300],
                })

            analysis_prompt = f"""
            User Query: {user_query}
            
            Found Datasets:
            {json.dumps(datasets_info, indent=2)}
            
            Please provide analysis based on these datasets.
            """

            llm_result = ask_llm(analysis_prompt)
            if not llm_result.success:
                return AuditResult(False, error=llm_result.error)

            return AuditResult(
                success=True,
                result={
                    "query": user_query,
                    "datasets_found": len(datasets),
                    "analysis": llm_result.content,
                    "datasets": datasets_info,
                },
            )

        except Exception as e:
            logger.error(f"Agent error: {e}")
            return AuditResult(False, error=f"Analysis error: {str(e)}")


_agent = None


def get_agent() -> APIAgent:
    """Get or create agent instance."""
    global _agent
    if _agent is None:
        _agent = APIAgent()
    return _agent