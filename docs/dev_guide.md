# Windows会话管理器 开发者指南

## 目录

1. [项目概述](#项目概述)
2. [架构设计](#架构设计)
3. [代码结构](#代码结构)
4. [核心功能](#核心功能)
5. [扩展开发](#扩展开发)
6. [构建与打包](#构建与打包)
7. [调试技巧](#调试技巧)
8. [贡献指南](#贡献指南)

## 项目概述

Windows会话管理器是一个用于保存和恢复Windows工作环境的工具，使用Python编写。项目的主要目标是提供简单易用的界面和可靠的会话管理功能，帮助用户在不同工作环境之间无缝切换。

### 技术栈

- **语言**：Python 3.6+
- **GUI框架**：Tkinter + ttk + ttkthemes
- **窗口管理**：pygetwindow, pywin32, win32gui
- **进程管理**：psutil
- **图像处理**：Pillow
- **系统集成**：winshell, keyboard
- **配置管理**：JSON, appdirs

## 架构设计

Windows会话管理器采用模块化设计，主要由以下几个部分组成：

1. **主程序** (`get_windows.py`)：程序入口、命令行参数处理和GUI启动
2. **配置模块** (`session_manager/config.py`)：配置加载与管理
3. **核心功能** (`session_manager/core.py`)：会话数据采集、保存和恢复核心逻辑
4. **GUI界面** (`session_manager/gui.py`)：图形用户界面
5. **辅助工具** (`session_manager/utils.py`)：实用函数和工具类

### 数据流

1. 用户通过GUI或命令行发起操作
2. 操作由主程序解析并分发给相应模块
3. 配置模块提供必要的设置参数
4. 核心模块执行会话数据的采集或恢复
5. 结果反馈给用户界面或命令行输出

## 代码结构

```
windows-session-manager/
├── get_windows.py            # 主程序入口
├── build.py                  # 构建脚本
├── create_icons.py           # 图标生成脚本
├── requirements.txt          # 依赖列表
├── README.md                 # 项目说明
├── CHANGELOG.md              # 版本变更记录
├── LICENSE                   # 许可证文件
├── docs/                     # 文档目录
│   ├── user_guide.md         # 用户指南
│   └── dev_guide.md          # 开发者指南
├── resources/                # 资源目录
│   ├── icon.ico              # 程序图标
│   ├── config.json           # 默认配置
│   └── ...                   # 其他资源
└── session_manager/          # 核心代码包
    ├── __init__.py           # 包初始化
    ├── config.py             # 配置管理
    ├── core.py               # 核心功能
    ├── gui.py                # 图形界面
    └── utils.py              # 工具函数
```

## 核心功能

### 窗口收集 (collect_session_data_core)

`session_manager/core.py` 中的 `collect_session_data_core` 函数负责收集当前系统中打开的窗口信息：

```python
def collect_session_data_core(config):
    """收集当前会话数据"""
    session_items = []
    processed_app_paths = set()
    processed_browser_paths = set()
    
    # 1. 使用pygetwindow采集常规窗口
    try:
        windows = gw.getAllWindows()
        for window in windows:
            process_path = is_window_relevant(window, config)
            if process_path:
                # 处理浏览器和普通应用
                # ...
    except Exception as e:
        logger.error(f"使用pygetwindow收集窗口信息时发生错误: {e}", exc_info=True)
    
    # 2. 使用win32gui采集特殊应用窗口
    try:
        # 特殊应用处理逻辑
        # ...
    except Exception as e:
        logger.error(f"使用win32gui收集特殊应用窗口时发生错误: {e}", exc_info=True)
    
    return session_items
```

此函数通过多种方法收集窗口信息，包括：
- 使用`pygetwindow`收集常规窗口
- 使用`win32gui`和`psutil`收集特殊应用程序窗口
- 对浏览器应用进行特殊处理

### 会话恢复 (restore_specific_session_core)

`restore_specific_session_core` 函数负责恢复保存的会话：

```python
def restore_specific_session_core(session_items, config):
    """恢复特定会话"""
    if not session_items:
        logger.info("没有会话条目可用于恢复。")
        return
        
    logger.info("开始恢复会话...")
    restored_count = 0
    failed_count = 0
    
    for window_info in session_items:
        app_path = window_info.get("path")
        app_title = window_info.get("title")
        # ...
        
        # 检查应用是否已经在运行
        # ...
        
        # 如果应用未运行，尝试启动
        if not already_running:
            try:
                logger.info(f"  - 启动应用: {app_path}")
                subprocess.Popen([app_path])
                restored_count += 1
                time.sleep(restore_delay_seconds)
            except Exception as e:
                logger.error(f"  - 启动应用失败: {e}")
                failed_count += 1
    
    logger.info(f"\n会话恢复完成。成功: {restored_count}, 失败: {failed_count}")
    return restored_count, failed_count
```

此函数的主要步骤：
1. 遍历会话中的所有窗口项
2. 检查每个应用程序是否已经在运行
3. 对于未运行的应用程序，尝试启动它们
4. 特殊处理特定类型的应用程序

### 配置管理

`session_manager/config.py` 提供了配置加载和保存功能：

```python
def load_config(filename=None):
    """从JSON文件加载配置，不存在则创建默认配置"""
    if filename is None:
        filename = CONFIG_FILE

    current_config = get_default_config()

    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                loaded_user_config = json.load(f)
            
            # 递归合并配置
            def merge_config(target, source):
                # 合并逻辑...
            
            merge_config(current_config, loaded_user_config)
            logger.info(f"配置已从 {filename} 加载。")
        except Exception as e:
            logger.error(f"加载配置时发生错误 {filename}: {e}.")
    else:
        logger.info(f"配置文件 {filename} 不存在，创建默认配置。")
        save_config(current_config, filename)

    # 设置数据文件和日志文件路径
    # ...

    return current_config
```

配置系统支持层次化合并，允许用户只覆盖需要修改的部分。

## 扩展开发

### 添加新功能

以下是向项目添加新功能的一般步骤：

1. **确定功能位置**：根据功能性质决定代码应该放在哪个模块
2. **实现核心逻辑**：在相应模块中添加功能实现
3. **添加UI元素**：如果需要，在GUI中添加相应控件和事件处理
4. **更新配置选项**：如果功能需要新的配置选项，更新默认配置
5. **添加测试**：确保新功能正常工作
6. **更新文档**：记录新功能的用法

### 添加特殊应用支持

如果需要添加对新的特殊应用程序的支持，请参考以下步骤：

1. 在 `core.py` 的 `collect_session_data_core` 函数中添加对该应用的检测逻辑
2. 修改 `special_apps` 列表，添加新应用的名称
3. 可能需要调整 `restore_specific_session_core` 函数以处理恢复逻辑
4. 测试是否能够正确检测和恢复该应用

示例：

```python
special_apps = ['PixPin', 'Everything', 'YourNewApp']

# 特殊应用检测逻辑
if (app.lower() in proc_name.lower() or 
    (proc_exe and app.lower() in proc_exe.lower())):
    is_special = True
    matching_app = app
    break

# 特殊处理：某些应用可能需要额外的启动参数
if is_special_app and "YourNewApp" in app_title:
    try:
        subprocess.Popen([app_path, "--some-special-flag"])
        restored_count += 1
    except Exception as e:
        logger.error(f"启动特殊应用失败: {e}")
```

### 添加新的命令行参数

1. 在 `get_windows.py` 的 `parse_arguments` 函数中添加新参数：

```python
def parse_arguments():
    parser = argparse.ArgumentParser(description=f'{APP_NAME} - 一个用于保存和恢复Windows工作环境的工具')
    # 添加新参数
    parser.add_argument('--your-new-option', type=str, help='您的新选项描述')
    return parser.parse_args()
```

2. 在 `main` 函数中添加对应的处理逻辑：

```python
if args.your_new_option:
    # 处理新选项
    print(f"处理新选项: {args.your_new_option}")
    # 执行相应操作
    sys.exit(0)
```

## 构建与打包

项目使用 PyInstaller 创建可执行文件。构建过程由 `build.py` 脚本管理：

```python
def run_pyinstaller():
    """运行PyInstaller构建可执行文件"""
    # 构建命令
    cmd = [
        'pyinstaller',
        '--name', APP_NAME,
        '--onefile',
        '--windowed',
        '--clean',
    ]
    
    if icon_path:
        cmd.extend(['--icon', icon_path])
    
    # 添加数据文件
    cmd.extend([
        '--add-data', f'resources{os.pathsep}resources',
    ])
    
    # 主脚本
    cmd.append('get_windows.py')
    
    # 执行构建
    subprocess.check_call(cmd)
```

### 创建发布版本

1. 更新版本号：修改 `get_windows.py` 和 `build.py` 中的 `VERSION` 常量
2. 更新 `CHANGELOG.md`：记录新版本的变更
3. 运行构建脚本：`python build.py`
4. 测试生成的可执行文件
5. 创建发布包：ZIP文件会自动创建在 `dist` 目录下

## 调试技巧

### GUI调试功能

应用程序包含一个专门的调试菜单，提供了多种调试工具：

- **枚举所有窗口**：显示系统中所有窗口的详细信息
- **显示主要窗口**：显示已过滤的主要窗口信息
- **查找特殊应用窗口**：专门查找特殊应用的窗口
- **列出所有进程**：显示系统中所有运行的进程

这些功能对于理解窗口检测和应用程序识别非常有用。

### 日志系统

应用程序使用Python的标准日志模块，日志文件位于：
```
%APPDATA%\Local\WSM\WindowsSessionManager\session_manager.log
```

日志级别可以在配置文件中调整，默认为INFO级别。

### 常见调试问题

1. **窗口检测问题**：
   - 使用调试菜单中的"枚举所有窗口"功能
   - 检查 `exclude_process_paths` 和 `exclude_window_titles` 配置
   - 临时增加日志级别到DEBUG以获取更多信息

2. **应用启动失败**：
   - 检查应用程序路径是否正确
   - 尝试手动使用相同命令启动应用
   - 检查应用程序是否需要特殊参数或权限

3. **配置加载问题**：
   - 检查JSON文件格式是否正确
   - 尝试删除配置文件，让程序重新创建默认配置

## 贡献指南

### 提交代码

1. Fork项目仓库
2. 创建功能分支：`git checkout -b feature/your-feature`
3. 提交更改：`git commit -m 'Add some feature'`
4. 推送到分支：`git push origin feature/your-feature`
5. 提交Pull Request

### 代码风格

- 遵循PEP 8 Python代码风格指南
- 使用有意义的变量名和函数名
- 为函数和类添加文档字符串
- 保持代码模块化和可测试

### 测试

在提交代码前，请确保：

1. 测试您的更改在Windows 10/11上能正常工作
2. 验证在不同显示器配置下的行为
3. 确保与现有功能没有冲突
4. 更新相关文档

### 报告问题

报告问题时，请提供：

1. 操作系统版本
2. Python版本
3. 详细的错误信息或日志
4. 复现步骤
5. 预期行为vs实际行为 