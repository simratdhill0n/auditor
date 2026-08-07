# Service tests - Person 1 (Canada API + DeepSeek)

from __future__ import annotations

from unittest.mock import MagicMock, patch

import requests

from services.canada_api import (
    get_dataset_details,
    list_dataset_ids,
    search_datasets,
)
from services.deepseek_service import LlmResponse, ask_llm


# ---------------------------------------------------------------------------
# Canada API
# ---------------------------------------------------------------------------


class TestSearchDatasets:
    @patch("services.canada_api.requests.get")
    def test_search_success(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "success": True,
                "result": {
                    "count": 1,
                    "results": [{"id": "abc", "title": "Climate Data"}],
                },
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        response = search_datasets("climate", limit=5)

        assert response.success is True
        assert isinstance(response.result, list)
        assert response.result[0]["title"] == "Climate Data"
        mock_get.assert_called_once()
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"q": "climate", "rows": 5}

    def test_search_requires_keyword(self):
        response = search_datasets("   ")
        assert response.success is False
        assert "keyword" in response.error

    @patch("services.canada_api.requests.get")
    def test_search_api_failure(self, mock_get):
        mock_get.side_effect = requests.exceptions.ConnectionError("down")

        response = search_datasets("climate")

        assert response.success is False
        assert "inaccessible" in response.error

    @patch("services.canada_api.requests.get")
    def test_search_unexpected_shape(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "result": "not-a-dict"},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        response = search_datasets("climate")

        assert response.success is False
        assert "shape" in response.error


class TestGetDatasetDetails:
    @patch("services.canada_api.requests.get")
    def test_details_success(self, mock_get):
        package = {"id": "pkg-1", "title": "Budget 2024"}
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "result": package},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        response = get_dataset_details("pkg-1")

        assert response.success is True
        assert response.result == package
        _, kwargs = mock_get.call_args
        assert kwargs["params"] == {"id": "pkg-1"}

    def test_details_requires_id(self):
        response = get_dataset_details("")
        assert response.success is False
        assert "dataset_id" in response.error

    @patch("services.canada_api.requests.get")
    def test_details_http_error(self, mock_get):
        resp = MagicMock()
        resp.raise_for_status.side_effect = requests.exceptions.HTTPError("404")
        mock_get.return_value = resp

        response = get_dataset_details("missing")

        assert response.success is False
        assert "inaccessible" in response.error

    @patch("services.canada_api.requests.get")
    def test_details_api_error_payload(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "success": False,
                "error": {"message": "Not found"},
            },
        )
        mock_get.return_value.raise_for_status = MagicMock()

        response = get_dataset_details("missing")

        assert response.success is False
        assert response.error == "Not found"


class TestListDatasetIds:
    @patch("services.canada_api.requests.get")
    def test_list_truncates(self, mock_get):
        mock_get.return_value = MagicMock(
            status_code=200,
            json=lambda: {"success": True, "result": ["a", "b", "c", "d"]},
        )
        mock_get.return_value.raise_for_status = MagicMock()

        response = list_dataset_ids(limit=2)

        assert response.success is True
        assert response.result == ["a", "b"]


# ---------------------------------------------------------------------------
# DeepSeek / OpenRouter
# ---------------------------------------------------------------------------


class TestAskLlm:
    def test_requires_question(self):
        response = ask_llm("  ")
        assert response.success is False
        assert "user_question" in response.error

    def test_requires_api_key(self, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)

        response = ask_llm("What changed?")

        assert response.success is False
        assert "DEEPSEEK_API_KEY" in response.error

    @patch("services.deepseek_service.requests.post")
    def test_ask_llm_success(self, mock_post, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {
                "choices": [{"message": {"content": "Spending rose 3%."}}],
            },
        )
        mock_post.return_value.raise_for_status = MagicMock()

        response = ask_llm("Summarize", data_context={"title": "Budget"})

        assert isinstance(response, LlmResponse)
        assert response.success is True
        assert response.content == "Spending rose 3%."
        args, kwargs = mock_post.call_args
        assert args[0].endswith("/chat/completions")
        assert kwargs["headers"]["Authorization"] == "Bearer test-key"
        assert "Budget" in kwargs["json"]["messages"][1]["content"]

    @patch("services.deepseek_service.requests.post")
    def test_ask_llm_accepts_openrouter_env_alias(self, mock_post, monkeypatch):
        monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
        monkeypatch.setenv("OPENROUTER_API_KEY", "alias-key")
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"choices": [{"message": {"content": "ok"}}]},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        response = ask_llm("Hi")

        assert response.success is True
        assert mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer alias-key"

    @patch("services.deepseek_service.requests.post")
    def test_ask_llm_network_error(self, mock_post, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_post.side_effect = requests.exceptions.Timeout("slow")

        response = ask_llm("Explain")

        assert response.success is False
        assert "timed out" in response.error

    @patch("services.deepseek_service.requests.post")
    def test_ask_llm_bad_shape(self, mock_post, monkeypatch):
        monkeypatch.setenv("DEEPSEEK_API_KEY", "test-key")
        mock_post.return_value = MagicMock(
            status_code=200,
            json=lambda: {"choices": []},
        )
        mock_post.return_value.raise_for_status = MagicMock()

        response = ask_llm("Explain")

        assert response.success is False
        assert "Unexpected response shape" in response.error
