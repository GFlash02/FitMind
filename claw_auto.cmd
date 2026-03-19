@echo off
chcp 65001 > nul 2>&1
set PYTHONUTF8=1
c:\python314\python.exe -X utf8 C:\Users\admin\.openclaw\workspace\lobster-contest\assistant\automation.py %*
