# Canada API service - Person 1
"""Query the Open Canada CKAN API for datasets."""

from __future__ import annotations

import os
from dataclasses import dataclass

import requests

DEFAULT_BASE_URL = "https://open.canada.ca/data/api"


@dataclass
class ApiResponse:
    success: bool
    result: dict | list | None = None
    error: str | None = None


def _base_url() -> str:
    return os.environ.get("CANADA_API_BASE_URL", DEFAULT_BASE_URL).rstrip("/")


def general_request(endpoint: str, params: dict | None = None) -> ApiResponse:
    """GET an Open Canada API action endpoint and normalize the response."""
    url = f"{_base_url()}/{endpoint.lstrip('/')}"
    try:
        response = requests.get(url, params=params, timeout=10)
        response.raise_for_status()
        data = response.json()
    except requests.exceptions.Timeout:
        return ApiResponse(success=False, error="The Open Canada API timed out")
    except requests.exceptions.RequestException as exc:
        return ApiResponse(
            success=False,
            error=f"The Open Canada API was inaccessible: {exc}",
        )
    except ValueError:
        return ApiResponse(success=False, error="The Open Canada API returned invalid JSON")

    if not isinstance(data, dict):
        return ApiResponse(success=False, error="Unexpected Open Canada API response shape")

    if not data.get("success"):
        error = data.get("error", "An unknown error occurred")
        if isinstance(error, dict):
            error = error.get("message") or str(error)
        return ApiResponse(success=False, error=str(error))

    return ApiResponse(success=True, result=data.get("result"))


def get_dataset_details(dataset_id: str) -> ApiResponse:
    """Fetch a single dataset package by id or name."""
    if not dataset_id or not str(dataset_id).strip():
        return ApiResponse(success=False, error="dataset_id is required")
    return general_request("action/package_show", params={"id": dataset_id})


def list_dataset_ids(limit: int = 10) -> ApiResponse:
    """List dataset ids, truncated to ``limit``."""
    response = general_request("action/package_list")
    if response.success:
        ids = response.result if isinstance(response.result, list) else []
        response.result = ids[: max(limit, 0)]
    return response


def search_datasets(keyword: str, limit: int = 10) -> ApiResponse:
    """Search datasets by keyword. ``result`` is a list of package dicts."""
    if not keyword or not str(keyword).strip():
        return ApiResponse(success=False, error="keyword is required")

    response = general_request(
        "action/package_search",
        params={"q": keyword, "rows": max(limit, 0)},
    )
    if not response.success:
        return response

    if not isinstance(response.result, dict):
        return ApiResponse(success=False, error="Unexpected search result shape")

    results = response.result.get("results")
    if not isinstance(results, list):
        return ApiResponse(success=False, error="Unexpected search result shape")

    return ApiResponse(success=True, result=results)
