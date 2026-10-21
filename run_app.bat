@echo off
REM Cyber Cafe Studio - start the app directly. The window stays open so any error is visible.
if "%~1"=="" goto :relaunch
setlocal
cd /d "%~dp0"
title Cyber Cafe Studio - Run

if not exist "main.py" goto :notextracted

echo.
echo === Looking for Python ===
set "PYCMD="
py -3.12 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3.12"
if defined PYCMD goto :havepy
py -3.13 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3.13"
if defined PYCMD goto :havepy
py -3.11 -c "import sys" >nul 2>nul
if not errorlevel 1 set "PYCMD=py -3.11"
if defined PYCMD goto :havepy
python -c "import sys; sys.exit(0 if (3,10)<=sys.version_info[:2]<=(3,13) else 1)" >nul 2>nul
if not errorlevel 1 set "PYCMD=python"
if defined PYCMD goto :havepy

echo.
echo  PYTHON NAHI MILA - Python not found.
echo  Install Python 3.12 from https://www.python.org/downloads/windows/
echo  and TICK the box "Add python.exe to PATH". Then restart the PC and run this file again.
echo.
exit /b 1

:havepy
echo Using: %PYCMD%
if exist ".venv\Scripts\python.exe" goto :venvok
echo Creating private environment...
%PYCMD% -m venv .venv
if errorlevel 1 goto :fail
:venvok
set "VPY=%~dp0.venv\Scripts\python.exe"

if exist ".venv\installed_v2.flag" goto :installed
echo.
echo === Installing libraries - first time only, needs internet, 5 to 15 minutes ===
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VPY%" -m pip install -r requirements.txt
if errorlevel 1 goto :fail
"%VPY%" -m pip install --no-deps "rapidocr-onnxruntime>=1.3"
if errorlevel 1 goto :fail
echo ok> ".venv\installed_v2.flag"
:installed

if not exist "assets\app.ico" "%VPY%" tools\make_icon.py
echo.
echo === Starting Cyber Cafe Studio ===
"%VPY%" main.py
if errorlevel 1 goto :fail
exit /b 0

:notextracted
echo.
echo  main.py not found. You probably opened this file from INSIDE the zip.
echo  Right-click the zip, choose Extract All, then open run_app.bat from the extracted folder.
echo.
exit /b 1

:fail
echo.
echo  *** FAILED. Copy the error lines above and send them for help. ***
echo.
exit /b 1

:relaunch
REM Re-open in a window that never closes by itself.
cmd /k ""%~f0" go"
exit /b
