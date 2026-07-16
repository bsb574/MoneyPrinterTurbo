# 口播视频生成 - 打包与分发指南

## 运行方式（无需打包）

### Windows
双击 `start.bat` 即可启动，浏览器打开 http://127.0.0.1:8501

### macOS / Linux
```bash
python3 run.py
```

---

## 打包为独立 APP

### 准备工作

1. 安装 PyInstaller：
```bash
pip install pyinstaller
```

2. 确保 FFmpeg 已安装并可在命令行中访问（`ffmpeg -version`）。

### Windows 打包

在 **Windows 机器** 上运行：
```bash
python build.py
```

输出目录：`dist/口播视频生成/`，包含：
- `run.exe` — 主程序入口，双击启动
- 所有依赖 DLL 和 Python 库
- 资源文件（字体、BGM、图标等）

### macOS 打包

```bash
python build.py
```

输出目录：`dist/口播视频生成/`

---

## 打包后分发注意事项

1. **首次运行**：程序会自动从 `config.example.toml` 创建 `config.toml`
2. **FFmpeg**：需确保系统有 FFmpeg，或打包时自动包含
3. **网络依赖**：Edge TTS 和 Pexels API 需要网络连接
4. **杀软误报**：PyInstaller 打包的程序可能被部分杀毒软件误报，添加白名单即可
5. **免安装运行**：打包后的目录可以复制到任何 Windows 电脑直接运行，无需安装 Python

---

## 文件清单（打包前必需）

```
resource/
  fonts/        — 字幕字体文件
  songs/        — 背景音乐
  public/       — 静态资源
webui/
  i18n/         — 多语言翻译
  Main.py       — WebUI 界面
app/            — 后端服务代码
config.example.toml  — 配置模板
main.py         — 后端入口
run.py          — 统一启动入口
build.py        — 打包脚本
```

## GitHub Actions 自动构建

项目根目录已包含 `.github/workflows/build.yml`，推送代码到 GitHub 后：
1. Actions 会自动在 Windows 环境打包
2. 构建产物以 zip 包形式上传到 Artifacts
3. 也可以在 Release 页面下载
