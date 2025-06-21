"""
core.py
会话采集、保存、恢复等核心逻辑模块。
"""

import os
import json
import shutil
import difflib
import subprocess
import time
import logging
import pygetwindow as gw
from session_manager.config import get_default_config
from PIL import Image, ImageDraw, ImageGrab
import win32gui
import win32con
import win32process
import win32api
import psutil

# 导入浏览器标签页支持模块
try:
    # 尝试导入混合标签页管理器
    from session_manager.hybrid_tabs import (
        get_browser_tabs_hybrid as get_browser_tabs,
        restore_browser_tabs_hybrid as restore_browser_tabs,
        initialize_websocket_server
    )
    BROWSER_TABS_SUPPORT = True
    HYBRID_TABS_SUPPORT = True
    # 初始化WebSocket服务器
    try:
        initialize_websocket_server()
    except Exception as e:
        logging.warning(f"初始化WebSocket服务器失败: {e}")
except ImportError:
    # 回退到静态提取方法
    try:
        from session_manager.browser_tabs import get_browser_tabs, restore_browser_tabs
        BROWSER_TABS_SUPPORT = True
        HYBRID_TABS_SUPPORT = False
    except ImportError:
        BROWSER_TABS_SUPPORT = False
        HYBRID_TABS_SUPPORT = False

logger = logging.getLogger(__name__)

# --- 会话采集 ---
def collect_session_data(config):
    """收集当前会话数据"""
    logger.info("开始收集当前会话数据...")
    session_data = {"applications": [], "browser_windows": []}
    
    # 跳过的应用程序列表
    excluded_apps = config.get("excluded_apps", [])
    excluded_exes = [os.path.basename(app).lower() for app in excluded_apps]
    
    # 特殊应用处理
    special_apps = config.get("special_apps", {})
    special_app_instances = {}
    
    # 获取所有窗口
    all_windows = gw.getAllWindows()
    processed_windows = set()
    
    # 遍历所有窗口
    for window in all_windows:
        # 跳过无效窗口
        if not window.visible or not window.title or window.title.strip() == "":
            continue
            
        # 尝试获取进程ID和路径
        try:
            _, pid = win32process.GetWindowThreadProcessId(window._hWnd)
            proc = psutil.Process(pid)
            process_path = proc.exe()
        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess, Exception):
                        continue
            
        # 跳过排除的应用程序
        if os.path.basename(process_path).lower() in excluded_exes:
                        continue
            
        # 检查是否已处理过此窗口（通过窗口标题和进程路径判断）
        window_key = f"{window.title}::{process_path}"
        if window_key in processed_windows:
            continue
        processed_windows.add(window_key)
    
        # 检查是否是浏览器窗口
        browser_info = is_browser_window(process_path, window.title)
        if browser_info:
            browser_name, browser_type = browser_info
            
            # 获取浏览器标签页
            browser_tabs = []
            try:
                # 使用混合标签页管理器获取标签页
                browser_tabs = get_browser_tabs(process_path, window.title, config)
            except Exception as e:
                logger.error(f"获取浏览器标签页时出错: {e}")
            
            # 保存浏览器窗口信息
            browser_data = {
                "title": window.title,
                "process_path": process_path,
                "pid": pid,
                "browser_name": browser_name,
                "browser_type": browser_type,
                "tabs": browser_tabs,
                "tab_count": len(browser_tabs)
            }
            session_data["browser_windows"].append(browser_data)
            continue
        
        # 处理特殊应用
        process_name = os.path.basename(process_path).lower()
        if process_name in special_apps:
            if process_name not in special_app_instances:
                special_app_instances[process_name] = True
                logger.info(f"发现特殊应用: {process_name} (PID: {pid}, 路径: {process_path})")
                
                app_data = {
                    "title": f"{special_apps[process_name]} 应用窗口",
                    "process_path": process_path,
                    "pid": pid,
                        "special_app": True
                    }
                session_data["applications"].append(app_data)
            continue
        
        # 处理普通应用
        app_data = {
            "title": window.title,
            "process_path": process_path,
            "pid": pid
        }
        session_data["applications"].append(app_data)
    
    logger.info(f"会话数据收集完成。共收集到 {len(session_data['applications']) + len(session_data['browser_windows'])} 个相关窗口/应用条目。")
    return session_data

# --- 会话数据文件管理 ---
def load_all_sessions(config):
    filename = config["session_data_file"]
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                all_sessions = json.load(f)
            logger.info(f"已从 {filename} 加载所有会话数据。共 {len(all_sessions)} 个会话。")
            return all_sessions
        else:
            logger.warning(f"会话文件 {filename} 不存在。")
            return {}
    except Exception as e:
        logger.error(f"加载所有会话数据时发生错误: {e}", exc_info=True)
        if config.get("backup_session_data", False):
            backup_filename = f"{filename}.bak"
            if os.path.exists(backup_filename):
                logger.warning(f"尝试从备份文件 {backup_filename} 加载所有会话数据...")
                try:
                    with open(backup_filename, 'r', encoding='utf-8') as f:
                        all_sessions = json.load(f)
                    logger.info(f"已从备份文件 {backup_filename} 成功加载所有会话数据。共 {len(all_sessions)} 个会话。")
                    return all_sessions
                except Exception as backup_e:
                    logger.error(f"从备份文件加载所有会话数据时发生错误: {backup_e}", exc_info=True)
                    return {}
        return {}

def save_all_sessions(all_sessions_data, config):
    filename = config["session_data_file"]
    if config.get("backup_session_data", False) and os.path.exists(filename):
        backup_filename = f"{filename}.bak"
        try:
            shutil.copyfile(filename, backup_filename)
            logger.info(f"已备份现有会话数据文件到 {backup_filename}")
        except Exception as e:
            logger.warning(f"备份会话数据文件时发生警告: {e}", exc_info=True)
    try:
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_sessions_data, f, ensure_ascii=False, indent=4)
        logger.info(f"所有会话数据已成功保存到 {filename}")
    except Exception as e:
        logger.error(f"保存所有会话数据时发生错误: {e}", exc_info=True)

# --- 会话恢复 ---
def restore_session(session_data, config):
    """恢复保存的会话"""
    logger.info("开始恢复会话...")
    success_count = 0
    fail_count = 0
    
    # 检查会话数据结构
    if not session_data:
        logger.warning("会话数据为空，无内容可恢复")
        return 0, 0
        
    # 兼容旧格式的会话数据
    if isinstance(session_data, list):
        # 旧格式：直接是项目列表
        applications = []
        browser_windows = []
        
        for item in session_data:
            if not isinstance(item, dict):
                continue
                
            item_type = item.get("type")
            if item_type == "browser":
                # 转换为新格式的浏览器窗口
                browser_windows.append({
                    "title": item.get("title", "未知浏览器"),
                    "process_path": item.get("path", ""),
                    "pid": 0,
                    "browser_name": "未知",
                    "browser_type": "chrome",
                    "tabs": item.get("urls", []),
                    "tab_count": len(item.get("urls", []))
                })
            else:
                # 转换为新格式的应用
                applications.append({
                    "title": item.get("title", "未知应用"),
                    "process_path": item.get("path", ""),
                    "pid": 0,
                    "special_app": item.get("special_app", False)
                })
                
        # 使用转换后的新格式数据
        session_data = {
            "applications": applications,
            "browser_windows": browser_windows
        }
    
    # 1. 恢复应用程序
    if "applications" in session_data and isinstance(session_data["applications"], list):
        for app in session_data["applications"]:
            try:
                logger.info(f"\n尝试恢复 (application): '{app['title']}' (路径: {app['process_path']})")
                result = restore_application(app, config)
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"恢复应用程序时发生错误: {e}")
                fail_count += 1
    
    # 2. 恢复浏览器窗口
    if "browser_windows" in session_data and isinstance(session_data["browser_windows"], list):
        for browser in session_data["browser_windows"]:
            try:
                logger.info(f"\n尝试恢复浏览器: '{browser['title']}' (路径: {browser['process_path']})")
                if "tab_count" in browser and browser["tab_count"] > 0:
                    logger.info(f"  - 尝试恢复 {browser['tab_count']} 个标签页")
                result = restore_browser(browser, config)
                if result:
                    success_count += 1
                else:
                    fail_count += 1
            except Exception as e:
                logger.error(f"恢复浏览器时发生错误: {e}")
                fail_count += 1
    
    logger.info(f"\n会话恢复完成。成功: {success_count}, 失败: {fail_count}")
    return success_count, fail_count

def restore_browser(browser_data, config):
    """恢复浏览器窗口"""
    if not BROWSER_TABS_SUPPORT:
        logger.warning("浏览器标签页支持模块未加载，无法恢复浏览器窗口")
        return False
        
    try:
        process_path = browser_data.get("process_path")
        window_title = browser_data.get("title", "")
        tabs = browser_data.get("tabs", [])
        
        if not process_path or not tabs:
            logger.warning(f"浏览器数据不完整，无法恢复: {window_title}")
            return False
        
        # 检查浏览器是否已经存在
        browser_exists = False
        browser_name = os.path.basename(process_path).lower()
        
        # 获取所有窗口
        windows = gw.getAllWindows()
        for window in windows:
            if not window.title or not window.visible:
                continue
                
            try:
                _, pid = win32process.GetWindowThreadProcessId(window._hWnd)
                proc = psutil.Process(pid)
                proc_path = proc.exe()
                proc_name = os.path.basename(proc_path).lower()
                
                # 如果找到相同类型的浏览器
                if proc_name == browser_name:
                    # 使用相似度比较窗口标题
                    similarity = difflib.SequenceMatcher(None, window.title.lower(), window_title.lower()).ratio()
                    if similarity >= 0.6:  # 60%相似度阈值
                        logger.info(f"浏览器窗口已存在: '{window.title}' (相似度: {similarity:.2f})")
                        browser_exists = True
                        break
            except Exception:
                continue
        
        # 如果浏览器已存在，则跳过恢复
        if browser_exists:
            logger.info(f"跳过恢复已存在的浏览器窗口: {window_title}")
            return True
            
        # 浏览器不存在，恢复标签页
        logger.info(f"浏览器窗口不存在，开始恢复: {window_title}")
        success = restore_browser_tabs(process_path, window_title, tabs, config)
        if success:
            logger.info(f"成功恢复浏览器窗口: {window_title}")
        else:
            logger.warning(f"恢复浏览器窗口失败: {window_title}")
        return success
    except Exception as e:
        logger.error(f"恢复浏览器窗口时出错: {e}")
        return False

def is_browser_window(process_path, window_title):
    """判断是否是浏览器窗口，返回浏览器名称和类型"""
    process_name = os.path.basename(process_path).lower()
    
    browsers = {
        "chrome.exe": ("Google Chrome", "chrome"),
        "msedge.exe": ("Microsoft Edge", "chrome"),
        "firefox.exe": ("Firefox", "firefox"),
        "brave.exe": ("Brave", "chrome"),
        "opera.exe": ("Opera", "opera"),
        "vivaldi.exe": ("Vivaldi", "chrome"),
        "360chrome.exe": ("360极速浏览器", "chrome"),
        "360se.exe": ("360安全浏览器", "chrome")
    }
    
    if process_name in browsers:
        return browsers[process_name]
    
    return None

def restore_application(app_data, config):
    """恢复普通应用程序"""
    app_title = app_data.get("title", "")
    app_path = app_data.get("process_path", "")
    app_pid = app_data.get("pid", 0)
    is_special_app = app_data.get("special_app", False)
    
    if not app_path or not os.path.isfile(app_path):
        logger.warning(f"应用路径无效: {app_path}")
        return False
    
    # 检查应用是否已在运行
    app_exists = False
    
    # 1. 首先尝试通过标题匹配
    windows = gw.getAllWindows()
    for window in windows:
        if not window.title:
            continue
        
        # 使用相似度比较窗口标题
        similarity = difflib.SequenceMatcher(None, window.title.lower(), app_title.lower()).ratio()
        if similarity >= 0.7:  # 70%相似度阈值
            logger.info(f"应用已在运行: '{window.title}' (相似度: {similarity:.2f})")
            app_exists = True
            break
    
    # 2. 如果标题匹配未找到，尝试通过进程路径匹配
    if not app_exists:
        for proc in psutil.process_iter(['pid', 'exe']):
            try:
                if proc.info['exe'] and proc.info['exe'] == app_path:
                    if is_special_app:
                        logger.info(f"特殊应用进程已在运行: {app_path}")
                    else:
                        logger.info(f"应用进程已在运行: {app_path}")
                    app_exists = True
                    break
            except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                continue
    
    # 如果应用已存在，则跳过恢复
    if app_exists:
        logger.info(f"跳过恢复已存在的应用程序: {app_title}")
        return True
    
    # 应用未运行，尝试启动
    try:
        logger.info(f"应用程序不存在，开始启动: {app_path}")
        subprocess.Popen([app_path])
        # 等待短暂时间，给应用启动留出时间
        time.sleep(1)
        return True
    except Exception as e:
        logger.error(f"启动应用失败: {e}")
        return False

# --- SessionManager 类 ---
class SessionManager:
    def __init__(self, session_file, backup=True, default_session_name="默认会话"):
        self.session_file = session_file
        self.backup = backup
        self.default_session_name = default_session_name
        self.sessions = self.load_sessions()

    def load_sessions(self):
        if not os.path.exists(self.session_file):
            return {self.default_session_name: []}
        try:
            with open(self.session_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            # 自动修正：只保留 value 为 list 的项，且列表元素为 dict
            fixed = {}
            for k, v in data.items():
                if isinstance(v, list):
                    # 进一步过滤，确保每个元素为 dict
                    filtered = [item for item in v if isinstance(item, dict)]
                    if len(filtered) < len(v):
                        logging.warning(f"会话 '{k}' 中存在非法项，已自动跳过。")
                    fixed[k] = filtered
                else:
                    logging.warning(f"会话 '{k}' 的数据不是列表，已自动忽略。")
            if not fixed:
                fixed = {self.default_session_name: []}
            return fixed
        except Exception as e:
            logging.error(f"加载会话数据失败: {e}")
            return {self.default_session_name: []}

    def save_sessions(self):
        if self.backup and os.path.exists(self.session_file):
            shutil.copyfile(self.session_file, self.session_file + ".bak")
        try:
            with open(self.session_file, 'w', encoding='utf-8') as f:
                json.dump(self.sessions, f, ensure_ascii=False, indent=4)
            return True
        except Exception as e:
            logging.error(f"保存会话数据失败: {e}")
            return False

    def get_session_names(self):
        return list(self.sessions.keys())

    def get_session(self, name):
        return self.sessions.get(name, [])

    def set_session(self, name, items):
        self.sessions[name] = items
        return self.save_sessions()

    def delete_session(self, name):
        if name in self.sessions:
            del self.sessions[name]
            return self.save_sessions()
        return False

    def clear_session(self, name):
        if name in self.sessions:
            self.sessions[name] = []
            return self.save_sessions()
        return False

    def export_session(self, name, export_path):
        if name in self.sessions:
            try:
                with open(export_path, 'w', encoding='utf-8') as f:
                    json.dump(self.sessions[name], f, ensure_ascii=False, indent=4)
                return True
            except Exception as e:
                logging.error(f"导出会话失败: {e}")
        return False

    def import_session(self, import_path, new_name):
        try:
            with open(import_path, 'r', encoding='utf-8') as f:
                items = json.load(f)
            # 校验导入内容必须为列表，且元素为 dict
            if not isinstance(items, list):
                logging.error(f"导入会话失败：文件内容不是列表。")
                return False
            filtered = [item for item in items if isinstance(item, dict)]
            if len(filtered) < len(items):
                logging.warning(f"导入会话 '{new_name}' 时发现非法项，已自动跳过。")
            self.sessions[new_name] = filtered
            return self.save_sessions()
        except Exception as e:
            logging.error(f"导入会话失败: {e}")
            return False 

# 添加以下函数来支持窗口预览功能
def create_session_preview(session_data, config, preview_size=(800, 600)):
    """
    创建会话窗口布局的预览图像
    
    参数:
        session_data: 会话数据字典
        config: 配置字典
        preview_size: 预览图像的大小 (宽, 高)
        
    返回:
        PIL.Image 对象
    """
    try:
        if not session_data or "windows" not in session_data:
            return None
            
        # 获取屏幕尺寸信息
        monitor_info = []
        def callback(monitor, dc, rect, data):
            monitor_info.append({
                'left': rect[0],
                'top': rect[1],
                'width': rect[2] - rect[0],
                'height': rect[3] - rect[1]
            })
            return True
            
        win32api.EnumDisplayMonitors(None, None, callback, None)
        
        if not monitor_info:
            return None
            
        # 计算所有显示器的总边界
        min_x = min(m['left'] for m in monitor_info)
        min_y = min(m['top'] for m in monitor_info)
        max_x = max(m['left'] + m['width'] for m in monitor_info)
        max_y = max(m['top'] + m['height'] for m in monitor_info)
        
        total_width = max_x - min_x
        total_height = max_y - min_y
        
        # 创建预览图像
        scale_factor = min(preview_size[0] / total_width, preview_size[1] / total_height)
        preview_width = int(total_width * scale_factor)
        preview_height = int(total_height * scale_factor)
        
        preview = Image.new('RGB', (preview_width, preview_height), color=(240, 240, 240))
        draw = ImageDraw.Draw(preview)
        
        # 绘制显示器边框
        for m in monitor_info:
            x1 = int((m['left'] - min_x) * scale_factor)
            y1 = int((m['top'] - min_y) * scale_factor)
            x2 = int(x1 + m['width'] * scale_factor)
            y2 = int(y1 + m['height'] * scale_factor)
            
            # 绘制显示器外框
            draw.rectangle([x1, y1, x2, y2], outline=(0, 0, 0), width=2)
            
            # 绘制显示器内部
            draw.rectangle([x1+2, y1+2, x2-2, y2-2], fill=(255, 255, 255))
        
        # 绘制窗口
        colors = [
            (52, 152, 219),  # 蓝色
            (46, 204, 113),  # 绿色
            (155, 89, 182),  # 紫色
            (230, 126, 34),  # 橙色
            (231, 76, 60),   # 红色
            (241, 196, 15)   # 黄色
        ]
        
        for i, window in enumerate(session_data["windows"]):
            if "rect" in window:
                rect = window["rect"]
                
                # 计算窗口在预览中的位置
                x1 = int((rect["left"] - min_x) * scale_factor)
                y1 = int((rect["top"] - min_y) * scale_factor)
                x2 = int(x1 + rect["width"] * scale_factor)
                y2 = int(y1 + rect["height"] * scale_factor)
                
                # 确保窗口在预览区域内
                x1 = max(0, min(x1, preview_width-1))
                y1 = max(0, min(y1, preview_height-1))
                x2 = max(0, min(x2, preview_width-1))
                y2 = max(0, min(y2, preview_height-1))
                
                # 如果窗口太小，至少确保它是可见的
                if x2 - x1 < 5:
                    x2 = x1 + 5
                if y2 - y1 < 5:
                    y2 = y1 + 5
                
                # 绘制窗口
                color = colors[i % len(colors)]
                draw.rectangle([x1, y1, x2, y2], fill=color, outline=(0, 0, 0), width=1)
                
                # 如果窗口足够大，添加标题文本
                if y2 - y1 > 20 and x2 - x1 > 50:
                    title = window.get("title", "")
                    if len(title) > 20:
                        title = title[:17] + "..."
                    draw.text((x1+5, y1+5), title, fill=(255, 255, 255))
        
        return preview
    except Exception as e:
        logging.error(f"创建会话预览失败: {e}", exc_info=True)
        return None

def capture_window_thumbnail(hwnd, size=(200, 150)):
    """
    捕获指定窗口的缩略图
    
    参数:
        hwnd: 窗口句柄
        size: 缩略图大小
        
    返回:
        PIL.Image 对象或 None（如果捕获失败）
    """
    try:
        # 获取窗口位置
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top
        
        if width <= 0 or height <= 0:
            return None
            
        # 截取窗口图像
        screenshot = ImageGrab.grab((left, top, right, bottom))
        
        # 调整大小
        thumbnail = screenshot.resize(size, Image.LANCZOS)
        return thumbnail
    except Exception as e:
        logging.error(f"捕获窗口缩略图失败 (hwnd={hwnd}): {e}", exc_info=True)
        return None 