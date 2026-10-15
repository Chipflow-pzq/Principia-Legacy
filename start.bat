@echo off
set PYTHONUTF8=1
cd /d "%~dp0"
py -3 start.py %*
