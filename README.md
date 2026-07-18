# NecoL Codex 宠物

NecoL 是一个 Codex 桌面端自定义宠物包。

## 动画行为

- 待机：只保留睁眼、闭眼两帧。
- 工作与等待：完整六帧吃薯片动画，持续循环到状态结束。
- 鼠标悬停、问候、完成：继续播放待机动画。
- 失败：播放八帧失败动画。
- 拖拽：保留左右拖拽动画。
- 完全取消放鸽子动画。

运行时补丁是通用的 `running` / `waiting` 循环和本地工作状态映射，不包含 NecoL 专属状态机。

## 一键安装

下载 [release/NecoL-codex-pet.zip](release/NecoL-codex-pet.zip)，完整解压后运行 `安装.ps1`。

安装包会：

1. 将宠物文件安装到 `%USERPROFILE%\.codex\pets\necol`。
2. 在 `%LOCALAPPDATA%\NecoL-Codex` 创建当前 Codex 的可写本地副本。
3. 安装工作/等待无限循环补丁。
4. 复制已有 Codex 用户数据。
5. 创建桌面快捷方式 `NecoL Codex.lnk` 并启动。

官方 WindowsApps 包不会被修改。内置运行时适配 Codex `26.715.3651.0`。

## 给 Codex 自动安装

把完整 ZIP 交给 Codex，然后发送：

> 读取压缩包内的 `NecoL_说明.md`，按照说明一次性完成安装和验证。

## 文件

- `pet/`：宠物图集、清单和原始动画素材。
- `runtime/`：构建、运行时补丁和验证脚本。
- `release/NecoL-codex-pet.zip`：完整便携安装包。

## 发布包校验

SHA-256：

`943B99B153BA0FB31E19CD6AD520F54C1196D1011F11572001BC929F71010712`
