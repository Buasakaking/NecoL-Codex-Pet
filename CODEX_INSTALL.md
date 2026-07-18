# Codex 一次性安装协议

目标：在 Windows 上安装并启动 `NecoL Codex 宠物`。请完整执行，不要只下载 `pet.json` 或 `spritesheet.webp`。

## 操作步骤

1. 确认系统为 Windows，并确认已安装 Codex 桌面端。
2. 读取当前 Codex 包版本；本发布包要求 `26.715.3651.0`。版本不匹配时停止并报告，不要覆盖运行时。
3. 下载：
   `https://github.com/Buasakaking/NecoL-Codex-Pet/releases/latest/download/NecoL-codex-pet.zip`
4. 计算 SHA-256，必须等于：
   `ADC88616817E9BE2D272C58689307FEA1B674E725EABE521585BE1304803FCFE`
5. 将 ZIP 完整解压到临时目录。
6. 阅读解压后的 `NecoL_说明.md`。
7. 使用 PowerShell 执行解压目录中的 `install.ps1`。
8. 验证以下文件存在：
   - `%USERPROFILE%\.codex\pets\necol\pet.json`
   - `%USERPROFILE%\.codex\pets\necol\spritesheet.webp`
   - `%LOCALAPPDATA%\NecoL-Codex\26.715.3651.0\app\ChatGPT.exe`
   - 桌面 `NecoL Codex.lnk`
9. 确认当前运行的 `ChatGPT.exe` 和 `codex.exe` 路径来自 `%LOCALAPPDATA%\NecoL-Codex`。
10. 确认宠物选择为 `custom:necol`、宠物浮窗开启。
11. 发起一个本地任务，验证工作时持续播放六帧吃薯片动画；任务结束后恢复双帧待机。

## 部署约束

- 不要修改官方 WindowsApps 目录；安装器会创建可写本地副本。
- 不要只复制 `pet.json` 或 `spritesheet.webp`，否则不会有工作/等待无限循环。
- 安装失败时保留临时目录和错误信息，先报告版本、校验和及失败步骤。
- 回滚使用解压目录中的 `Restore-WorkLoop.ps1`，它只恢复本地副本的原始运行时。
