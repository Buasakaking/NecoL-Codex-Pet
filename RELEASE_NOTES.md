# NecoL codex宠物 v1.0.0

## 包含内容

- 睁眼/闭眼双帧待机动画。
- 工作与等待状态使用完整六帧吃薯片动画。
- 工作或等待期间持续循环，状态结束后回到待机。
- 失败动画与左右拖拽动画。
- 一键安装器、运行时补丁和完整验证脚本。

## 直接部署方案（Windows）

### 前置条件

- Windows 系统。
- 已安装 Codex 桌面端。
- 当前 Codex 版本为 `26.715.3651.0`。

### 安装步骤

1. 在本页面的 Assets 中下载 `NecoL-codex-pet.zip`。
2. 校验下载文件 SHA-256，必须是：

   `ADC88616817E9BE2D272C58689307FEA1B674E725EABE521585BE1304803FCFE`

3. 将 ZIP 完整解压到一个普通目录，不要直接在压缩包内运行脚本。
4. 运行解压目录中的 `install.ps1`；也可以运行中文文件名 `安装.ps1`。
5. 安装器会自动完成：
   - 将 `pet.json` 和 `spritesheet.webp` 安装到 `%USERPROFILE%\\.codex\\pets\\necol`。
   - 复制当前 Codex 到 `%LOCALAPPDATA%\\NecoL-Codex\\26.715.3651.0` 可写目录。
   - 安装工作/等待无限循环补丁和本地任务状态映射。
   - 复制已有 Codex 用户数据。
   - 创建桌面快捷方式 `NecoL Codex.lnk`。
   - 启动补丁版 Codex。

### 安装后验证

1. 当前运行的 `ChatGPT.exe` 和 `codex.exe` 路径应来自 `%LOCALAPPDATA%\\NecoL-Codex`，不是 `WindowsApps`。
2. 宠物选择应为 `custom:necol`，浮窗应处于开启状态。
3. 待机应只显示睁眼和闭眼两种画面。
4. 启动一个本地任务：宠物应持续播放六帧吃薯片动画。
5. 任务结束：宠物应回到双帧待机。
6. 等待用户输入时：宠物仍应持续吃薯片。
7. 失败时：宠物应播放失败动画。

### 回滚

运行解压目录中的 `Restore-WorkLoop.ps1`，它只恢复 `%LOCALAPPDATA%\\NecoL-Codex` 本地副本的原始 `app.asar`。官方 WindowsApps Codex 不会被修改。

### 版本不匹配

如果当前 Codex 不是 `26.715.3651.0`，安装器会停止并提示，不会覆盖不兼容文件。
