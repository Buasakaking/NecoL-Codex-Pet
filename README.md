# NecoL Codex 宠物

适用于 Codex 桌面端的 NecoL 动画宠物：双帧眨眼待机、工作/等待时循环吃薯片，并包含失败和左右拖拽动画。

## 部署入口

完整部署方案见 [`CODEX_INSTALL.md`](CODEX_INSTALL.md)。自动化工具读取本仓库后，按该方案完成版本检查、下载校验、解压、安装、启动和验证。

## PowerShell 一键安装

```powershell
$script = "$env:TEMP\NecoL-Codex-Pet-install.ps1"
Invoke-WebRequest 'https://raw.githubusercontent.com/Buasakaking/NecoL-Codex-Pet/main/install.ps1' -OutFile $script
powershell -NoProfile -ExecutionPolicy Bypass -File $script
```

## 手动安装

1. 打开 [Latest Release](https://github.com/Buasakaking/NecoL-Codex-Pet/releases/latest)。
2. 下载 `NecoL-codex-pet.zip`。
3. 完整解压 ZIP，不要只打开压缩包内单个文件。
4. 运行解压目录中的 `install.ps1` 或 `安装.ps1`。
5. 安装完成后从桌面快捷方式 `NecoL Codex.lnk` 启动。

## 安装器会做什么

1. 安装 `pet.json` 和 `spritesheet.webp` 到 `%USERPROFILE%\.codex\pets\necol`。
2. 复制当前 Codex 桌面端到 `%LOCALAPPDATA%\NecoL-Codex`，保留官方 WindowsApps 安装不变。
3. 安装工作/等待循环与本地任务状态映射。
4. 复制现有 Codex 用户数据。
5. 创建桌面快捷方式并启动 NecoL Codex。

## 兼容性

- 系统：Windows。
- 当前内置运行时适配 Codex `26.715.3651.0`。
- 安装脚本检测到其他版本时会停止，不会覆盖不兼容文件。

## 验证标准

- 待机只显示睁眼、闭眼两种画面。
- 本地任务运行或等待时，完整六帧吃薯片动画持续循环。
- 任务结束后恢复待机。
- 失败状态播放八帧失败动画。
- 鼠标悬停、问候和完成状态保持待机动画。

## 仓库结构

- [`CODEX_INSTALL.md`](CODEX_INSTALL.md)：给 Codex 代理读取的完整安装协议。
- [`install.ps1`](install.ps1)：从 Latest Release 下载并安装的引导脚本。
- `pet/`：图集、清单和原始动画素材。
- `runtime/`：构建、补丁和验证脚本。
- `release/NecoL-codex-pet.zip`：完整离线安装包。

## 当前发布包校验

SHA-256：

`ADC88616817E9BE2D272C58689307FEA1B674E725EABE521585BE1304803FCFE`
