@echo off
setlocal
cd /d "%~dp0"

if exist "venvapp\Scripts\python.exe" (
  set PORT=8501
  netstat -ano | findstr /R /C:":8501 .*LISTENING" >nul
  if %errorlevel%==0 (
    set PORT=8502
  )
  echo Starting NSP Resume Analyzer on port %PORT%...
  "venvapp\Scripts\python.exe" -m streamlit run "App\App.py" --server.headless true --server.port %PORT%
) else (
  echo Python virtual environment not found at venvapp\Scripts\python.exe
  echo Please create it first using: python -m venv venvapp
  pause
)
