@echo off
echo ============================
echo  AI 个人健康管理助理
echo  OpenClaw 集成版
echo ============================
echo.
cd /d "%~dp0"
c:\python314\python.exe -m streamlit run app_standalone.py --server.port 8502 --server.headless true --browser.gatherUsageStats false
pause
