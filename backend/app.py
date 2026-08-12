from flask import Flask
from flask_cors import CORS
import logging
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@app.route('/health', methods=['GET'])
def health():
    return {'status': 'ok'}, 200

@app.route('/api/analyze', methods=['POST'])
def analyze():
    return {'message': 'analyze endpoint - coming soon'}, 200

@app.route('/api/history', methods=['GET'])
def history():
    return {'message': 'history endpoint - coming soon'}, 200

@app.route('/api/datasets/search', methods=['GET'])
def search():
    return {'message': 'search endpoint - coming soon'}, 200




if __name__ == '__main__':
    app.run(debug=True, port=5000)
