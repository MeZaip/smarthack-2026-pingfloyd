@echo off
rem Windows version of ./run.sh for cmd.exe users. Same options as run.ps1, e.g.:  run.cmd -Demo   run.cmd -NoAI
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0run.ps1" %*
