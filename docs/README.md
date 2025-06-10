# docs 目录说明

本目录用于存放项目相关的文档资料，包括但不限于：

- 安装说明（INSTALL.md）
- 使用手册（USAGE.md）
- 常见问题（FAQ.md）
- 更新日志（CHANGELOG.md）
- 开发者文档（DEVELOPER.md）
- 其它开发、维护、贡献相关文档

建议文档结构如下：

```
docs/
├── README.md         # 本说明文件
├── INSTALL.md        # 安装与环境配置说明
├── USAGE.md          # 详细使用说明
├── FAQ.md            # 常见问题解答
├── CHANGELOG.md      # 版本更新日志
├── DEVELOPER.md      # 开发者文档
```

## 文档维护建议
- 所有文档请使用 Markdown 格式（.md）。
- 文档内容应简明扼要，便于查阅和维护。
- 重要变更请同步更新 CHANGELOG.md。
- 欢迎通过 Pull Request 或 Issue 参与文档完善。
- 命名规范：文档名建议全大写、下划线分隔，便于识别。

如需补充其它文档，请在本目录下新建相应文件。 

# Windows 会话管理器

## 项目简介

**Windows 会话管理器** 是一个 Python 编写的实用工具，旨在帮助用户在关闭电脑前保存当前打开的应用程序和浏览器窗口状态，并在下次开机后恢复到关机前的状态。这对于经常需要处理多个应用程序和大量浏览器标签页的用户非常方便，可以节省重新打开和组织窗口的时间。

**注意：** 目前该工具主要依靠记录应用程序的可执行文件路径和窗口标题来实现恢复。对于浏览器，它依赖浏览器自身的会话恢复功能来恢复标签页，无法精确保存和恢复单个标签页的 URL 列表。

## 主要功能

*   **保存当前会话：** 记录当前桌面上运行的非系统应用程序和浏览器窗口信息。
*   **恢复保存的会话：** 启动或切换到之前保存的应用程序和浏览器。
*   **多会话管理：** 支持保存和管理多个不同的会话记录。
*   **图形用户界面 (GUI)：** 提供一个直观的界面来查看、管理和恢复会话。
*   **命令行接口 (CLI)：** 支持通过命令行执行保存和恢复操作，方便通过任务计划程序自动化。
*   **可配置的排除列表：** 可以自定义排除不需要保存的应用程序和窗口。
*   **数据备份：** 在保存会话数据前创建备份，防止数据丢失。

## 安装

### 1. 安装 Python

确保您的系统安装了 Python 3.6 或更高版本。您可以从 [Python 官方网站](https://www.python.org/downloads/) 下载并安装。

安装时请勾选 "Add Python to PATH" (将 Python 添加到环境变量)。

### 2. 安装依赖库

打开命令行（命令提示符或 PowerShell），运行以下命令安装所需的 Python 库：

```bash
pip install pygetwindow
```

如果您希望将脚本打包成独立的 `.exe` 文件（推荐），还需要安装 `PyInstaller`：

```bash
pip install pyinstaller
```

### 3. 获取项目代码

将 `get_windows.py` 文件下载到您的本地目录。例如，您可以放在 `D:\project\SessionManager` 这样的目录中。

## 快速开始

### 使用 GUI 界面

直接运行 `get_windows.py` 脚本即可启动图形用户界面：

```bash
python D:\project\SessionManager\get_windows.py
```

（请将路径替换为您实际存放脚本的路径）

启动后，您可以通过界面上的按钮进行会话的保存、恢复和管理。

### 使用命令行 (CLI)

您也可以通过命令行参数来执行操作：

*   **保存当前会话到默认名称 ("上次会话")：**
    ```bash
    python D:\project\SessionManager\get_windows.py --save
    ```
*   **恢复默认名称 ("上次会话") 的会话：**
    ```bash
    python D:\project\SessionManager\get_windows.py --restore
    ```
*   **打开会话数据文件所在的目录：**
    ```bash
    python D:\project\SessionManager\get_windows.py --manage
    ```

（请将路径替换为您实际存放脚本的路径）

### 配置

工具的配置存储在与脚本同一目录下的 `config.json` 文件中。如果文件不存在，运行脚本时会自动创建默认配置文件。您可以编辑此文件来修改排除列表、会话数据文件路径等设置。

详细的配置文件说明请参考 [USAGE.md](#使用文档)。

### 自动化 (通过任务计划程序)

要实现系统关机自动保存、开机自动恢复，需要结合 Windows 的任务计划程序。这部分配置步骤较多，请参考 [USAGE.md](#使用文档) 中的详细说明。

## 使用文档

更详细的功能说明、配置文件、任务计划程序设置等内容，请参考 [USAGE.md](USAGE.md) 文件。

## 局限性

*   无法精确保存和恢复浏览器所有标签页的 URL。恢复浏览器时依赖浏览器自身的会话恢复功能。
*   对于需要管理员权限运行的应用程序，本工具可能也需要以管理员权限运行才能正常管理其窗口。
*   `tkinter` 库提供了基础的 GUI 功能，界面可能不够现代化和美观。
*   未实现跨设备或跨系统同步会话功能。

## 贡献

欢迎对本项目提出建议或贡献代码。如果您发现 Bug 或有功能建议，请提交 Issue。

## 许可证

本项目采用 [MIT 许可证](LICENSE)。

## 目录结构

```
windows-session-manager/
├── get_windows.py              # 主程序入口（后续将精简为仅启动）
├── session_manager/            # 业务逻辑包（核心代码将迁移至此）
│   ├── __init__.py
│   ├── core.py                 # 会话采集/恢复等核心逻辑
│   ├── gui.py                  # Tkinter界面相关
│   ├── config.py               # 配置管理
│   ├── utils.py                # 工具函数
├── resources/                  # 图标、图片、样式等资源
├── tests/                      # 单元测试
├── docs/                       # 文档目录
│   ├── README.md
│   ├── INSTALL.md
│   ├── USAGE.md
│   ├── FAQ.md
│   └── CHANGELOG.md
├── config.json                 # 默认配置文件
├── requirements.txt            # 依赖包列表
├── setup.py                    # （可选）打包/安装脚本
├── LICENSE
└── .gitignore
```
