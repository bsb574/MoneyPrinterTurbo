---
AIGC:
    Label: "1"
    ContentProducer: 001191440300708461136T1XGW3
    ProduceID: 4f894c1f4497151e134335373802667c_1204323f817c11f1b625525400e6dd8f
    ReservedCode1: YOtIylGOON7ufKm/Em7rn5z84dc7lb638vysao0b2iTiMO7HEvpkenLmoOIxQdRbi+PTPcuWwcCyaEQlGyy4bq7BcC4Q+bFVrE6LkDJrpkAYD+06J/VtNKRcszpcUUXMe0eQ1HOUZv7obPhLnSdHtbYjHkPE/On0NNnqLeuyarGE0m6Vd1Z2pLynMzY=
    ContentPropagator: 001191440300708461136T1XGW3
    PropagateID: 4f894c1f4497151e134335373802667c_1204323f817c11f1b625525400e6dd8f
    ReservedCode2: YOtIylGOON7ufKm/Em7rn5z84dc7lb638vysao0b2iTiMO7HEvpkenLmoOIxQdRbi+PTPcuWwcCyaEQlGyy4bq7BcC4Q+bFVrE6LkDJrpkAYD+06J/VtNKRcszpcUUXMe0eQ1HOUZv7obPhLnSdHtbYjHkPE/On0NNnqLeuyarGE0m6Vd1Z2pLynMzY=
---

# 口播视频生成 - Windows 安装说明

## 一、获取程序

1. 打开 https://github.com/bsb574/MoneyPrinterTurbo/actions
2. 点击最新一次成功的构建（绿色勾）
3. 滚动到页面底部 **Artifacts** 区域
4. 点击 **口播视频生成-Windows** 下载 zip 包

## 二、安装（解压即用）

1. 将下载的 zip 解压到任意目录（如 `D:\口播视频生成\`）
2. 进入解压后的 `口播视频生成` 文件夹
3. 双击 **`run.exe`** 启动程序

> 无需安装 Python、FFmpeg 或任何其他依赖，所有组件已打包在内。

## 三、启动后

1. 程序启动后会自动打开浏览器访问 `http://127.0.0.1:8501`
2. 如浏览器未自动打开，手动在浏览器输入该地址
3. 首次运行会自动在程序目录生成 `config.toml` 配置文件

## 四、配置

如需使用 AI 文案生成、语音合成等高级功能，编辑程序目录下的 `config.toml`，填写对应的 API Key：

- OpenAI / 通义千问 / Gemini 等 LLM 的 API Key
- Azure 语音服务密钥（可选）
- Pexels API Key（可选，用于自动匹配视频素材）

## 五、注意事项

- **杀毒软件误报**：PyInstaller 打包的程序可能被部分杀软（360、腾讯管家等）误报为风险程序，添加信任/白名单即可
- **网络要求**：Edge TTS 语音合成、AI 文案生成、Pexels 视频素材等功能需要网络连接
- **程序关闭**：直接关闭命令行窗口或浏览器页面即可，后台服务会自动终止
- **数据存储**：生成的视频保存在程序目录下的 `storage/` 文件夹中

## 六、常见问题

**Q：双击 run.exe 闪退？**
A：右键 run.exe → 以管理员身份运行。如仍闪退，检查杀毒软件是否拦截。

**Q：浏览器打开后页面空白？**
A：等待几秒让后端服务完全启动，刷新页面即可。

**Q：端口被占用？**
A：程序默认使用 8080（后端）和 8501（前端）端口，确保这些端口未被其他程序占用。
*（内容由AI生成，仅供参考）*
