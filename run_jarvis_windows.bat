@echo off
chcp 65001 >nul
cd /d "%~dp0"
where py >nul 2>nul
if errorlevel 1 (
  echo Python 3 not found. Install Python 3.11+ from python.org
  pause
  exit /b 1
)
py -3 start_jarvis.py
if errorlevel 1 pause
