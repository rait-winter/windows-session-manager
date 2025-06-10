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

# 需要从主程序导入的工具函数（如 get_process_path_from_hwnd、is_browser_process）
# 这里假设后续会迁移这些函数到 utils.py 或 core.py 内部
# from .utils import get_process_path_from_hwnd, is_browser_process

logger = logging.getLogger(__name__)

# --- 会话采集 ---
def collect_session_data_core(config):
    from session_manager.utils import is_window_relevant, is_browser_process, get_process_path_from_hwnd, get_browser_tabs
    session_items = []
    processed_app_paths = set()
    processed_browser_paths = set()
    logger.info("开始收集当前会话数据...")
    
    # 1. 使用pygetwindow采集常规窗口
    try:
        windows = gw.getAllWindows()
        if not windows:
            logger.info("未找到任何可见窗口进行收集。")
        else:
            for window in windows:
                process_path = is_window_relevant(window, config)
                if process_path:
                    is_browser = is_browser_process(process_path, config)
                    if is_browser:
                        if process_path not in processed_browser_paths:
                            browser_info = {
                                "type": "browser",
                                "title": window.title,
                                "path": process_path,
                                "urls": get_browser_tabs(process_path, window.title, config),
                            }
                            session_items.append(browser_info)
                            processed_browser_paths.add(process_path)
                            logger.debug(f"收集到浏览器: '{window.title}' ({process_path})")
                        continue
                    else:
                        if process_path not in processed_app_paths:
                            window_info = {
                                "type": "application",
                                "title": window.title,
                                "path": process_path,
                            }
                            session_items.append(window_info)
                            processed_app_paths.add(process_path)
                            logger.debug(f"收集到应用: '{window.title}' ({process_path})")
                        continue
    except Exception as e:
        logger.error(f"使用pygetwindow收集窗口信息时发生错误: {e}", exc_info=True)
    
    # 2. 使用win32gui采集特殊应用窗口
    try:
        import win32gui
        import win32process
        import win32con
        import psutil
        
        # 特殊应用名称列表
        special_apps = ['PixPin', 'FastOrange', 'Everything']
        
        # 获取所有进程
        for proc in psutil.process_iter(['pid', 'name', 'exe']):
            try:
                proc_info = proc.info
                proc_name = proc_info['name'] if 'name' in proc_info else ""
                proc_exe = proc_info['exe'] if 'exe' in proc_info else ""
                
                # 检查进程名是否包含特殊应用名称
                is_special = False
                matching_app = ""
                for app in special_apps:
                    if (app.lower() in proc_name.lower() or 
                        (proc_exe and app.lower() in proc_exe.lower())):
                        is_special = True
                        matching_app = app
                        break
                
                # 特殊处理：通过进程名精确匹配
                if not is_special:
                    # Everything 搜索工具的进程名通常是 Everything.exe
                    if proc_name.lower() == "everything.exe":
                        is_special = True
                        matching_app = "Everything"
                
                if is_special and proc_exe and proc_exe not in processed_app_paths:
                    # 将特殊应用添加到会话列表
                    logger.info(f"发现特殊应用: {proc_name} (PID: {proc_info['pid']}, 路径: {proc_exe})")
                    window_info = {
                        "type": "application",
                        "title": f"{matching_app} 应用窗口",
                        "path": proc_exe,
                        "special_app": True
                    }
                    session_items.append(window_info)
                    processed_app_paths.add(proc_exe)
                    logger.debug(f"收集到特殊应用: '{matching_app}' ({proc_exe})")
                    
                    # 尝试查找该进程的所有窗口
                    def enum_windows_callback(hwnd, pid):
                        try:
                            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
                            if win_pid == pid:
                                title = win32gui.GetWindowText(hwnd)
                                if title:
                                    logger.debug(f"  - 找到特殊应用窗口: {title} (HWND: {hwnd})")
                        except Exception as e:
                            logger.debug(f"枚举特殊应用窗口时出错: {e}")
                        return True
                    
                    win32gui.EnumWindows(lambda hwnd, lParam: enum_windows_callback(hwnd, proc_info['pid']), None)
            except Exception as e:
                logger.debug(f"处理特殊应用进程时出错: {e}")
    except Exception as e:
        logger.error(f"使用win32gui收集特殊应用窗口时发生错误: {e}", exc_info=True)
    
    logger.info(f"会话数据收集完成。共收集到 {len(session_items)} 个相关窗口/应用条目。")
    return session_items

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
def restore_specific_session_core(session_items, config):
    from session_manager.utils import get_process_path_from_hwnd, is_browser_process
    if not session_items:
        logger.info("没有会话条目可用于恢复。")
        return
    logger.info("开始恢复会话...")
    restored_count = 0
    failed_count = 0
    window_title_similarity_threshold = config.get("window_title_similarity_threshold", get_default_config()["window_title_similarity_threshold"])
    restore_delay_seconds = config.get("restore_delay_seconds", get_default_config()["restore_delay_seconds"])
    for window_info in session_items:
        app_path = window_info.get("path")
        app_title = window_info.get("title")
        item_type = window_info.get("type", "unknown")
        is_special_app = window_info.get("special_app", False)
        
        if not app_path:
            logger.warning(f"跳过没有路径的会话条目: {window_info}")
            failed_count += 1
            continue
            
        logger.info(f"\n尝试恢复 ({item_type}): '{app_title}' (路径: {app_path})")
        
        # 检查应用是否已经在运行
        already_running = False
        try:
            windows = gw.getAllWindows()
            for window in windows:
                try:
                    process_path = get_process_path_from_hwnd(window._hWnd)
                    if process_path and process_path.lower() == app_path.lower():
                        if window.title and app_title:
                            similarity = difflib.SequenceMatcher(None, window.title.lower(), app_title.lower()).ratio()
                            if similarity >= window_title_similarity_threshold:
                                logger.info(f"  - 应用已在运行: '{window.title}' (相似度: {similarity:.2f})")
                                already_running = True
                                restored_count += 1
                                break
                except Exception as e:
                    logger.debug(f"  - 检查窗口时出错: {e}")
                    continue
        except Exception as e:
            logger.debug(f"  - 获取窗口列表时出错: {e}")
        
        # 特殊处理特殊应用
        if is_special_app:
            if already_running:
                logger.info(f"  - 特殊应用 '{app_title}' 已在运行，无需启动")
                continue
                
            # 检查进程是否已运行
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        proc_info = proc.info
                        proc_exe = proc_info.get('exe', '')
                        if proc_exe and proc_exe.lower() == app_path.lower():
                            logger.info(f"  - 特殊应用进程已在运行: {proc_exe}")
                            already_running = True
                            restored_count += 1
                            break
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"  - 检查特殊应用进程时出错: {e}")
        
        # 如果应用未运行，尝试启动
        if not already_running:
            try:
                logger.info(f"  - 启动应用: {app_path}")
                subprocess.Popen([app_path])
                restored_count += 1
                time.sleep(restore_delay_seconds)  # 等待应用启动
            except Exception as e:
                logger.error(f"  - 启动应用失败: {e}")
                failed_count += 1
    
    logger.info(f"\n会话恢复完成。成功: {restored_count}, 失败: {failed_count}")
    return restored_count, failed_count

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