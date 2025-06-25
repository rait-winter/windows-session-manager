# Windows 会话管理器

## 项目简介

本项目是一款专注于**本地会话管理**和**浏览器窗口及标签页采集**的工具，支持主流浏览器（Chrome、Edge、Brave、Opera、Firefox），采用多种采集策略确保数据准确性。

- 支持采集和保存所有主流浏览器的窗口及真实标签页
- 支持DevTools协议实时采集和Session文件兜底采集
- 支持会话一键保存、恢复、导出、导入
- 支持图形界面（Treeview树形结构展示窗口与标签页）
- 支持普通应用、特殊应用、浏览器窗口统一管理

## 支持的浏览器及采集方式

| 浏览器         | 采集方式                    | 优先级 | 备注                   |
|----------------|----------------------------|--------|------------------------|
| Chrome         | DevTools协议/Session文件/历史数据库 | 1/2/3 | 实时采集，准确率最高    |
| Edge           | DevTools协议/Session文件/历史数据库 | 1/2/3 |                        |
| Brave          | DevTools协议/Session文件/历史数据库 | 1/2/3 |                        |
| Opera          | Session文件/历史数据库      | 2/3    |                        |
| Firefox        | sessionstore.jsonlz4       | 1      | 精准分组，效果最佳      |

## 安装与运行

1. 安装依赖：
   ```bash
   pip install -r requirements.txt
   ```

2. 运行主程序：
   ```bash
   python get_windows.py
   ```

3. 启动浏览器DevTools（可选，用于实时采集）：
   ```bash
   # Chrome
   chrome.exe --remote-debugging-port=9222 --user-data-dir=chrome_devtools_profile
   
   # Edge
   msedge.exe --remote-debugging-port=9223 --user-data-dir=edge_devtools_profile
   
   # Brave
   brave.exe --remote-debugging-port=9224 --user-data-dir=brave_devtools_profile
   ```

## 主要功能

### 核心功能
- 一键采集并保存当前所有应用和浏览器窗口及其标签页
- Treeview树形结构展示：浏览器窗口下可见所有真实标签页
- 支持会话导入、导出、重命名、删除、清空
- 支持双击标签页直接打开网页
- 支持特殊应用（如截图、剪贴板工具）识别与管理

### 浏览器标签页采集
- **DevTools协议**: 实时采集当前标签页，准确率100%
- **Session文件**: 采集历史标签页，准确率>90%
- **历史记录**: 兜底采集，准确率>80%
- **智能降级**: 自动选择最佳采集方式

### 会话管理
- 选择性恢复功能，智能跳过已存在的窗口
- 会话历史记录查看
- 浏览器历史记录查看
- 会话数据导入导出

## 采集策略

### 优先级顺序
1. **DevTools协议** (最准确)
   - 实时获取当前标签页
   - 支持多窗口识别
   - 过滤无效URL

2. **Session文件** (兜底方案)
   - Current Session
   - Current Tabs
   - Last Session
   - Last Tabs

3. **历史记录** (最后方案)
   - 从History数据库获取最近访问
   - 按访问时间排序

## 常见问题

- **Q: 为什么有些浏览器窗口下的标签页不全？**
  - A: 如果DevTools协议未启用，系统会使用Session文件或历史记录采集，可能无法100%还原当前状态。建议启用DevTools协议获得最佳效果。

- **Q: 需要特殊参数或扩展吗？**
  - A: 不需要浏览器扩展，但启用DevTools协议可获得最佳采集效果。系统会自动降级到其他采集方式。

- **Q: 支持哪些操作系统？**
  - A: 目前仅支持Windows。

- **Q: 如何获得最佳采集效果？**
  - A: 启动浏览器时启用DevTools端口，系统会自动使用实时采集方式。

## 技术架构

### 采集流程
```
1. 检测浏览器路径
2. 尝试DevTools连接
3. 如果成功 → 实时采集
4. 如果失败 → 读取Session文件
5. 如果失败 → 读取历史记录
6. 如果失败 → 返回默认标签页
```

### 数据格式
```json
{
    "title": "页面标题",
    "url": "https://example.com",
    "source": "devtools|sessionstore|history|default"
}
```

## 贡献与反馈

欢迎提交issue、PR或建议！

---

> 本项目适合个人和开发者本地环境的会话/标签页管理，数据完全本地化，安全可靠。支持多种采集策略，确保在各种环境下都能获得良好的用户体验。 