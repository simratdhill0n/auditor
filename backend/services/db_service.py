import uuid
import threading
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key
from botocore.exceptions import ClientError

from backend.config.config import Config
from backend.config.logging_config import get_logger

logger = get_logger(__name__)

_lock = threading.Lock()


def _get_resource():
    return boto3.resource(
        "dynamodb",
        region_name=Config.AWS_REGION,
        endpoint_url=Config.DYNAMODB_ENDPOINT_URL or None,
        aws_access_key_id=Config.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=Config.AWS_SECRET_ACCESS_KEY,
    )


_resource = _get_resource()
_table = _resource.Table(Config.DYNAMODB_TABLE_NAME)


def ensure_table_exists() -> None:
    """Creates the analyses table if missing. Local dev convenience only."""
    existing = [t.name for t in _resource.tables.all()]
    if Config.DYNAMODB_TABLE_NAME in existing:
        return
    logger.info(f"Creating table {Config.DYNAMODB_TABLE_NAME}")
    _resource.create_table(
        TableName=Config.DYNAMODB_TABLE_NAME,
        KeySchema=[
            {"AttributeName": "user_id", "KeyType": "HASH"},
            {"AttributeName": "analysis_id", "KeyType": "RANGE"},
        ],
        AttributeDefinitions=[
            {"AttributeName": "user_id", "AttributeType": "S"},
            {"AttributeName": "analysis_id", "AttributeType": "S"},
        ],
        BillingMode="PAY_PER_REQUEST",
    ).wait_until_exists()


def save_analysis(user_id: str, prompt: str, dataset_info: dict, analysis_result: str) -> str:
    """Persist one analysis. Raises on failure — caller (route) decides
    how to surface `saved: false` without losing the LLM response."""
    analysis_id = f"{datetime.now(timezone.utc).isoformat()}#{uuid.uuid4().hex[:8]}"
    item = {
        "user_id": user_id,
        "analysis_id": analysis_id,
        "prompt": prompt,
        "dataset_info": dataset_info,
        "analysis_result": analysis_result,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    with _lock:
        try:
            _table.put_item(Item=item)
            logger.info(f"Saved analysis {analysis_id} for user {user_id}")
            return analysis_id
        except ClientError as e:
            logger.error(f"Failed to save analysis: {e}")
            raise


def get_user_history(user_id: str, limit: int = 20) -> list[dict]:
    """Matches Rahul's temp in-memory signature: get_user_history(user_id, limit=...)."""
    try:
        response = _table.query(
            KeyConditionExpression=Key("user_id").eq(user_id),
            ScanIndexForward=False,  # newest first
            Limit=limit,
        )
        return response.get("Items", [])
    except ClientError as e:
        logger.error(f"Failed to get history: {e}")
        raise


def get_analysis(user_id: str, analysis_id: str) -> dict | None:
    """Extra helper, not in Rahul's current contract but handy for lookups."""
    try:
        response = _table.get_item(Key={"user_id": user_id, "analysis_id": analysis_id})
        return response.get("Item")
    except ClientError as e:
        logger.error(f"Failed to get analysis: {e}")
        raise