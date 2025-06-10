# 开发者文档（DEVELOPER.md）

## 代码结构说明

- `get_windows.py`：主入口，仅负责启动。
- `session_manager/config.py`：配置加载与管理。
- `session_manager/core.py`：会话采集、保存、恢复等核心逻辑。
- `session_manager/utils.py`：通用工具函数（如窗口/进程操作）。
- `session_manager/gui.py`：Tkinter 图形界面。
- `resources/`：配置、日志、图标等资源文件。
- `tests/`：测试用例和数据样例。
- `docs/`：文档资料。

## 主要模块职责
- config.py：配置文件的读写、默认值、路径解析。
- core.py：会话数据的采集、保存、恢复、SessionManager 类。
- utils.py：窗口/进程相关的底层操作、过滤逻辑。
- gui.py：主界面、交互逻辑、用户操作反馈。

## 本地调试与测试
- 推荐使用 venv 虚拟环境隔离依赖。
- 可直接运行 `python get_windows.py` 进行功能测试。
- 测试数据可放在 `tests/` 目录，便于导入导出。
- 日志输出在 `resources/session_manager.log`，便于排查问题。

## 贡献代码流程
1. Fork 本仓库，创建新分支。
2. 按照模块分层原则开发或修复。
3. 补充/修正相关文档和测试用例。
4. 提交 Pull Request，说明变更内容和影响范围。
5. 等待维护者 review 和合并。

## 代码风格建议
- 遵循 PEP8 规范，变量/函数/类命名清晰。
- 注释和文档齐全，便于他人理解和维护。
- 重要变更请同步更新 CHANGELOG.md。

## 联系与支持
如有疑问、建议或合作意向，请通过 issue 或邮件联系维护者。 