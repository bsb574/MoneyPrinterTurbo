#!/usr/bin/env python3
"""
口播视频生成 - 打包脚本

使用 PyInstaller 将项目打包为独立可执行程序。

Windows 打包（在 Windows 上运行）:
    pip install pyinstaller
    python build.py

macOS 打包（在 macOS 上运行）:
    pip install pyinstaller
    python build.py

打包产物在 dist/口播视频生成/ 目录下，可独立复制到任意电脑运行。
"""

import os
import sys
import shutil
import platform
import zipfile
import urllib.request
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"

APP_NAME = "口播视频生成"


def ensure_ffmpeg() -> Path | None:
    """确保 FFmpeg 二进制存在。未安装时自动下载（Windows/macOS）。"""
    # 先检查系统 PATH
    ffmpeg_bin = shutil.which("ffmpeg") or shutil.which("ffmpeg.exe")
    if ffmpeg_bin:
        print(f"✅ 找到系统 FFmpeg: {ffmpeg_bin}")
        return Path(ffmpeg_bin)

    # 检查项目内是否已下载
    local_ffmpeg = ROOT_DIR / "ffmpeg.exe" if sys.platform == "win32" else ROOT_DIR / "ffmpeg"
    if local_ffmpeg.exists():
        print(f"✅ 找到本地 FFmpeg: {local_ffmpeg}")
        return local_ffmpeg

    # 自动下载
    print("📥 下载 FFmpeg...")
    base_dir = ROOT_DIR
    try:
        if sys.platform == "win32":
            url = "https://www.gyan.dev/ffmpeg/builds/ffmpeg-release-essentials.zip"
            zip_path = base_dir / "ffmpeg.zip"
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                for f in zf.namelist():
                    if f.endswith("ffmpeg.exe"):
                        zf.extract(f, base_dir)
                        extracted = base_dir / f
                        shutil.move(str(extracted), str(base_dir / "ffmpeg.exe"))
                        break
            zip_path.unlink()
            return base_dir / "ffmpeg.exe"
        else:
            url = "https://evermeet.cx/ffmpeg/getrelease/zip"
            zip_path = base_dir / "ffmpeg.zip"
            urllib.request.urlretrieve(url, zip_path)
            with zipfile.ZipFile(zip_path, "r") as zf:
                zf.extract("ffmpeg", base_dir)
            zip_path.unlink()
            os.chmod(base_dir / "ffmpeg", 0o755)
            return base_dir / "ffmpeg"
    except Exception as e:
        print(f"⚠️ FFmpeg 下载失败: {e}")
        return None


def get_data_files():
    """收集需要打包的数据文件"""
    data_files = []

    resource_dir = ROOT_DIR / "resource"
    if resource_dir.exists():
        for item in resource_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(ROOT_DIR)
                data_files.append((str(item), str(rel.parent)))

    i18n_dir = ROOT_DIR / "webui" / "i18n"
    if i18n_dir.exists():
        for item in i18n_dir.glob("*.json"):
            data_files.append((str(item), "webui/i18n"))

    example_config = ROOT_DIR / "config.example.toml"
    if example_config.exists():
        data_files.append((str(example_config), "."))

    # 如果项目目录有兼容的 config.toml，也打包进去作为初始配置
    config_toml = ROOT_DIR / "config.toml"
    if config_toml.exists():
        data_files.append((str(config_toml), "."))

    ffmpeg = ensure_ffmpeg()
    if ffmpeg:
        data_files.append((str(ffmpeg), "."))

    return data_files


def get_hidden_imports():
    """PyInstaller 可能遗漏的隐式导入"""
    return [
        # 项目核心模块
        "app", "app.asgi", "app.router", "app.config", "app.config.config",
        "app.services", "app.services.voice", "app.services.video",
        "app.services.subtitle", "app.services.task", "app.services.material",
        "app.services.llm", "app.services.state", "app.services.upload_post",
        "app.controllers", "app.controllers.ping",
        "app.controllers.v1", "app.controllers.v1.video", "app.controllers.v1.llm",
        "app.controllers.manager", "app.controllers.manager.memory_manager",
        "app.models", "app.models.schema", "app.models.const", "app.models.exception",
        "app.utils", "app.utils.utils", "app.utils.file_security",
        # 第三方库
        "pydantic", "pydantic.dataclasses",
        "toml", "tomllib",
        "moviepy", "moviepy.video.tools.subtitles",
        "moviepy.video.io.VideoFileClip", "moviepy.video.io.ffmpeg_reader",
        "moviepy.audio.io.AudioFileClip",
        "edge_tts", "requests", "loguru", "numpy",
        "PIL", "PIL.Image", "PIL.ImageDraw", "PIL.ImageFont",
        "pydub", "pydub.playback",
        # Streamlit
        "streamlit", "streamlit.web.bootstrap",
        "streamlit.runtime", "streamlit.runtime.scriptrunner",
        # FastAPI + uvicorn
        "fastapi", "uvicorn", "uvicorn.loops", "uvicorn.loops.auto",
        "uvicorn.protocols", "uvicorn.protocols.http", "uvicorn.protocols.http.auto",
        "python_multipart",
        # OpenAI SDK
        "openai",
    ]


def get_excludes():
    """排除不需要的大文件，减小包体积"""
    return [
        "tkinter", "tcl", "tk",
        "matplotlib", "scipy", "pandas",
        "IPython", "jupyter", "notebook",
        "pip", "setuptools", "wheel",
        "pytest", "unittest", "test",
        "sqlite3", "sqlalchemy",
        "curses", "readline",
        "lib2to3",
    ]


def get_pyinstaller_args():
    """构建 PyInstaller 命令行参数"""
    data_files = get_data_files()
    hidden = get_hidden_imports()
    excludes = get_excludes()

    # Windows 特有：无控制台窗口（运行时不弹 cmd）
    is_windows = sys.platform == "win32"

    args = [
        "--clean",
        "--noconfirm",
        "--onedir",
        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        # 排除不需要的模块，减少包体积
        *[f"--exclude-module={m}" for m in excludes],
        *[f"--hidden-import={m}" for m in hidden],
        # 复制包元数据（moviepy/streamlit/numpy 等通过 importlib.metadata 读取版本）
        "--copy-metadata", "moviepy",
        "--copy-metadata", "numpy",
        "--copy-metadata", "streamlit",
        "--copy-metadata", "fastapi",
    ]

    for src, dst in data_files:
        # Windows 上用分号，POSIX 用冒号
        sep = ";" if is_windows else ":"
        args.append(f"--add-data={src}{sep}{dst}")

    if is_windows:
        # Windows 下不弹控制台，但保留日志输出到文件
        # 如果调试需要看控制台，注释这行
        # args.append("--noconsole")
        pass

    args.append(str(ROOT_DIR / "run.py"))
    return args


def build():
    """执行打包"""
    import PyInstaller.__main__
    PyInstaller.__main__.run(get_pyinstaller_args())


def post_build():
    """打包后处理：复制额外的运行时文件，清理临时目录"""
    out_dir = DIST_DIR / APP_NAME

    if not out_dir.exists():
        print("❌ 打包输出目录不存在")
        return

    # 创建必要的运行时目录
    for sub in ["storage", "storage/logs", "storage/tasks", "storage/cache_videos",
                "storage/temp", "storage/local_videos"]:
        (out_dir / sub).mkdir(parents=True, exist_ok=True)

    # 打包时 ffmpeg 作为数据文件会放在根目录，确认下
    ffmpeg_bin = out_dir / "ffmpeg.exe" if sys.platform == "win32" else out_dir / "ffmpeg"
    if not ffmpeg_bin.exists():
        # 尝试从 build 产物中找
        for f in out_dir.iterdir():
            if f.name.startswith("ffmpeg"):
                print(f"ℹ️ FFmpeg 路径: {f.name}")

    # 如果当前机器有 config.toml，也复制过去
    local_config = ROOT_DIR / "config.toml"
    if local_config.exists() and not (out_dir / "config.toml").exists():
        shutil.copy2(local_config, out_dir / "config.toml")

    print(f"\n✅ 打包完成！")
    print(f"程序目录: {out_dir}")
    exe_name = "run.exe" if sys.platform == "win32" else "run"
    print(f"启动文件: {out_dir / exe_name}")
    print(f"\n📁 将此目录完整复制到任意电脑即可运行，无需安装 Python 或任何依赖。")


def main():
    system = platform.system().lower()
    print("=" * 60)
    print(f"  口播视频生成 - 打包工具")
    print(f"  目标平台: {system}")
    print("=" * 60)

    if not shutil.which("pyinstaller"):
        print("❌ 未安装 PyInstaller")
        print("   运行: pip install pyinstaller")
        sys.exit(1)

    # 清理旧的构建产物
    for d in [BUILD_DIR, DIST_DIR]:
        if d.exists():
            print(f"清理: {d}")
            shutil.rmtree(d)

    build()
    post_build()


if __name__ == "__main__":
    main()
