@echo off
setlocal
cd /d "%~dp0"

if not exist ".venv\Scripts\python.exe" (
  py -3.12 -m venv .venv 2>nul
  if errorlevel 1 python -m venv .venv
)
if not exist ".venv\Scripts\python.exe" (
  echo Python was not found. Install Python 3.12 and enable Add Python to PATH.
  exit /b 1
)

call .venv\Scripts\activate.bat
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m pip install -r streamlit_dashboard\requirements.txt
if not exist .env copy .env.example .env
python manage.py migrate
python streamlit_dashboard\generate_dataset.py
python streamlit_dashboard\train_models.py
echo.
echo Setup complete. Run run_django.bat and run_streamlit.bat in two terminals.
pause
