"""
utils.py
通用工具函数模块。
"""

import os
import sys
import ctypes
import logging
from typing import Optional

logger = logging.getLogger(__name__)

# Windows API 相关常量和函数
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
OpenProcess = ctypes.windll.kernel32.OpenProcess
QueryFullProcessImageNameW = ctypes.windll.kernel32.QueryFullProcessImageNameW
CloseHandle = ctypes.windll.kernel32.CloseHandle

# --- 获取进程路径 ---
def get_process_path_from_hwnd(hwnd):
    """获取窗口句柄对应进程的可执行文件路径。"""
    pid = ctypes.c_ulong()
    try:
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    except Exception as e:
        logger.debug(f"Error calling GetWindowThreadProcessId for HWND {hwnd}: {e}", exc_info=True)
        return None
    if pid.value == 0:
        return None
    try:
        process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value)
    except Exception as e:
        logger.debug(f"Error calling OpenProcess for PID {pid.value}: {e}", exc_info=True)
        return None
    if not process_handle:
        return None
    buffer_size = 4096
    image_name_buffer = ctypes.create_unicode_buffer(buffer_size)
    buffer_chars = ctypes.c_ulong(buffer_size)
    success = False
    try:
        success = QueryFullProcessImageNameW(process_handle, 0, image_name_buffer, ctypes.byref(buffer_chars))
    except Exception as e:
        logger.debug(f"Error calling QueryFullProcessImageNameW for process handle {process_handle}: {e}", exc_info=True)
    try:
        CloseHandle(process_handle)
    except Exception as e:
        logger.debug(f"Error closing process handle {process_handle}: {e}", exc_info=True)
    if success:
        return image_name_buffer.value[:buffer_chars.value]
    else:
        return None

# --- 判断是否为浏览器进程 ---
def is_browser_process(process_path, config):
    """判断进程路径是否为已知浏览器。"""
    if process_path:
        browser_executables = config.get("browser_executables", [])
        return os.path.basename(process_path).lower() in [b.lower() for b in browser_executables]
    return False

# --- 判断窗口是否相关 ---
def is_window_relevant(window, config):
    """判断窗口是否为需要保存的应用窗口，返回进程路径或 False。"""
    if not window or not hasattr(window, 'visible') or not hasattr(window, 'title') or not hasattr(window, '_hWnd'):
        return False
        
    # 特殊应用可能没有可见属性或标题，但仍然需要保存
    special_app_names = ['everything', 'pixpin', 'fastorange']
    
    # 检查窗口标题是否包含特殊应用名称
    is_special_app = False
    if hasattr(window, 'title') and window.title:
        for app_name in special_app_names:
            if app_name.lower() in window.title.lower():
                is_special_app = True
                break
    
    # 如果不是特殊应用，则应用标准过滤规则
    if not is_special_app:
        if not window.visible or not window.title:
            return False
            
    exclude_window_titles = config.get("exclude_window_titles", [])
    if window.title.lower() in [t.lower() for t in exclude_window_titles]:
        return False
        
    process_path = get_process_path_from_hwnd(window._hWnd)
    if process_path:
        # 检查进程路径是否包含特殊应用名称
        for app_name in special_app_names:
            if app_name.lower() in os.path.basename(process_path).lower():
                return process_path  # 如果是特殊应用，直接返回路径
                
        exclude_process_paths = config.get("exclude_process_paths", [])
        if process_path.lower() in [p.lower() for p in exclude_process_paths]:
            return False
        return process_path
    else:
        return False

# --- 获取浏览器标签页 ---
def get_browser_tabs(browser_process_path, window_title, config):
    """
    获取浏览器标签页。
    
    参数:
        browser_process_path: 浏览器进程路径
        window_title: 窗口标题
        config: 配置信息
        
    返回:
        标签页URL列表
    """
    try:
        from session_manager.browser_tabs import get_browser_tabs as get_tabs_impl
        return get_tabs_impl(browser_process_path, window_title, config)
    except Exception as e:
        logger.error(f"获取浏览器标签页时出错: {e}", exc_info=True)
        return []

def get_valid_data_path(browser_exe: str, browser_profiles: dict) -> Optional[str]:
    """
    获取有效的浏览器数据路径
    :param browser_exe: 浏览器可执行文件名（如 chrome.exe）
    :param browser_profiles: 浏览器配置信息字典
    :return: 有效数据路径或None
    """
    if browser_exe not in browser_profiles:
        return None
    info = browser_profiles[browser_exe]
    for path in info.get("data_paths", []):
        if os.path.exists(path):
            logger.info(f"找到{browser_exe}数据路径: {path}")
            return path
    logger.warning(f"未找到{browser_exe}的有效数据路径")
    return None 