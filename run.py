#!/usr/bin/env python3
"""
口播视频生成 - 统一启动入口（单进程版）

在同一个进程中启动：
  1. FastAPI 后端 — uvicorn 后台线程
  2. Streamlit 前端 — 同进程内启动

启动后在浏览器打开 http://127.0.0.1:8501 使用。
"""

import os
import sys
import time
import signal
import atexit
import threading
import webbrowser
import socket
from pathlib import Path


def _get_data_dir():
    """获取用户数据目录（可写）。PyInstaller打包后不写入只读的_MEPASS"""
    if getattr(sys, 'frozen', False):
        if sys.platform == "darwin":
            return Path.home() / "Library" / "Application Support" / "MoneyPrinterTurbo"
        elif sys.platform == "win32":
            return Path(os.environ.get("APPDATA", "")) / "MoneyPrinterTurbo"
        else:
            xdg = os.environ.get("XDG_CONFIG_HOME", "")
            return Path(xdg) / "MoneyPrinterTurbo" if xdg else Path.home() / ".config" / "MoneyPrinterTurbo"
    return Path(__file__).resolve().parent / "storage"


DATA_DIR = _get_data_dir()
RESOURCE_DIR = Path(sys._MEIPASS) if (getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS')) else Path(__file__).resolve().parent

os.environ["MPT_DATA_DIR"] = str(DATA_DIR)
os.environ.setdefault("PYTHONPATH", str(RESOURCE_DIR))

_WEBUI_HOST = "127.0.0.1"
_WEBUI_PORT = 8501
_BACKEND_PORT = 8080

_backend_thread = None
_backend_server = None


def _load_backend_port():
    try:
        import toml
        cfg_path = DATA_DIR / "config.toml"
        if cfg_path.exists():
            cfg = toml.load(str(cfg_path))
            return int(cfg.get("listen_port", 8080))
    except Exception:
        pass
    return 8080


def _port_in_use(port, host="127.0.0.1"):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0


def start_backend_in_thread():
    """在后台线程中启动 FastAPI 后端（uvicorn）"""
    import uvicorn
    from app.asgi import app
    from app.config import config as app_config
    import asyncio

    host = app_config.listen_host if hasattr(app_config, 'listen_host') else "127.0.0.1"
    port = _BACKEND_PORT

    config = uvicorn.Config(app, host=host, port=port, log_level="warning")
    server = uvicorn.Server(config)

    global _backend_server
    _backend_server = server

    print(f"[后端] 启动中... http://{host}:{port}/docs")
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())
    except Exception as e:
        print(f"[后端] 异常: {e}")
    print("[后端] 已停止")


def start_frontend():
    """同进程内启动 Streamlit 前端，通过 CLI 方式"""
    from streamlit.web import cli as stcli
    import sys as _sys

    webui_script = str(RESOURCE_DIR / "webui" / "Main.py")
    print(f"[前端] 启动中...")

    # Streamlit 内部会修改 sys.argv，保存后恢复
    saved_argv = _sys.argv[:]
    _sys.argv = [
        "streamlit", "run", webui_script,
        f"--server.address={_WEBUI_HOST}",
        f"--server.port={_WEBUI_PORT}",
        "--server.enableCORS=True",
        "--browser.gatherUsageStats=False",
        "--server.showEmailPrompt=False",
        "--server.headless=True",
        "--server.fileWatcherType=none",
    ]

    try:
        stcli.main()
    except SystemExit:
        pass
    finally:
        _sys.argv = saved_argv


def wait_for_port(port, timeout=120, description=""):
    """等待端口就绪"""
    elapsed = 0
    while elapsed < timeout:
        if _port_in_use(port, _WEBUI_HOST):
            print(f"[{description}] 就绪 → http://{_WEBUI_HOST}:{port}")
            return True
        time.sleep(0.5)
        elapsed += 0.5
    return False


def cleanup():
    print("\n正在停止服务...")
    if _backend_server:
        _backend_server.should_exit = True
    time.sleep(1)


def main():
    global _BACKEND_PORT
    _BACKEND_PORT = _load_backend_port()

    # 确保数据目录存在
    for sub in ["logs", "tasks", "cache_videos"]:
        (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)

    # 首次运行：复制配置模板
    config_dst = DATA_DIR / "config.toml"
    if not config_dst.exists():
        example_src = RESOURCE_DIR / "config.example.toml"
        if not example_src.exists():
            example_src = RESOURCE_DIR / "config.toml"
        if example_src.exists():
            import shutil
            shutil.copy2(str(example_src), str(config_dst))
            print(f"[初始化] 已创建配置文件: {config_dst}")
    os.environ["MPT_CONFIG_FILE"] = str(config_dst)

    print("=" * 60)
    print("  口播视频生成 1.0 (单进程模式)")
    print("=" * 60)
    print(f"  数据目录: {DATA_DIR}")
    print(f"  资源目录: {RESOURCE_DIR}")
    print("=" * 60)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    # 后台线程启动 FastAPI
    import asyncio
    backend_thread = threading.Thread(target=start_backend_in_thread, daemon=True)
    backend_thread.start()

    # 等待后端就绪
    print("\n等待后端启动...")
    if not wait_for_port(_BACKEND_PORT, timeout=60, description="后端"):
        print("\n⚠️ 后端启动超时，请检查配置")
        sys.exit(1)

    # 后端 OK，启动前端
    time.sleep(1)
    print(f"\n打开浏览器访问: http://{_WEBUI_HOST}:{_WEBUI_PORT}")

    url = f"http://{_WEBUI_HOST}:{_WEBUI_PORT}"
    try:
        webbrowser.open(url)
    except Exception:
        pass

    # 同进程内启动 Streamlit（阻塞直到退出）
    start_frontend()


if __name__ == "__main__":
    main()
