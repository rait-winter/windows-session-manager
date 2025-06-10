# 使用说明（USAGE.md）

## 主要功能
- 一键保存/恢复所有应用和浏览器窗口
- 多会话管理、导入导出、重命名、删除
- 图形界面美观，操作直观
- 日志、状态栏、配置自定义

## 图形界面操作
1. 启动程序后，左侧为会话列表，右侧为当前会话的应用/窗口条目。
2. 下方按钮区可进行保存、恢复、导入、导出、重命名、删除、清空等操作。
3. 菜单栏支持文件、会话、帮助等操作。
4. 日志输出区可查看操作日志和错误信息。

> ![界面截图](screenshot.png)  <!-- 如有实际截图请替换此文件 -->

## 导入/导出会话文件格式示例

```json
[
  {
    "type": "application",
    "title": "记事本",
    "path": "C:\\Windows\\notepad.exe"
  },
  {
    "type": "browser",
    "title": "百度 - Google Chrome",
    "path": "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe",
    "urls": []
  }
]
```

## 命令行用法
- 保存当前会话：
  ```bash
  python get_windows.py --save
  ```
- 恢复会话：
  ```bash
  python get_windows.py --restore
  ```
- 打开数据目录：
  ```bash
  python get_windows.py --manage
  ```

## 配置文件字段说明
| 字段名 | 类型 | 说明 |
|--------|------|------|
| session_data_file | str | 会话数据文件路径 |
| exclude_process_paths | list | 排除的进程路径 |
| exclude_window_titles | list | 排除的窗口标题 |
| browser_executables | list | 浏览器可执行文件名 |
| window_title_similarity_threshold | float | 标题相似度阈值 |
| restore_delay_seconds | float | 恢复窗口时的延迟 |
| backup_session_data | bool | 是否自动备份数据 |
| startup_delay_seconds | int/float | 启动恢复前的延迟 |

## 快捷键与右键菜单
- 支持标准 Windows 右键菜单（如有）
- 常用操作可通过菜单栏或按钮区快速完成

## 自动化建议
- 可结合 Windows 任务计划程序实现关机前自动保存、开机后自动恢复。
- 具体设置方法请参考主项目 README 或 FAQ。

## 常见问题
- 导入会话时，文件内容必须为"会话条目列表"，而非整个 sessions.json 字典。
- 日志文件在 `resources/session_manager.log`，可用于排查问题。

如需更多帮助，请查阅 FAQ.md 或提交 issue。 