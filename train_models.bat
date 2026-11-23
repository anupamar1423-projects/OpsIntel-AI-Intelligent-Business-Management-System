@echo off
setlocal
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Run setup_windows.bat first.
  exit /b 1
)
call .venv\Scripts\activate.bat
cd /d "%~dp0streamlit_dashboard"
python generate_dataset.py
if errorlevel 1 exit /b 1
python train_models.py
pause
