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
10. [浏览器标签页支持](#浏览器标签页支持)
11. [选择性恢复功能](#选择性恢复功能)
12. [混合标签页采集方法](#混合标签页采集方法)

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

## 浏览器标签页支持

Windows会话管理器现在支持保存和恢复浏览器标签页，这使您可以在恢复会话时自动恢复之前打开的网页。

### 支持的浏览器

目前支持以下浏览器的标签页保存和恢复：

- Google Chrome
- Microsoft Edge
- Mozilla Firefox
- Brave Browser
- Opera

### 工作原理

当您保存会话时，Windows会话管理器会：

1. 检测运行中的浏览器窗口
2. 识别每个浏览器窗口的类型
3. 使用混合标签页采集方法获取标签页信息
4. 将这些URL和标题保存到会话数据中

当您恢复会话时，Windows会话管理器会：

1. 检查浏览器是否已经在运行
2. 如果浏览器未运行，启动浏览器
3. 使用特殊方法将保存的标签页发送到浏览器，使其打开这些网页

### 注意事项

- 标签页恢复基于混合采集方法，优先使用实时数据
- 由于浏览器安全限制，某些情况下可能无法获取全部标签页
- 最多保存每个浏览器窗口的30个最近访问的网页
- 恢复标签页时，浏览器可能会显示安全提示，这是正常的安全机制
- 如果您使用隐私浏览模式，标签页可能无法被保存

### 隐私考虑

Windows会话管理器不会将您的浏览历史上传到任何服务器。所有数据都保存在本地会话文件中。如果您共享会话文件，请注意其中可能包含您访问过的URL和网页标题。

## 选择性恢复功能

选择性恢复是Windows会话管理器的一项智能功能，它可以自动检测已存在的窗口，并只恢复不存在的窗口。这避免了重复打开已有窗口的问题，提高了会话恢复的效率和用户体验。

### 工作原理

当您恢复会话时，Windows会话管理器会执行以下步骤：

1. **窗口检测**：扫描当前系统中所有运行的窗口
2. **应用程序匹配**：将这些窗口与会话中保存的应用程序进行匹配
3. **浏览器窗口匹配**：特别处理浏览器窗口，使用标题相似度进行匹配
4. **选择性恢复**：只恢复那些在当前系统中不存在的窗口

### 匹配算法

Windows会话管理器使用以下方法来确定窗口是否已存在：

1. **进程路径匹配**：比较应用程序的可执行文件路径
2. **窗口标题相似度**：使用相似度算法比较窗口标题
   - 对于普通应用程序，使用70%的相似度阈值
   - 对于浏览器窗口，使用60%的相似度阈值（考虑到标签页变化导致的标题变化）
3. **特殊应用识别**：对于特殊应用程序（如PixPin、Everything等），使用专门的识别方法

### 使用场景

选择性恢复功能在以下场景特别有用：

1. **部分关闭**：当您关闭了部分窗口后，希望只恢复这些关闭的窗口
2. **多会话切换**：在不同会话之间切换时，避免重复打开相同的应用程序
3. **系统重启后**：系统重启后，某些应用程序可能已自动启动，无需再次启动

### 测试和验证

您可以使用`test_restore_selective.py`脚本测试选择性恢复功能：

1. 运行`test_restore_selective.bat`或`python test_restore_selective.py`
2. 脚本会首先采集当前会话数据
3. 然后尝试恢复会话（此时应该跳过所有已存在的窗口）
4. 关闭一个浏览器窗口后再次恢复，此时应只恢复刚关闭的窗口

## 混合标签页采集方法

Windows会话管理器使用混合标签页采集方法，结合了WebSocket实时数据和静态文件提取两种技术，提供更准确、更可靠的浏览器标签页信息。

### 技术组成

混合标签页采集方法包括以下组件：

1. **浏览器扩展**：安装在浏览器中，通过WebSocket实时发送标签页数据
2. **WebSocket服务器**：接收浏览器扩展发送的数据，并提供API
3. **静态提取模块**：从浏览器的会话文件和历史记录中提取标签页信息
4. **混合标签页管理器**：协调两种方法，提供统一的API

### 工作流程

当保存会话时，混合标签页采集方法按以下流程工作：

1. **初始化检查**：检查WebSocket服务器是否已启动
2. **优先使用WebSocket**：如果WebSocket服务器已启动且连接正常，尝试从WebSocket获取标签页数据
3. **自动回退**：如果WebSocket数据不可用，自动回退到静态提取方法
4. **数据整合**：将获取的标签页数据整合到会话中

### 安装和配置浏览器扩展

要使用WebSocket实时数据功能，您需要安装浏览器扩展：

1. 从`browser_extension`目录找到适合您浏览器的扩展
2. 按照[浏览器扩展安装指南](../browser_extension_guide.md)中的步骤安装扩展
3. 确保WebSocket服务器已启动（可通过`start_tabs_server.bat`启动）
4. 点击浏览器扩展图标，连接到WebSocket服务器

### 配置选项

您可以在配置文件中自定义混合标签页采集方法的行为：

```json
{
  "websocket": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8765,
    "auto_start": true
  },
  "browser_tabs": {
    "prefer_websocket": true,
    "fallback_to_static": true,
    "max_tabs_per_window": 30,
    "cache_duration": 60
  }
}
```

- **enabled**：是否启用WebSocket功能
- **auto_start**：程序启动时是否自动启动WebSocket服务器
- **prefer_websocket**：是否优先使用WebSocket方法
- **fallback_to_static**：WebSocket不可用时是否回退到静态方法
- **cache_duration**：缓存数据的有效期（秒）

### 优势和局限性

混合标签页采集方法的优势：

- **实时性**：通过WebSocket获取实时标签页变化
- **准确性**：直接从浏览器API获取数据，避免解析错误
- **可靠性**：当WebSocket不可用时，自动回退到静态提取方法
- **兼容性**：保持与现有代码的向后兼容性

局限性：

- **需要安装扩展**：要获得最佳体验，需要安装浏览器扩展
- **隐私浏览**：无法获取隐私浏览模式下的标签页
- **资源消耗**：WebSocket服务器会占用少量系统资源 