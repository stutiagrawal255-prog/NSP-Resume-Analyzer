@echo off
setlocal
cd /d "%~dp0"

if not exist "venvapp\Scripts\python.exe" (
  echo Python virtual environment not found at venvapp\Scripts\python.exe
  echo Please create it first using: python -m venv venvapp
  pause
  exit /b 1
)

set PORT=
for /L %%P in (8501,1,8510) do (
  netstat -ano | findstr /R /C:":%%P .*LISTENING" >nul
  if errorlevel 1 (
    set PORT=%%P
    goto :port_found
  )
)

:port_found
if "%PORT%"=="" (
  echo No free port found in range 8501-8510.
  pause
  exit /b 1
)

echo Starting NSP Resume Analyzer server on port %PORT%...
echo Local URL   : http://localhost:%PORT%
echo Network URL : http://^<your-local-ip^>:%PORT%
echo.
"venvapp\Scripts\python.exe" -m streamlit run "App\App.py" --server.address 0.0.0.0 --server.headless true --server.port %PORT%
