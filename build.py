#!/usr/bin/env python3
"""
口播视频生成 - 打包脚本

使用 PyInstaller 将项目打包为独立可执行程序。

Windows 打包（在 Windows 上运行）:
    python build.py

macOS 打包（在 macOS 上运行）:
    python build.py

需要先安装 PyInstaller:
    pip install pyinstaller
"""

import os
import sys
import shutil
import platform
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent
BUILD_DIR = ROOT_DIR / "build"
DIST_DIR = ROOT_DIR / "dist"

APP_NAME = "口播视频生成"


def find_ffmpeg():
    """找到 FFmpeg 二进制文件"""
    ffmpeg = shutil.which("ffmpeg")
    if ffmpeg:
        return Path(ffmpeg)
    # 检查项目内是否有
    for p in [ROOT_DIR / "ffmpeg.exe", ROOT_DIR / "ffmpeg"]:
        if p.exists():
            return p
    return None


def get_data_files():
    """收集需要打包的数据文件"""
    data_files = []

    # 资源文件
    resource_dir = ROOT_DIR / "resource"
    if resource_dir.exists():
        for item in resource_dir.rglob("*"):
            if item.is_file():
                rel = item.relative_to(ROOT_DIR)
                data_files.append((str(item), str(rel.parent)))

    # WebUI 国际化文件
    i18n_dir = ROOT_DIR / "webui" / "i18n"
    if i18n_dir.exists():
        for item in i18n_dir.glob("*.json"):
            data_files.append((str(item), "webui/i18n"))

    # 配置文件模板
    example_config = ROOT_DIR / "config.example.toml"
    if example_config.exists():
        data_files.append((str(example_config), "."))

    # FFmpeg（如果有）
    ffmpeg = find_ffmpeg()
    if ffmpeg:
        data_files.append((str(ffmpeg), "."))

    # BGM 文件
    songs_dir = ROOT_DIR / "resource" / "songs"
    if songs_dir.exists():
        for f in songs_dir.glob("*.mp3"):
            data_files.append((str(f), "resource/songs"))

    return data_files


def get_hidden_imports():
    """PyInstaller 可能遗漏的隐式导入"""
    return [
        "app.services.voice",
        "app.services.video",
        "app.services.subtitle",
        "app.services.task",
        "app.services.material",
        "app.services.llm",
        "app.services.state",
        "app.controllers.v1.video",
        "app.controllers.v1.llm",
        "app.controllers.ping",
        "app.config.config",
        "app.models.schema",
        "app.models.const",
        "app.utils.utils",
        "pydantic",
        "toml",
        "moviepy.video.tools.subtitles",
        # 音频解码
        "edge_tts",
        # PIL 插件
        "PIL.ImageDraw",
        "PIL.ImageFont",
    ]


def build_windows():
    """Windows 打包配置"""
    import PyInstaller.__main__

    data_files = get_data_files()
    data_args = []
    for src, dst in data_files:
        data_args.append(f"--add-data={src}{os.pathsep}{dst}")

    hidden = get_hidden_imports()
    hidden_args = [f"--hidden-import={m}" for m in hidden]

    args = [
        "--clean",
        "--noconfirm",
        "--onedir",
        # 窗口模式（无控制台），去掉可看到日志
        # "--noconsole",
        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        "--icon=NONE",
        # 资源
        *data_args,
        *hidden_args,
        # 入口
        str(ROOT_DIR / "run.py"),
    ]

    print("=" * 50)
    print(f"打包 {APP_NAME} for Windows")
    print(f"输出目录: {DIST_DIR}")
    print("=" * 50)

    PyInstaller.__main__.run(args)

    print(f"\n✅ 打包完成！")
    print(f"程序位于: {DIST_DIR / APP_NAME / 'run.exe'}")
    print("首次运行时会自动创建 config.toml")


def build_macos():
    """macOS 打包配置"""
    import PyInstaller.__main__

    data_files = get_data_files()
    data_args = []
    for src, dst in data_files:
        data_args.append(f"--add-data={src}{os.pathsep}{dst}")

    hidden = get_hidden_imports()
    hidden_args = [f"--hidden-import={m}" for m in hidden]

    args = [
        "--clean",
        "--noconfirm",
        "--onedir",
        f"--name={APP_NAME}",
        f"--distpath={DIST_DIR}",
        f"--workpath={BUILD_DIR}",
        *data_args,
        *hidden_args,
        str(ROOT_DIR / "run.py"),
    ]

    print("=" * 50)
    print(f"打包 {APP_NAME} for macOS")
    print(f"输出目录: {DIST_DIR}")
    print("=" * 50)

    PyInstaller.__main__.run(args)

    print(f"\n✅ 打包完成！")
    print(f"程序位于: {DIST_DIR / APP_NAME / 'run'}")


def main():
    if not shutil.which("pyinstaller"):
        print("❌ 未安装 PyInstaller，请先运行: pip install pyinstaller")
        sys.exit(1)

    system = platform.system().lower()
    if system == "windows":
        build_windows()
    elif system == "darwin":
        build_macos()
    else:
        print(f"当前系统: {system}")
        print("支持 Windows 和 macOS 打包。")


if __name__ == "__main__":
    main()
