"""
config.py
配置加载与管理模块。
"""

import os
import sys
import json
import logging

# SCRIPT_DIR 用于定位配置和数据文件
if getattr(sys, 'frozen', False):
    SCRIPT_DIR = sys._MEIPASS
else:
    SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

CONFIG_FILE = os.path.join(SCRIPT_DIR, "config.json")
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
        "startup_delay_seconds": 2
    }

def load_config(filename=CONFIG_FILE):
    """
    从 JSON 文件加载配置，不存在则创建默认配置。
    解析 session_data_file 和 log_file 的完整路径。
    """
    current_config = get_default_config()

    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                loaded_user_config = json.load(f)
            for key, value in loaded_user_config.items():
                if key in current_config:
                    current_config[key] = value
                else:
                    logger.warning(f"配置文件 '{filename}' 包含未知键: '{key}'，将忽略。")
            logger.info(f"配置已从 {filename} 加载。")
        except Exception as e:
            logger.error(f"加载配置时发生错误 {filename}: {e}. 使用默认配置。", exc_info=True)
    else:
        logger.info(f"配置文件 {filename} 不存在，创建默认配置。")
        save_config(current_config, filename)

    current_config["session_data_file"] = os.path.join(SCRIPT_DIR, current_config["session_data_file_name"])
    current_config["log_file"] = os.path.join(SCRIPT_DIR, current_config["log_file_name"])

    return current_config

def save_config(config_data_to_save, filename=CONFIG_FILE):
    """保存配置到 JSON 文件。"""
    try:
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        save_data = config_data_to_save.copy()
        if "session_data_file" in save_data:
            del save_data["session_data_file"]
        if "log_file" in save_data:
            del save_data["log_file"]
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(save_data, f, ensure_ascii=False, indent=4)
        logger.debug(f"配置已保存到 {filename}")
    except Exception as e:
        logger.error(f"保存配置时发生错误 {filename}: {e}", exc_info=True) 