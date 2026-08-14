from flask import Flask
from flask_cors import CORS
import logging
from dotenv import load_dotenv
from awsgi import response

load_dotenv()

app = Flask(__name__)

# Explicit CORS configuration
CORS(app, resources={
    r"/*": {
        "origins": "*",
        "methods": ["GET", "POST", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization"]
    }
})

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from routes.analyze import analyze_bp
from routes.datasets import datasets_bp
from routes.history import history_bp

app.register_blueprint(datasets_bp)
app.register_blueprint(analyze_bp)
app.register_blueprint(history_bp)


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


# Lambda handler for AWS
def lambda_handler(event, context):
    """AWS Lambda handler for the Flask app"""
    return response(app, event, context)


if __name__ == '__main__':
    app.run(debug=True, port=5000)