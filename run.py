#!/usr/bin/env python3
"""
口播视频生成 - 统一启动入口

同时启动：
  1. FastAPI 后端（提供 API + 视频下载）
  2. Streamlit 前端（WebUI 操作界面）

启动后在浏览器打开 http://127.0.0.1:8501 使用。
"""

import os
import sys
import subprocess
import time
import signal
import atexit
import webbrowser
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
os.environ["MPT_RESOURCE_DIR"] = str(RESOURCE_DIR)
os.environ.setdefault("PYTHONPATH", str(RESOURCE_DIR))
os.environ.setdefault("MPT_WEBUI_HOST", "127.0.0.1")
os.environ.setdefault("MPT_WEBUI_PORT", "8501")

_BACKEND_PORT = "8080"
_WEBUI_PORT = "8501"
_WEBUI_HOST = "127.0.0.1"
_processes = []


def _find_python():
    if getattr(sys, 'frozen', False):
        return sys.executable
    venv_py = RESOURCE_DIR / "venv" / "bin" / "python"
    if sys.platform != "win32" and venv_py.exists():
        return str(venv_py)
    venv_py_w = RESOURCE_DIR / "venv" / "Scripts" / "python.exe"
    if sys.platform == "win32" and venv_py_w.exists():
        return str(venv_py_w)
    return sys.executable


def _load_backend_port():
    try:
        import toml
        cfg_path = DATA_DIR / "config.toml"
        if cfg_path.exists():
            cfg = toml.load(str(cfg_path))
            return str(cfg.get("listen_port", 8080))
    except Exception:
        pass
    return "8080"


def start_backend():
    python_exe = _find_python()
    backend_script = str(RESOURCE_DIR / "main.py")
    logs_dir = DATA_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(str(logs_dir / "backend.log"), "a")
    proc = subprocess.Popen(
        [python_exe, backend_script],
        stdout=log_file, stderr=subprocess.STDOUT,
        env={**os.environ},
    )
    _processes.append(("backend", proc, log_file))
    print(f"[后端] 启动中... PID={proc.pid}")
    return proc


def start_frontend():
    python_exe = _find_python()
    webui_script = str(RESOURCE_DIR / "webui" / "Main.py")
    logs_dir = DATA_DIR / "logs"
    logs_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(str(logs_dir / "frontend.log"), "a")
    proc = subprocess.Popen(
        [python_exe, "-m", "streamlit", "run", webui_script,
         f"--server.address={_WEBUI_HOST}", f"--server.port={_WEBUI_PORT}",
         "--server.enableCORS=True", "--browser.gatherUsageStats=False",
         "--server.showEmailPrompt=False"],
        stdout=log_file, stderr=subprocess.STDOUT,
        env={**os.environ},
    )
    _processes.append(("frontend", proc, log_file))
    print(f"[前端] 启动中... PID={proc.pid}")
    return proc


def wait_for_ports(timeout=30):
    import socket
    backend_ready = False
    frontend_ready = False
    start = time.time()
    while time.time() - start < timeout:
        if not backend_ready:
            s = socket.socket()
            try:
                s.connect((_WEBUI_HOST, int(_BACKEND_PORT)))
                backend_ready = True
                print(f"[后端] 就绪 → http://{_WEBUI_HOST}:{_BACKEND_PORT}/docs")
            except: pass
            finally: s.close()
        if not frontend_ready:
            s = socket.socket()
            try:
                s.connect((_WEBUI_HOST, int(_WEBUI_PORT)))
                frontend_ready = True
                print(f"[前端] 就绪 → http://{_WEBUI_HOST}:{_WEBUI_PORT}")
            except: pass
            finally: s.close()
        if backend_ready and frontend_ready:
            return True
        time.sleep(0.5)
    return False


def cleanup():
    for name, proc, log_file in _processes:
        if proc.poll() is None:
            print(f"停止 {name} PID={proc.pid}...")
            if sys.platform == "win32":
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            try: proc.wait(timeout=5)
            except subprocess.TimeoutExpired: proc.kill()
        log_file.close()


def main():
    global _BACKEND_PORT
    _BACKEND_PORT = _load_backend_port()

    for sub in ["logs", "tasks", "cache_videos"]:
        (DATA_DIR / sub).mkdir(parents=True, exist_ok=True)

    # 首次运行：从打包资源复制 config.example.toml 为 config.toml
    config_dst = DATA_DIR / "config.toml"
    if not config_dst.exists():
        example_src = RESOURCE_DIR / "config.example.toml"
        if not example_src.exists():
            example_src = RESOURCE_DIR / "config.toml"
        if example_src.exists():
            import shutil
            shutil.copy2(str(example_src), str(config_dst))
            print(f"[初始化] 已创建配置文件: {config_dst}")
    # 设置环境变量让 app/config 使用数据目录下的配置
    os.environ["MPT_CONFIG_FILE"] = str(config_dst)

    print("=" * 50)
    print("  口播视频生成 1.0")
    print("=" * 50)
    print(f"  数据目录: {DATA_DIR}")
    print(f"  资源目录: {RESOURCE_DIR}")
    print("=" * 50)

    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    start_backend()
    time.sleep(1)
    start_frontend()

    print("\n等待服务启动...")
    ready = wait_for_ports(timeout=60)
    if ready:
        url = f"http://{_WEBUI_HOST}:{_WEBUI_PORT}"
        print(f"\n✅ 启动完成！打开浏览器访问: {url}")
        try: webbrowser.open(url)
        except: pass
    else:
        print("\n⚠️ 服务启动超时，请检查日志: " + str(DATA_DIR / "logs"))

    print("\n按 Ctrl+C 停止所有服务")
    try:
        while all(p.poll() is None for _, p, _ in _processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass
    print("\n正在停止服务...")


if __name__ == "__main__":
    main()
