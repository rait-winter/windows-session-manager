"""
hybrid_tabs/__init__.py
混合标签页采集模块，结合WebSocket和静态提取方法
"""

from session_manager.hybrid_tabs.hybrid_tabs_manager import (
    HybridTabsManager,
    get_browser_tabs_hybrid,
    restore_browser_tabs_hybrid,
    initialize_websocket_server
)

__all__ = [
    'HybridTabsManager',
    'get_browser_tabs_hybrid',
    'restore_browser_tabs_hybrid',
    'initialize_websocket_server'
] 