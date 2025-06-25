import os
import json
import requests
import logging
from difflib import SequenceMatcher
from session_manager.utils import get_valid_data_path

logger = logging.getLogger(__name__)

# 端口映射
PORT_MAPPING = {
    "chrome.exe": 9222,
    "msedge.exe": 9223,
    "brave.exe": 9224
}


def get_chromium_tabs_by_devtools(window_title, browser_exe):
    """使用DevTools协议获取Chromium浏览器标签页"""
    logger.info(f"尝试使用DevTools协议采集: {window_title} ({browser_exe})")
    ports = [PORT_MAPPING.get(browser_exe, 9222)]
    if not is_devtools_available(ports[0]):
        ports.extend([9222, 9223, 9224, 9225, 9226])
    for port in ports:
        try:
            response = requests.get(f"http://127.0.0.1:{port}/json", timeout=2)
            if response.status_code != 200:
                continue
            all_tabs = response.json()
            if not all_tabs:
                continue
            target_window_id = None
            best_match_score = 0
            for tab in all_tabs:
                tab_title = tab.get('title', '')
                if tab_title:
                    similarity = SequenceMatcher(None, tab_title.lower(), window_title.lower()).ratio()
                    if similarity > best_match_score and similarity > 0.3:
                        best_match_score = similarity
                        target_window_id = tab.get('windowId')
            if target_window_id is None and all_tabs:
                target_window_id = all_tabs[0].get('windowId')
            if target_window_id is not None:
                tabs = []
                for tab in all_tabs:
                    if tab.get('windowId') == target_window_id:
                        url = tab.get('url', '')
                        title = tab.get('title', '')
                        if url and not url.startswith('chrome://') and not url.startswith('about:'):
                            tabs.append({
                                "title": title or url,
                                "url": url,
                                "source": "devtools"
                            })
                if tabs:
                    logger.info(f"DevTools端口{port}成功采集到{len(tabs)}个标签页")
                    return tabs
        except Exception as e:
            logger.error(f"DevTools端口{port}处理异常: {e}")
            continue
    logger.warning("DevTools协议采集失败")
    return None


def get_chromium_tabs_by_session(browser_exe, window_title, browser_profiles):
    """使用Session文件获取Chromium浏览器标签页（兜底方案）"""
    logger.info(f"尝试使用Session文件采集: {window_title} ({browser_exe})")
    data_path = get_valid_data_path(browser_exe, browser_profiles)
    if not data_path:
        logger.error(f"未找到{browser_exe}的数据路径")
        return None
    # ...此处省略，迁移原有Session采集逻辑...
    return []


def get_chromium_tabs_for_window(browser_exe, window_title, browser_profiles):
    """获取Chromium浏览器特定窗口的标签页，优先DevTools，兜底Session"""
    tabs = get_chromium_tabs_by_devtools(window_title, browser_exe)
    if tabs:
        return tabs
    tabs = get_chromium_tabs_by_session(browser_exe, window_title, browser_profiles)
    if tabs:
        return tabs
    return [{"title": "新标签页", "url": "about:newtab", "source": "fallback"}]


def is_devtools_available(port):
    import socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(1)
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except:
        return False 