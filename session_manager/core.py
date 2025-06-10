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
    try:
        windows = gw.getAllWindows()
        if not windows:
            logger.info("未找到任何可见窗口进行收集。")
            return session_items
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
        logger.error(f"收集窗口信息时发生错误: {e}", exc_info=True)
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
        if not app_path:
            logger.warning(f"跳过没有路径的会话条目: {window_info}")
            failed_count += 1
            continue
        logger.info(f"\n尝试恢复 ({item_type}): '{app_title}' (路径: {app_path})")
        try:
            all_current_windows = gw.getAllWindows()
            existing_windows = [
                win for win in all_current_windows
                if win.visible and win.title
                and get_process_path_from_hwnd(win._hWnd) == app_path
            ]
            found_existing = False
            if existing_windows:
                logger.debug(f"  - 找到 {len(existing_windows)} 个同路径的现有窗口。")
                best_match_window = None
                highest_similarity = -1
                for win in existing_windows:
                    if win.title == app_title:
                        best_match_window = win
                        logger.debug(f"  - 找到精确匹配标题的窗口 (标题: '{best_match_window.title}')。")
                        break
                if not best_match_window and len(existing_windows) > 1:
                    logger.debug("  - 未找到精确匹配标题的窗口，尝试模糊匹配...")
                    for win in existing_windows:
                        similarity = difflib.SequenceMatcher(None, app_title.lower(), win.title.lower()).ratio()
                        logger.debug(f"    - Comparing '{app_title}' with '{win.title}': {similarity:.2f}")
                        if similarity > window_title_similarity_threshold and similarity > highest_similarity:
                            highest_similarity = similarity
                            best_match_window = win
                    if best_match_window:
                        logger.debug(f"  - 找到最匹配的窗口 (标题: '{best_match_window.title}', 相似度: {highest_similarity:.2f})，尝试聚焦...")
                if best_match_window:
                    found_existing = True
                    try:
                        logger.debug(f"  - 尝试使用 pygetwindow.restore() 和 activate() 对窗口 '{best_match_window.title}' (HWND: {best_match_window._hWnd})...")
                        if best_match_window.isMinimized:
                            best_match_window.restore()
                            time.sleep(restore_delay_seconds)
                        best_match_window.activate()
                        logger.info("  - 窗口聚焦尝试成功。")
                    except Exception as focus_e:
                        logger.warning(f"  - 使用 pygetwindow 聚焦现有窗口 '{best_match_window.title}' 时发生错误: {focus_e}", exc_info=True)
                        try:
                            from session_manager.utils import ShowWindow, SW_RESTORE, SetForegroundWindow
                            hwnd = best_match_window._hWnd
                            ShowWindow(hwnd, SW_RESTORE)
                            SetForegroundWindow(hwnd)
                            logger.info("  - API 聚焦尝试成功。")
                        except Exception as api_e:
                            logger.error(f"  - API 聚焦尝试失败对 HWND {hwnd}: {api_e}. 可能原因：权限不足或窗口不可聚焦。", exc_info=True)
                            failed_count += 1
                else:
                    logger.info("  - 未找到可用的现有窗口进行聚焦（精确或相似标题匹配失败）。")
            if not found_existing:
                logger.info("  - 未找到可用的现有窗口或聚焦失败，尝试启动新实例...")
                try:
                    is_browser_app = is_browser_process(app_path, config)
                    if is_browser_app:
                        logger.info(f"  - 识别为浏览器 ({os.path.basename(app_path)})，启动可执行文件，依赖浏览器自身会话恢复...")
                        subprocess.Popen([app_path])
                        logger.info(f"  - 浏览器 '{app_title}' 启动命令成功。")
                    else:
                        logger.info("  - 启动应用程序...")
                        subprocess.Popen([app_path])
                        logger.info(f"  - 应用程序 '{app_title}' 启动命令成功。")
                except FileNotFoundError:
                    logger.error(f"  - 启动应用程序失败: 找不到可执行文件 {app_path}")
                except Exception as e:
                    logger.error(f"  - 启动应用程序时发生意外错误: {e}", exc_info=True)
            restored_count += 1
        except Exception as outer_e:
            logger.error(f"恢复 '{app_title}' 时发生意外错误: {outer_e}", exc_info=True)
            failed_count += 1
    logger.info(f"\n会话恢复完成。成功尝试处理 {restored_count} 个条目，失败 {failed_count} 个。")
    if failed_count > 0:
        logger.warning("部分条目恢复失败，请检查日志了解详情。")

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