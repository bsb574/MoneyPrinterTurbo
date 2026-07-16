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

# 项目根目录
ROOT_DIR = Path(__file__).resolve().parent

# 环境变量：确保能导入项目模块
os.environ.setdefault("PYTHONPATH", str(ROOT_DIR))
os.environ.setdefault("MPT_WEBUI_HOST", "127.0.0.1")
os.environ.setdefault("MPT_WEBUI_PORT", "8501")

# 从配置读取后端端口
_BACKEND_PORT = "8080"
_WEBUI_PORT = "8501"
_WEBUI_HOST = "127.0.0.1"

# 保存子进程引用，便于退出时清理
_processes = []


def _load_backend_port():
    """从 config.toml 中读取后端端口"""
    try:
        import toml
        config_path = ROOT_DIR / "config.toml"
        if config_path.exists():
            cfg = toml.load(str(config_path))
            port = cfg.get("listen_port", 8080)
            return str(port)
    except Exception:
        pass
    return "8080"


def _find_streamlit():
    """查找 streamlit 可执行文件路径"""
    # 1. venv 中的 streamlit
    venv_streamlit = (
        ROOT_DIR / "venv" / "bin" / "streamlit"
        if sys.platform != "win32"
        else ROOT_DIR / "venv" / "Scripts" / "streamlit.exe"
    )
    if venv_streamlit.exists():
        return str(venv_streamlit)
    # 2. 同目录下的 streamlit
    local = ROOT_DIR / "venv" / "bin" / "streamlit"
    if local.exists():
        return str(local)

    # 3. PATH 中的 streamlit
    import shutil
    return shutil.which("streamlit") or "streamlit"


def _find_python():
    """查找合适的 Python 解释器"""
    # 1. venv 中的 python
    venv_python = (
        ROOT_DIR / "venv" / "bin" / "python"
        if sys.platform != "win32"
        else ROOT_DIR / "venv" / "Scripts" / "python.exe"
    )
    if venv_python.exists():
        return str(venv_python)
    # 2. 当前解释器
    return sys.executable


def start_backend():
    """启动 FastAPI 后端"""
    python_exe = _find_python()
    backend_script = str(ROOT_DIR / "main.py")
    log_file = open(str(ROOT_DIR / "storage" / "logs" / "backend.log"), "a")
    proc = subprocess.Popen(
        [python_exe, backend_script],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "MPT_CONFIG_FILE": str(ROOT_DIR / "config.toml")},
    )
    _processes.append(("backend", proc, log_file))
    print(f"[后端] 启动中... PID={proc.pid}")
    return proc


def start_frontend():
    """启动 Streamlit 前端"""
    streamlit_exe = _find_streamlit()
    webui_script = str(ROOT_DIR / "webui" / "Main.py")
    log_file = open(str(ROOT_DIR / "storage" / "logs" / "frontend.log"), "a")
    proc = subprocess.Popen(
        [
            streamlit_exe,
            "run",
            webui_script,
            f"--server.address={_WEBUI_HOST}",
            f"--server.port={_WEBUI_PORT}",
            "--server.enableCORS=True",
            "--browser.gatherUsageStats=False",
            "--server.showEmailPrompt=False",
        ],
        stdout=log_file,
        stderr=subprocess.STDOUT,
        env={**os.environ, "PYTHONPATH": str(ROOT_DIR)},
    )
    _processes.append(("frontend", proc, log_file))
    print(f"[前端] 启动中... PID={proc.pid}")
    return proc


def wait_for_ports(timeout=30):
    """等待后端和前端就绪"""
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
            except:
                pass
            finally:
                s.close()

        if not frontend_ready:
            s = socket.socket()
            try:
                s.connect((_WEBUI_HOST, int(_WEBUI_PORT)))
                frontend_ready = True
                print(f"[前端] 就绪 → http://{_WEBUI_HOST}:{_WEBUI_PORT}")
            except:
                pass
            finally:
                s.close()

        if backend_ready and frontend_ready:
            return True
        time.sleep(0.5)

    return False


def cleanup():
    """退出时清理子进程"""
    for name, proc, log_file in _processes:
        if proc.poll() is None:
            print(f"停止 {name} PID={proc.pid}...")
            if sys.platform == "win32":
                proc.terminate()
            else:
                proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                proc.kill()
        log_file.close()


def main():
    global _BACKEND_PORT
    _BACKEND_PORT = _load_backend_port()

    # 确保目录存在
    os.makedirs(str(ROOT_DIR / "storage" / "logs"), exist_ok=True)
    os.makedirs(str(ROOT_DIR / "storage" / "tasks"), exist_ok=True)

    print("=" * 50)
    print("  口播视频生成 1.0")
    print("=" * 50)

    # 注册退出清理
    atexit.register(cleanup)
    signal.signal(signal.SIGINT, lambda s, f: sys.exit(0))
    signal.signal(signal.SIGTERM, lambda s, f: sys.exit(0))

    # 启动后端
    start_backend()
    time.sleep(1)

    # 启动前端
    start_frontend()

    # 等待就绪
    print("\n等待服务启动...")
    ready = wait_for_ports(timeout=60)
    if ready:
        url = f"http://{_WEBUI_HOST}:{_WEBUI_PORT}"
        print(f"\n✅ 启动完成！打开浏览器访问: {url}")
        try:
            webbrowser.open(url)
        except:
            pass
    else:
        print("\n⚠️ 服务启动超时，请检查日志文件: storage/logs/")

    print("\n按 Ctrl+C 停止所有服务")

    # 保持运行，等待子进程
    try:
        while all(p.poll() is None for _, p, _ in _processes):
            time.sleep(1)
    except KeyboardInterrupt:
        pass

    print("\n正在停止服务...")


if __name__ == "__main__":
    main()
