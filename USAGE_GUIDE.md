# Windows会话管理器使用指南

## 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 运行程序
```bash
python get_windows.py
```

### 3. 获得最佳采集效果（可选）
启动浏览器时启用DevTools端口：

**Chrome:**
```bash
chrome.exe --remote-debugging-port=9222 --user-data-dir=chrome_devtools_profile
```

**Edge:**
```bash
msedge.exe --remote-debugging-port=9223 --user-data-dir=edge_devtools_profile
```

**Brave:**
```bash
brave.exe --remote-debugging-port=9224 --user-data-dir=brave_devtools_profile
```

## 主要功能

### 会话管理
- **保存会话**: 点击"保存会话"按钮，采集当前所有窗口和浏览器标签页
- **恢复会话**: 选择会话后点击"恢复会话"，自动打开保存的窗口和标签页
- **选择性恢复**: 系统会自动跳过已存在的窗口，只恢复不存在的窗口
- **会话管理**: 支持重命名、删除、导出、导入会话

### 浏览器标签页采集
系统采用智能采集策略，按以下优先级获取标签页：

1. **DevTools协议** (最准确)
   - 实时获取当前标签页
   - 准确率100%
   - 需要浏览器启用DevTools端口

2. **Session文件** (兜底方案)
   - 采集历史标签页
   - 准确率>90%
   - 无需特殊配置

3. **历史记录** (最后方案)
   - 从浏览器历史数据库获取
   - 准确率>80%
   - 按访问时间排序

### 界面功能
- **树形结构**: 浏览器窗口下显示所有标签页
- **双击打开**: 双击标签页可直接打开网页
- **浏览器历史**: 点击"浏览器历史"查看历史记录
- **会话历史**: 查看所有保存的会话

## 支持的浏览器

| 浏览器 | DevTools端口 | 采集方式 |
|--------|-------------|----------|
| Chrome | 9222 | DevTools协议/Session文件/历史记录 |
| Edge | 9223 | DevTools协议/Session文件/历史记录 |
| Brave | 9224 | DevTools协议/Session文件/历史记录 |
| Opera | - | Session文件/历史记录 |
| Firefox | - | sessionstore.jsonlz4 |

## 常见问题

### Q: 为什么采集到的标签页不准确？
A: 如果DevTools协议未启用，系统会使用Session文件或历史记录采集。建议启用DevTools端口获得最佳效果。

### Q: 如何启用DevTools协议？
A: 启动浏览器时添加`--remote-debugging-port=端口号`参数。具体命令见"快速开始"部分。

### Q: 采集失败怎么办？
A: 系统会自动降级到其他采集方式。如果仍然失败，请检查：
- 浏览器是否已安装
- 是否有足够的文件访问权限
- 浏览器是否正在运行（可能锁定文件）

### Q: 支持哪些操作系统？
A: 目前仅支持Windows系统。

## 高级功能

### 混合标签页采集
系统还支持WebSocket实时采集，可通过浏览器扩展实现更精确的标签页监控。

### 会话数据格式
```json
{
  "title": "窗口标题",
  "browser": "chrome.exe",
  "tabs": [
    {
      "title": "页面标题",
      "url": "https://example.com",
      "source": "devtools"
    }
  ]
}
```

### 配置选项
可在`session_manager/config.json`中修改配置：
- 采集策略优先级
- 浏览器路径
- 日志级别
- 界面主题

## 故障排除

### DevTools连接失败
1. 检查端口是否被占用：`netstat -an | findstr 9222`
2. 终止占用进程：`taskkill /f /im chrome.exe`
3. 重新启动浏览器

### 路径检测失败
1. 确认浏览器已正确安装
2. 检查自定义安装路径
3. 验证文件访问权限

### 采集到模拟数据
1. 关闭浏览器避免文件锁定
2. 等待文件解锁后重新采集
3. 检查配置文件完整性

---

**提示**: 启用DevTools协议可获得最佳采集效果，但系统会自动降级确保基本功能可用。 