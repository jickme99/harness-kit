@echo off
setlocal EnableExtensions
set PYTHONUNBUFFERED=1
REM conda's `python` is often python.cmd, which drops piped stdin. Prefer python.exe.
set "PY="
for /f "delims=" %%i in ('where python.exe 2^>nul') do (
  set "PY=%%i"
  goto :run
)
:run
if not defined PY set "PY=python"
"%PY%" -u "%~dp0..\..\scripts\cursor_hook_bridge.py"
exit /b %ERRORLEVEL%
