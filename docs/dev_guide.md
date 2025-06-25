# 开发者指南

## 1. 代码结构

- `get_windows.py`：主程序入口，负责GUI和主流程控制。
- `session_manager/core.py`：会话采集、保存、恢复等核心逻辑。
- `session_manager/browser_tabs.py`：浏览器标签页采集与分配核心。
- `session_manager/gui.py`：图形界面，Treeview展示窗口与标签页。

## 2. 扩展会话采集

- 可在`core.py`的`collect_session_data`中扩展采集逻辑，支持更多应用类型。
- 特殊应用可通过`special_apps`配置自动识别。

## 3. 浏览器标签页采集

- `browser_tabs.py`支持多种采集方式（session文件、历史数据库）。
- 可扩展支持更多浏览器或更精细的窗口-标签页分配算法。

## 4. GUI展示

- `gui.py`使用Tkinter+Treeview实现树形结构展示。
- 可自定义节点样式、交互逻辑、右键菜单等。

## 5. 贡献建议

- 保持代码风格一致，注重模块解耦。
- 提交PR前请确保通过基本测试。

---

> 本项目专注本地会话与标签页管理，欢迎开发者扩展和优化！ 