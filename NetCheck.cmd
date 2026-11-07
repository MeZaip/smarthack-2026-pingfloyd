@echo off
rem NetCheck - double-click to start. First start prepares everything (about 1 minute), then opens the app.
setlocal
cd /d "%~dp0"
set "VENV=.venv-windows"

if not exist "%VENV%\Scripts\pythonw.exe" (
  echo Pregatim NetCheck pentru prima pornire / Preparing NetCheck for the first start...
  py -3 -m venv "%VENV%" 2>nul || python -m venv "%VENV%"
  if not exist "%VENV%\Scripts\python.exe" (
    echo.
    echo Python nu este instalat. Instaleaza-l de pe https://www.python.org/downloads/ si porneste din nou.
    echo Python is not installed. Install it from https://www.python.org/downloads/ and start again.
    pause
    exit /b 1
  )
)

rem (re)install packages only when requirements.txt changed
fc /b requirements.txt "%VENV%\requirements.installed" >nul 2>&1
if errorlevel 1 (
  echo Instalam componentele / Installing components...
  "%VENV%\Scripts\python.exe" -m pip install -q --disable-pip-version-check -r requirements.txt || (pause & exit /b 1)
  copy /y requirements.txt "%VENV%\requirements.installed" >nul
)

start "" "%VENV%\Scripts\pythonw.exe" -m netcheck app
