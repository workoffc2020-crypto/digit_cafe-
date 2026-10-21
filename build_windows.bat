@echo off
REM ===== Cyber Cafe Studio - one-click Windows build. The window stays open so errors are visible. =====
if "%~1"=="" goto :relaunch
setlocal
cd /d "%~dp0"
title Cyber Cafe Studio - Build

if not exist "main.py" goto :notextracted

echo.
echo === Step 1: Looking for Python ===
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
echo  1. Open https://www.python.org/downloads/windows/
echo  2. Download Python 3.12, Windows installer 64-bit
echo  3. Run it and TICK the box "Add python.exe to PATH" on the first screen, then Install Now
echo  4. Restart the PC, then double-click build_windows.bat again
echo  Python 3.14 or newer is too new for some libraries. Use 3.12.
echo.
exit /b 1

:havepy
echo Using: %PYCMD%
%PYCMD% --version

echo.
echo === Step 2: Creating private environment ===
if exist ".venv\Scripts\python.exe" goto :venvok
%PYCMD% -m venv .venv
if errorlevel 1 goto :fail
:venvok
set "VPY=%~dp0.venv\Scripts\python.exe"

echo.
echo === Step 3: Installing libraries, needs internet, 5 to 15 minutes first time ===
"%VPY%" -m pip install --upgrade pip
if errorlevel 1 goto :fail
"%VPY%" -m pip install -r requirements-dev.txt
if errorlevel 1 goto :fail
"%VPY%" -m pip install --no-deps "rapidocr-onnxruntime>=1.3"
if errorlevel 1 goto :fail

echo.
echo === Step 4: Creating app icon ===
"%VPY%" tools\make_icon.py
if errorlevel 1 goto :fail

echo.
echo === Step 5: Running automated tests ===
"%VPY%" -m pytest tests -q
if errorlevel 1 echo  WARNING: some tests failed. Build continues. Please send the message above for checking.

echo.
echo === Step 6: Building the application, 5 to 10 minutes ===
"%VPY%" -m PyInstaller CyberCafeStudio.spec --noconfirm
if errorlevel 1 goto :fail

echo.
echo === Step 7: Testing the built program ===
"dist\CyberCafeStudio\CyberCafeStudio.exe" --selftest
if errorlevel 1 goto :fail
echo Built program self-test PASSED.

echo.
echo === Step 8: Creating installer Setup.exe ===
set "ISCC=%ProgramFiles(x86)%\Inno Setup 6\ISCC.exe"
if not exist "%ISCC%" set "ISCC=%ProgramFiles%\Inno Setup 6\ISCC.exe"
if exist "%ISCC%" goto :makesetup
echo.
echo  Inno Setup 6 is not installed, so Setup.exe was not created.
echo  You can still use the program directly: dist\CyberCafeStudio\CyberCafeStudio.exe
echo  For Setup.exe: install Inno Setup 6 from https://jrsoftware.org/isdl.php and run this file again.
echo.
exit /b 0

:makesetup
"%ISCC%" installer\CyberCafeStudio.iss
if errorlevel 1 goto :fail
echo.
echo  DONE!  Installer is here:  %~dp0dist_installer\CyberCafeStudio_Setup.exe
echo.
exit /b 0

:notextracted
echo.
echo  main.py not found. You probably opened this file from INSIDE the zip.
echo  Right-click the zip, choose Extract All, then open build_windows.bat from the extracted folder.
echo.
exit /b 1

:fail
echo.
echo  *** BUILD FAILED. Scroll up, copy the last error lines and send them for help. ***
echo.
exit /b 1

:relaunch
REM Re-open in a window that never closes by itself.
cmd /k ""%~f0" go"
exit /b
