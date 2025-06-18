# Windows会话管理器 配置文件参考

Windows会话管理器使用JSON格式的配置文件来存储设置。默认配置文件位于用户数据目录：

```
%APPDATA%\Local\WSM\WindowsSessionManager\config.json
```

本文档详细说明所有可用的配置选项。

## 配置文件结构

完整的配置文件结构如下：

```json
{
    "exclude_process_paths": [
        "C:\\Windows\\System32\\svchost.exe",
        "C:\\Windows\\explorer.exe",
        "C:\\Windows\\System32\\dwm.exe",
        "C:\\Windows\\System32\\conhost.exe",
        "C:\\Windows\\SystemApps\\Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy\\StartMenuExperienceHost.exe",
        "C:\\Windows\\System32\\RuntimeBroker.exe"
    ],
    "exclude_window_titles": [
        "Program Manager",
        "Default IME",
        "MSCTFIME UI",
        "NVIDIA GeForce Overlay",
        "Settings",
        "Microsoft Text Input Application",
        "dummyLayeredWnd"
    ],
    "browser_executables": [
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "brave.exe",
        "opera.exe"
    ],
    "session_data_file_name": "sessions.json",
    "log_file_name": "session_manager.log",
    "window_title_similarity_threshold": 0.7,
    "restore_delay_seconds": 0.1,
    "backup_session_data": true,
    "startup_delay_seconds": 2,
    "ui": {
        "theme": "vista",
        "dark_mode": false,
        "window_width": 1000,
        "window_height": 750,
        "show_tooltips": true,
        "confirm_session_delete": true,
        "confirm_window_delete": true,
        "font_size": 10,
        "max_recent_sessions": 5
    },
    "hotkeys": {
        "save_session": "ctrl+alt+s",
        "restore_session": "ctrl+alt+r",
        "quick_restore": "ctrl+alt+q"
    },
    "startup": {
        "autostart": false,
        "minimized": false,
        "restore_last_session": false,
        "last_session": ""
    },
    "advanced": {
        "window_detection_timeout": 5,
        "virtual_desktop_support": true,
        "collect_window_icons": true,
        "max_restore_retries": 3,
        "keep_session_history": true,
        "max_session_history": 10,
        "auto_save_interval": 300
    }
}
```

## 配置选项详解

### 基本配置选项

#### exclude_process_paths

**类型**：字符串数组  
**默认值**：系统进程路径列表  
**说明**：要排除的应用程序进程路径列表。这些进程的窗口不会被保存到会话中。通常包含系统进程和后台服务。

```json
"exclude_process_paths": [
    "C:\\Windows\\System32\\svchost.exe",
    "C:\\Windows\\explorer.exe"
]
```

#### exclude_window_titles

**类型**：字符串数组  
**默认值**：常见系统窗口标题列表  
**说明**：要排除的窗口标题列表。带有这些标题的窗口不会被保存到会话中。通常包括桌面管理器和系统窗口。

```json
"exclude_window_titles": [
    "Program Manager",
    "Default IME"
]
```

#### browser_executables

**类型**：字符串数组  
**默认值**：常见浏览器可执行文件名列表  
**说明**：浏览器可执行文件名列表。这些程序被识别为浏览器，会话管理器会对它们进行特殊处理。

```json
"browser_executables": [
    "chrome.exe",
    "msedge.exe",
    "firefox.exe"
]
```

#### session_data_file_name

**类型**：字符串  
**默认值**："sessions.json"  
**说明**：会话数据文件的名称。完整路径在程序启动时动态生成，通常位于用户数据目录下。

#### log_file_name

**类型**：字符串  
**默认值**："session_manager.log"  
**说明**：日志文件的名称。完整路径在程序启动时动态生成，通常位于用户数据目录下。

#### window_title_similarity_threshold

**类型**：浮点数（0.0 - 1.0）  
**默认值**：0.7  
**说明**：窗口标题匹配的相似度阈值。当检查应用程序是否已经在运行时，如果窗口标题的相似度超过此阈值，则认为是同一个窗口。

#### restore_delay_seconds

**类型**：浮点数  
**默认值**：0.1  
**说明**：恢复应用程序时的延迟秒数。在启动一个应用程序后，等待此时间再启动下一个应用程序。

#### backup_session_data

**类型**：布尔值  
**默认值**：true  
**说明**：是否备份会话数据文件。如果启用，每次保存会话数据时，会先将原文件备份为.bak文件。

#### startup_delay_seconds

**类型**：整数  
**默认值**：2  
**说明**：程序启动时的延迟秒数。用于等待系统环境准备就绪。

### UI配置选项

#### ui.theme

**类型**：字符串  
**默认值**："vista"  
**可选值**："winnative", "clam", "alt", "default", "classic", "vista", "xpnative"  
**说明**：GUI界面的主题。基于ttkthemes库提供的主题。

#### ui.dark_mode

**类型**：布尔值  
**默认值**：false  
**说明**：是否启用暗色模式。如果启用，程序将使用暗色配色方案。

#### ui.window_width

**类型**：整数  
**默认值**：1000  
**说明**：主窗口的初始宽度（像素）。

#### ui.window_height

**类型**：整数  
**默认值**：750  
**说明**：主窗口的初始高度（像素）。

#### ui.show_tooltips

**类型**：布尔值  
**默认值**：true  
**说明**：是否显示工具提示。如果启用，鼠标悬停在控件上时会显示提示信息。

#### ui.confirm_session_delete

**类型**：布尔值  
**默认值**：true  
**说明**：删除会话前是否要求确认。如果启用，删除会话时会弹出确认对话框。

#### ui.confirm_window_delete

**类型**：布尔值  
**默认值**：true  
**说明**：从会话中删除窗口前是否要求确认。如果启用，删除窗口时会弹出确认对话框。

#### ui.font_size

**类型**：整数  
**默认值**：10  
**说明**：GUI界面的字体大小。

#### ui.max_recent_sessions

**类型**：整数  
**默认值**：5  
**说明**：在"最近会话"列表中显示的最大会话数量。

### 热键配置选项

#### hotkeys.save_session

**类型**：字符串  
**默认值**："ctrl+alt+s"  
**说明**：保存当前会话的热键。使用keyboard库的热键格式。

#### hotkeys.restore_session

**类型**：字符串  
**默认值**："ctrl+alt+r"  
**说明**：恢复当前选中会话的热键。使用keyboard库的热键格式。

#### hotkeys.quick_restore

**类型**：字符串  
**默认值**："ctrl+alt+q"  
**说明**：快速恢复上次使用会话的热键。使用keyboard库的热键格式。

### 启动配置选项

#### startup.autostart

**类型**：布尔值  
**默认值**：false  
**说明**：是否开机自启动。如果启用，程序会在Windows启动时自动运行。

#### startup.minimized

**类型**：布尔值  
**默认值**：false  
**说明**：是否以最小化方式启动。如果启用，程序启动时会自动最小化到系统托盘。

#### startup.restore_last_session

**类型**：布尔值  
**默认值**：false  
**说明**：是否自动恢复上次使用的会话。如果启用，程序启动时会自动恢复上次使用的会话。

#### startup.last_session

**类型**：字符串  
**默认值**：""  
**说明**：上次使用的会话名称。程序在恢复上次会话时使用此值。

### 高级配置选项

#### advanced.window_detection_timeout

**类型**：整数  
**默认值**：5  
**说明**：窗口检测的超时时间（秒）。在此时间内未能检测到窗口则超时。

#### advanced.virtual_desktop_support

**类型**：布尔值  
**默认值**：true  
**说明**：是否支持虚拟桌面。如果启用，程序会尝试识别和恢复虚拟桌面上的窗口。

#### advanced.collect_window_icons

**类型**：布尔值  
**默认值**：true  
**说明**：是否收集窗口图标。如果启用，程序会尝试获取窗口的图标并在界面中显示。

#### advanced.max_restore_retries

**类型**：整数  
**默认值**：3  
**说明**：恢复窗口时的最大重试次数。如果恢复失败，程序会尝试重试此次数。

#### advanced.keep_session_history

**类型**：布尔值  
**默认值**：true  
**说明**：是否保留会话历史记录。如果启用，程序会保存会话的历史版本。

#### advanced.max_session_history

**类型**：整数  
**默认值**：10  
**说明**：保留的最大会话历史记录数量。超过此数量的旧历史记录会被删除。

#### advanced.auto_save_interval

**类型**：整数  
**默认值**：300  
**说明**：自动保存会话的间隔时间（秒）。如果设为0，则禁用自动保存。

## 配置文件修改方法

1. **手动修改**：直接编辑config.json文件。请确保JSON格式正确，否则可能导致程序无法正常加载配置。

2. **通过程序修改**：某些配置可以通过程序界面修改，例如启用自启动选项。

3. **通过代码修改**：可以使用`update_config`函数编程方式修改配置：

```python
from session_manager.config import update_config

# 更新单个配置项
update_config({"restore_delay_seconds": 0.5})

# 更新嵌套配置项
update_config({"ui": {"dark_mode": True}})
```

## 配置文件位置

配置文件在不同操作系统上的位置：

- **Windows 10/11**：`%APPDATA%\Local\WSM\WindowsSessionManager\config.json`

## 注意事项

1. 修改配置文件前建议先备份，以便在出现问题时可以恢复。
2. 某些配置选项的更改需要重启程序才能生效。
3. 如果配置文件损坏，程序会自动创建一个新的默认配置文件。
4. 路径相关的配置应使用双反斜杠（`\\`）或原始字符串（`r"C:\Path"`）来避免转义问题。 