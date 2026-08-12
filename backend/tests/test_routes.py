# Route tests - Person 2

from __future__ import annotations

from unittest.mock import patch

import pytest

from app import app
from services.canada_api import ApiResponse
from services.db_service import clear_all, save_analysis
from services.deepseek_service import LlmResponse


@pytest.fixture
def client():
    app.config["TESTING"] = True
    clear_all()
    with app.test_client() as test_client:
        yield test_client
    clear_all()


class TestDatasetsSearch:
    def test_missing_query_returns_400(self, client):
        response = client.get("/api/datasets/search")
        assert response.status_code == 400
        data = response.get_json()
        assert data["success"] is False
        assert "q" in data["error"] or "keyword" in data["error"]

    def test_invalid_limit_returns_400(self, client):
        response = client.get("/api/datasets/search?q=climate&limit=abc")
        assert response.status_code == 400
        assert response.get_json()["success"] is False

    def test_limit_out_of_range_returns_400(self, client):
        response = client.get("/api/datasets/search?q=climate&limit=100")
        assert response.status_code == 400

    @patch("routes.datasets.search_datasets")
    def test_search_success(self, mock_search, client):
        mock_search.return_value = ApiResponse(
            success=True,
            result=[
                {
                    "id": "1",
                    "name": "climate-data",
                    "title": "Climate Data",
                    "notes": "About climate",
                    "organization": {"title": "Environment Canada"},
                    "metadata_created": "2024-01-01",
                    "metadata_modified": "2024-02-01",
                }
            ],
        )

        response = client.get("/api/datasets/search?q=climate&limit=5")

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["keyword"] == "climate"
        assert data["count"] == 1
        assert data["datasets"][0]["title"] == "Climate Data"
        assert data["datasets"][0]["organization"] == "Environment Canada"
        mock_search.assert_called_once_with("climate", limit=5)

    @patch("routes.datasets.search_datasets")
    def test_search_upstream_failure(self, mock_search, client):
        mock_search.return_value = ApiResponse(success=False, error="API down")

        response = client.get("/api/datasets/search?keyword=budget")

        assert response.status_code == 502
        data = response.get_json()
        assert data["success"] is False
        assert data["error"] == "API down"


class TestAnalyze:
    def test_requires_json(self, client):
        response = client.post("/api/analyze", data="not-json")
        assert response.status_code == 400

    def test_missing_user_id(self, client):
        response = client.post("/api/analyze", json={"prompt": "Summarize climate data"})
        assert response.status_code == 400
        assert "user_id" in response.get_json()["error"]

    def test_missing_prompt(self, client):
        response = client.post("/api/analyze", json={"user_id": "u1"})
        assert response.status_code == 400
        assert "prompt" in response.get_json()["error"]

    @patch("routes.analyze.search_datasets")
    @patch("routes.analyze.ask_llm")
    def test_analyze_success(self, mock_llm, mock_search, client):
        mock_search.return_value = ApiResponse(
            success=True,
            result=[
                {
                    "id": "1",
                    "title": "Climate Data",
                    "notes": "Notes",
                    "organization": {"title": "ECCC"},
                }
            ],
        )
        mock_llm.return_value = LlmResponse(
            success=True,
            content="Climate datasets cover temperature and precipitation.",
        )

        response = client.post(
            "/api/analyze",
            json={
                "user_id": "rahul",
                "prompt": "What climate datasets exist?",
                "keyword": "climate",
                "limit": 3,
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["user_id"] == "rahul"
        assert "Climate datasets" in data["analysis"]
        assert data["saved"] is True
        assert data["id"]
        assert data["datasets_used"][0]["title"] == "Climate Data"
        mock_search.assert_called_once_with("climate", limit=3)
        mock_llm.assert_called_once()

    @patch("routes.analyze.get_dataset_details")
    @patch("routes.analyze.ask_llm")
    def test_analyze_with_dataset_id(self, mock_llm, mock_details, client):
        mock_details.return_value = ApiResponse(
            success=True,
            result={"id": "abc", "title": "Budget 2024", "notes": "Federal budget"},
        )
        mock_llm.return_value = LlmResponse(success=True, content="Budget rose.")

        response = client.post(
            "/api/analyze",
            json={
                "user_id": "rahul",
                "prompt": "Summarize this dataset",
                "dataset_id": "abc",
            },
        )

        assert response.status_code == 200
        data = response.get_json()
        assert data["dataset_id"] == "abc"
        assert data["analysis"] == "Budget rose."
        mock_details.assert_called_once_with("abc")

    @patch("routes.analyze.search_datasets")
    def test_analyze_canada_failure(self, mock_search, client):
        mock_search.return_value = ApiResponse(success=False, error="Canada down")

        response = client.post(
            "/api/analyze",
            json={"user_id": "u1", "prompt": "Tell me about housing"},
        )

        assert response.status_code == 502
        assert response.get_json()["error"] == "Canada down"

    @patch("routes.analyze.search_datasets")
    @patch("routes.analyze.ask_llm")
    def test_analyze_llm_failure(self, mock_llm, mock_search, client):
        mock_search.return_value = ApiResponse(success=True, result=[])
        mock_llm.return_value = LlmResponse(success=False, error="DEEPSEEK_API_KEY is not set")

        response = client.post(
            "/api/analyze",
            json={"user_id": "u1", "prompt": "Anything"},
        )

        assert response.status_code == 502
        assert "DEEPSEEK_API_KEY" in response.get_json()["error"]


class TestHistory:
    def test_missing_user_id(self, client):
        response = client.get("/api/history")
        assert response.status_code == 400
        assert "user_id" in response.get_json()["error"]

    def test_invalid_limit(self, client):
        response = client.get("/api/history?user_id=rahul&limit=nope")
        assert response.status_code == 400

    def test_empty_history(self, client):
        response = client.get("/api/history?user_id=rahul")
        assert response.status_code == 200
        data = response.get_json()
        assert data["success"] is True
        assert data["count"] == 0
        assert data["history"] == []

    def test_returns_user_history_newest_first(self, client):
        save_analysis(user_id="rahul", prompt="first", analysis="a1")
        save_analysis(user_id="rahul", prompt="second", analysis="a2")
        save_analysis(user_id="other", prompt="nope", analysis="x")

        response = client.get("/api/history?user_id=rahul&limit=10")

        assert response.status_code == 200
        data = response.get_json()
        assert data["count"] == 2
        assert data["history"][0]["prompt"] == "second"
        assert data["history"][1]["prompt"] == "first"
        assert all(item["user_id"] == "rahul" for item in data["history"])

    @patch("routes.analyze.search_datasets")
    @patch("routes.analyze.ask_llm")
    def test_analyze_then_history(self, mock_llm, mock_search, client):
        mock_search.return_value = ApiResponse(success=True, result=[])
        mock_llm.return_value = LlmResponse(success=True, content="Done.")

        analyze_resp = client.post(
            "/api/analyze",
            json={"user_id": "rahul", "prompt": "Summarize housing", "keyword": "housing"},
        )
        assert analyze_resp.status_code == 200
        assert analyze_resp.get_json()["saved"] is True

        history_resp = client.get("/api/history?user_id=rahul")
        data = history_resp.get_json()
        assert history_resp.status_code == 200
        assert data["count"] == 1
        assert data["history"][0]["analysis"] == "Done."
        assert data["history"][0]["prompt"] == "Summarize housing"
