@echo off
setlocal
cd /d "%~dp0"

if "%HF_SPACE_ID%"=="" (
  echo First create a Hugging Face Docker Space, then set HF_SPACE_ID to username/space-name.
  echo Example: set HF_SPACE_ID=my-account/opsintel-ai
  exit /b 1
)

hf auth whoami
if errorlevel 1 (
  echo Sign in first with: hf auth login
  exit /b 1
)

hf upload "%HF_SPACE_ID%" . --type space --exclude ".venv/**" --exclude "__pycache__/**" --exclude "*.pyc" --exclude ".streamlit/secrets.toml" --exclude "artifacts/**" --commit-message "Deploy OpsIntel AI Streamlit analytics"
