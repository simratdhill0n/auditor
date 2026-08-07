import os
from pathlib import Path

# Get current directory
base_dir = Path.cwd()

# Define folder structure
folders = [
    'backend/routes',
    'backend/services',
    'backend/config',
    'backend/tests',
    'extension/images',
    'deployment',
    'docs',
    '.github/workflows'
]

# Define files with their content
files = {
    'backend/__init__.py': '',
    'backend/app.py': '''from flask import Flask
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
''',
    
    'backend/requirements.txt': '''Flask==2.3.0
python-dotenv==1.0.0
boto3==1.28.0
anthropic==0.7.0
requests==2.31.0
pytest==7.4.0
pytest-cov==4.1.0
gunicorn==21.0.0
flask-cors==4.0.0
''',

    'backend/Dockerfile': '''FROM python:3.11-slim

WORKDIR /app

COPY backend/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ .

EXPOSE 5000

ENV FLASK_APP=app.py
ENV FLASK_ENV=production

CMD ["gunicorn", "--bind", "0.0.0.0:5000", "app:app"]
''',

    'backend/.dockerignore': '''__pycache__
*.pyc
.pytest_cache
.env
.git
.gitignore
''',

    'backend/routes/__init__.py': '',
    'backend/routes/analyze.py': '# Analyze route - Person 2\n',
    'backend/routes/history.py': '# History route - Person 2\n',
    'backend/routes/datasets.py': '# Datasets route - Person 2\n',

    'backend/services/__init__.py': '',
    'backend/services/claude_service.py': '# Claude service - Person 1\n',
    'backend/services/canada_api.py': '# Canada API service - Person 1\n',
    'backend/services/db_service.py': '# Database service - Person 3\n',

    'backend/config/__init__.py': '',
    'backend/config/config.py': '# Configuration - Person 3\n',
    'backend/config/logging_config.py': '# Logging - Person 3\n',

    'backend/tests/__init__.py': '',
    'backend/tests/test_routes.py': '# Route tests - Person 2\n',
    'backend/tests/test_services.py': '# Service tests - Person 3\n',
    'backend/tests/test_integration.py': '# Integration tests - Person 1\n',

    'extension/manifest.json': '''{
  "manifest_version": 3,
  "name": "Auditor",
  "version": "1.0",
  "description": "AI-powered analysis of Canadian government data",
  "permissions": ["storage"],
  "action": {
    "default_popup": "popup.html",
    "default_title": "Auditor"
  }
}
''',

    'extension/popup.html': '''<!DOCTYPE html>
<html>
<head>
  <link rel="stylesheet" href="popup.css">
</head>
<body>
  <h1>Auditor</h1>
  <textarea id="prompt" placeholder="Ask about government data..."></textarea>
  <button id="analyze">Analyze</button>
  <div id="result"></div>
  <script src="popup.js"></script>
</body>
</html>
''',

    'extension/popup.js': '// Extension UI - Person 4\n',
    'extension/popup.css': '/* Extension styling - Person 4 */\n',

    'deployment/dev.env': '''ENVIRONMENT=dev
FLASK_ENV=development
LOG_LEVEL=INFO
DYNAMODB_TABLE=auditor-analyses-dev
CLAUDE_API_KEY=sk-your-key-here
AWS_REGION=us-east-1
''',

    'deployment/prod.env': '''ENVIRONMENT=prod
FLASK_ENV=production
LOG_LEVEL=INFO
DYNAMODB_TABLE=auditor-analyses-prod
CLAUDE_API_KEY=sk-your-key-here
AWS_REGION=us-east-1
''',

    'deployment/docker-compose.yml': '''version: '3.8'

services:
  auditor:
    build: .
    ports:
      - "5000:5000"
    environment:
      FLASK_ENV: development
      CLAUDE_API_KEY: ${CLAUDE_API_KEY}
    volumes:
      - ./backend:/app
''',

    'deployment/sam-template.yaml': '# SAM template - Person 4\n',

    '.github/workflows/dev-deploy.yml': '''name: Deploy to Dev

on:
  push:
    branches:
      - dev

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt pytest pytest-cov
      - run: pytest backend/tests -v
      - run: docker build -f backend/Dockerfile -t auditor:dev .
''',

    '.github/workflows/prod-deploy.yml': '''name: Deploy to Production

on:
  push:
    tags:
      - 'v*'

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r backend/requirements.txt pytest pytest-cov
      - run: pytest backend/tests -v
      - run: docker build -f backend/Dockerfile -t auditor:latest .
''',

    '.gitignore': '''__pycache__/
*.py[cod]
*.egg-info/
.env
.vscode/
.idea/
venv/
.pytest_cache/
.coverage
''',

    '.env.example': '''ENVIRONMENT=dev
FLASK_ENV=development
LOG_LEVEL=INFO
DYNAMODB_TABLE=auditor-analyses-dev
CLAUDE_API_KEY=sk-your-key-here
AWS_REGION=us-east-1
''',

    'README.md': '''# Auditor - AI-Powered Government Data Analysis

## Quick Start for Developers

### 1. Clone & Setup (Do Once)
```bash
git clone https://github.com/yourteam/auditor.git
cd auditor
python -m venv venv
venv\\Scripts\\activate  # Windows
pip install -r backend/requirements.txt
```

### 2. Create your branch
```bash
git checkout -b yourname/feature-name
```

### 3. Run locally
```bash
cd backend
python app.py
# Visit http://localhost:5000/health
```

### 4. Run tests
```bash
pytest backend/tests -v
```

### 5. Push & Create PR
```bash
git add .
git commit -m "feat: your feature description"
git push origin yourname/feature-name
# Go to GitHub and create Pull Request
```

## Team Assignments

- **Person 1 (Data Integration)**: `services/canada_api.py`, `services/claude_service.py`
- **Person 2 (Routes/API)**: `routes/analyze.py`, `routes/history.py`
- **Person 3 (Database)**: `services/db_service.py`, `config/`
- **Person 4 (Frontend/DevOps)**: `extension/`, `.github/workflows/`

## Environments

- **Dev**: Auto-deploys when you merge to `dev` branch
- **Prod**: Auto-deploys when you create a tag like `v1.0.0`
'''
}

# Create folders
print("Creating folders...")
for folder in folders:
    Path(folder).mkdir(parents=True, exist_ok=True)
    print(f"✓ {folder}")

# Create files
print("\nCreating files...")
for file_path, content in files.items():
    Path(file_path).write_text(content, encoding='utf-8')
    print(f"✓ {file_path}")

print("\n✅ Project structure created successfully!")
print("\nNext steps:")
print("1. git add .")
print("2. git commit -m 'initial: project structure'")
print("3. git push origin main")