import os
from dotenv import load_dotenv

load_dotenv()


class Config:
    """Central app configuration, driven by environment variables."""

    ENV = os.getenv("ENVIRONMENT", os.getenv("FLASK_ENV", "development"))

    # DynamoDB
    AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
    DYNAMODB_ENDPOINT_URL = os.getenv("DYNAMODB_ENDPOINT_URL", "http://localhost:8000")  # unset in prod -> real AWS
    DYNAMODB_TABLE_NAME = os.getenv("DYNAMODB_TABLE", "auditor-analyses-dev")

    # AWS credentials (local DynamoDB accepts dummy values)
    AWS_ACCESS_KEY_ID = os.getenv("AWS_ACCESS_KEY_ID", "local")
    AWS_SECRET_ACCESS_KEY = os.getenv("AWS_SECRET_ACCESS_KEY", "local")

    # External services
    DEEPSEEK_API_KEY = os.getenv("DEEPSEEK_API_KEY", "")  # OpenRouter key
    CANADA_API_BASE_URL = os.getenv("CANADA_API_BASE_URL", "https://open.canada.ca/data/api")

    @classmethod
    def is_local_db(cls) -> bool:
        return bool(cls.DYNAMODB_ENDPOINT_URL)