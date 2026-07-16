@echo off
chcp 65001 >nul
title 口播视频生成 1.0

echo =============================================
echo   口播视频生成 1.0
echo =============================================
echo.

REM 检查 Python
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo ❌ 未找到 Python，请先安装 Python 3.9+
    pause
    exit /b 1
)

REM 检查 venv
if not exist "venv\Scripts\python.exe" (
    echo 创建虚拟环境...
    python -m venv venv
    if %errorlevel% neq 0 (
        echo ❌ 创建虚拟环境失败
        pause
        exit /b 1
    )
    echo 安装依赖...
    venv\Scripts\pip install moviepy==2.2.1 edge_tts==7.2.7 loguru requests pydantic toml numpy pillow streamlit fastapi uvicorn python-multipart -q
)

echo 启动服务...
start "口播视频生成-后端" /B venv\Scripts\python main.py
echo 后端启动中...
timeout /t 3 /nobreak >nul

echo 启动前端...
start "口播视频生成-前端" /B venv\Scripts\streamlit run webui/Main.py --server.address=127.0.0.1 --server.port=8501 --server.enableCORS=True --browser.gatherUsageStats=False

echo.
echo ✅ 启动完成！
echo 打开浏览器访问: http://127.0.0.1:8501
echo.
echo 关闭本窗口即可停止所有服务。
pause
