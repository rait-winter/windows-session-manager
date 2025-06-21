# 混合标签页采集方法实现说明

## 一、概述

本项目实现了一种混合的浏览器标签页采集方法，结合了WebSocket实时采集和静态文件提取两种技术。这种混合方法具有以下优势：

1. **实时性**：通过WebSocket获取实时标签页变化
2. **准确性**：直接从浏览器API获取数据，避免解析错误
3. **可靠性**：当WebSocket不可用时，自动回退到静态提取方法
4. **兼容性**：保持与现有代码的向后兼容性

## 二、架构设计

混合标签页采集方法的架构包括以下组件：

1. **浏览器扩展**：安装在用户浏览器中，监控标签页变化并通过WebSocket发送数据
2. **WebSocket服务器**：接收浏览器扩展发送的数据，并提供API供其他组件访问
3. **混合标签页管理器**：协调WebSocket和静态提取方法，提供统一的API
4. **会话管理器集成**：将混合标签页管理器集成到现有的会话管理器中

## 三、目录结构

```
session_manager/
├── hybrid_tabs/
│   ├── __init__.py          # 导出主要函数和类
│   ├── websocket_server.py  # WebSocket服务器实现
│   └── hybrid_tabs_manager.py # 混合标签页管理器实现
├── browser_tabs.py          # 原有的静态提取方法
└── core.py                  # 已修改，使用混合方法

docs/
└── browser_extension_guide.md # 浏览器扩展安装和配置指南

websocket_tabs_poc/
└── browser_extension/       # 浏览器扩展源代码

start_tabs_server.py         # 启动WebSocket服务器的脚本
start_tabs_server.bat        # Windows批处理文件
```

## 四、实现细节

### 1. 混合标签页管理器

混合标签页管理器(`HybridTabsManager`)是核心组件，负责协调WebSocket和静态提取方法：

- 优先使用WebSocket方法获取标签页数据
- 当WebSocket数据不可用时，自动回退到静态提取方法
- 提供缓存机制，减少重复查询
- 使用单例模式确保全局只有一个实例

### 2. WebSocket服务器

WebSocket服务器(`websocket_server.py`)负责与浏览器扩展通信：

- 接收浏览器扩展发送的标签页数据
- 存储最新的标签页数据
- 提供API供混合标签页管理器访问
- 支持在后台线程中运行

### 3. 会话管理器集成

修改了会话管理器的核心模块(`core.py`)，使其使用混合标签页管理器：

- 导入混合标签页管理器的函数
- 在启动时初始化WebSocket服务器
- 在采集和恢复会话时使用混合方法
- 保持向后兼容性，当混合方法不可用时回退到静态方法

## 五、使用方法

### 1. 安装浏览器扩展

详见`docs/browser_extension_guide.md`

### 2. 启动WebSocket服务器

有两种方式启动WebSocket服务器：

1. **自动启动**：会话管理器启动时自动启动WebSocket服务器
2. **手动启动**：运行`start_tabs_server.bat`或`python start_tabs_server.py`

### 3. 配置

在配置文件中添加WebSocket相关配置：

```json
{
  "websocket": {
    "enabled": true,
    "host": "127.0.0.1",
    "port": 8765,
    "auto_start": true
  }
}
```

## 六、未来改进

1. **多浏览器支持**：扩展Firefox和其他浏览器的支持
2. **安全性增强**：添加WebSocket连接的认证机制
3. **UI集成**：在会话管理器UI中添加WebSocket服务器状态显示
4. **性能优化**：优化数据传输和处理效率
5. **错误恢复**：增强连接断开、数据不一致等情况的处理机制 