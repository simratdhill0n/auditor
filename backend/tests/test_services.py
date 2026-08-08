import pytest

from backend.services import db_service


@pytest.fixture(autouse=True)
def setup_table():
    db_service.ensure_table_exists()


def test_save_and_get_analysis():
    analysis_id = db_service.save_analysis(
        user_id="test_user",
        prompt="What are Canada's top exports?",
        dataset_info={"dataset_id": "abc123", "name": "trade-data"},
        analysis_result="Sample response text",
    )
    item = db_service.get_analysis("test_user", analysis_id)
    assert item is not None
    assert item["prompt"] == "What are Canada's top exports?"


def test_get_user_history():
    db_service.save_analysis("history_user", "prompt 1", {}, "response 1")
    db_service.save_analysis("history_user", "prompt 2", {}, "response 2")
    history = db_service.get_user_history("history_user", limit=10)
    assert len(history) >= 2
    # newest first
    assert history[0]["created_at"] >= history[1]["created_at"]