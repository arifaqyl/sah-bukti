@echo off
setlocal
cd /d D:\kedai-ops
python D:\kedai-ops\scripts\claude_opus.py --prompt-file D:\kedai-ops\docs\claude-video-brief.txt --model claude-opus-4.6 --output-file D:\kedai-ops\docs\claude-video-opus-output.md
echo.
echo Output saved to D:\kedai-ops\docs\claude-video-opus-output.md
pause
