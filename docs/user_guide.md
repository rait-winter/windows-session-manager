# Windows会话管理器 用户指南

## 目录

1. [简介](#简介)
2. [安装](#安装)
3. [基本操作](#基本操作)
4. [图形界面详解](#图形界面详解)
5. [命令行操作](#命令行操作)
6. [配置文件](#配置文件)
7. [高级功能](#高级功能)
8. [故障排除](#故障排除)
9. [常见问题](#常见问题)

## 简介

Windows会话管理器是一个用于保存和恢复Windows工作环境的工具。它可以记录您当前打开的所有应用程序窗口，并在需要时恢复它们。这对于以下场景非常有用：

- 在不同的工作项目之间快速切换
- 系统重启后恢复之前的工作环境
- 创建针对不同任务的预设工作环境
- 在多台电脑之间同步工作环境

## 安装

### 方法1：使用预编译的可执行文件（推荐）

1. 从[发布页面](https://github.com/yourusername/windows-session-manager/releases)下载最新版本的`WindowsSessionManager-1.0.0-portable.zip`
2. 解压文件到任意位置
3. 运行`WindowsSessionManager.exe`
4. 可选：使用`--create-desktop-shortcut`参数创建桌面快捷方式：
   ```
   WindowsSessionManager.exe --create-desktop-shortcut
   ```
5. 可选：使用`--enable-autostart`参数启用开机自启动：
   ```
   WindowsSessionManager.exe --enable-autostart
   ```

### 方法2：从源代码安装

1. 确保您已安装Python 3.6或更高版本
2. 克隆或下载源代码库
3. 打开命令提示符或PowerShell，导航到源代码目录
4. 安装依赖库：
   ```
   pip install -r requirements.txt
   ```
5. 运行主程序：
   ```
   python get_windows.py
   ```

## 基本操作

### 首次启动

首次启动时，程序会自动在用户数据目录`%APPDATA%\Local\WSM\WindowsSessionManager\`中创建必要的配置文件和默认会话。

### 保存会话

1. 启动应用程序并打开您想要保存的所有应用程序窗口
2. 在会话管理器中，通过以下方式之一创建新会话：
   - 点击"新建会话"按钮
   - 使用菜单：会话 > 新建会话
   - 输入会话名称，例如"工作环境"
3. 选择创建的会话，点击"保存会话"按钮
4. 程序将收集当前所有打开的窗口信息并保存到会话中

### 恢复会话

1. 在会话列表中选择要恢复的会话
2. 点击"恢复会话"按钮
3. 程序将尝试启动所有保存在会话中的应用程序，并将它们恢复到保存时的状态

## 图形界面详解

Windows会话管理器的图形界面分为几个主要部分：

### 菜单栏

- **文件菜单**
  - 导入会话：从JSON文件导入会话配置
  - 导出会话：将会话配置导出到JSON文件
  - 退出：关闭应用程序

- **会话菜单**
  - 新建会话：创建新的会话
  - 重命名会话：重命名选定的会话
  - 删除会话：删除选定的会话
  - 清空会话：清空选定会话中的所有应用程序

- **调试菜单**
  - 枚举所有窗口：显示系统中所有窗口的详细信息
  - 显示主要窗口：仅显示主要应用程序窗口
  - 查找特殊应用窗口：显示特殊应用程序的窗口
  - 列出所有进程：显示所有运行中的进程
  - 刷新窗口列表：刷新窗口检测

- **帮助菜单**
  - 使用说明：显示简要使用说明
  - 关于：显示程序版本和作者信息

### 主界面

- **左侧面板**：显示所有保存的会话列表
- **右侧面板**：显示当前选中会话中包含的应用程序列表，包括：
  - 应用类型（普通应用程序、浏览器等）
  - 窗口标题
  - 应用程序路径

### 底部操作区

- **功能按钮**：
  - 保存会话：保存当前窗口状态到选中的会话
  - 恢复会话：恢复选中会话的窗口状态
  - 导入会话：从文件导入会话
  - 导出会话：将会话导出到文件
  - 重命名：重命名选中的会话
  - 删除：删除选中的会话
  - 清空：清空选中会话的内容

- **日志区域**：显示操作日志和详细信息
- **状态栏**：显示当前状态和操作结果

## 命令行操作

Windows会话管理器支持丰富的命令行参数，便于自动化操作：

```
usage: get_windows.py [-h] [-v] [--minimized] [--restore RESTORE] [--restore-last] [--save SAVE]
                      [--create-desktop-shortcut] [--enable-autostart] [--disable-autostart]
```

### 参数详解

- `-h, --help`：显示帮助信息
- `-v, --version`：显示版本信息
- `--minimized`：以最小化方式启动程序
- `--restore RESTORE`：恢复指定名称的会话，例如：`--restore "工作环境"`
- `--restore-last`：恢复上次使用的会话
- `--save SAVE`：保存当前窗口状态到指定名称的会话，例如：`--save "工作环境"`
- `--create-desktop-shortcut`：创建桌面快捷方式
- `--enable-autostart`：启用开机自启动
- `--disable-autostart`：禁用开机自启动

### 命令行示例

1. 保存当前窗口状态到指定会话：
   ```
   python get_windows.py --save "开发环境"
   ```

2. 恢复指定会话：
   ```
   python get_windows.py --restore "开发环境"
   ```

3. 创建快捷方式：
   ```
   python get_windows.py --create-desktop-shortcut
   ```

4. 启用自启动：
   ```
   python get_windows.py --enable-autostart
   ```

5. 以最小化方式启动并恢复上次会话：
   ```
   python get_windows.py --minimized --restore-last
   ```

## 配置文件

Windows会话管理器的配置文件位于`%APPDATA%\Local\WSM\WindowsSessionManager\config.json`。您可以手动编辑此文件来自定义程序行为。

### 主要配置项

```json
{
    "exclude_process_paths": ["C:\\Windows\\System32\\svchost.exe", ...],
    "exclude_window_titles": ["Program Manager", ...],
    "browser_executables": ["chrome.exe", "msedge.exe", ...],
    "session_data_file_name": "sessions.json",
    "window_title_similarity_threshold": 0.7,
    "restore_delay_seconds": 0.1,
    "ui": {
        "theme": "vista",
        "dark_mode": false,
        "window_width": 1000,
        "window_height": 750
    },
    "hotkeys": {
        "save_session": "ctrl+alt+s",
        "restore_session": "ctrl+alt+r"
    },
    "startup": {
        "autostart": false,
        "minimized": false,
        "restore_last_session": false
    },
    "advanced": {
        "window_detection_timeout": 5,
        "virtual_desktop_support": true,
        "collect_window_icons": true,
        "max_restore_retries": 3
    }
}
```

### 配置项说明

- **exclude_process_paths**：要排除的应用程序路径列表
- **exclude_window_titles**：要排除的窗口标题列表
- **browser_executables**：浏览器可执行文件名列表
- **window_title_similarity_threshold**：窗口标题匹配阈值，范围0-1
- **restore_delay_seconds**：恢复应用程序时的延迟秒数
- **ui**：用户界面设置（主题、尺寸等）
- **hotkeys**：快捷键设置
- **startup**：启动相关设置
- **advanced**：高级设置

## 高级功能

### 会话导入导出

您可以将会话配置导出为JSON文件，便于备份或在不同电脑间共享：

1. 选择要导出的会话
2. 点击"导出会话"按钮或使用菜单：文件 > 导出会话
3. 选择保存位置并确认

导入会话：

1. 点击"导入会话"按钮或使用菜单：文件 > 导入会话
2. 选择JSON格式的会话文件
3. 输入导入后的会话名称
4. 确认导入

### 特殊应用支持

Windows会话管理器能够识别和恢复一些特殊应用程序：

- **Everything**：文件搜索工具
- **PixPin**：截图和标注工具

这些应用通常使用非标准窗口管理方式，程序会使用特殊方法检测和恢复它们。

### 热键支持

默认热键配置：

- **Ctrl+Alt+S**：保存当前会话
- **Ctrl+Alt+R**：恢复当前选中的会话
- **Ctrl+Alt+Q**：快速恢复上次使用的会话

您可以在配置文件中自定义这些热键。

## 故障排除

### 常见问题及解决方法

1. **程序无法启动**
   - 确保已安装所有依赖库
   - 检查Python版本是否为3.6或更高版本
   - 查看日志文件`%APPDATA%\Local\WSM\WindowsSessionManager\session_manager.log`

2. **无法保存某些窗口**
   - 某些系统窗口和特殊应用程序可能无法被检测
   - 检查该应用是否在exclude_process_paths或exclude_window_titles列表中

3. **应用程序恢复失败**
   - 确保应用程序路径正确且可访问
   - 某些应用可能需要特殊参数才能从命令行启动
   - 增加restore_delay_seconds值以允许更多启动时间

4. **窗口位置不正确**
   - 确保显示器配置与保存时相同
   - 某些应用程序可能会自行决定窗口位置

5. **中文或特殊字符显示乱码**
   - 这通常发生在查看JSON文件时，不影响程序功能
   - 可修改config.py中的JSON序列化参数解决

### 日志文件

程序会在以下位置生成日志文件：
```
%APPDATA%\Local\WSM\WindowsSessionManager\session_manager.log
```

查看此文件可以帮助排查问题。

## 常见问题

**问：会话管理器是否能保存应用程序内部状态？**  
答：不能。它只能保存和恢复窗口位置和应用程序路径，无法保存应用程序内部的工作状态。

**问：如何彻底卸载程序？**  
答：删除程序文件夹和用户数据目录`%APPDATA%\Local\WSM\WindowsSessionManager`即可完全卸载。

**问：多显示器支持如何工作？**  
答：程序会记录每个窗口在哪个显示器上以及其具体位置。恢复时会尝试将窗口放回原来的位置。

**问：会话数据存储在哪里？**  
答：会话数据存储在`%APPDATA%\Local\WSM\WindowsSessionManager\sessions.json`文件中。

**问：如何快速切换不同的工作环境？**  
答：创建多个会话，分别保存不同的工作环境，然后使用命令行参数`--restore`或热键快速切换。 