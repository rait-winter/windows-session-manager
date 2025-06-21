#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
混合标签页管理器 - 结合WebSocket和静态提取方法
"""

import os
import sys
import json
import time
import logging
import threading
from datetime import datetime, timedelta

# 导入静态提取方法
from session_manager.browser_tabs import (
    get_browser_tabs as get_browser_tabs_static,
    restore_browser_tabs as restore_browser_tabs_static
)

# 导入WebSocket服务器
from session_manager.hybrid_tabs.websocket_server import (
    get_latest_tabs,
    get_server_status,
    run_server_in_thread,
    stop_server
)

logger = logging.getLogger(__name__)

# WebSocket服务器配置
DEFAULT_WS_CONFIG = {
    "enabled": True,
    "host": "127.0.0.1",
    "port": 8765,
    "auto_start": True
}

# 浏览器ID映射
BROWSER_ID_MAPPING = {
    "chrome.exe": "chrome",
    "msedge.exe": "edge",
    "firefox.exe": "firefox",
    "brave.exe": "brave",
    "opera.exe": "opera"
}

class HybridTabsManager:
    """混合标签页管理器，结合WebSocket和静态提取方法"""
    
    _instance = None
    
    def __new__(cls, config=None):
        """单例模式"""
        if cls._instance is None:
            cls._instance = super(HybridTabsManager, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self, config=None):
        """初始化混合标签页管理器
        
        参数:
            config: 配置信息，包含WebSocket服务器配置
        """
        if self._initialized:
            return
            
        self.config = config or {}
        self.ws_config = self.config.get("websocket", DEFAULT_WS_CONFIG)
        self.websocket_enabled = self.ws_config.get("enabled", True)
        self.websocket_started = False
        self.tabs_cache = {}  # 缓存标签页数据
        self.cache_time = {}  # 缓存时间
        self.cache_duration = timedelta(seconds=30)  # 缓存有效期30秒
        
        # 如果启用了WebSocket并配置了自动启动，则启动WebSocket服务器
        if self.websocket_enabled and self.ws_config.get("auto_start", True):
            self.start_websocket_server()
        
        self._initialized = True
    
    def start_websocket_server(self):
        """启动WebSocket服务器"""
        if not self.websocket_enabled:
            logger.info("WebSocket服务器已禁用")
            return False
            
        if self.websocket_started:
            logger.info("WebSocket服务器已经在运行")
            return True
            
        host = self.ws_config.get("host", "127.0.0.1")
        port = self.ws_config.get("port", 8765)
        
        success = run_server_in_thread(host, port)
        if success:
            self.websocket_started = True
            logger.info(f"WebSocket服务器已启动 ({host}:{port})")
        else:
            logger.warning("启动WebSocket服务器失败")
            
        return success
    
    def stop_websocket_server(self):
        """停止WebSocket服务器"""
        if not self.websocket_started:
            return
            
        stop_server()
        self.websocket_started = False
        logger.info("WebSocket服务器已停止")
    
    def get_browser_tabs(self, browser_process_path, window_title, config=None):
        """获取浏览器标签页，优先使用WebSocket数据
        
        参数:
            browser_process_path: 浏览器进程路径
            window_title: 窗口标题
            config: 配置信息
            
        返回:
            标签页URL列表
        """
        browser_exe = os.path.basename(browser_process_path).lower()
        
        # 检查缓存
        cache_key = f"{browser_process_path}::{window_title}"
        if cache_key in self.tabs_cache and cache_key in self.cache_time:
            if datetime.now() - self.cache_time[cache_key] < self.cache_duration:
                logger.debug(f"使用缓存的标签页数据: {cache_key}")
                return self.tabs_cache[cache_key]
        
        # 如果WebSocket服务器已启动，尝试从WebSocket获取数据
        if self.websocket_enabled and self.websocket_started:
            tabs = self._get_tabs_from_websocket(browser_exe, window_title)
            if tabs:
                logger.info(f"使用WebSocket方法获取到 {len(tabs)} 个标签页")
                # 缓存结果
                self.tabs_cache[cache_key] = tabs
                self.cache_time[cache_key] = datetime.now()
                return tabs
        
        # 如果WebSocket方法失败或未启用，回退到静态提取方法
        logger.info(f"WebSocket方法未获取到标签页，回退到静态提取方法")
        tabs = get_browser_tabs_static(browser_process_path, window_title, config or self.config)
        
        # 缓存结果
        self.tabs_cache[cache_key] = tabs
        self.cache_time[cache_key] = datetime.now()
        
        return tabs
    
    def restore_browser_tabs(self, browser_process_path, window_title, tabs, config=None):
        """恢复浏览器标签页
        
        参数:
            browser_process_path: 浏览器进程路径
            window_title: 窗口标题
            tabs: 标签页列表
            config: 配置信息
            
        返回:
            是否成功恢复
        """
        # 直接使用静态方法恢复标签页
        return restore_browser_tabs_static(browser_process_path, window_title, tabs, config or self.config)
    
    def _get_tabs_from_websocket(self, browser_exe, window_title):
        """从WebSocket获取标签页数据
        
        参数:
            browser_exe: 浏览器可执行文件名
            window_title: 窗口标题
            
        返回:
            标签页列表，如果未找到则返回空列表
        """
        try:
            # 获取浏览器ID
            browser_id = BROWSER_ID_MAPPING.get(browser_exe, "unknown")
            
            # 获取最新的标签页数据
            tabs_data = get_latest_tabs()
            if not tabs_data or browser_id not in tabs_data:
                logger.debug(f"WebSocket中未找到浏览器 {browser_id} 的标签页数据")
                return []
            
            # 清理窗口标题，去除浏览器后缀
            clean_window_title = window_title
            for suffix in [" - Google Chrome", " - Microsoft Edge", " - Brave", " - Firefox", " - Opera"]:
                if clean_window_title.endswith(suffix):
                    clean_window_title = clean_window_title[:-len(suffix)]
                    break
            
            # 遍历所有窗口，寻找匹配的窗口
            matching_tabs = []
            best_match_window = None
            best_match_score = 0
            
            for window_id, window_data in tabs_data[browser_id].items():
                window_tabs = window_data.get("tabs", [])
                
                # 检查是否有标签页标题与窗口标题匹配
                for tab in window_tabs:
                    tab_title = tab.get("title", "")
                    if not tab_title:
                        continue
                        
                    # 计算标题相似度
                    from session_manager.browser_tabs import calculate_similarity
                    similarity = calculate_similarity(tab_title, clean_window_title)
                    
                    # 如果找到活动标签页且相似度高，认为找到了匹配的窗口
                    if tab.get("active", False) and similarity > 0.7:
                        logger.debug(f"找到匹配的活动标签页: {tab_title[:30]}... (相似度: {similarity:.2f})")
                        best_match_window = window_id
                        best_match_score = similarity
                        break
                    
                    # 记录最佳匹配
                    if similarity > best_match_score:
                        best_match_score = similarity
                        best_match_window = window_id
            
            # 如果找到匹配的窗口，返回该窗口的所有标签页
            if best_match_window:
                window_data = tabs_data[browser_id][best_match_window]
                window_tabs = window_data.get("tabs", [])
                
                # 转换为静态方法返回的格式
                for tab in window_tabs:
                    matching_tabs.append({
                        "url": tab.get("url", ""),
                        "title": tab.get("title", ""),
                        "active": tab.get("active", False)
                    })
                
                logger.debug(f"从WebSocket获取到窗口 {best_match_window} 的 {len(matching_tabs)} 个标签页")
                return matching_tabs
            
            logger.debug(f"WebSocket中未找到与窗口标题 '{clean_window_title}' 匹配的窗口")
            return []
            
        except Exception as e:
            logger.error(f"从WebSocket获取标签页时出错: {e}")
            return []
    
    def get_server_status(self):
        """获取WebSocket服务器状态"""
        return get_server_status()

# 全局单例实例
_manager_instance = None

def get_hybrid_tabs_manager(config=None):
    """获取混合标签页管理器的单例实例"""
    global _manager_instance
    if _manager_instance is None:
        _manager_instance = HybridTabsManager(config)
    return _manager_instance

def initialize_websocket_server(config=None):
    """初始化并启动WebSocket服务器"""
    manager = get_hybrid_tabs_manager(config)
    return manager.start_websocket_server()

def get_browser_tabs_hybrid(browser_process_path, window_title, config=None):
    """获取浏览器标签页，混合方法"""
    manager = get_hybrid_tabs_manager(config)
    return manager.get_browser_tabs(browser_process_path, window_title, config)

def restore_browser_tabs_hybrid(browser_process_path, window_title, tabs, config=None):
    """恢复浏览器标签页，混合方法"""
    manager = get_hybrid_tabs_manager(config)
    return manager.restore_browser_tabs(browser_process_path, window_title, tabs, config) 