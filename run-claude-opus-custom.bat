@echo off
setlocal
cd /d D:\kedai-ops
if "%~1"=="" (
  echo Usage:
  echo   run-claude-opus-custom.bat D:\path\to\prompt.txt
  pause
  exit /b 1
)

python D:\kedai-ops\scripts\claude_opus.py --prompt-file "%~1" --model claude-opus-4.6
echo.
pause
