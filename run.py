#!/usr/bin/env python3
"""
口播视频生成 - 单进程启动入口

启动 FastAPI 后端，浏览器打开内置 HTML 前端。
无需 Streamlit，打包体积小、启动快。
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

_WEB_HOST = "127.0.0.1"
_WEB_PORT = 3000
_backend_server = None


def _load_port():
    try:
        import toml
        cfg = DATA_DIR / "config.toml"
        if cfg.exists():
            return int(toml.load(str(cfg)).get("listen_port", _WEB_PORT))
    except Exception:
        pass
    return _WEB_PORT


def start_backend():
    """在后台线程中启动 uvicorn"""
    import uvicorn
    from app.asgi import app

    config = uvicorn.Config(app, host=_WEB_HOST, port=_WEB_PORT, log_level="warning")
    server = uvicorn.Server(config)
    global _backend_server
    _backend_server = server

    print(f"[后端] http://{_WEB_HOST}:{_WEB_PORT}")
    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(server.serve())
    except Exception as e:
        print(f"[后端] 异常: {e}")
    print("[后端] 已停止")


def wait_for_port(port, timeout=30):
    for _ in range(timeout * 2):
        s = socket.socket()
        try:
            s.settimeout(0.5)
            s.connect((_WEB_HOST, port))
            s.close()
            return True
        except Exception:
            time.sleep(0.5)
        finally:
            s.close()
    return False


def cleanup():
    print("\n正在停止...")
    if _backend_server:
        _backend_server.should_exit = True
    time.sleep(1)


def main():
    global _WEB_PORT
    _WEB_PORT = _load_port()

    for sub in ["logs", "tasks", "cache_videos"]:
        (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)

    config_dst = DATA_DIR / "config.toml"
    if not config_dst.exists():
        for src_name in ["config.example.toml", "config.toml"]:
            example = RESOURCE_DIR / src_name
            if example.exists():
                import shutil
                shutil.copy2(str(example), str(config_dst))
                print(f"[初始化] 已创建: {config_dst}")
                break
    os.environ["MPT_CONFIG_FILE"] = str(config_dst)

    print("=" * 50)
    print("  口播视频生成 1.0")
    print("=" * 50)
    print(f"  数据: {DATA_DIR}")
    print(f"  资源: {RESOURCE_DIR}")
    print("=" * 50)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    # 后台线程启动后端
    threading.Thread(target=start_backend, daemon=True).start()

    if not wait_for_port(_WEB_PORT):
        print(f"\n⚠️ 后端启动超时，请检查 {DATA_DIR}/logs/")
        input("按回车退出...")
        sys.exit(1)

    url = f"http://{_WEB_HOST}:{_WEB_PORT}"
    print(f"\n✅ 已启动: {url}")
    try:
        webbrowser.open(url)
    except Exception:
        pass
    print("\n按 Ctrl+C 停止")

    try:
        while _backend_server and not _backend_server.should_exit:
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    print("\n再见。")


if __name__ == "__main__":
    main()
