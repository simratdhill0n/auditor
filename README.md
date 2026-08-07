# Auditor - AI-Powered Government Data Analysis

## Quick Start for Developers

### 1. Clone & Setup (Do Once)
```bash
git clone https://github.com/yourteam/auditor.git
cd auditor
python -m venv venv
venv\Scripts\activate  # Windows
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
