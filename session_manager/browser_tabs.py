"""
browser_tabs.py
浏览器标签页处理模块，负责获取和恢复浏览器标签页。
优化版本 - 优先使用DevTools协议，增强错误处理
"""

import os
import json
import requests
import pygetwindow as gw
import win32process
import psutil
import sqlite3
import tempfile
import shutil
import lz4.block
from collections import defaultdict
from difflib import SequenceMatcher
import logging
import subprocess
import socket
import time
import threading

logger = logging.getLogger(__name__)

# 浏览器配置信息 - 优化路径检测
BROWSER_PROFILES = {
    "chrome.exe": {
        "name": "Google Chrome",
        "data_paths": [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Google", "Chrome", "User Data"),
            os.path.join(os.environ.get("APPDATA", ""), "Google", "Chrome", "User Data"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Google", "Chrome", "User Data")
        ],
        "default_profile": "Default",
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session --remote-debugging-port=9222"
    },
    "msedge.exe": {
        "name": "Microsoft Edge",
        "data_paths": [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "Edge", "User Data"),
            os.path.join(os.environ.get("APPDATA", ""), "Microsoft", "Edge", "User Data"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "Microsoft", "Edge", "User Data")
        ],
        "default_profile": "Default",
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session --remote-debugging-port=9223"
    },
    "brave.exe": {
        "name": "Brave Browser",
        "data_paths": [
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "BraveSoftware", "Brave-Browser", "User Data"),
            os.path.join(os.environ.get("APPDATA", ""), "BraveSoftware", "Brave-Browser", "User Data"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Local", "BraveSoftware", "Brave-Browser", "User Data")
        ],
        "default_profile": "Default",
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session --remote-debugging-port=9224"
    },
    "opera.exe": {
        "name": "Opera",
        "data_paths": [
            os.path.join(os.environ.get("APPDATA", ""), "Opera Software", "Opera Stable"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Opera Software", "Opera Stable"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming", "Opera Software", "Opera Stable")
        ],
        "default_profile": None,
        "history_db": "History",
        "bookmarks_file": "Bookmarks",
        "current_tabs_file": "Current Tabs",
        "current_session_file": "Current Session",
        "local_state_file": "Local State",
        "command_line_args": "--restore-last-session"
    },
    "firefox.exe": {
        "name": "Mozilla Firefox",
        "data_paths": [
            os.path.join(os.environ.get("APPDATA", ""), "Mozilla", "Firefox", "Profiles"),
            os.path.join(os.environ.get("LOCALAPPDATA", ""), "Mozilla", "Firefox", "Profiles"),
            os.path.join(os.environ.get("USERPROFILE", ""), "AppData", "Roaming", "Mozilla", "Firefox", "Profiles")
        ]
    }
}

def get_valid_data_path(browser_exe):
    """获取有效的浏览器数据路径"""
    if browser_exe not in BROWSER_PROFILES:
        return None
    
    info = BROWSER_PROFILES[browser_exe]
    for path in info.get("data_paths", []):
        if os.path.exists(path):
            logger.info(f"找到{browser_exe}数据路径: {path}")
            return path
    
    logger.warning(f"未找到{browser_exe}的有效数据路径")
    return None

def is_devtools_available(port):
    """检查DevTools端口是否可用"""
    try:
        response = requests.get(f"http://127.0.0.1:{port}/json", timeout=1)
        return response.status_code == 200
    except:
        return False

def get_chromium_tabs_by_devtools(window_title, browser_exe):
    """使用DevTools协议获取Chromium浏览器标签页"""
    logger.info(f"尝试使用DevTools协议采集: {window_title} ({browser_exe})")
    
    # 根据浏览器类型确定端口
    port_mapping = {
        "chrome.exe": 9222,
        "msedge.exe": 9223,
        "brave.exe": 9224
    }
    
    ports = [port_mapping.get(browser_exe, 9222)]
    # 如果主端口不可用，尝试其他端口
    if not is_devtools_available(ports[0]):
        ports.extend([9222, 9223, 9224, 9225, 9226])
    
    for port in ports:
        try:
            logger.debug(f"尝试连接DevTools端口: {port}")
            response = requests.get(f"http://127.0.0.1:{port}/json", timeout=2)
            if response.status_code != 200:
                continue
                
            all_tabs = response.json()
            if not all_tabs:
                continue
                
            # 查找匹配的窗口
            target_window_id = None
            best_match_score = 0
            
            for tab in all_tabs:
                tab_title = tab.get('title', '')
                if tab_title:
                    # 计算标题匹配度
                    similarity = SequenceMatcher(None, tab_title.lower(), window_title.lower()).ratio()
                    if similarity > best_match_score and similarity > 0.3:
                        best_match_score = similarity
                        target_window_id = tab.get('windowId')
            
            # 如果没找到匹配的窗口，使用第一个窗口
            if target_window_id is None and all_tabs:
                target_window_id = all_tabs[0].get('windowId')
            
            if target_window_id is not None:
                tabs = []
                for tab in all_tabs:
                    if tab.get('windowId') == target_window_id:
                        url = tab.get('url', '')
                        title = tab.get('title', '')
                        
                        # 过滤无效URL
                        if url and not url.startswith('chrome://') and not url.startswith('about:'):
                            tabs.append({
                                "title": title or url,
                                "url": url,
                                "source": "devtools"
                            })
                
                if tabs:
                    logger.info(f"DevTools端口{port}成功采集到{len(tabs)}个标签页")
                    return tabs
                    
        except requests.exceptions.RequestException as e:
            logger.debug(f"DevTools端口{port}连接失败: {e}")
            continue
        except Exception as e:
            logger.error(f"DevTools端口{port}处理异常: {e}")
            continue
    
    logger.warning("DevTools协议采集失败")
    return None

def get_chromium_tabs_by_session(browser_exe, window_title):
    """使用Session文件获取Chromium浏览器标签页（兜底方案）"""
    logger.info(f"尝试使用Session文件采集: {window_title} ({browser_exe})")
    
    data_path = get_valid_data_path(browser_exe)
    if not data_path:
        logger.error(f"未找到{browser_exe}的数据路径")
        return None
    
    info = BROWSER_PROFILES[browser_exe]
    profiles = ["Default"]
    
    # 读取Local State获取所有配置文件
    local_state_path = os.path.join(data_path, "Local State")
    if os.path.exists(local_state_path):
        try:
            with open(local_state_path, 'r', encoding='utf-8') as f:
                local_state = json.load(f)
                profile_info = local_state.get("profile", {}).get("info_cache", {})
                for profile_name in profile_info.keys():
                    if profile_name != "Default" and os.path.exists(os.path.join(data_path, profile_name)):
                        profiles.append(profile_name)
        except Exception as e:
            logger.error(f"解析Local State失败: {e}")
    
    all_tabs = []
    for profile in profiles:
        profile_path = os.path.join(data_path, profile)
        
        # 尝试从Session文件获取标签页
        session_files = [
            os.path.join(profile_path, "Current Session"),
            os.path.join(profile_path, "Current Tabs"),
            os.path.join(profile_path, "Last Session"),
            os.path.join(profile_path, "Last Tabs")
        ]
        
        for session_file in session_files:
            if os.path.exists(session_file):
                try:
                    tabs = extract_tabs_from_session_files(info, session_file)
                    if tabs:
                        all_tabs.extend(tabs)
                        logger.info(f"从{session_file}采集到{len(tabs)}个标签页")
                except Exception as e:
                    logger.error(f"读取Session文件失败 {session_file}: {e}")
        
        # 如果Session文件没有数据，从历史记录获取
        if not all_tabs:
            try:
                tabs = extract_tabs_from_history(info, profile_path)
                if tabs:
                    all_tabs.extend(tabs)
                    logger.info(f"从{profile}历史记录采集到{len(tabs)}个标签页")
            except Exception as e:
                logger.error(f"读取历史记录失败 {profile}: {e}")
    
    # 去重并限制数量
    unique_tabs = []
    seen_urls = set()
    for tab in all_tabs:
        if tab.get('url') and tab['url'] not in seen_urls:
            seen_urls.add(tab['url'])
            unique_tabs.append(tab)
            if len(unique_tabs) >= 20:  # 限制最多20个标签页
                break
    
    if unique_tabs:
        logger.info(f"Session/历史采集成功，共{len(unique_tabs)}个标签页")
        return unique_tabs
    
    logger.warning("Session/历史采集失败，返回默认标签页")
    return [{"title": "新标签页", "url": "about:newtab", "source": "default"}]

def get_firefox_tabs(window_title):
    """获取Firefox浏览器标签页"""
    logger.info(f"尝试采集Firefox标签页: {window_title}")
    
    # 获取有效的Firefox数据路径
    data_paths = BROWSER_PROFILES["firefox.exe"]["data_paths"]
    profiles_path = None
    
    for path in data_paths:
        if os.path.exists(path):
            profiles_path = path
            logger.info(f"找到Firefox profiles路径: {path}")
            break
    
    if not profiles_path:
        logger.error("未找到Firefox profiles目录")
        return [{"title": "新标签页", "url": "about:newtab", "source": "default"}]
    
    # 查找配置文件目录
    profile_dir = None
    profile_candidates = []
    
    try:
        for item in os.listdir(profiles_path):
            item_path = os.path.join(profiles_path, item)
            if os.path.isdir(item_path):
                if item.endswith('.default') or item.endswith('.default-release'):
                    profile_candidates.append((item_path, 1))  # 优先级1
                else:
                    profile_candidates.append((item_path, 0))  # 优先级0
        
        # 按优先级排序
        profile_candidates.sort(key=lambda x: x[1], reverse=True)
        
        if profile_candidates:
            profile_dir = profile_candidates[0][0]
            logger.info(f"选择Firefox profile: {os.path.basename(profile_dir)}")
        
    except Exception as e:
        logger.error(f"查找Firefox profile失败: {e}")
    
    if not profile_dir:
        logger.error("未找到Firefox profile目录")
        return [{"title": "新标签页", "url": "about:newtab", "source": "default"}]
    
    # 方法1: 从sessionstore.jsonlz4获取当前会话
    session_file = os.path.join(profile_dir, "sessionstore.jsonlz4")
    if os.path.exists(session_file):
        try:
            with open(session_file, "rb") as f:
                f.read(8)  # 跳过LZ4头部
                data = lz4.block.decompress(f.read())
                session_data = json.loads(data.decode("utf-8"))
                
                best_score = 0
                best_tabs = []
                
                for win in session_data.get("windows", []):
                    # 提取窗口标题
                    win_title = ""
                    if win.get("tabs"):
                        entries = win["tabs"][0].get("entries", [])
                        if entries:
                            win_title = entries[-1].get("title", "")
                    
                    # 计算窗口标题匹配度
                    if win_title:
                        similarity = calculate_similarity(win_title, window_title)
                        if similarity > best_score:
                            best_score = similarity
                            tabs = []
                            for tab in win.get("tabs", []):
                                idx = tab.get("index", 1) - 1
                                entries = tab.get("entries", [])
                                if entries and 0 <= idx < len(entries):
                                    entry = entries[idx]
                                    url = entry.get("url", "")
                                    title = entry.get("title", url)
                                    
                                    # 过滤无效URL
                                    if url and not url.startswith('about:') and not url.startswith('chrome:'):
                                        tabs.append({
                                            "title": title,
                                            "url": url,
                                            "source": "sessionstore"
                                        })
                            best_tabs = tabs
                
                if best_tabs:
                    logger.info(f"从sessionstore.jsonlz4采集到{len(best_tabs)}个标签页")
                    return best_tabs
                    
        except Exception as e:
            logger.error(f"解析sessionstore.jsonlz4失败: {e}")
    
    # 方法2: 从places.sqlite获取历史记录
    places_file = os.path.join(profile_dir, 'places.sqlite')
    if os.path.exists(places_file):
        try:
            with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                temp_db_path = temp_file.name
            
            try:
                shutil.copy2(places_file, temp_db_path)
                conn = sqlite3.connect(temp_db_path)
                cursor = conn.cursor()
                
                # 获取最近的访问记录
                cursor.execute("""
                    SELECT title, url, last_visit_date 
                    FROM moz_places 
                    WHERE url LIKE 'http%' 
                    AND last_visit_date IS NOT NULL
                    ORDER BY last_visit_date DESC 
                    LIMIT 30
                """)
                
                tabs = []
                for row in cursor.fetchall():
                    title, url, visit_date = row
                    if url and not url.startswith('about:') and not url.startswith('chrome:'):
                        tabs.append({
                            'title': title or url,
                            'url': url,
                            'source': 'history',
                            'visit_date': visit_date
                        })
                
                conn.close()
                logger.info(f"从places.sqlite采集到{len(tabs)}个标签页")
                
                if tabs:
                    return tabs
                    
            except Exception as e:
                logger.error(f"读取places.sqlite失败: {e}")
            finally:
                try:
                    os.unlink(temp_db_path)
                except:
                    pass
                    
        except Exception as e:
            logger.error(f"复制places.sqlite失败: {e}")
    
    # 方法3: 如果都失败了，返回默认标签页
    logger.warning("Firefox采集失败，返回默认标签页")
    return [{"title": "新标签页", "url": "about:newtab", "source": "fallback"}]

def collect_all_browser_tabs():
    """仅通过session文件和历史数据库采集标签页，并按窗口标题与tab标题相似度分配"""
    browser_windows = []
    local_windows = []
    for w in gw.getAllWindows():
        if not w.title:
            continue
        try:
            _, pid = win32process.GetWindowThreadProcessId(w._hWnd)
            proc = psutil.Process(pid)
            exe = os.path.basename(proc.exe()).lower()
            if exe in BROWSER_PROFILES:
                local_windows.append({
                    "title": w.title,
                    "hwnd": w._hWnd,
                    "pid": pid,
                    "browser": exe
                })
        except Exception:
            continue
    # 采集所有profile下的tabs
    def get_chromium_all_tabs(browser_exe):
        info = BROWSER_PROFILES[browser_exe]
        user_data_dir = info["data_paths"][0]
        tabs = []
        # 遍历所有profile
        profiles = ["Default"]
        local_state_path = os.path.join(user_data_dir, "Local State")
        if os.path.exists(local_state_path):
            with open(local_state_path, 'r', encoding='utf-8') as f:
                try:
                    local_state = json.load(f)
                    profile_info = local_state.get("profile", {}).get("info_cache", {})
                    for profile_name in profile_info.keys():
                        if profile_name != "Default" and os.path.exists(os.path.join(user_data_dir, profile_name)):
                            profiles.append(profile_name)
                except:
                    pass
        for profile in profiles:
            # 1. Session文件
            for fname in ["Current Session", "Current Tabs", "Last Session", "Last Tabs"]:
                fpath = os.path.join(user_data_dir, profile, fname)
                if os.path.exists(fpath):
                    try:
                        with open(fpath, "rb") as f:
                            data = f.read()
                            import re
                            urls = re.findall(b'https?://[^"]+', data)
                            for u in urls:
                                try:
                                    url = u.decode("utf-8", errors="ignore")
                                    if url.startswith("http"):
                                        tabs.append({"title": url, "url": url})
                                except:
                                    continue
                    except:
                        continue
            # 2. 历史数据库
            history_db = os.path.join(user_data_dir, profile, "History")
            if os.path.exists(history_db):
                import tempfile, shutil, sqlite3
                with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as temp_file:
                    temp_db_path = temp_file.name
                try:
                    shutil.copy2(history_db, temp_db_path)
                    conn = sqlite3.connect(temp_db_path)
                    cursor = conn.cursor()
                    cursor.execute("SELECT url, title FROM urls ORDER BY last_visit_time DESC LIMIT 30")
                    for url, title in cursor.fetchall():
                        tabs.append({"title": title or url, "url": url})
                    conn.close()
                except:
                    pass
                finally:
                    try: os.unlink(temp_db_path)
                    except: pass
        # 去重
        seen = set()
        unique_tabs = []
        for tab in tabs:
            if tab["url"] and tab["url"] not in seen:
                seen.add(tab["url"])
                unique_tabs.append(tab)
        return unique_tabs
    # 分配tabs到窗口
    for browser_exe in ["chrome.exe", "msedge.exe", "brave.exe", "opera.exe"]:
        all_tabs = get_chromium_all_tabs(browser_exe)
        for win in [w for w in local_windows if w["browser"] == browser_exe]:
            from difflib import SequenceMatcher
            best_tabs = []
            for tab in all_tabs:
                score = SequenceMatcher(None, win["title"], tab["title"]).ratio()
                if score > 0.3:
                    best_tabs.append(tab)
            if not best_tabs:
                best_tabs = all_tabs[:5]
            browser_windows.append({
                "title": win["title"],
                "browser": browser_exe,
                "tabs": best_tabs
            })
    # Firefox sessionstore.jsonlz4分组
    if os.path.exists(BROWSER_PROFILES["firefox.exe"]["data_paths"][0]):
        profiles_path = BROWSER_PROFILES["firefox.exe"]["data_paths"][0]
        for item in os.listdir(profiles_path):
            if item.endswith('.default') or item.endswith('.default-release'):
                profile_dir = os.path.join(profiles_path, item)
                session_file = os.path.join(profile_dir, "sessionstore.jsonlz4")
                if os.path.exists(session_file):
                    try:
                        with open(session_file, "rb") as f:
                            f.read(8)
                            data = lz4.block.decompress(f.read())
                            session_data = json.loads(data.decode("utf-8"))
                            for win in session_data.get("windows", []):
                                tabs = []
                                seen = set()
                                for tab in win.get("tabs", []):
                                    idx = tab.get("index", 1) - 1
                                    entries = tab.get("entries", [])
                                    if entries and 0 <= idx < len(entries):
                                        entry = entries[idx]
                                        url = entry.get("url", "")
                                        title = entry.get("title", url)
                                        if url and url not in seen:
                                            seen.add(url)
                                            tabs.append({"title": title, "url": url})
                                win_title = ""
                                if win.get("tabs") and win["tabs"]:
                                    entries = win["tabs"][0].get("entries", [])
                                    if entries:
                                        win_title = entries[-1].get("title", "")
                                if not tabs:
                                    tabs = [{"title": "新标签页", "url": "about:newtab"}]
                                browser_windows.append({
                                    "title": win_title,
                                    "browser": "firefox.exe",
                                    "tabs": tabs
                                })
                    except Exception:
                        continue
    return browser_windows

def get_browser_tabs(browser_process_path, window_title, config):
    """
    获取特定浏览器窗口的标签页信息
    
    参数:
        browser_process_path: 浏览器进程路径
        window_title: 窗口标题
        config: 配置信息
        
    返回:
        标签页URL列表
    """
    browser_exe = os.path.basename(browser_process_path).lower()
    
    logger.info(f"开始获取浏览器标签页: {browser_exe}, 窗口标题: {window_title}")
    
    if browser_exe not in BROWSER_PROFILES:
        logger.warning(f"不支持的浏览器: {browser_exe}")
        return []
    
    # 获取浏览器窗口特定PID和窗口句柄
    browser_pid, window_hwnd = get_browser_pid(browser_process_path, window_title)
    if not browser_pid:
        logger.warning(f"无法获取浏览器PID: {window_title}")
        return []
    
    logger.info(f"成功获取浏览器PID: {browser_pid}, 窗口句柄: {window_hwnd}")
    
    # 根据浏览器类型选择不同的标签页获取方法
    if browser_exe in ["chrome.exe", "msedge.exe", "brave.exe"]:
        # 获取特定窗口的标签页
        tabs = get_chromium_tabs_for_window(browser_exe, browser_pid, window_title, window_hwnd)
        logger.info(f"获取到 {len(tabs)} 个Chrome标签页")
        return tabs
    elif browser_exe == "firefox.exe":
        tabs = get_firefox_tabs_for_window(browser_pid, window_title)
        logger.info(f"获取到 {len(tabs)} 个Firefox标签页")
        return tabs
    elif browser_exe == "opera.exe":
        tabs = get_opera_tabs_for_window(browser_pid, window_title)
        logger.info(f"获取到 {len(tabs)} 个Opera标签页")
        return tabs
    
    return []

def get_browser_pid(browser_process_path, window_title):
    """获取浏览器进程ID和窗口句柄"""
    browser_exe = os.path.basename(browser_process_path).lower()
    
    try:
        # 存储所有匹配的浏览器窗口
        matching_windows = []
        
        # 首先尝试精确匹配窗口标题和进程
        for window in gw.getWindowsWithTitle(window_title):
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(window._hWnd)
                proc = psutil.Process(window_pid)
                if os.path.basename(proc.exe()).lower() == browser_exe:
                    logger.debug(f"精确匹配到浏览器窗口: {window.title} (PID: {window_pid}, HWND: {window._hWnd})")
                    # 返回窗口PID和窗口句柄
                    return window_pid, window._hWnd
            except:
                pass
        
        # 如果没有精确匹配，尝试模糊匹配
        for window in gw.getAllWindows():
            if not window.title:
                continue
                
            try:
                _, window_pid = win32process.GetWindowThreadProcessId(window._hWnd)
                proc = psutil.Process(window_pid)
                if os.path.basename(proc.exe()).lower() == browser_exe:
                    # 计算窗口标题与目标标题的相似度
                    similarity = calculate_similarity(window.title, window_title)
                    if similarity > 0.6:  # 60%以上的相似度
                        logger.debug(f"模糊匹配到浏览器窗口: {window.title} (PID: {window_pid}, 相似度: {similarity:.2f}, HWND: {window._hWnd})")
                        # 返回窗口PID和窗口句柄
                        return window_pid, window._hWnd
                    else:
                        # 记录所有浏览器窗口，以备后用
                        matching_windows.append((window_pid, window._hWnd, window.title))
            except:
                pass
        
        # 如果仍未找到匹配，使用第一个浏览器窗口
        if matching_windows:
            pid, hwnd, title = matching_windows[0]
            logger.debug(f"未找到精确匹配，使用第一个浏览器窗口: {title} (PID: {pid}, HWND: {hwnd})")
            return pid, hwnd
            
        # 如果没有找到任何窗口，尝试查找浏览器进程
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            if proc.info['exe'] and os.path.basename(proc.info['exe']).lower() == browser_exe:
                logger.debug(f"未找到匹配窗口，使用浏览器进程: {proc.info['pid']}")
                return proc.info['pid'], None
    except Exception as e:
        logger.error(f"获取浏览器PID时出错: {e}")
    
    return None, None

def get_chromium_tabs(browser_exe, browser_pid):
    """获取基于Chromium的浏览器（Chrome、Edge、Brave）的标签页"""
    browser_info = BROWSER_PROFILES.get(browser_exe)
    if not browser_info:
        return []
    
    tabs = []
    
    try:
        # 获取所有用户配置文件目录
        user_data_dir = browser_info["data_paths"][0]
        profiles = get_chromium_profiles(user_data_dir)
        
        for profile_name in profiles:
            profile_tabs = get_tabs_from_profile(browser_info, user_data_dir, profile_name)
            if profile_tabs:
                tabs.extend(profile_tabs)
                logger.debug(f"从配置文件 {profile_name} 获取到 {len(profile_tabs)} 个标签页")
    
    except Exception as e:
        logger.error(f"获取{browser_info['name']}标签页时出错: {e}")
    
    # 去重并限制返回的标签页数量
    unique_tabs = []
    seen_urls = set()
    
    for tab in tabs:
        url = tab.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_tabs.append(tab)
    
    return unique_tabs[:50]  # 最多返回50个标签页

def get_chromium_profiles(user_data_dir):
    """获取Chrome/Edge/Brave的所有用户配置文件"""
    profiles = ["Default"]  # 始终包含默认配置文件
    
    try:
        # 读取Local State文件以获取所有配置文件
        local_state_path = os.path.join(user_data_dir, "Local State")
        if os.path.exists(local_state_path):
            with open(local_state_path, 'r', encoding='utf-8') as f:
                try:
                    local_state = json.load(f)
                    profile_info = local_state.get("profile", {}).get("info_cache", {})
                    if profile_info:
                        for profile_name in profile_info.keys():
                            if profile_name != "Default" and os.path.exists(os.path.join(user_data_dir, profile_name)):
                                profiles.append(profile_name)
                except json.JSONDecodeError:
                    logger.warning("无法解析Local State文件")
        
        # 直接查找目录
        if not profiles or len(profiles) <= 1:
            for item in os.listdir(user_data_dir):
                item_path = os.path.join(user_data_dir, item)
                if os.path.isdir(item_path) and item.startswith("Profile "):
                    if item not in profiles:
                        profiles.append(item)
    except Exception as e:
        logger.error(f"获取Chrome配置文件时出错: {e}")
    
    return profiles

def get_tabs_from_profile(browser_info, user_data_dir, profile_name):
    """从特定配置文件获取标签页"""
    tabs = []
    profile_path = os.path.join(user_data_dir, profile_name)
    
    # 1. 尝试从Current Session和Current Tabs文件中获取标签页
    session_tabs = extract_tabs_from_session_files(browser_info, profile_path)
    if session_tabs:
        tabs.extend(session_tabs)
    
    # 2. 如果从会话文件获取的标签页太少，尝试从历史记录获取
    if len(tabs) < 5:
        history_tabs = extract_tabs_from_history(browser_info, profile_path)
        if history_tabs:
            # 添加不重复的标签页
            for tab in history_tabs:
                if not any(existing_tab.get("url") == tab.get("url") for existing_tab in tabs):
                    tabs.append(tab)
    
    return tabs

def extract_tabs_from_session_files(browser_info, profile_path):
    """从会话文件中提取标签页"""
    tabs = []
    
    # 尝试读取会话文件
    files_to_check = [
        (os.path.join(profile_path, "Current Tabs"), "Current Tabs"),
        (os.path.join(profile_path, "Current Session"), "Current Session"),
        (os.path.join(profile_path, "Last Tabs"), "Last Tabs"),
        (os.path.join(profile_path, "Last Session"), "Last Session"),
        (os.path.join(profile_path, "Sessions", "Tabs_journal"), "Tabs Journal"),
        (os.path.join(profile_path, "Sessions", "Session_journal"), "Session Journal"),
        (os.path.join(profile_path, "Sessions", "last"), "Last Session")
    ]
    
    # 保存每个文件中提取的标签页计数，用于日志
    file_tab_counts = {}
    
    for file_path, file_type in files_to_check:
        if os.path.exists(file_path):
            try:
                # 创建临时副本
                with tempfile.NamedTemporaryFile(delete=False, suffix='.bin') as temp_file:
                    temp_path = temp_file.name
                    logger.debug(f"正在处理会话文件: {file_type}，创建临时副本: {temp_path}")
                
                # 复制文件可能会失败，如果文件被锁定
                try:
                    shutil.copy2(file_path, temp_path)
                except Exception as e:
                    logger.debug(f"复制文件 {file_type} 失败: {e}")
                    try:
                        os.unlink(temp_path)  # 删除可能创建的空临时文件
                    except:
                        pass
                    continue
                
                # 读取二进制文件并尝试提取URL
                with open(temp_path, 'rb') as f:
                    data = f.read()
                    file_size = len(data)
                    logger.debug(f"读取文件 {file_type} 成功，大小: {file_size} 字节")
                    
                    # 检查文件大小，如果太小可能不包含有用信息
                    if file_size < 100:
                        logger.debug(f"文件 {file_type} 太小 ({file_size} 字节)，可能不包含有效数据")
                        continue
                    
                    # 尝试提取URL和标题
                    extracted_tabs = extract_urls_and_titles_from_binary(data)
                    
                    # 记录提取结果
                    if extracted_tabs:
                        old_count = len(tabs)
                        
                        # 只添加新的、不重复的标签页
                        existing_urls = {tab.get("url") for tab in tabs}
                        new_tabs = [tab for tab in extracted_tabs if tab.get("url") not in existing_urls]
                        
                        if new_tabs:
                            tabs.extend(new_tabs)
                            new_count = len(tabs) - old_count
                            logger.debug(f"从 {file_type} 提取到 {len(extracted_tabs)} 个标签页，其中 {new_count} 个是新的")
                            file_tab_counts[file_type] = new_count
                        else:
                            logger.debug(f"从 {file_type} 提取到 {len(extracted_tabs)} 个标签页，但都是重复的")
                    else:
                        logger.debug(f"从 {file_type} 未提取到有效标签页")
                
                # 删除临时文件
                try:
                    os.unlink(temp_path)
                    logger.debug(f"删除临时文件: {temp_path}")
                except Exception as e:
                    logger.debug(f"删除临时文件失败: {e}")
            except Exception as e:
                logger.debug(f"读取 {file_type} 文件时出错: {e}")
    
    # 总结日志
    if file_tab_counts:
        logger.info(f"从会话文件中成功提取标签页: {sum(file_tab_counts.values())} 个，详情: {file_tab_counts}")
    else:
        logger.warning(f"未能从任何会话文件中提取到标签页")
    
    # 对标签页进行去重和排序（假设更重要的标签页可能在多个文件中出现）
    unique_tabs = []
    seen_urls = set()
    
    for tab in tabs:
        url = tab.get("url", "")
        if url and url not in seen_urls:
            seen_urls.add(url)
            unique_tabs.append(tab)
    
    return unique_tabs

def extract_urls_and_titles_from_binary(data):
    """从二进制数据中提取URL和标题"""
    tabs = []
    seen_urls = set()
    
    # 提取URL - 使用更严格的模式匹配有效URL
    url_pattern = re.compile(b'https?://[^\x00-\x1F\x7F-\xFF\s]{2,}[^\x00-\x1F\x7F-\xFF\s]{2,}')
    url_matches = url_pattern.findall(data)
    
    # 提取可能的标题（ASCII和UTF-16编码的文本）
    title_pattern = re.compile(b'[\x20-\x7E]{5,100}')  # ASCII文本
    title_matches = title_pattern.findall(data)
    
    # 尝试UTF-16编码的标题
    utf16_title_pattern = re.compile(b'(?:[\x20-\x7E]\x00){5,50}')  # UTF-16编码的文本
    utf16_matches = utf16_title_pattern.findall(data)
    
    # 解码UTF-16标题
    decoded_utf16 = []
    for match in utf16_matches:
        try:
            text = match.decode('utf-16-le').strip()
            if text and len(text) >= 5 and not text.startswith('http'):
                # 过滤掉常见的非标题文本
                if not any(skip in text.lower() for skip in ['javascript:', 'var ', 'function(', '{ ', ' }', ');']):
                    decoded_utf16.append(text)
        except:
            pass
    
    # 解码URL
    decoded_urls = []
    for match in url_matches:
        try:
            url = match.decode('utf-8')
            # 过滤掉不需要的URL
            if not any(skip in url.lower() for skip in [
                'favicon.ico', 'chrome-extension://', 'chrome-devtools://', 
                'data:', 'javascript:', 'blob:', 'about:blank', 'file://'
            ]):
                # 确保URL是有效的网址（至少包含域名）
                domain = extract_domain(url)
                if domain and '.' in domain and len(domain) > 3:
                    # 移除URL末尾的非标准字符
                    url = re.sub(r'[\s"\'\\]+$', '', url)
                    decoded_urls.append(url)
        except:
            pass
    
    # 解码ASCII标题
    decoded_titles = []
    for match in title_matches:
        try:
            text = match.decode('utf-8').strip()
            if text and len(text) >= 5 and not text.startswith('http'):
                # 过滤掉常见的非标题文本
                if not any(skip in text.lower() for skip in [
                    'javascript:', 'var ', 'function(', '{ ', ' }', ');', '://', '.js', '.css',
                    'undefined', 'null', 'error', 'exception', '<html>', '<div', '</div>'
                ]):
                    decoded_titles.append(text)
        except:
            pass
    
    # 合并所有可能的标题
    all_titles = decoded_titles + decoded_utf16
    
    # 尝试匹配URL和标题
    for url in decoded_urls:
        if url in seen_urls:
            continue
            
        seen_urls.add(url)
        best_title = None
        best_score = 0
        
        # 尝试找到最匹配的标题
        for title in all_titles:
            # 如果标题包含URL的一部分，可能是相关的
            domain = extract_domain(url)
            if domain and domain.lower() in title.lower():
                score = 0.8
                
                # 如果标题看起来像一个真实的页面标题（有空格，不是纯技术文本）
                if ' ' in title and not any(tech in title.lower() for tech in ['function', 'var ', 'const ', 'error:', 'exception:']):
                    score += 0.1
            else:
                # 否则检查标题中是否包含URL中的关键词
                url_parts = re.split(r'[/\-_\.]', url.lower())
                url_keywords = [part for part in url_parts if len(part) > 3]
                
                matches = 0
                for keyword in url_keywords:
                    if keyword in title.lower():
                        matches += 1
                
                if url_keywords:
                    score = matches / len(url_keywords)
                else:
                    score = 0
            
            if score > best_score:
                best_score = score
                best_title = title
        
        # 如果没有找到好的标题匹配，使用URL的域名作为标题
        if not best_title or best_score < 0.3:
            domain = extract_domain(url)
            if domain:
                # 将域名转换为更友好的格式，例如 "example.com" 变为 "Example"
                best_title = domain.split('.')[0].capitalize()
            else:
                best_title = "无标题页面"
        
        tabs.append({
            "url": url,
            "title": best_title
        })
    
    return tabs

def extract_tabs_from_history(browser_info, profile_path):
    """从历史记录数据库中提取标签页"""
    tabs = []
    
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
            logger.error(f"读取历史记录时出错: {e}")
        finally:
            # 删除临时文件
            try:
                os.unlink(temp_db_path)
            except:
                pass
    
    return tabs

def get_firefox_tabs_for_window(browser_pid, window_title):
    """获取特定Firefox窗口的标签页"""
    all_tabs = get_firefox_tabs(window_title)
    window_keywords = extract_keywords(window_title)
    
    if window_keywords:
        relevant_tabs = [tab for tab in all_tabs 
                         if any(keyword.lower() in tab.get("title", "").lower() 
                                for keyword in window_keywords)]
        if relevant_tabs:
            return relevant_tabs[:30]
    
    return all_tabs[:10]

def get_opera_tabs_for_window(browser_pid, window_title):
    """获取特定Opera窗口的标签页"""
    all_tabs = get_opera_tabs(browser_pid)
    window_keywords = extract_keywords(window_title)
    
    if window_keywords:
        relevant_tabs = [tab for tab in all_tabs 
                         if any(keyword.lower() in tab.get("title", "").lower() 
                                for keyword in window_keywords)]
        if relevant_tabs:
            return relevant_tabs[:30]
    
    return all_tabs[:10]

def get_opera_tabs(browser_pid):
    """获取Opera的标签页"""
    browser_info = BROWSER_PROFILES.get("opera.exe")
    if not browser_info:
        return []
    
    # Opera基于Chromium，可以使用类似的方法
    return get_chromium_tabs("opera.exe", browser_pid)

def find_firefox_profile_dir():
    """查找Firefox的配置文件目录"""
    profiles_path = BROWSER_PROFILES["firefox.exe"]["data_paths"][0]
    
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

def restore_browser_tabs(browser_process_path, window_title, tabs, config):
    """
    恢复浏览器标签页
    
    参数:
        browser_process_path: 浏览器进程路径
        window_title: 窗口标题
        tabs: 标签页列表
        config: 配置信息
        
    返回:
        是否成功
    """
    browser_exe = os.path.basename(browser_process_path).lower()
    
    if browser_exe not in BROWSER_PROFILES:
        logger.warning(f"不支持的浏览器: {browser_exe}")
        return False
        
    # 检查是否有标签页需要恢复
    if not tabs:
        logger.warning("没有标签页需要恢复")
        return False
        
    # 获取标签页URL列表
    urls = []
    for tab in tabs:
        if isinstance(tab, dict) and "url" in tab and tab["url"]:
            urls.append(tab["url"])
        elif isinstance(tab, str):
            urls.append(tab)
            
    if not urls:
        logger.warning("无有效URL可恢复")
        return False
        
    # 根据不同浏览器选择不同的恢复方法
    try:
        # 确保创建新窗口并恢复所有标签页
        browser_path = find_browser_path(browser_exe)
        if not browser_path:
            logger.error(f"无法找到浏览器路径: {browser_exe}")
            return False
            
        # 根据浏览器类型选择不同的恢复方法
        if browser_exe in ["chrome.exe", "msedge.exe", "brave.exe"]:
            return restore_chromium_window(browser_path, urls)
        elif browser_exe == "firefox.exe":
            return restore_firefox_window(browser_path, urls)
        elif browser_exe == "opera.exe":
            return restore_opera_window(browser_path, urls)
            
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

def restore_chromium_window(browser_path, urls):
    """
    在Chrome/Edge/Brave中创建新窗口并恢复标签页
    """
    try:
        if not urls:
            logger.warning("没有需要恢复的URL")
            return False
        
        # 确保URLs列表中不包含重复项
        unique_urls = []
        seen_urls = set()
        for url in urls:
            if isinstance(url, dict):
                url = url.get("url", "")
            if url and url not in seen_urls and url.strip().startswith(('http://', 'https://')):
                # 验证URL格式
                try:
                    # 标准化URL，移除末尾的空格和某些特殊字符
                    url = url.strip().rstrip('"\' \t\n\r\f\v\\')
                    seen_urls.add(url)
                    unique_urls.append(url)
                except:
                    logger.debug(f"跳过无效URL: {url[:50]}...")
        
        if not unique_urls:
            logger.warning("没有有效的URL可以恢复")
            return False
            
        logger.info(f"准备恢复 {len(unique_urls)} 个唯一的URL到新浏览器窗口")
        
        # 尝试两种方法恢复标签页
        
        # 方法1: 使用HTML文件方法
        success = restore_using_html_method(browser_path, unique_urls)
        if success:
            return True
            
        # 方法2: 如果HTML方法失败，尝试命令行参数方法
        logger.info("HTML方法失败，尝试使用命令行参数方法")
        success = restore_using_command_line(browser_path, unique_urls)
        if success:
            return True
            
        # 方法3: 作为最后的尝试，打开第一个URL，然后通过JavaScript打开剩余的URL
        logger.info("命令行方法失败，尝试使用JavaScript方法")
        return restore_using_javascript(browser_path, unique_urls)
            
    except Exception as e:
        logger.error(f"恢复Chromium窗口时出错: {e}")
        return False

def restore_using_html_method(browser_path, urls):
    """使用HTML文件方法恢复标签页"""
    try:
        # 创建临时HTML文件，用于一次性打开所有标签页到同一个窗口中
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
            temp_html_path = f.name
            logger.debug(f"创建临时HTML文件: {temp_html_path}")
            
            # 创建自动打开多个标签页的HTML
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>恢复浏览器会话</title>
                <style>
                body {
                    font-family: Arial, sans-serif;
                    margin: 20px;
                    background-color: #f5f5f5;
                    text-align: center;
                }
                h1 {
                    color: #333;
                }
                .progress {
                    margin: 20px auto;
                    width: 300px;
                    height: 20px;
                    background-color: #ddd;
                    border-radius: 10px;
                    overflow: hidden;
                }
                .progress-bar {
                    height: 100%;
                    background-color: #4CAF50;
                    width: 0%;
                    transition: width 0.3s;
                }
                .info {
                    color: #666;
                    margin-top: 10px;
                }
                .url-list {
                    margin-top: 20px;
                    text-align: left;
                    max-height: 200px;
                    overflow-y: auto;
                    padding: 10px;
                    background-color: #fff;
                    border-radius: 5px;
                    border: 1px solid #ddd;
                    font-size: 12px;
                    display: none;
                }
                .show-urls {
                    margin-top: 10px;
                    background-color: #f0f0f0;
                    border: 1px solid #ddd;
                    padding: 5px 10px;
                    cursor: pointer;
                    border-radius: 3px;
                }
                .error-message {
                    color: #d9534f;
                    margin-top: 10px;
                    display: none;
                }
                </style>
                <script>
                // 所有要恢复的URL
                var urls = [
            """)
            
            # 写入URL列表
            for url in urls:
                # 处理URL中的单引号和双引号
                safe_url = url.replace("'", "\\'").replace('"', '\\"')
                f.write(f'        "{safe_url}",\n')
            
            f.write("""
                ];
                
                var currentIndex = 0;
                var totalUrls = urls.length;
                var pauseRestore = false;
                var restoreInterval = null;
                var errorCount = 0;
                var maxErrors = 3;
                
                function updateProgress() {
                    var percent = Math.round((currentIndex / totalUrls) * 100);
                    document.getElementById('progress-bar').style.width = percent + '%';
                    document.getElementById('status').textContent = '正在打开标签页 ' + currentIndex + ' / ' + totalUrls;
                }
                
                function openNextTab() {
                    if (pauseRestore) {
                        return;
                    }
                    
                    if (currentIndex < urls.length) {
                        var url = urls[currentIndex];
                        
                        try {
                            if (currentIndex === 0) {
                                // 第一个URL在当前页面打开
                                window.location.href = url;
                            } else {
                                // 其余URL在新标签页打开
                                var newTab = window.open(url, '_blank');
                                
                                // 检查是否成功打开（可能会被弹窗拦截器阻止）
                                if (!newTab || newTab.closed || typeof newTab.closed=='undefined') {
                                    errorCount++;
                                    console.error("打开标签页可能被拦截:", url);
                                    document.getElementById('error-message').style.display = 'block';
                                    
                                    // 如果错误过多，切换到手动模式
                                    if (errorCount >= maxErrors) {
                                        pauseRestore = true;
                                        clearInterval(restoreInterval);
                                        document.getElementById('manual-mode').style.display = 'block';
                                        document.getElementById('pause-btn').style.display = 'none';
                                        return;
                                    }
                                }
                            }
                        } catch (e) {
                            console.error("打开标签页失败:", e);
                            errorCount++;
                        }
                        
                        currentIndex++;
                        updateProgress();
                        
                        // 如果已经处理完所有URL，清除定时器
                        if (currentIndex >= urls.length) {
                            clearInterval(restoreInterval);
                            document.getElementById('status').textContent = '已完成所有标签页恢复';
                        }
                    }
                }
                
                function toggleUrlList() {
                    var urlList = document.getElementById('url-list');
                    if (urlList.style.display === 'none' || !urlList.style.display) {
                        urlList.style.display = 'block';
                        document.getElementById('toggle-btn').textContent = '隐藏URL列表';
                    } else {
                        urlList.style.display = 'none';
                        document.getElementById('toggle-btn').textContent = '显示URL列表';
                    }
                }
                
                function togglePause() {
                    pauseRestore = !pauseRestore;
                    document.getElementById('pause-btn').textContent = pauseRestore ? '继续恢复' : '暂停恢复';
                    
                    if (!pauseRestore && currentIndex < urls.length) {
                        // 如果恢复过程被暂停过，重新启动恢复
                        restoreInterval = setInterval(openNextTab, 400);
                    }
                }
                
                function manualRestore() {
                    // 手动恢复模式
                    var manualDiv = document.getElementById('manual-urls');
                    var manualHtml = '';
                    
                    for (var i = currentIndex; i < urls.length; i++) {
                        manualHtml += '<div class="manual-url">' +
                            (i+1) + '. <a href="' + urls[i] + '" target="_blank">' + 
                            (urls[i].length > 50 ? urls[i].substring(0, 50) + '...' : urls[i]) + 
                            '</a></div>';
                    }
                    
                    manualDiv.innerHTML = manualHtml;
                }
                
                window.onload = function() {
                    // 显示URL列表
                    var urlListHtml = '';
                    for (var i = 0; i < urls.length; i++) {
                        urlListHtml += (i+1) + '. ' + urls[i] + '<br>';
                    }
                    document.getElementById('url-list').innerHTML = urlListHtml;
                    
                    // 延迟启动，确保页面已完全加载
                    setTimeout(function() {
                        // 开始恢复过程
                        restoreInterval = setInterval(openNextTab, 400);
                    }, 500);
                };
                </script>
            </head>
            <body>
                <h1>正在恢复浏览器会话</h1>
                <div class="progress">
                    <div id="progress-bar" class="progress-bar"></div>
                </div>
                <p id="status">准备恢复 <strong>""" + str(len(urls)) + """</strong> 个标签页</p>
                <p class="info">请不要关闭此页面，恢复过程将自动进行</p>
                <button id="pause-btn" onclick="togglePause()">暂停恢复</button>
                <button id="toggle-btn" class="show-urls" onclick="toggleUrlList()">显示URL列表</button>
                <div id="url-list" class="url-list"></div>
                <div id="error-message" class="error-message">警告: 可能有标签页被弹窗拦截器阻止，请检查浏览器通知。</div>
                
                <div id="manual-mode" style="display:none; margin-top:20px; padding:10px; background:#f9f9f9; border:1px solid #ddd;">
                    <h3>自动恢复被阻止</h3>
                    <p>您的浏览器可能阻止了自动打开多个标签页。请手动点击下方链接来打开剩余标签页：</p>
                    <div id="manual-urls" style="text-align:left; margin-top:10px;"></div>
                    <button onclick="manualRestore()" style="margin-top:10px;">显示剩余链接</button>
                </div>
            </body>
            </html>
            """)
        
        # 创建新窗口并打开临时HTML文件
        logger.info(f"使用HTML方法启动浏览器恢复 {len(urls)} 个标签页")
        subprocess.Popen([browser_path, "--new-window", temp_html_path])
        
        # 延迟删除临时文件
        def delete_temp_file():
            time.sleep(90)  # 等待90秒，确保浏览器有足够时间加载
            try:
                if os.path.exists(temp_html_path):
                    os.unlink(temp_html_path)
                    logger.debug(f"临时HTML文件已删除: {temp_html_path}")
            except Exception as e:
                logger.debug(f"删除临时文件失败: {e}")
        
        # 在后台线程中删除临时文件
        threading.Thread(target=delete_temp_file, daemon=True).start()
        
        return True
    except Exception as e:
        logger.error(f"HTML方法恢复标签页失败: {e}")
        return False

def restore_using_command_line(browser_path, urls):
    """使用命令行参数方法恢复标签页"""
    try:
        if not urls:
            return False
            
        # 构建命令行参数
        cmd = [browser_path, "--new-window"]
        
        # 添加第一个URL（将在新窗口中打开）
        cmd.append(urls[0])
        
        # 如果有更多URL，添加为新标签页
        for url in urls[1:10]:  # 限制为前10个，避免命令行过长
            cmd.append(url)
        
        # 启动浏览器
        logger.info(f"使用命令行方法启动浏览器恢复标签页")
        process = subprocess.Popen(cmd)
        
        # 如果有超过10个URL，分批次添加剩余的URL
        if len(urls) > 10:
            # 等待第一批次启动
            time.sleep(3)
            
            # 添加剩余URL
            remaining_urls = urls[10:]
            logger.info(f"添加剩余的 {len(remaining_urls)} 个URL")
            
            # 每10个URL一批次
            for i in range(0, len(remaining_urls), 10):
                batch = remaining_urls[i:i+10]
                cmd = [browser_path]
                cmd.extend(batch)
                subprocess.Popen(cmd)
                time.sleep(1)  # 短暂延迟，避免浏览器过载
        
        return True
    except Exception as e:
        logger.error(f"命令行方法恢复标签页失败: {e}")
        return False

def restore_using_javascript(browser_path, urls):
    """使用JavaScript方法恢复标签页"""
    try:
        if not urls:
            return False
            
        # 创建一个简单的HTML文件，使用JavaScript在页面加载后打开所有标签页
        with tempfile.NamedTemporaryFile(delete=False, suffix='.html', mode='w', encoding='utf-8') as f:
            temp_html_path = f.name
            
            # 创建HTML内容
            f.write("""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>正在恢复标签页</title>
                <style>
                    body { font-family: Arial, sans-serif; margin: 20px; text-align: center; }
                    h2 { margin-top: 20px; }
                    .url-list { text-align: left; margin: 20px auto; max-width: 800px; }
                    .url-item { margin: 5px 0; }
                    button { padding: 8px 15px; margin: 5px; cursor: pointer; }
                </style>
            </head>
            <body>
                <h1>标签页恢复</h1>
                <p>由于浏览器限制，无法自动打开所有标签页。请使用下面的按钮手动恢复。</p>
                
                <button onclick="openFirst10Tabs()">打开前10个标签页</button>
                <button onclick="openAllTabsManually()">逐个打开所有标签页</button>
                
                <h2>所有待恢复的URL：</h2>
                <div class="url-list" id="urlList"></div>
                
                <script>
                    // 所有URL
                    const urls = [
            """)
            
            # 写入URL列表
            for url in urls:
                safe_url = url.replace("'", "\\'").replace('"', '\\"')
                f.write(f'        "{safe_url}",\n')
            
            f.write("""
                    ];
                    
                    // 在页面加载时显示URL列表
                    window.onload = function() {
                        const urlListElement = document.getElementById('urlList');
                        urls.forEach((url, index) => {
                            const div = document.createElement('div');
                            div.className = 'url-item';
                            div.innerHTML = `${index + 1}. <a href="${url}" target="_blank">${url}</a>`;
                            urlListElement.appendChild(div);
                        });
                    };
                    
                    // 打开前10个标签页
                    function openFirst10Tabs() {
                        const max = Math.min(10, urls.length);
                        for (let i = 0; i < max; i++) {
                            if (i === 0) {
                                window.location.href = urls[i];
                            } else {
                                window.open(urls[i], '_blank');
                            }
                        }
                    }
                    
                    // 逐个打开所有标签页
                    function openAllTabsManually() {
                        alert('请点击URL列表中的链接，逐个打开所有标签页。');
                    }
                </script>
            </body>
            </html>
            """)
        
        # 打开浏览器
        logger.info(f"使用JavaScript方法启动浏览器恢复标签页")
        subprocess.Popen([browser_path, "--new-window", temp_html_path])
        
        # 延迟删除临时文件
        def delete_temp_file():
            time.sleep(120)
            try:
                if os.path.exists(temp_html_path):
                    os.unlink(temp_html_path)
            except:
                pass
        
        # 在后台线程中删除临时文件
        threading.Thread(target=delete_temp_file, daemon=True).start()
        
        return True
    except Exception as e:
        logger.error(f"JavaScript方法恢复标签页失败: {e}")
        return False

def restore_firefox_window(browser_path, urls):
    """
    在Firefox中创建新窗口并恢复标签页
    """
    try:
        if not urls:
            return False
            
        # Firefox可以通过命令行参数直接打开多个URL
        cmd = [browser_path, "-new-window"]
        
        # 第一个URL添加到命令行，会在新窗口中打开
        first_url = urls[0]
        if isinstance(first_url, dict):
            first_url = first_url.get("url", "about:blank")
        cmd.append(first_url)
        
        # 启动Firefox创建新窗口
        firefox_process = subprocess.Popen(cmd)
        
        # 等待一段时间，确保窗口创建成功
        time.sleep(2)
        
        # 添加其余URL到新窗口中作为新标签页
        if len(urls) > 1:
            cmd = [browser_path]
            for url in urls[1:]:
                if isinstance(url, dict):
                    url = url.get("url", "")
                cmd.append(url)
            
            # 打开其余标签页
            subprocess.Popen(cmd)
        
        logger.info(f"已创建新Firefox窗口并恢复 {len(urls)} 个标签页")
        return True
    except Exception as e:
        logger.error(f"恢复Firefox窗口时出错: {e}")
        return False

def restore_opera_window(browser_path, urls):
    """
    在Opera中创建新窗口并恢复标签页
    """
    try:
        if not urls:
            return False
            
        # Opera基于Chromium，可以使用类似的方法
        return restore_chromium_window(browser_path, urls)
    except Exception as e:
        logger.error(f"恢复Opera窗口时出错: {e}")
        return False

def get_chromium_tabs_for_window(browser_exe, browser_pid, window_title, window_hwnd=None):
    """
    获取Chromium浏览器特定窗口的标签页
    优化版本：优先使用DevTools协议，兜底使用Session/历史记录
    """
    logger.info(f"开始获取Chromium标签页: {browser_exe}, 窗口: {window_title}")
    
    # 方法1: 优先使用DevTools协议
    tabs = get_chromium_tabs_by_devtools(window_title, browser_exe)
    if tabs:
        logger.info(f"DevTools协议成功获取{len(tabs)}个标签页")
        return tabs
    
    # 方法2: 使用Session文件和历史记录（兜底方案）
    tabs = get_chromium_tabs_by_session(browser_exe, window_title)
    if tabs:
        logger.info(f"Session/历史记录成功获取{len(tabs)}个标签页")
        return tabs
    
    # 方法3: 如果都失败了，返回默认标签页
    logger.warning(f"所有采集方法都失败，返回默认标签页")
    return [{"title": "新标签页", "url": "about:newtab", "source": "fallback"}]

def extract_keywords(text):
    """从文本中提取关键词"""
    if not text:
        return []
        
    # 移除常见浏览器后缀
    text = text.replace(" - Google Chrome", "")
    text = text.replace(" - Microsoft Edge", "")
    text = text.replace(" - Brave", "")
    text = text.replace(" - Firefox", "")
    text = text.replace(" - Opera", "")
    
    # 英文停用词
    english_stopwords = [
        "the", "of", "and", "to", "a", "in", "for", "is", "on", "that", "by", 
        "this", "with", "you", "it", "not", "or", "be", "are", "from", "at", 
        "as", "your", "all", "have", "new", "more", "an", "was", "we", "will", 
        "home", "can", "us", "about", "if", "page", "my", "has", "search", 
        "free", "but", "our", "one", "other", "do", "no", "information", "time",
        "they", "site", "he", "up", "may", "what", "which", "their", "news",
        "out", "use", "any", "there", "see", "only", "so", "his", "when",
        "contact", "here", "business", "who", "web", "also", "now", "help",
        "get", "view", "online", "first", "am", "been", "would", "how", "were",
        "me", "some", "these", "its", "like", "than", "find", "date", "back",
        "top", "had", "list", "name", "just", "over", "year", "day", "into",
        "email", "two", "health", "world", "next", "used", "go", "work", "last",
        "most", "products", "music", "buy", "data", "make", "them", "should",
        "product", "system", "post", "her", "city", "add", "policy", "number",
        "such", "please", "available", "copyright", "support", "message", "after",
        "best", "software", "then", "jan", "good", "video", "well", "where",
        "info", "rights", "public", "books", "high", "school", "through",
        "each", "links", "she", "review", "years", "order", "very", "privacy",
        "book", "items", "company", "read", "group", "sex", "need", "many", 
        "user", "said", "de", "does", "set", "under", "general", "research",
        "university", "mail", "full", "map", "reviews"
    ]
    
    # 中文停用词
    chinese_stopwords = [
        "的", "了", "和", "是", "就", "都", "而", "及", "与", "着", "或", "一个", "没有",
        "我们", "你们", "他们", "她们", "它们", "也", "还", "但", "但是", "然而", "可是",
        "只是", "不过", "至于", "况且", "并", "并且", "而且", "不仅", "不但", "而是",
        "乃至", "之", "的话", "说", "等", "等等", "呢", "吧", "吗", "啊", "嗯", "那么",
        "这么", "这个", "那个", "这", "那", "如此", "这样", "那样", "怎样", "如何",
        "什么", "哪些", "谁", "哪个", "多少", "几", "何", "怎么", "怎么样", "一些",
        "有些", "有的", "所有", "每个", "各个", "各种", "和", "跟", "同", "以及",
        "与", "以", "及", "既", "又", "既然", "因为", "由于", "所以", "因此", "故",
        "以致", "致使", "却", "虽", "虽然", "尽管", "不过", "可是", "然而", "假如",
        "如果", "即使", "假使", "要是", "除非", "只有", "除了", "而", "并", "且", "乃至",
        "之", "的话", "一", "一个", "一些", "一何", "一切", "一则", "一方面", "一旦",
        "一来", "一样", "一般", "一转眼", "万一"
    ]
    
    # 创建综合停用词集合，包含中英文
    stopwords = set(english_stopwords + chinese_stopwords)
    
    # 判断文本是否包含中文
    contains_chinese = any('\u4e00' <= ch <= '\u9fff' for ch in text)
    
    if contains_chinese:
        # 中文文本处理
        # 尝试使用结巴分词（如果安装了）
        try:
            import jieba
            # 分词
            words = jieba.cut(text)
            # 过滤停用词和短词
            keywords = [word for word in words 
                        if word not in stopwords 
                        and len(word) >= 2 
                        and not word.isdigit()]
        except ImportError:
            # 如果没有结巴分词，使用简单的字符分割
            # 先按空格分割
            words = text.split()
            
            # 如果分割后还是很少的词（说明可能是没有空格的中文），尝试按字符提取
            if len(words) <= 2:
                # 提取2个及以上连续的中文字符作为关键词
                import re
                chinese_words = re.findall(r'[\u4e00-\u9fff]{2,}', text)
                words.extend(chinese_words)
            
            # 过滤停用词和短词
            keywords = [word for word in words 
                        if word not in stopwords 
                        and len(word) >= 2 
                        and not word.isdigit()]
    else:
        # 英文文本处理
        # 分词并移除停用词和短词
        words = text.split()
        keywords = [word for word in words 
                    if word.lower() not in stopwords 
                    and len(word) > 2 
                    and not word.isdigit()
                    and not all(c.isdigit() or c in '.-:' for c in word)]  # 排除日期、时间等数字形式
    
    # 去除标点符号和特殊字符
    import re
    clean_keywords = []
    for word in keywords:
        # 清理词首尾的标点符号
        word = re.sub(r'^[^\w\s]|[^\w\s]$', '', word)
        # 如果清理后的词长度仍然够长，添加到结果中
        if len(word) >= 2:
            clean_keywords.append(word)
    
    # 去重并保留顺序
    seen = set()
    unique_keywords = []
    for word in clean_keywords:
        lowercase_word = word.lower()
        if lowercase_word not in seen:
            seen.add(lowercase_word)
            unique_keywords.append(word)
    
    # 限制关键词数量，优先保留较长的词
    if len(unique_keywords) > 10:
        unique_keywords.sort(key=len, reverse=True)
        unique_keywords = unique_keywords[:10]
    
    return unique_keywords

def calculate_similarity(text1, text2):
    """计算两个文本的相似度，返回0-1之间的值"""
    import difflib
    return difflib.SequenceMatcher(None, text1.lower(), text2.lower()).ratio()

def extract_domain(url):
    """从URL中提取域名"""
    try:
        if not url:
            return ""
            
        # 移除协议部分
        if "://" in url:
            url = url.split("://", 1)[1]
            
        # 获取域名部分
        domain = url.split("/", 1)[0]
        
        # 移除www.前缀
        if domain.startswith("www."):
            domain = domain[4:]
            
        return domain
    except:
        return ""

def get_firefox_tabs_for_window(browser_pid, window_title):
    """获取特定Firefox窗口的标签页"""
    all_tabs = get_firefox_tabs(window_title)
    window_keywords = extract_keywords(window_title)
    
    if window_keywords:
        relevant_tabs = [tab for tab in all_tabs 
                         if any(keyword.lower() in tab.get("title", "").lower() 
                                for keyword in window_keywords)]
        if relevant_tabs:
            return relevant_tabs[:30]
    
    return all_tabs[:10]

def get_opera_tabs_for_window(browser_pid, window_title):
    """获取特定Opera窗口的标签页"""
    all_tabs = get_opera_tabs(browser_pid)
    window_keywords = extract_keywords(window_title)
    
    if window_keywords:
        relevant_tabs = [tab for tab in all_tabs 
                         if any(keyword.lower() in tab.get("title", "").lower() 
                                for keyword in window_keywords)]
        if relevant_tabs:
            return relevant_tabs[:30]
    
    return all_tabs[:10] 

def is_port_in_use(port):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.settimeout(0.5)
        s.connect(("127.0.0.1", port))
        s.close()
        return True
    except Exception:
        return False

def launch_chrome_with_devtools(port=9222):
    """自动启动chrome.exe并带上--remote-debugging-port参数"""
    if is_port_in_use(port):
        print(f"[调试] 端口{port}已被占用，跳过Chrome启动")
        return
    # 常见Chrome路径
    possible_paths = [
        os.path.join(os.environ.get("PROGRAMFILES", r"C:\Program Files"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.join(os.environ.get("PROGRAMFILES(X86)", r"C:\Program Files (x86)"), "Google", "Chrome", "Application", "chrome.exe"),
        os.path.expandvars(r"%LOCALAPPDATA%\Google\Chrome\Application\chrome.exe"),
    ]
    chrome_path = None
    for path in possible_paths:
        if os.path.exists(path):
            chrome_path = path
            break
    if not chrome_path:
        print("[调试] 未找到chrome.exe路径，无法自动启动Chrome")
        return
    try:
        subprocess.Popen([chrome_path, f"--remote-debugging-port={port}"])
        print(f"[调试] 已自动启动Chrome并监听端口{port}")
    except Exception as e:
        print(f"[调试] 启动Chrome失败: {e}")