"""
browser_tabs.py
浏览器标签页处理模块，负责获取和恢复浏览器标签页。
"""

import os
import sys
import json
import time
import logging
import subprocess
import winreg
import re
import sqlite3
import shutil
import tempfile
from pathlib import Path
import psutil

logger = logging.getLogger(__name__)

# 浏览器配置信息
BROWSER_PROFILES = {
    "chrome.exe": {
        "name": "Google Chrome",
        "data_path": os.path.join(os.environ["LOCALAPPDATA"], "Google", "Chrome", "User Data"),
        "default_profile": "Default",
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session"
    },
    "msedge.exe": {
        "name": "Microsoft Edge",
        "data_path": os.path.join(os.environ["LOCALAPPDATA"], "Microsoft", "Edge", "User Data"),
        "default_profile": "Default",
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session"
    },
    "firefox.exe": {
        "name": "Mozilla Firefox",
        "data_path": os.path.join(os.environ["APPDATA"], "Mozilla", "Firefox", "Profiles"),
        "default_profile": None,  # 需要动态查找
        "places_db": "places.sqlite",
        "session_store": "sessionstore.jsonlz4",
        "command_line_args": "-new-tab"
    },
    "brave.exe": {
        "name": "Brave Browser",
        "data_path": os.path.join(os.environ["LOCALAPPDATA"], "BraveSoftware", "Brave-Browser", "User Data"),
        "default_profile": "Default",
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session"
    },
    "opera.exe": {
        "name": "Opera",
        "data_path": os.path.join(os.environ["APPDATA"], "Opera Software", "Opera Stable"),
        "default_profile": None,  # Opera 使用不同的结构
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session"
    }
}

def get_browser_tabs(browser_process_path, window_title, config):
    """
    获取浏览器标签页信息
    
    参数:
        browser_process_path: 浏览器进程路径
        window_title: 窗口标题
        config: 配置信息
        
    返回:
        标签页URL列表
    """
    browser_exe = os.path.basename(browser_process_path).lower()
    
    if browser_exe not in BROWSER_PROFILES:
        logger.warning(f"不支持的浏览器: {browser_exe}")
        return []
    
    # 获取浏览器PID
    browser_pid = get_browser_pid(browser_process_path, window_title)
    if not browser_pid:
        logger.warning(f"无法获取浏览器PID: {window_title}")
        return []
    
    # 根据浏览器类型选择不同的标签页获取方法
    if browser_exe in ["chrome.exe", "msedge.exe", "brave.exe"]:
        return get_chromium_tabs(browser_exe, browser_pid)
    elif browser_exe == "firefox.exe":
        return get_firefox_tabs(browser_pid)
    elif browser_exe == "opera.exe":
        return get_opera_tabs(browser_pid)
    
    return []

def get_browser_pid(browser_process_path, window_title):
    """获取浏览器进程ID"""
    browser_exe = os.path.basename(browser_process_path).lower()
    
    try:
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            if proc.info['exe'] and os.path.basename(proc.info['exe']).lower() == browser_exe:
                return proc.info['pid']
    except Exception as e:
        logger.error(f"获取浏览器PID时出错: {e}")
    
    return None

def get_chromium_tabs(browser_exe, browser_pid):
    """获取基于Chromium的浏览器（Chrome、Edge、Brave）的标签页"""
    browser_info = BROWSER_PROFILES.get(browser_exe)
    if not browser_info:
        return []
    
    tabs = []
    
    try:
        # 尝试从数据库获取最近的标签页
        profile_path = os.path.join(browser_info["data_path"], browser_info["default_profile"])
        
        # 如果浏览器正在运行，需要创建数据库的副本
        history_db = os.path.join(profile_path, browser_info["history_db"])
        
        if os.path.exists(history_db):
            # 创建临时副本
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_db_path = temp_file.name
            
            try:
                shutil.copy2(history_db, temp_db_path)
                
                # 连接到数据库副本
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                
                # 获取最近访问的URL（最多30个）
                cursor.execute("""
                    SELECT url, title, last_visit_time 
                    FROM urls 
                    ORDER BY last_visit_time DESC 
                    LIMIT 30
                """)
                
                for url, title, _ in cursor.fetchall():
                    tabs.append({
                        "url": url,
                        "title": title or "无标题"
                    })
                
                conn.close()
            except Exception as e:
                logger.error(f"读取{browser_info['name']}历史记录时出错: {e}")
            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_db_path)
                except:
                    pass
    
    except Exception as e:
        logger.error(f"获取{browser_info['name']}标签页时出错: {e}")
    
    return tabs

def get_firefox_tabs(browser_pid):
    """获取Firefox的标签页"""
    browser_info = BROWSER_PROFILES.get("firefox.exe")
    if not browser_info:
        return []
    
    tabs = []
    
    try:
        # 查找Firefox配置文件目录
        profile_dir = find_firefox_profile_dir()
        if not profile_dir:
            return []
        
        # 尝试从places.sqlite获取历史记录
        places_db = os.path.join(profile_dir, browser_info["places_db"])
        
        if os.path.exists(places_db):
            # 创建临时副本
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_db_path = temp_file.name
            
            try:
                shutil.copy2(places_db, temp_db_path)
                
                # 连接到数据库副本
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                
                # 获取最近访问的URL（最多30个）
                cursor.execute("""
                    SELECT url, title, last_visit_date 
                    FROM moz_places 
                    ORDER BY last_visit_date DESC 
                    LIMIT 30
                """)
                
                for url, title, _ in cursor.fetchall():
                    tabs.append({
                        "url": url,
                        "title": title or "无标题"
                    })
                
                conn.close()
            except Exception as e:
                logger.error(f"读取Firefox历史记录时出错: {e}")
            finally:
                # 删除临时文件
                try:
                    os.unlink(temp_db_path)
                except:
                    pass
    
    except Exception as e:
        logger.error(f"获取Firefox标签页时出错: {e}")
    
    return tabs

def get_opera_tabs(browser_pid):
    """获取Opera的标签页"""
    browser_info = BROWSER_PROFILES.get("opera.exe")
    if not browser_info:
        return []
    
    # Opera基于Chromium，可以使用类似的方法
    return get_chromium_tabs("opera.exe", browser_pid)

def find_firefox_profile_dir():
    """查找Firefox的配置文件目录"""
    profiles_path = BROWSER_PROFILES["firefox.exe"]["data_path"]
    
    try:
        if not os.path.exists(profiles_path):
            return None
        
        # 查找默认配置文件（通常以.default结尾）
        for item in os.listdir(profiles_path):
            if item.endswith('.default') or item.endswith('.default-release'):
                return os.path.join(profiles_path, item)
        
        # 如果没有找到默认配置文件，返回第一个配置文件
        dirs = [d for d in os.listdir(profiles_path) if os.path.isdir(os.path.join(profiles_path, d))]
        if dirs:
            return os.path.join(profiles_path, dirs[0])
    
    except Exception as e:
        logger.error(f"查找Firefox配置文件目录时出错: {e}")
    
    return None

def restore_browser_tabs(browser_exe, urls, config):
    """
    恢复浏览器标签页
    
    参数:
        browser_exe: 浏览器可执行文件名
        urls: 要恢复的URL列表
        config: 配置信息
        
    返回:
        是否成功恢复
    """
    if not urls:
        return True  # 没有标签页需要恢复
    
    browser_info = BROWSER_PROFILES.get(browser_exe.lower())
    if not browser_info:
        logger.warning(f"不支持的浏览器: {browser_exe}")
        return False
    
    # 获取浏览器完整路径
    browser_path = find_browser_path(browser_exe)
    if not browser_path:
        logger.error(f"无法找到浏览器路径: {browser_exe}")
        return False
    
    try:
        # 根据浏览器类型选择不同的恢复方法
        if browser_exe.lower() in ["chrome.exe", "msedge.exe", "brave.exe", "opera.exe"]:
            return restore_chromium_tabs(browser_path, urls)
        elif browser_exe.lower() == "firefox.exe":
            return restore_firefox_tabs(browser_path, urls)
    
    except Exception as e:
        logger.error(f"恢复浏览器标签页时出错: {e}")
    
    return False

def find_browser_path(browser_exe):
    """查找浏览器的完整路径"""
    try:
        # 常见的安装位置
        common_paths = {
            "chrome.exe": [
                os.path.join(os.environ["PROGRAMFILES"], "Google", "Chrome", "Application", "chrome.exe"),
                os.path.join(os.environ["PROGRAMFILES(X86)"], "Google", "Chrome", "Application", "chrome.exe")
            ],
            "msedge.exe": [
                os.path.join(os.environ["PROGRAMFILES"], "Microsoft", "Edge", "Application", "msedge.exe"),
                os.path.join(os.environ["PROGRAMFILES(X86)"], "Microsoft", "Edge", "Application", "msedge.exe")
            ],
            "firefox.exe": [
                os.path.join(os.environ["PROGRAMFILES"], "Mozilla Firefox", "firefox.exe"),
                os.path.join(os.environ["PROGRAMFILES(X86)"], "Mozilla Firefox", "firefox.exe")
            ],
            "brave.exe": [
                os.path.join(os.environ["PROGRAMFILES"], "BraveSoftware", "Brave-Browser", "Application", "brave.exe"),
                os.path.join(os.environ["PROGRAMFILES(X86)"], "BraveSoftware", "Brave-Browser", "Application", "brave.exe")
            ],
            "opera.exe": [
                os.path.join(os.environ["PROGRAMFILES"], "Opera", "launcher.exe"),
                os.path.join(os.environ["PROGRAMFILES(X86)"], "Opera", "launcher.exe")
            ]
        }
        
        # 检查常见路径
        browser_paths = common_paths.get(browser_exe.lower(), [])
        for path in browser_paths:
            if os.path.exists(path):
                return path
        
        # 如果常见路径中没有找到，尝试从注册表获取
        try:
            with winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"SOFTWARE\Microsoft\Windows\CurrentVersion\App Paths\\" + browser_exe) as key:
                return winreg.QueryValue(key, None)
        except:
            pass
        
        # 最后尝试使用where命令查找
        try:
            result = subprocess.run(["where", browser_exe], capture_output=True, text=True, check=True)
            paths = result.stdout.strip().split('\n')
            if paths:
                return paths[0]
        except:
            pass
    
    except Exception as e:
        logger.error(f"查找浏览器路径时出错: {e}")
    
    return None

def restore_chromium_tabs(browser_path, urls):
    """恢复基于Chromium的浏览器（Chrome、Edge、Brave、Opera）的标签页"""
    try:
        # 检查浏览器是否已经在运行
        browser_exe = os.path.basename(browser_path).lower()
        browser_running = False
        
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == browser_exe:
                browser_running = True
                break
        
        # 创建临时HTML文件，用于一次性打开多个标签页
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
            temp_html_path = f.name
            
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <title>恢复标签页</title>
                <script>
                function openTabs() {
                    var urls = [
            """)
            
            # 写入URL列表
            for tab in urls:
                url = tab.get("url", "").replace("'", "\\'")
                f.write(f"        '{url}',\n")
            
            f.write("""
                    ];
                    
                    for (var i = 0; i < urls.length; i++) {
                        window.open(urls[i], '_blank');
                    }
                }
                </script>
            </head>
            <body onload="openTabs()">
                <h1>正在恢复标签页，请稍候...</h1>
            </body>
            </html>
            """)
        
        # 启动浏览器并打开临时HTML文件
        cmd = [browser_path]
        
        if browser_running:
            cmd.append(temp_html_path)
        else:
            # 如果浏览器未运行，添加一些启动参数
            browser_info = BROWSER_PROFILES.get(browser_exe)
            if browser_info and browser_info.get("command_line_args"):
                cmd.append(browser_info["command_line_args"])
            cmd.append(temp_html_path)
        
        subprocess.Popen(cmd)
        
        # 等待一段时间后删除临时文件
        def delete_temp_file():
            time.sleep(30)  # 等待30秒，确保浏览器有足够时间加载
            try:
                os.unlink(temp_html_path)
            except:
                pass
        
        import threading
        threading.Thread(target=delete_temp_file, daemon=True).start()
        
        return True
    
    except Exception as e:
        logger.error(f"恢复Chromium标签页时出错: {e}")
        return False

def restore_firefox_tabs(browser_path, urls):
    """恢复Firefox的标签页"""
    try:
        # 检查Firefox是否已经在运行
        firefox_running = False
        
        for proc in psutil.process_iter(['name']):
            if proc.info['name'] and proc.info['name'].lower() == "firefox.exe":
                firefox_running = True
                break
        
        # Firefox可以通过命令行参数一次性打开多个URL
        cmd = [browser_path]
        
        if not firefox_running:
            cmd.append("-new-window")
        
        # 添加URL列表
        for tab in urls:
            url = tab.get("url", "")
            cmd.append(url)
        
        subprocess.Popen(cmd)
        return True
    
    except Exception as e:
        logger.error(f"恢复Firefox标签页时出错: {e}")
        return False 