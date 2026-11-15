@echo off
cd /d "%~dp0"
echo Building WhaleMate.exe (one-file, windowed)...
py -3 -m PyInstaller --noconfirm --clean WhaleMate.spec
if errorlevel 1 (
  echo.
  echo Build failed. See the messages above.
  pause
  exit /b 1
)
echo.
echo Done: dist\WhaleMate.exe
echo Run "dist\WhaleMate.exe --check" to verify the bundle.
pause
