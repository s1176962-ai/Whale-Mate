@echo off
cd /d "%~dp0"
where py >nul 2>nul
if not errorlevel 1 (
  py -3 launcher.py
) else (
  python launcher.py
)
if errorlevel 1 (
  echo.
  echo WhaleMate did not start. Follow the instruction printed above, then try again.
  echo If Python itself is missing: install Python 3.10+ from python.org with
  echo "tcl/tk and IDLE" and "Add Python to PATH" enabled.
  pause
)
