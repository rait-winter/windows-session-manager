"""
config.py
配置加载与管理模块。
"""

import os
import sys
import json
import logging
import appdirs

# SCRIPT_DIR 用于定位配置和数据文件
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = sys._MEIPASS
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

# 用户数据目录
USER_DATA_DIR = appdirs.user_data_dir("WindowsSessionManager", "WSM")
os.makedirs(USER_DATA_DIR, exist_ok=True)

# 配置文件路径
CONFIG_FILE = os.path.join(USER_DATA_DIR, "config.json")
DEFAULT_SESSION_NAME = "默认会话"

logger = logging.getLogger(__name__)

def get_default_config():
    """返回默认配置字典。"""
    return {
        "exclude_process_paths": [
            os.path.normcase(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "svchost.exe")),
            os.path.normcase(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "explorer.exe")),
            os.path.normcase(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "dwm.exe")),
            os.path.normcase(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "conhost.exe")),
            os.path.normcase(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "SystemApps", "Microsoft.Windows.StartMenuExperienceHost_cw5n1h2txyewy", "StartMenuExperienceHost.exe")),
            os.path.normcase(os.path.join(os.environ.get("WINDIR", "C:\\Windows"), "System32", "RuntimeBroker.exe")),
            os.path.normcase(os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "WindowsApps", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "wt.exe")),
            os.path.normcase(os.path.join(os.environ.get("PROGRAMFILES", "C:\\Program Files"), "WindowsApps", "Microsoft.WindowsTerminal_8wekyb3d8bbwe", "WindowsTerminal.exe")),
            os.path.normcase(sys.executable)
        ],
        "exclude_window_titles": [
            "Program Manager",
            "Default IME",
            "MSCTFIME UI",
            "NVIDIA GeForce Overlay",
            "Settings",
            "Microsoft Text Input Application",
            "dummyLayeredWnd"
        ],
        "browser_executables": [
            "chrome.exe",
            "msedge.exe",
            "firefox.exe",
            "brave.exe",
            "opera.exe"
        ],
        "session_data_file_name": "sessions.json",
        "log_file_name": "session_manager.log",
        "window_title_similarity_threshold": 0.7,
        "restore_delay_seconds": 0.1,
        "backup_session_data": True,
        "startup_delay_seconds": 2,
        "ui": {
            "theme": "vista",
            "dark_mode": False,
            "window_width": 1000,
            "window_height": 750,
            "show_tooltips": True,
            "confirm_session_delete": True,
            "confirm_window_delete": True,
            "font_size": 10,
            "max_recent_sessions": 5
        },
        "hotkeys": {
            "save_session": "ctrl+alt+s",
            "restore_session": "ctrl+alt+r",
            "quick_restore": "ctrl+alt+q"
        },
        "startup": {
            "autostart": False,
            "minimized": False,
            "restore_last_session": False,
            "last_session": ""
        },
        "advanced": {
            "window_detection_timeout": 5,
            "virtual_desktop_support": True,
            "collect_window_icons": True,
            "max_restore_retries": 3,
            "keep_session_history": True,
            "max_session_history": 10,
            "auto_save_interval": 300  # 5分钟
        }
    }

def load_config(filename=None):
    """
    从 JSON 文件加载配置，不存在则创建默认配置。
    解析 session_data_file 和 log_file 的完整路径。
    """
    if filename is None:
        filename = CONFIG_FILE

    current_config = get_default_config()

    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                loaded_user_config = json.load(f)
            
            # 递归合并配置
            def merge_config(target, source):
                for key, value in source.items():
                    if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                        merge_config(target[key], value)
                    elif key in target:
                        target[key] = value
                    else:
                        logger.warning(f"配置文件 '{filename}' 包含未知键: '{key}'，将忽略。")
            
            merge_config(current_config, loaded_user_config)
            logger.info(f"配置已从 {filename} 加载。")
        except Exception as e:
            logger.error(f"加载配置时发生错误 {filename}: {e}. 使用默认配置。", exc_info=True)
    else:
        logger.info(f"配置文件 {filename} 不存在，创建默认配置。")
        save_config(current_config, filename)

    # 设置数据文件和日志文件路径
    current_config["session_data_file"] = os.path.join(USER_DATA_DIR, current_config["session_data_file_name"])
    current_config["log_file"] = os.path.join(USER_DATA_DIR, current_config["log_file_name"])
    current_config["sessions_dir"] = os.path.join(USER_DATA_DIR, "sessions")
    current_config["backup_dir"] = os.path.join(USER_DATA_DIR, "backups")
    
    # 确保所需目录存在
    os.makedirs(current_config["sessions_dir"], exist_ok=True)
    os.makedirs(current_config["backup_dir"], exist_ok=True)

    return current_config

def save_config(config_data_to_save, filename=None):
    """保存配置到 JSON 文件。"""
    if filename is None:
        filename = CONFIG_FILE
        
    try:
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        save_data = config_data_to_save.copy()
        
        # 移除动态生成的路径
        for key in ["session_data_file", "log_file", "sessions_dir", "backup_dir"]:
            if key in save_data:
                del save_data[key]
                
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        logger.debug(f"配置已保存到 {filename}")
        return True
    except Exception as e:
        logger.error(f"保存配置时发生错误 {filename}: {e}", exc_info=True)
        return False

def update_config(updates, filename=None):
    """更新并保存配置的特定部分"""
    if filename is None:
        filename = CONFIG_FILE
        
    config = load_config(filename)
    
    # 递归更新配置
    def update_dict(target, source):
        for key, value in source.items():
            if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                update_dict(target[key], value)
            elif key in target:
                target[key] = value
            else:
                logger.warning(f"更新配置时包含未知键: '{key}'，将忽略。")
    
    update_dict(config, updates)
    return save_config(config, filename)

def get_config_value(path, config=None):
    """
    获取配置中的特定值，path为以点分隔的路径，如 "ui.theme"
    """
    if config is None:
        config = load_config()
    
    keys = path.split('.')
    result = config
    try:
        for key in keys:
            result = result[key]
        return result
    except (KeyError, TypeError):
        return None 