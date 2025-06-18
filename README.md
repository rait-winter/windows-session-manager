# Windows会话管理器

[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.6+-blue.svg)](https://www.python.org/)
[![Windows](https://img.shields.io/badge/Platform-Windows%2010%2F11-blue.svg)](https://www.microsoft.com/windows)
[![Version](https://img.shields.io/badge/Version-1.0.0-green.svg)](CHANGELOG.md)

Windows会话管理器是一个强大的工具，可以帮助您保存和恢复Windows工作环境，包括打开的应用程序和窗口布局。无论您是需要在不同任务之间快速切换，还是想在重启后恢复工作环境，这个工具都能为您提供高效的解决方案。

## 功能特点

- **会话管理**：保存、加载和管理多个工作环境会话
- **智能窗口检测**：自动识别和排除系统窗口
- **应用程序识别**：根据进程路径和窗口标题识别应用程序
- **命令行支持**：通过命令行快速保存或恢复会话
- **系统集成**：支持开机自启动和系统托盘运行
- **多显示器支持**：保存和恢复跨多显示器的窗口布局
- **用户友好界面**：简洁直观的图形界面
- **热键支持**：使用快捷键快速保存和恢复会话
- **会话导入/导出**：便于在不同电脑间共享会话配置
- **特殊应用支持**：能够识别和恢复特殊应用程序（如PixPin、Everything等）
- **主题支持**：支持多种视觉主题和暗色模式

## 系统要求

- Windows 10/11
- Python 3.6+
- 依赖库：pygetwindow, pywin32, psutil, Pillow, keyboard, winshell, ttkthemes, appdirs

## 安装方法

### 方法1：使用可执行文件（推荐）

1. 从[发布页面](https://github.com/yourusername/windows-session-manager/releases)下载最新版本的`WindowsSessionManager-1.0.0-portable.zip`
2. 解压文件到任意位置
3. 运行 `WindowsSessionManager.exe`
4. 可选：使用`--create-desktop-shortcut`参数创建桌面快捷方式

### 方法2：从源代码安装

1. 克隆或下载本仓库
2. 安装依赖：
   ```
   pip install -r requirements.txt
   ```
3. 运行主程序：
   ```
   python get_windows.py
   ```

## 快速入门

### 首次使用

1. 启动应用程序
2. 应用程序会自动创建一个默认会话
3. 点击"保存会话"按钮保存当前打开的窗口状态
4. 通过GUI界面或命令行参数恢复会话

### 保存会话

1. 启动应用程序并调整窗口至所需位置
2. 在会话管理器中，点击"新建会话"并输入会话名称
3. 点击"保存会话"按钮
4. 当前所有应用程序窗口将被记录到会话中

### 恢复会话

1. 打开会话管理器
2. 从会话列表中选择一个会话
3. 点击"恢复会话"按钮
4. 应用程序将被启动并重新排列到保存时的位置

## 详细使用说明

### 图形界面操作

会话管理器的图形界面包含以下主要部分：

1. **会话列表**：左侧显示已保存的所有会话
2. **应用列表**：右侧显示当前选中会话包含的应用程序
3. **功能按钮**：底部提供保存、恢复、导入、导出等功能按钮
4. **日志区域**：底部显示操作日志，方便排查问题
5. **状态栏**：最底部显示程序状态信息

主要操作包括：

- **创建新会话**：点击"新建会话"按钮或使用菜单`会话 > 新建会话`
- **重命名会话**：选中会话后点击"重命名"按钮或使用菜单`会话 > 重命名会话`
- **删除会话**：选中会话后点击"删除"按钮或使用菜单`会话 > 删除会话`
- **清空会话**：选中会话后点击"清空"按钮或使用菜单`会话 > 清空会话`
- **导入/导出会话**：使用对应按钮或菜单`文件 > 导入会话/导出会话`

### 命令行使用

通过命令行工具，您可以轻松实现自动化：

```bash
# 显示帮助信息
get_windows.py -h

# 显示版本信息
get_windows.py -v

# 保存当前窗口状态到指定会话
get_windows.py --save "我的工作环境"

# 恢复指定会话
get_windows.py --restore "我的工作环境"

# 恢复上次使用的会话
get_windows.py --restore-last

# 以最小化方式启动
get_windows.py --minimized

# 创建桌面快捷方式
get_windows.py --create-desktop-shortcut

# 启用开机自启动
get_windows.py --enable-autostart

# 禁用开机自启动
get_windows.py --disable-autostart
```

### 配置选项

配置文件位于 `%APPDATA%\Local\WSM\WindowsSessionManager\config.json`，可自定义以下设置：

- **UI设置**：主题、窗口大小、字体大小、暗色模式等
- **启动设置**：是否自动启动、最小化启动、自动恢复上次会话等
- **热键设置**：自定义保存和恢复会话的快捷键
- **高级设置**：窗口检测超时、最大重试次数、会话历史记录等
- **排除列表**：可自定义要排除的进程和窗口

## 高级功能

### 特殊应用支持

Windows会话管理器能够识别和恢复特殊应用程序，如：

- **Everything**：文件搜索工具
- **PixPin**：截图工具
- 以及其他常见的Windows应用程序

### 浏览器会话管理

当前版本支持检测浏览器窗口，包括：

- Google Chrome
- Microsoft Edge
- Firefox
- 其他常见浏览器

未来版本将增强对浏览器标签页的管理功能。

### 会话导入/导出

您可以将会话配置导出为JSON文件，以便：

- 在不同电脑之间迁移会话配置
- 备份重要的工作环境设置
- 与团队成员共享工作环境配置

## 故障排除

1. **无法恢复某些应用程序**
   - 检查应用程序是否需要管理员权限
   - 某些应用程序可能不支持命令行启动或有特殊参数

2. **窗口位置不正确**
   - 确保显示器配置与保存会话时相同
   - 某些应用程序可能不遵循标准窗口管理规则

3. **启动时报错**
   - 检查日志文件 `%APPDATA%\Local\WSM\WindowsSessionManager\session_manager.log`
   - 确保所有依赖库已正确安装

4. **中文显示乱码**
   - 这是JSON文件查看时的编码问题，不影响程序功能
   - 可通过修改config.py中的JSON序列化参数来解决

## 常见问题解答

**问：会话管理器能否跨不同显示器设置工作？**  
答：是的，但最佳效果需要相同的显示器配置。如果配置变化，窗口可能需要手动调整。

**问：是否支持保存浏览器标签页？**  
答：当前版本支持检测浏览器窗口，但不会详细记录标签页内容。未来版本计划增强此功能。

**问：如何使用热键快速保存/恢复会话？**  
答：默认热键为Ctrl+Alt+S（保存）和Ctrl+Alt+R（恢复）。可在配置文件中自定义。

**问：如何卸载程序？**  
答：删除应用程序文件夹和 `%APPDATA%\Local\WSM\WindowsSessionManager` 目录即可完全卸载。

## 贡献指南

欢迎为项目做出贡献！以下是参与方式：

1. Fork 项目仓库
2. 创建您的功能分支 (`git checkout -b feature/AmazingFeature`)
3. 提交您的更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 打开 Pull Request

## 许可证

本项目采用 MIT 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件

## 致谢

- 感谢所有参与测试和提供反馈的用户
- 特别感谢开源社区提供的各种优秀工具和库 