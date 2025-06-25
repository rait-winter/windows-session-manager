import os
import logging
from session_manager.browser_collectors.chrome_collector import get_chromium_tabs_for_window

logger = logging.getLogger(__name__)

def get_opera_tabs(browser_pid, browser_profiles):
    """获取Opera的标签页"""
    # Opera基于Chromium，可以直接调用get_chromium_tabs
    return get_chromium_tabs("opera.exe", browser_pid, browser_profiles)

def get_opera_tabs_for_window(browser_pid, window_title, browser_profiles):
    """获取特定Opera窗口的标签页"""
    # Opera基于Chromium，直接调用Chromium采集接口
    return get_chromium_tabs_for_window("opera.exe", window_title, browser_profiles) 