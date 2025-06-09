import pygetwindow as gw
import ctypes
import os
import json # Import json for saving/loading
import subprocess
import time # Import time for a small delay if needed
import difflib
import sys
import logging
import shutil # Import shutil for backing up files
import tkinter as tk # Import tkinter
from tkinter import scrolledtext # Import scrolledtext for a multi-line text area
from tkinter import messagebox # Import messagebox for pop-up messages
from tkinter import filedialog # Import filedialog for opening files/directories
from tkinter import ttk # Import ttk for Treeview
from tkinter import simpledialog # Import simpledialog for user input
import platform # Import platform to check OS for context menu (optional, but good practice)

# --- Logging Configuration ---
# Get the directory of the currently running script to place the log file and config
# Use sys._MEIPASS if running from PyInstaller --onefile temp dir
if getattr(sys, 'frozen', False):
    # Running in a bundle
    script_dir = os.path.dirname(sys.executable)
else:
    # Running as a script
    script_dir = os.path.dirname(os.path.abspath(sys.argv[0]))

log_file_path = os.path.join(script_dir, "session_manager.log")

# Ensure the log file directory exists
os.makedirs(script_dir, exist_ok=True)

# Create a logger
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Remove existing handlers to prevent duplicate logs if script is run multiple times
if logger.hasHandlers():
    logger.handlers.clear()

# Create handlers
# Console handler (optional in GUI app, useful for debugging)
# console_handler = logging.StreamHandler(sys.stdout)
# console_handler.setLevel(logging.INFO)
# logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler(log_file_path, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
logger.addHandler(file_handler)

# Custom handler to send logs to the GUI text widget
class TextWidgetHandler(logging.Handler):
    def __init__(self, text_widget):
        super().__init__()
        self.text_widget = text_widget
        self.text_widget.tag_config('INFO', foreground='black')
        self.text_widget.tag_config('DEBUG', foreground='gray')
        self.text_widget.tag_config('WARNING', foreground='orange')
        self.text_widget.tag_config('ERROR', foreground='red')
        self.text_widget.tag_config('CRITICAL', foreground='red', underline=1)

    def emit(self, record):
        msg = self.format(record) + '\n'
        # Append message to the text widget and scroll to the end
        def append():
            try:
                self.text_widget.config(state='normal') # Enable writing temporarily
                self.text_widget.insert(tk.END, msg, record.levelname)
                self.text_widget.see(tk.END)
                self.text_widget.config(state='disabled') # Disable editing
            except Exception as e:
                # Avoid logging to the same handler if it fails
                print(f"Error writing to text widget: {e}")

        # Use text_widget.after to append message in the main GUI thread
        # This is important because log messages might come from a different thread (though unlikely in this single-threaded GUI for now)
        # or simply to ensure GUI updates happen safely.
        try:
             self.text_widget.after(0, append)
        except Exception as e:
             print(f"Error scheduling text widget update: {e}")


# Formatter
formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
# console_handler.setFormatter(formatter)
file_handler.setFormatter(formatter)
# No formatter for TextWidgetHandler, format inside emit

# GUI handler will be added later once the text widget is created

# Define necessary Windows API functions
# BOOL GetWindowThreadProcessId(HWND hWnd, LPDWORD lpdwProcessId);
# Note: The second argument is an output parameter, expecting a pointer to a DWORD.
GetWindowThreadProcessId = ctypes.windll.user32.GetWindowThreadProcessId

# HANDLE OpenProcess(DWORD dwDesiredAccess, BOOL bInheritHandle, DWORD dwProcessId);
# dwDesiredAccess: PROCESS_QUERY_INFORMATION = 0x0400, PROCESS_VM_READ = 0x0010
PROCESS_QUERY_INFORMATION = 0x0400
PROCESS_VM_READ = 0x0010
OpenProcess = ctypes.windll.kernel32.OpenProcess

# BOOL QueryFullProcessImageNameW(HANDLE hProcess, DWORD dwFlags, LPWSTR lpExeName, PDWORD lpdwSize);
# dwFlags: 0 (default)
QueryFullProcessImageNameW = ctypes.windll.kernel32.QueryFullProcessImageNameW

# CloseHandle(HANDLE hObject);
CloseHandle = ctypes.windll.kernel32.CloseHandle

# Define Windows API for window activation/manipulation
SW_RESTORE = 9
ShowWindow = ctypes.windll.user32.ShowWindow
SetForegroundWindow = ctypes.windll.user32.SetForegroundWindow

# --- Configuration Management ---

# Configuration file path relative to the script/executable directory
CONFIG_FILE = os.path.join(script_dir, "config.json")

DEFAULT_CONFIG = {
    # Session data file path relative to the script/executable directory
    # Changed to store multiple sessions
    "session_data_file": os.path.join(script_dir, "sessions.json"),
    "exclude_process_paths": [
        r"C:\Windows\explorer.exe",
        r"C:\Windows\System32\ApplicationFrameHost.exe",
        r"C:\Windows\SystemApps\MicrosoftWindows.Client.CBS_cw5n1h2txyewy\TextInputHost.exe",
        r"C:\Windows\ImmersiveControlPanel\SystemSettings.exe",
        r"C:\Windows\System32\cmd.exe",
        r"C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe",
        r"C:\Program Files\WindowsApps\Microsoft.CursorStudio_*.exe", # Exclude Cursor itself
        # We will handle browsers separately, so they are not in the general exclusion list
        # r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        # r"C:\Program Files\Microsoft\Edge\Application\msedge.exe",
        # Add other paths if you identify more irrelevant system processes
    ],
    "exclude_window_titles": [
        "Program Manager",
        "dummyLayeredWnd",
        "Microsoft Text Input Application",
        "设置", # Windows Settings title
        # Add other titles if you identify more irrelevant windows
    ],
    "browser_executables": [
        "chrome.exe",
        "msedge.exe",
        "firefox.exe",
        "opera.exe",
        # Add other browser executables if needed
    ],
    "window_title_similarity_threshold": 0.7, # Increased threshold slightly for better matching
    "restore_delay_seconds": 0.1, # Small delay after restoring minimized window
    "backup_session_data": True, # Whether to create a backup before saving any session
    "default_session_name": "上次会话", # Default name for auto-saved session
    "startup_delay_seconds": 2, # Delay before restoring on startup (CLI mode)
    # Add other configuration options here in the future
}

def load_config(filename=CONFIG_FILE):
    """Loads configuration from a JSON file. Creates default if not found."""
    config = DEFAULT_CONFIG.copy() # Start with default config
    if os.path.exists(filename):
        try:
            with open(filename, 'r', encoding='utf-8') as f:
                loaded_config = json.load(f)
                # Update default config with loaded values, using .get() for safety
                for key, value in loaded_config.items():
                    # Only update if the key exists in default config
                    if key in config:
                        # Special handling for lists: extend or replace? Let's replace for simplicity
                        # and ensure we use the loaded list if it exists.
                        # For other types, just update.
                         config[key] = value
                    else:
                        logger.warning(f"配置文件 '{filename}' 包含未知键: '{key}'")

            logger.info(f"配置已从 {filename} 加载。")
        except Exception as e:
            logger.error(f"加载配置时发生错误 {filename}: {e}. 使用默认配置。", exc_info=True)
            # If loading fails, we still return the default config, but might want to save it
            # save_config(DEFAULT_CONFIG, filename) # Avoid infinite loop if save also fails
    else:
        logger.info(f"配置文件 {filename} 不存在，创建默认配置。")
        # Save the default config if the file doesn't exist
        save_config(config, filename)

    # Validate and ensure paths are absolute if they are relative to script_dir
    # For session_data_file
    session_data_file_path = config.get("session_data_file", DEFAULT_CONFIG["session_data_file"])
    if not os.path.isabs(session_data_file_path):
         config["session_data_file"] = os.path.join(script_dir, session_data_file_path)

    return config

def save_config(config_data, filename=CONFIG_FILE):
    """Saves configuration data to a JSON file."""
    try:
        # Ensure the directory exists if filename is a path (already done at the top)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(config_data, f, ensure_ascii=False, indent=4)
        logger.debug(f"配置已保存到 {filename}")
    except Exception as e:
        logger.error(f"保存配置时发生错误 {filename}: {e}", exc_info=True)

# Load configuration
config = load_config()

# Use values from the loaded configuration
# SESSION_DATA_FILE will now store ALL sessions
SESSION_DATA_FILE = config.get("session_data_file", os.path.join(script_dir, "sessions.json"))
EXCLUDE_PROCESS_PATHS = config.get("exclude_process_paths", [])
EXCLUDE_WINDOW_TITLES = config.get("exclude_window_titles", [])
BROWSER_EXECUTABLES = config.get("browser_executables", [])
WINDOW_TITLE_SIMILARITY_THRESHOLD = config.get("window_title_similarity_threshold", 0.7)
RESTORE_DELAY_SECONDS = config.get("restore_delay_seconds", 0.1)
BACKUP_SESSION_DATA = config.get("backup_session_data", True)
DEFAULT_SESSION_NAME = config.get("default_session_name", "上次会话")
STARTUP_DELAY_SECONDS = config.get("startup_delay_seconds", 2)


logger.debug(f"配置加载完成：{config}")

def get_process_path_from_hwnd(hwnd):
    """Gets the executable path of the process associated with a window handle."""
    pid = ctypes.c_ulong() # Use c_ulong for DWORD
    # Call GetWindowThreadProcessId to get the Process ID
    try:
        GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
    except Exception as e:
        logger.debug(f"Error calling GetWindowThreadProcessId for HWND {hwnd}: {e}", exc_info=True)
        return None

    if pid.value == 0:
        return None # Could not get process ID

    # Open the process to query information
    # Use required access flags: PROCESS_QUERY_INFORMATION | PROCESS_VM_READ
    try:
        process_handle = OpenProcess(PROCESS_QUERY_INFORMATION | PROCESS_VM_READ, False, pid.value)
    except Exception as e:
         logger.debug(f"Error calling OpenProcess for PID {pid.value}: {e}", exc_info=True)
         return None


    if not process_handle:
        # logger.debug(f"Could not open process {pid.value}. Error: {ctypes.GetLastError()}")
        return None # Could not open process

    # Get the full process image name (executable path)
    # Allocate buffer for the path
    buffer_size = 4096 # Max path length, using a safe large value
    image_name_buffer = ctypes.create_unicode_buffer(buffer_size)
    buffer_chars = ctypes.c_ulong(buffer_size) # Size in characters

    success = False
    try:
        success = QueryFullProcessImageNameW(process_handle, 0, image_name_buffer, ctypes.byref(buffer_chars))
    except Exception as e:
         logger.debug(f"Error calling QueryFullProcessImageNameW for process handle {process_handle}: {e}", exc_info=True)


    # Close the process handle
    try:
        CloseHandle(process_handle)
    except Exception as e:
        logger.debug(f"Error closing process handle {process_handle}: {e}", exc_info=True)


    if success:
        # image_name_buffer contains the path. buffer_chars contains the length used.
        # We need to slice the buffer to get the actual string
        return image_name_buffer.value[:buffer_chars.value]
    else:
        # logger.debug(f"Could not get process image name for PID {pid.value}. Error: {ctypes.GetLastError()}")
        return None # Could not get image name

# --- New filtering logic ---

def is_browser_process(process_path):
    """Checks if a process path corresponds to a known browser executable."""
    if process_path:
        return os.path.basename(process_path).lower() in [b.lower() for b in BROWSER_EXECUTABLES]
    return False

def is_window_relevant(window):
    """Checks if a window is relevant for session saving and returns its process path if relevant."""
    # Check basic window properties first for efficiency
    if not window or not hasattr(window, 'visible') or not hasattr(window, 'title') or not hasattr(window, '_hWnd'):
        return False

    # Only process if visible and has a title
    if not window.visible or not window.title:
        return False

    # Exclude based on title (case-insensitive)
    if window.title.lower() in [t.lower() for t in EXCLUDE_WINDOW_TITLES]:
        return False

    # Get process path
    process_path = get_process_path_from_hwnd(window._hWnd)
    if process_path:
        # Convert to lowercase for case-insensitive comparison
        if process_path.lower() in [p.lower() for p in EXCLUDE_PROCESS_PATHS]:
            return False
        # If it's not in the general exclusion list and we got a path, it's relevant. Return its path.
        return process_path
    else:
        # If we can't get the process path, exclude it as we can't restore it reliably
        return False

# --- Function to collect browser tab URLs (Placeholder for future implementation) ---
def get_browser_tabs(browser_process_path, window_title):
    """
    Placeholder function to get tab URLs for a given browser window.
    This is a complex task and requires browser-specific implementation.
    Returns a list of URLs or an empty list if unable to retrieve.
    """
    # In a real product, this would involve significant effort per browser.
    # For now, we explicitly log that it's not implemented.
    logger.info(f"  - Note: Collecting tab URLs for '{window_title}' ({os.path.basename(browser_process_path)}) is not yet implemented.")
    # Potential future implementation options:
    # 1. Use browser automation libraries (Selenium, Playwright) - requires browser setup.
    # 2. Interact with browser-specific APIs or debug interfaces.
    # 3. Develop browser extensions and communicate with them.
    # 4. Attempt to read/parse browser session files (highly unstable).

    # Returning an empty list means we rely on browser's own session restore.
    return []


def collect_session_data_core():
    """Core logic to collect session data from current windows."""
    session_items = []
    processed_app_paths = set() # To avoid adding multiple windows of the same non-browser app
    processed_browser_paths = set() # To avoid adding multiple windows of the same browser process

    logger.info("开始收集当前会话数据...")

    try:
        windows = gw.getAllWindows()
        if not windows:
            logger.info("未找到任何可见窗口进行收集。")
            return session_items

        for window in windows:
            # Check if the window is relevant and get its process path
            process_path = is_window_relevant(window)
            if process_path:
                is_browser = is_browser_process(process_path)

                # Decide how to handle duplicates.
                # For non-browsers, we often only need one entry to restart the app.
                # For browsers, we also usually just need one entry to let the browser restore its session.
                # A more advanced version might save info about *each* window of an app, but this complicates restoration.
                # Sticking to one entry per executable path for now.

                if is_browser:
                    if process_path not in processed_browser_paths:
                         browser_info = {
                             "type": "browser",
                             "title": window.title,
                             "path": process_path,
                             "urls": get_browser_tabs(process_path, window.title), # Still a placeholder
                             # Could add window position/size here if pygetwindow provides it reliably
                         }
                         session_items.append(browser_info)
                         processed_browser_paths.add(process_path)
                         logger.debug(f"收集到浏览器: '{window.title}' ({process_path})")
                    # else:
                    #      logger.debug(f"跳过重复浏览器进程: '{window.title}' ({process_path})")
                    continue
                else:
                     # Non-browser application
                     if process_path not in processed_app_paths:
                        window_info = {
                            "type": "application",
                            "title": window.title,
                            "path": process_path,
                            # Could add window position/size here
                        }
                        session_items.append(window_info)
                        processed_app_paths.add(process_path)
                        logger.debug(f"收集到应用: '{window.title}' ({process_path})")
                    # else:
                    #      logger.debug(f"跳过重复应用进程: '{window.title}' ({process_path})")
                     continue

    except Exception as e:
        logger.error(f"收集窗口信息时发生错误: {e}", exc_info=True)

    logger.info(f"会话数据收集完成。共收集到 {len(session_items)} 个相关窗口/应用条目。")
    return session_items

# --- Function to manage saving/loading ALL sessions ---

def load_all_sessions(filename=SESSION_DATA_FILE):
    """Loads all session data from the JSON file."""
    try:
        if os.path.exists(filename):
            with open(filename, 'r', encoding='utf-8') as f:
                # The file now contains a dict: {"session_name": [session_items_list], ...}
                all_sessions = json.load(f)
            logger.info(f"已从 {filename} 加载所有会话数据。共 {len(all_sessions)} 个会话。")
            return all_sessions # Return the dictionary of sessions
        else:
            logger.warning(f"会话文件 {filename} 不存在。")
            return {} # Return an empty dictionary if file doesn't exist
    except Exception as e:
        logger.error(f"加载所有会话数据时发生错误: {e}", exc_info=True)
        # Try loading from backup if original file failed
        if BACKUP_SESSION_DATA:
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
                     return {} # Return empty dict if backup also fails
        return {} # Return empty dict if no backup or backup fails

def save_all_sessions(all_sessions_data, filename=SESSION_DATA_FILE):
    """Saves all session data (the dictionary of sessions) to the JSON file."""
    if BACKUP_SESSION_DATA and os.path.exists(filename):
        backup_filename = f"{filename}.bak"
        try:
            shutil.copyfile(filename, backup_filename)
            logger.info(f"已备份现有会话数据文件到 {backup_filename}")
        except Exception as e:
            logger.warning(f"备份会话数据文件时发生警告: {e}", exc_info=True)

    try:
        # Ensure the directory exists
        os.makedirs(os.path.dirname(filename) or '.', exist_ok=True)
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(all_sessions_data, f, ensure_ascii=False, indent=4)
        logger.info(f"所有会话数据已成功保存到 {filename}")
    except Exception as e:
        logger.error(f"保存所有会话数据时发生错误: {e}", exc_info=True)

# --- Placeholder for restoring a SPECIFIC session ---
def restore_specific_session_core(session_items):
    """Core logic to restore session based on a list of session items."""
    if not session_items:
        logger.info("没有会话条目可用于恢复。")
        return

    logger.info("开始恢复会话...")

    restored_count = 0
    failed_count = 0

    for window_info in session_items:
        app_path = window_info.get("path")
        app_title = window_info.get("title")
        item_type = window_info.get("type", "unknown") # New: get item type
        is_browser = (item_type == "browser") # Determine if it's a browser based on type
        urls = window_info.get("urls", []) # Still included, though not used for restoration yet

        if not app_path:
            logger.warning(f"跳过没有路径的会话条目: {window_info}")
            failed_count += 1
            continue

        logger.info(f"\n尝试恢复 ({item_type}): '{app_title}' (路径: {app_path})")

        try:
            # --- Attempt to find and activate existing window ---
            all_current_windows = gw.getAllWindows()
            # Filter current windows by process path
            existing_windows = [
                win for win in all_current_windows
                if win.visible and win.title # Check visibility and title
                and get_process_path_from_hwnd(win._hWnd) == app_path # Match process path
            ]

            found_existing = False
            if existing_windows:
                logger.debug(f"  - 找到 {len(existing_windows)} 个同路径的现有窗口。")

                best_match_window = None
                highest_similarity = -1

                # First, look for an exact title match
                for win in existing_windows:
                    if win.title == app_title:
                        best_match_window = win
                        logger.debug(f"  - 找到精确匹配标题的窗口 (标题: '{best_match_window.title}')。")
                        break # Found exact match, no need for fuzzy

                # If no exact match, try fuzzy matching if there are multiple windows
                if not best_match_window and len(existing_windows) > 1:
                     logger.debug("  - 未找到精确匹配标题的窗口，尝试模糊匹配...")
                     for win in existing_windows:
                         similarity = difflib.SequenceMatcher(None, app_title.lower(), win.title.lower()).ratio()
                         logger.debug(f"    - Comparing '{app_title}' with '{win.title}': {similarity:.2f}")
                         # Use the similarity threshold from config
                         if similarity > WINDOW_TITLE_SIMILARITY_THRESHOLD and similarity > highest_similarity:
                             highest_similarity = similarity
                             best_match_window = win

                     if best_match_window:
                         logger.debug(f"  - 找到最匹配的窗口 (标题: '{best_match_window.title}', 相似度: {highest_similarity:.2f})，尝试聚焦...")

                # If a best match window was found (either exact or fuzzy)
                if best_match_window:
                    found_existing = True
                    try:
                        logger.debug(f"  - 尝试使用 pygetwindow.restore() 和 activate() 对窗口 '{best_match_window.title}' (HWND: {best_match_window._hWnd})...")
                        # Check if minimized before trying to restore
                        if best_match_window.isMinimized:
                             best_match_window.restore()
                             # Add a small delay after restoring to allow the window to be ready for activation
                             time.sleep(RESTORE_DELAY_SECONDS)
                        best_match_window.activate()
                        logger.info("  - 窗口聚焦尝试成功。")
                    except Exception as focus_e:
                        logger.warning(f"  - 使用 pygetwindow 聚焦现有窗口 '{best_match_window.title}' 时发生错误: {focus_e}", exc_info=True)
                        # Fallback to Windows API calls if pygetwindow failed
                        try:
                            hwnd = best_match_window._hWnd
                            logger.debug(f"  - 尝试使用 ShowWindow(SW_RESTORE) 和 SetForegroundWindow API 对 HWND {hwnd}...")
                            # Ensure window is restored (not minimized or maximized)
                            ShowWindow(hwnd, SW_RESTORE)
                            # Bring window to the foreground and activate it
                            SetForegroundWindow(hwnd)
                            logger.info("  - API 聚焦尝试成功。")
                        except Exception as api_focus_e:
                             logger.error(f"  - API 聚焦尝试失败对 HWND {hwnd}: {api_focus_e}. 可能原因：权限不足或窗口不可聚焦。", exc_info=True)
                             failed_count += 1
                else:
                    logger.info("  - 未找到可用的现有窗口进行聚焦（精确或相似标题匹配失败）。")

            # --- If no existing window was found or activated successfully, try to start the application ---
            if not found_existing:
                logger.info("  - 未找到可用的现有窗口或聚焦失败，尝试启动新实例...")
                try:
                    # For browsers, simply start the executable. Rely on browser's own session restore.
                    if is_browser:
                        logger.info(f"  - 识别为浏览器 ({os.path.basename(app_path)})，启动可执行文件，依赖浏览器自身会话恢复...")
                        subprocess.Popen([app_path])
                        logger.info(f"  - 浏览器 '{app_title}' 启动命令成功。")
                    # For other applications
                    else:
                        logger.info("  - 启动应用程序...")
                        subprocess.Popen([app_path])
                        logger.info(f"  - 应用程序 '{app_title}' 启动命令成功。")

                    # Note: If we had collected URLs for browsers, we would pass them here
                    # command = [app_path] + urls # Example if URLs were collected

                except FileNotFoundError:
                     logger.error(f"  - 启动应用程序失败: 找不到可执行文件 {app_path}")
                     self.update_status("启动失败！找不到可执行文件。")
                     messagebox.showerror("启动失败", f"无法找到可执行文件:\n{app_path}", parent=self.root)
                except Exception as e:
                     logger.error(f"  - 启动应用程序时发生意外错误: {e}", exc_info=True)
                     self.update_status("启动失败！")
                     messagebox.showerror("启动失败", f"启动应用程序时发生错误:\n{e}", parent=self.root)
            restored_count += 1 # Count even if just started a new instance

        except Exception as outer_e:
            logger.error(f"恢复 '{app_title}' 时发生意外错误: {outer_e}", exc_info=True)
            failed_count += 1

    logger.info(f"\n会话恢复完成。成功尝试处理 {restored_count} 个条目，失败 {failed_count} 个。")
    if failed_count > 0:
         logger.warning("部分条目恢复失败，请检查日志了解详情。")


# --- GUI Application ---

class SessionManagerApp:
    def __init__(self, root):
        self.root = root
        root.title("会话管理器")
        root.geometry("800x600") # Adjusted size again
        root.minsize(600, 500) # Set a minimum size

        # --- Add Window Icon ---
        try:
            # Assume icon file is in the same directory as the script/executable
            icon_path = os.path.join(script_dir, "app_icon.ico") # <-- 请将 "app_icon.ico" 替换为您实际的图标文件名
            if os.path.exists(icon_path):
                root.iconbitmap(icon_path)
                logger.info(f"窗口图标已设置为: {icon_path}")
            else:
                logger.warning(f"未找到窗口图标文件: {icon_path}")
        except Exception as e:
            logger.error(f"设置窗口图标时发生错误: {e}", exc_info=True)
        # --- End Add Window Icon ---


        # --- Internal Data ---
        # Stores all sessions loaded from the file: {"session_name": [session_items_list], ...}
        self.all_sessions_data = {}
        # Stores the session items currently displayed in the Treeview (the selected session)
        self.current_session_items = []
        # Stores the name of the currently selected session
        self.current_session_name = ""


        # --- Layout Frames ---
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)

        # Top frame for session selection and action buttons
        top_frame = ttk.Frame(main_frame)
        top_frame.pack(pady=5, fill=tk.X)

        # Frame for session data display (middle)
        data_frame = ttk.LabelFrame(main_frame, text="会话条目", padding="10")
        data_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        # Frame for log output (bottom)
        log_frame = ttk.LabelFrame(main_frame, text="日志输出", padding="10")
        log_frame.pack(pady=5, fill=tk.BOTH, expand=True)

        # --- Create Widgets ---
        # Top Frame Widgets
        ttk.Label(top_frame, text="选择会话:").grid(row=0, column=0, padx=(0, 5), pady=5, sticky=tk.W)
        self.session_selector = ttk.Combobox(top_frame, state="readonly", width=30) # Added width
        self.session_selector.grid(row=0, column=1, padx=(0, 15), pady=5, sticky=(tk.W, tk.E))
        self.session_selector.bind("<<ComboboxSelected>>", self.on_session_selected) # Bind selection event

        self.save_button = ttk.Button(top_frame, text="保存当前会话...", command=self.on_save_click)
        self.save_button.grid(row=0, column=2, padx=5, pady=5)

        self.restore_button = ttk.Button(top_frame, text="恢复选中会话", command=self.on_restore_click)
        self.restore_button.grid(row=0, column=3, padx=5, pady=5)

        self.refresh_data_button = ttk.Button(top_frame, text="刷新列表", command=self.on_refresh_data_click) # Renamed Load to Refresh
        self.refresh_data_button.grid(row=0, column=4, padx=5, pady=5)

        # Add some padding between buttons
        top_frame.grid_columnconfigure(0, weight=0) # Label column - no stretch
        top_frame.grid_columnconfigure(1, weight=1) # Combobox column - stretches
        top_frame.grid_columnconfigure(2, weight=0) # Button column - no stretch
        top_frame.grid_columnconfigure(3, weight=0) # Button column - no stretch
        top_frame.grid_columnconfigure(4, weight=0) # Button column - no stretch
        # Add dummy columns for spacing if needed, or use padx/ipadx

        # Data Frame Widgets (Treeview and its buttons)
        self.data_tree = ttk.Treeview(data_frame, columns=("Type", "Title", "Path"), show="headings", selectmode='extended') # Allow selecting multiple items
        self.data_tree.heading("Type", text="类型", anchor=tk.CENTER)
        self.data_tree.heading("Title", text="标题")
        self.data_tree.heading("Path", text="路径")

        # Configure column widths and stretching (adjusting initial widths)
        # Make 'Title' and 'Path' columns stretch
        self.data_tree.column("Type", anchor=tk.CENTER, stretch=tk.NO, width=80, minwidth=60)
        self.data_tree.column("Title", stretch=tk.YES, minwidth=150)
        self.data_tree.column("Path", stretch=tk.YES, minwidth=200)

        # Scrollbars for Treeview
        data_yscroll = ttk.Scrollbar(data_frame, orient=tk.VERTICAL, command=self.data_tree.yview)
        data_xscroll = ttk.Scrollbar(data_frame, orient=tk.HORIZONTAL, command=self.data_tree.xview)
        self.data_tree.configure(yscrollcommand=data_yscroll.set, xscrollcommand=data_xscroll.set)

        # Use grid for Treeview and its scrollbars
        self.data_tree.grid(row=0, column=0, sticky='nsew')
        data_yscroll.grid(row=0, column=1, sticky='ns')
        data_xscroll.grid(row=1, column=0, sticky='ew')

        # Configure data frame grid to make Treeview expand
        data_frame.grid_columnconfigure(0, weight=1)
        data_frame.grid_rowconfigure(0, weight=1)

        # Buttons below the Treeview for managing items
        item_management_frame = ttk.Frame(data_frame)
        # Use grid within this frame
        item_management_frame.grid(row=2, column=0, pady=(5,0), sticky=tk.W) # Place below treeview and xscroll

        self.delete_selected_button = ttk.Button(item_management_frame, text="删除选中条目", command=self.on_delete_selected_click)
        self.delete_selected_button.grid(row=0, column=0, padx=(0, 5))

        self.clear_current_session_button = ttk.Button(item_management_frame, text="清空当前会话", command=self.on_clear_current_session_click)
        self.clear_current_session_button.grid(row=0, column=1, padx=(0, 5))

        self.delete_session_button = ttk.Button(item_management_frame, text="删除当前会话", command=self.on_delete_session_click)
        self.delete_session_button.grid(row=0, column=2, padx=(0, 5))

        self.open_folder_button = ttk.Button(item_management_frame, text="打开数据目录", command=self.on_open_folder_click)
        self.open_folder_button.grid(row=0, column=3, padx=(0, 5))


        # Log Frame Widgets
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=8, wrap=tk.WORD, font=('Arial', 9)) # Changed font to Arial, adjusted height.
        self.log_text.grid(row=0, column=0, sticky='nsew')

        # Configure log frame grid to make Text widget expand
        log_frame.grid_columnconfigure(0, weight=1)
        log_frame.grid_rowconfigure(0, weight=1)

        # Status bar
        self.status_label = ttk.Label(root, text="启动中...", relief=tk.SUNKEN, anchor=tk.W)
        self.status_label.pack(side=tk.BOTTOM, fill=tk.X)

        # --- Add Handlers ---
        # Add the custom handler to the logger
        self.text_widget_handler = TextWidgetHandler(self.log_text)
        self.text_widget_handler.setLevel(logging.INFO) # Log INFO level and above to GUI
        self.text_widget_handler.setFormatter(formatter)
        logger.addHandler(self.text_widget_handler)

        # --- Initial Setup ---
        logger.info("会话管理器应用程序已启动。")
        logger.info(f"配置文件: {CONFIG_FILE}")
        logger.info(f"会话数据文件: {SESSION_DATA_FILE}")
        logger.info(f"日志文件: {log_file_path}")
        self.update_status("应用程序已启动")

        # Load all sessions on startup and populate the session selector
        self.load_and_populate_sessions()


        # --- Bind events ---
        # Double click on Treeview item
        self.data_tree.bind("<Double-1>", self.on_item_double_click)

        # Right click (Context Menu) on Treeview
        # '<Button-3>' for Windows, '<Button-2>' for macOS
        if platform.system() == "Windows":
             self.data_tree.bind("<Button-3>", self.show_context_menu)
        else: # For other systems like Linux/macOS
             self.data_tree.bind("<Button-2>", self.show_context_menu)

        # Create the context menu
        self.context_menu = tk.Menu(root, tearoff=0)
        self.context_menu.add_command(label="打开/切换到此应用", command=self.context_open_item)
        self.context_menu.add_command(label="删除选中条目", command=self.context_delete_selected)


    def update_status(self, message):
        """Updates the status bar message."""
        self.status_label.config(text=message)
        # logger.debug(f"状态更新: {message}") # Avoid excessive status logging unless needed

    def log_message(self, level, message):
        """Helper to log messages to both file/console and GUI."""
        if level == 'info':
            logger.info(message)
        elif level == 'warning':
            logger.warning(message)
        elif level == 'error':
            logger.error(message)
        elif level == 'debug':
             logger.debug(message)
        elif level == 'critical':
             logger.critical(message)

    def load_and_populate_sessions(self):
        """Loads all sessions from file and populates the session selector."""
        self.update_status("正在加载所有会话...")
        self.log_message('info', "加载所有会话...")
        self.all_sessions_data = load_all_sessions()

        # --- Start of Fix ---
        # Check if the loaded data is a list (old format) and convert it
        if isinstance(self.all_sessions_data, list):
            if self.all_sessions_data: # If the list is not empty
                self.log_message('warning', "检测到旧版会话数据格式 (列表)。正在将其迁移到默认会话。")
                # Put the list data under the default session name
                self.all_sessions_data = {DEFAULT_SESSION_NAME: self.all_sessions_data}
                # Optionally, save the migrated data back in the new format
                try:
                    save_all_sessions(self.all_sessions_data)
                    self.log_message('info', "旧版会话数据已迁移并保存为默认会话。")
                except Exception as e:
                    self.log_message('error', f"迁移旧版会话数据并保存时发生错误: {e}", exc_info=True)
            else: # If the list is empty
                self.log_message('info', "会话文件为空列表，初始化为空会话数据。")
                self.all_sessions_data = {}
        # --- End of Fix ---


        session_names = list(self.all_sessions_data.keys())
        # Ensure there is at least the default session if no sessions are loaded
        if not session_names:
             self.all_sessions_data[DEFAULT_SESSION_NAME] = []
             session_names = [DEFAULT_SESSION_NAME]
             # No need to save immediately, it will be saved on the first "Save" click

        self.session_selector['values'] = session_names

        # Select the default session if it exists, otherwise select the first one
        if DEFAULT_SESSION_NAME in session_names:
            self.session_selector.set(DEFAULT_SESSION_NAME)
        elif session_names:
            self.session_selector.set(session_names[0])
        else:
             self.session_selector.set("") # Should not happen if default session is ensured


        # Trigger the selection handler to populate the treeview with the initially selected session
        self.on_session_selected(None) # Pass None as event

        self.update_status(f"已加载 {len(self.all_sessions_data)} 个会话。")
        self.log_message('info', f"会话加载完成。共 {len(self.all_sessions_data)} 个会话。")


    def populate_data_tree(self, session_items):
        """Clears and populates the Treeview with items from a specific session."""
        # Clear existing items
        for item in self.data_tree.get_children():
            self.data_tree.delete(item)

        if not session_items:
             self.log_message('info', "当前选中的会话没有条目可显示。")
             return

        # Populate with new data
        for item in session_items:
            item_type = item.get("type", "未知") # Use saved type
            title = item.get('title', 'N/A')
            path = item.get('path', 'N/A')
            # We can store the original data item (or its index) in the Treeview tag
            # to easily retrieve it later for deletion/editing.
            # Storing the whole dict is easier for now.
            self.data_tree.insert("", tk.END, values=(item_type, title, path), tags=(json.dumps(item),)) # Store as JSON string in tag


        self.log_message('info', f"Treeview 已加载 {len(session_items)} 个条目。")


    def on_session_selected(self, event):
        """Handler for when a session is selected from the dropdown."""
        self.current_session_name = self.session_selector.get()
        self.log_message('info', f"选中会话: '{self.current_session_name}'")
        if self.current_session_name in self.all_sessions_data:
            self.current_session_items = self.all_sessions_data[self.current_session_name]
            self.populate_data_tree(self.current_session_items)
            self.update_status(f"显示会话: '{self.current_session_name}'")
        else:
            self.current_session_items = []
            self.populate_data_tree([]) # Clear the treeview
            self.update_status("未选中有效会话")
            self.log_message('warning', f"选中的会话名称 '{self.current_session_name}' 不存在。")


    def on_save_click(self):
        """Handles Save Session button click."""
        session_name = simpledialog.askstring("保存会话", "请输入会话名称:", initialvalue=DEFAULT_SESSION_NAME, parent=self.root) # Added parent
        if session_name:
            session_name = session_name.strip() # Remove leading/trailing whitespace
            if not session_name:
                messagebox.showwarning("无效名称", "会话名称不能为空。", parent=self.root)
                self.log_message('warning', "用户尝试使用空名称保存会话。")
                self.update_status("保存失败：名称无效。")
                return

            # Optional: Check for invalid characters in session name
            # This might depend on the file system or other constraints, but for now, keep it simple.

            self.update_status(f"正在保存会话 '{session_name}'...")
            self.log_message('info', f"点击：保存当前会话为 '{session_name}'")
            try:
                current_session_items = collect_session_data_core()
                # Add or update the session data
                self.all_sessions_data[session_name] = current_session_items
                save_all_sessions(self.all_sessions_data)
                self.load_and_populate_sessions() # Reload and select the new/updated session
                self.session_selector.set(session_name) # Ensure the newly saved session is selected
                self.update_status(f"会话 '{session_name}' 保存完成。共记录 {len(current_session_items)} 个条目。")
                self.log_message('info', f"会话 '{session_name}' 保存成功。")
            except Exception as e:
                self.log_message('error', f"保存会话 '{session_name}' 失败: {e}")
                self.update_status(f"保存会话 '{session_name}' 失败！")
                messagebox.showerror("保存失败", f"保存会话时发生错误: {e}", parent=self.root)
        else:
            self.log_message('info', "用户取消保存会话。")
            self.update_status("操作取消。")


    def on_restore_click(self):
        """Handles Restore Session button click."""
        if not self.current_session_name:
             messagebox.showwarning("没有选中会话", "请先在下拉列表中选择一个要恢复的会话。", parent=self.root)
             self.log_message('warning', "用户尝试恢复，但没有选中会话。")
             self.update_status("请选择要恢复的会话。")
             return

        if not self.current_session_items:
            messagebox.showinfo("会话为空", f"选中的会话 '{self.current_session_name}' 没有条目可恢复。", parent=self.root)
            self.log_message('info', f"用户尝试恢复会话 '{self.current_session_name}'，但该会话为空。")
            self.update_status(f"会话 '{self.current_session_name}' 为空。")
            return

        confirm = messagebox.askyesno("确认恢复", f"确定要恢复会话 '{self.current_session_name}' 吗？这将尝试启动或聚焦列表中的应用和浏览器。", parent=self.root)
        if confirm:
            self.update_status(f"正在尝试恢复会话 '{self.current_session_name}'...")
            self.log_message('info', f"点击：恢复会话 '{self.current_session_name}'")
            try:
                 restore_specific_session_core(self.current_session_items)
                 self.update_status(f"会话 '{self.current_session_name}' 恢复尝试完成。请检查日志了解详情。")
                 self.log_message('info', f"会话 '{self.current_session_name}' 恢复尝试完成。")
            except Exception as e:
                self.log_message('error', f"恢复会话 '{self.current_session_name}' 失败: {e}")
                self.update_status(f"恢复会话 '{self.current_session_name}' 失败！")
                messagebox.showerror("恢复失败", f"恢复会话时发生错误: {e}", parent=self.root)
        else:
            self.log_message('info', "用户取消恢复操作。")
            self.update_status("操作取消。")


    def on_refresh_data_click(self):
        """Handles Refresh List button click - reloads all sessions and displays the current one."""
        self.load_and_populate_sessions() # This reloads all sessions and updates the displayed session


    def on_item_double_click(self, event):
        """Handles double click on a Treeview item - attempts to launch/activate the app."""
        # Get the item ID at the click position
        item_id = self.data_tree.identify_row(event.y)
        if not item_id:
            return # No item was clicked

        # Ensure the item is selected when double-clicked for consistency
        self.data_tree.selection_set(item_id)
        # Set focus to the item
        self.data_tree.focus(item_id)

        # Get the data associated with the clicked item (stored as JSON string in tags)
        item_tag_json = self.data_tree.item(item_id, 'tags')[0]
        item_data = json.loads(item_tag_json) # Load the JSON string back into a dictionary

        app_path = item_data.get("path")
        app_title = item_data.get("title", "未知应用")

        if not app_path or not os.path.exists(app_path):
            messagebox.showwarning("无法打开", f"无法找到或打开路径:\n{app_path}", parent=self.root)
            self.log_message('warning', f"用户双击尝试打开不存在的路径: {app_path}")
            return

        # No confirmation dialog for double-click, assume user intends to open
        self.update_status(f"正在尝试打开/切换到 '{app_title}'...")
        self.log_message('info', f"用户双击尝试打开/切换到: '{app_title}' ({app_path})")
        try:
            # Attempt to find and activate existing window first
            all_current_windows = gw.getAllWindows()
            existing_windows = [
                win for win in all_current_windows
                if win.visible and win.title
                and get_process_path_from_hwnd(win._hWnd) == app_path
            ]

            activated = False
            if existing_windows:
                 try:
                     logger.debug(f"  - 找到现有窗口，尝试 pygetwindow.restore() 和 activate() 对 '{existing_windows[0].title}'...")
                     if existing_windows[0].isMinimized:
                         existing_windows[0].restore()
                         time.sleep(RESTORE_DELAY_SECONDS)
                     existing_windows[0].activate()
                     self.log_message('info', f"已切换到现有窗口: '{existing_windows[0].title}'")
                     activated = True
                 except Exception as e:
                     self.log_message('warning', f"尝试切换到现有窗口失败: {e}", exc_info=True)
                     try:
                        hwnd = existing_windows[0]._hWnd
                        logger.debug(f"  - 尝试使用 ShowWindow(SW_RESTORE) 和 SetForegroundWindow API 对 HWND {hwnd}...")
                        ShowWindow(hwnd, SW_RESTORE)
                        SetForegroundWindow(hwnd)
                        self.log_message('info', f"已切换到现有窗口 (API): '{existing_windows[0].title}'")
                        activated = True
                     except Exception as api_e:
                        self.log_message('error', f"API 尝试切换到现有窗口失败: {api_e}", exc_info=True)

            if not activated:
                # If no existing window found or activation failed, start a new instance
                self.log_message('info', f"未找到现有窗口或切换失败，启动新实例: {app_path}")
                subprocess.Popen([app_path])
                self.log_message('info', f"应用程序 '{app_title}' 启动命令成功。")

            self.update_status(f"已尝试打开/切换到 '{app_title}'。")

        except FileNotFoundError:
             self.log_message('error', f"启动应用程序失败: 找不到可执行文件 {app_path}")
             self.update_status("启动失败！找不到可执行文件。")
             messagebox.showerror("启动失败", f"无法找到可执行文件:\n{app_path}", parent=self.root)
        except Exception as e:
             self.log_message('error', f"启动应用程序时发生意外错误: {e}", exc_info=True)
             self.update_status("启动失败！")
             messagebox.showerror("启动失败", f"启动应用程序时发生错误:\n{e}", parent=self.root)


    def show_context_menu(self, event):
        """Displays the context menu on right-click."""
        # Select the item under the cursor
        item_id = self.data_tree.identify_row(event.y)
        if item_id:
            # self.data_tree.selection_set(item_id) # Select the item
            # self.data_tree.focus(item_id) # Set focus to the item (optional)
            try:
                self.context_menu.tk_popup(event.x_root, event.y_root)
            finally:
                # make sure to release the grab (Tk 8.0+).
                self.context_menu.grab_release()

    def context_open_item(self):
        """Handler for 'Open/Switch to' from context menu. Calls on_item_double_click logic."""
        selected_item_ids = self.data_tree.selection()
        if selected_item_ids:
             # Just handle the first selected item for the 'Open/Switch' action
             item_id = selected_item_ids[0]
             item_tag_json = self.data_tree.item(item_id, 'tags')[0]
             item_data = json.loads(item_tag_json)
             # Simulate the double-click event data structure for on_item_double_click
             # This is a bit hacky, a better way would be to refactor the core logic
             # out of on_item_double_click into a separate function.
             # For simplicity now, we'll call the core logic directly.
             self._open_item_core(item_data)

    def _open_item_core(self, item_data):
        """Core logic to open/switch to an application based on its data."""
        app_path = item_data.get("path")
        app_title = item_data.get("title", "未知应用")

        if not app_path or not os.path.exists(app_path):
            messagebox.showwarning("无法打开", f"无法找到或打开路径:\n{app_path}", parent=self.root)
            self.log_message('warning', f"_open_item_core 尝试打开不存在的路径: {app_path}")
            return

        self.update_status(f"正在尝试打开/切换到 '{app_title}'...")
        self.log_message('info', f"_open_item_core 尝试打开/切换到: '{app_title}' ({app_path})")
        try:
            all_current_windows = gw.getAllWindows()
            existing_windows = [
                win for win in all_current_windows
                if win.visible and win.title
                and get_process_path_from_hwnd(win._hWnd) == app_path
            ]

            activated = False
            if existing_windows:
                 try:
                     logger.debug(f"  - 找到现有窗口，尝试 pygetwindow.restore() 和 activate() 对 '{existing_windows[0].title}'...")
                     if existing_windows[0].isMinimized:
                         existing_windows[0].restore()
                         time.sleep(RESTORE_DELAY_SECONDS)
                     existing_windows[0].activate()
                     self.log_message('info', f"已切换到现有窗口: '{existing_windows[0].title}'")
                     activated = True
                 except Exception as e:
                     self.log_message('warning', f"尝试切换到现有窗口失败: {e}", exc_info=True)
                     try:
                        hwnd = existing_windows[0]._hWnd
                        logger.debug(f"  - 尝试使用 ShowWindow(SW_RESTORE) 和 SetForegroundWindow API 对 HWND {hwnd}...")
                        ShowWindow(hwnd, SW_RESTORE)
                        SetForegroundWindow(hwnd)
                        self.log_message('info', f"已切换到现有窗口 (API): '{existing_windows[0].title}'")
                        activated = True
                     except Exception as api_e:
                        self.log_message('error', f"API 尝试切换到现有窗口失败: {api_e}", exc_info=True)

            if not activated:
                self.log_message('info', f"未找到现有窗口或切换失败，启动新实例: {app_path}")
                subprocess.Popen([app_path])
                self.log_message('info', f"应用程序 '{app_title}' 启动命令成功。")

            self.update_status(f"已尝试打开/切换到 '{app_title}'。")

        except FileNotFoundError:
             self.log_message('error', f"启动应用程序失败: 找不到可执行文件 {app_path}")
             self.update_status("启动失败！找不到可执行文件。")
             messagebox.showerror("启动失败", f"无法找到可执行文件:\n{app_path}", parent=self.root)
        except Exception as e:
             self.log_message('error', f"启动应用程序时发生意外错误: {e}", exc_info=True)
             self.update_status("启动失败！")
             messagebox.showerror("启动失败", f"启动应用程序时发生错误:\n{e}", parent=self.root)


    def context_delete_selected(self):
         """Handler for 'Delete Selected Items' from context menu. Calls on_delete_selected_click."""
         self.on_delete_selected_click() # Reuse the existing button handler logic


    def on_delete_selected_click(self):
        """Handles Delete Selected Items button click."""
        selected_item_ids = self.data_tree.selection() # Get IDs of selected items in the treeview
        if not selected_item_ids:
            messagebox.showwarning("没有选中项", "请在列表中选择要删除的条目。", parent=self.root)
            self.log_message('warning', "用户尝试删除选中条目，但没有选中项。")
            return

        # Get the data dictionaries of the items to delete from the Treeview tags (JSON strings)
        items_to_delete_data_json = [self.data_tree.item(item_id, 'tags')[0] for item_id in selected_item_ids]
        # Convert the JSON strings back to dictionaries
        items_to_delete_data = [json.loads(item_json) for item_json in items_to_delete_data_json]


        confirm = messagebox.askyesno("确认删除", f"确定要从当前会话中删除选中的 {len(items_to_delete_data)} 个条目吗？此操作将立即保存。", parent=self.root)
        if confirm:
            self.update_status("正在删除选中条目...")
            self.log_message('info', f"点击：从当前会话删除选中条目 ({len(items_to_delete_data)} 个)")

            # Create a new list for the current session excluding the items to delete
            # Compare the data dictionaries
            new_current_session_items = [item for item in self.current_session_items if item not in items_to_delete_data]

            # Check if anything was actually removed (handles potential matching issues)
            if len(new_current_session_items) < len(self.current_session_items):
                 self.current_session_items = new_current_session_items # Update internal data

                 # Update the data in the all_sessions_data dictionary
                 if self.current_session_name in self.all_sessions_data:
                     self.all_sessions_data[self.current_session_name] = self.current_session_items
                     save_all_sessions(self.all_sessions_data) # Save the updated data

                     # Refresh the Treeview to reflect the changes
                     self.populate_data_tree(self.current_session_items)

                     deleted_count = len(items_to_delete_data)
                     self.log_message('info', f"已从会话 '{self.current_session_name}' 删除 {deleted_count} 个条目并保存。")
                     self.update_status(f"已从会话 '{self.current_session_name}' 删除 {deleted_count} 个条目并保存。")
                     messagebox.showinfo("删除成功", f"已从会话 '{self.current_session_name}' 删除选中的 {deleted_count} 个条目，并已保存更改。", parent=self.root)
                 else:
                      self.log_message('error', f"尝试删除条目时，当前会话 '{self.current_session_name}' 不存在于加载的所有会话中。")
                      self.update_status("删除失败：会话状态异常。")
                      messagebox.showerror("删除失败", "当前会话状态异常，无法删除条目。", parent=self.root)

            else:
                 self.log_message('warning', "未能删除任何选中项，可能匹配有问题或会话为空。")
                 self.update_status("删除失败：未能匹配选中项。")
                 messagebox.showwarning("删除失败", "未能删除任何选中项。请尝试刷新列表。", parent=self.root)

        else:
            self.log_message('info', "用户取消删除选中条目操作。")
            self.update_status("操作取消。")

    def on_clear_current_session_click(self):
        """Handles Clear Current Session button click."""
        if not self.current_session_name:
             messagebox.showwarning("没有选中会话", "请先在下拉列表中选择一个要清空的会话。", parent=self.root)
             self.log_message('warning', "用户尝试清空当前会话，但没有选中会话。")
             self.update_status("请选择要清空的会话。")
             return

        if not self.current_session_items:
            messagebox.showinfo("会话已空", f"当前会话 '{self.current_session_name}' 已经是空的了。", parent=self.root)
            self.log_message('info', f"用户尝试清空会话 '{self.current_session_name}'，但该会话已空。")
            self.update_status(f"会话 '{self.current_session_name}' 已空。")
            return

        confirm = messagebox.askyesno("确认清空当前会话", f"确定要清空当前会话 '{self.current_session_name}' 中的所有条目吗？此操作将立即保存，但不会删除会话本身。", parent=self.root)
        if confirm:
            self.update_status(f"正在清空会话 '{self.current_session_name}'...")
            self.log_message('info', f"点击：清空当前会话 '{self.current_session_name}'")

            # Clear the internal data for the current session
            self.current_session_items = []

            # Update the data in the all_sessions_data dictionary
            self.all_sessions_data[self.current_session_name] = self.current_session_items

            # Save the entire sessions data back to the file
            save_all_sessions(self.all_sessions_data)

            # Refresh the Treeview to reflect the changes (it will now be empty for this session)
            self.populate_data_tree(self.current_session_items)

            self.log_message('info', f"会话 '{self.current_session_name}' 已清空并保存。")
            self.update_status(f"会话 '{self.current_session_name}' 已清空并保存。")
            messagebox.showinfo("清空完成", f"会话 '{self.current_session_name}' 已清空。", parent=self.root)
        else:
            self.log_message('info', "用户取消清空当前会话操作。")
            self.update_status("操作取消。")

    def on_delete_session_click(self):
        """Handles Delete Current Session button click."""
        if not self.current_session_name:
             messagebox.showwarning("没有选中会话", "请先在下拉列表中选择一个要删除的会话。", parent=self.root)
             self.log_message('warning', "用户尝试删除当前会话，但没有选中会话。")
             self.update_status("请选择要删除的会话。")
             return

        if self.current_session_name == DEFAULT_SESSION_NAME and len(self.all_sessions_data) > 1:
             # Optional: Prevent deleting the default session if other sessions exist, to ensure there's always one
             # Or allow it, but make sure a new default is created or another session is selected.
             pass # For now, allow deleting the default session


        confirm = messagebox.askyesno("确认删除会话", f"确定要永久删除会话 '{self.current_session_name}' 吗？此操作不可撤销！", parent=self.root)
        if confirm:
            self.update_status(f"正在删除会话 '{self.current_session_name}'...")
            self.log_message('info', f"点击：删除会话 '{self.current_session_name}'")

            if self.current_session_name in self.all_sessions_data:
                del self.all_sessions_data[self.current_session_name] # Delete the session from the dictionary
                save_all_sessions(self.all_sessions_data) # Save the updated data

                # Reset current session variables
                self.current_session_items = []
                self.current_session_name = ""

                # Reload and populate sessions to update the combobox and treeview
                self.load_and_populate_sessions()

                self.log_message('info', f"会话已删除并保存。")
                self.update_status(f"会话已删除并保存。")
                messagebox.showinfo("删除完成", f"会话 '{self.current_session_name}' 已删除。", parent=self.root)
            else:
                 self.log_message('warning', f"尝试删除的会话 '{self.current_session_name}' 不存在。")
                 self.update_status(f"删除失败：会话 '{self.current_session_name}' 不存在。")
                 messagebox.showwarning("删除失败", f"会话 '{self.current_session_name}' 不存在。", parent=self.root)

        else:
            self.log_message('info', "用户取消删除会话操作。")
            self.update_status("操作取消。")


    def on_open_folder_click(self):
        """Handles Open Data Folder button click."""
        self.log_message('info', "点击：打开数据目录")
        session_data_folder = os.path.dirname(SESSION_DATA_FILE)
        if not os.path.exists(session_data_folder):
            try:
                 os.makedirs(session_data_folder, exist_ok=True)
                 self.log_message('info', f"创建会话数据目录: {session_data_folder}")
            except Exception as e:
                 self.log_message('error', f"创建数据目录失败: {e}", exc_info=True)
                 self.update_status("创建数据目录失败！")
                 messagebox.showerror("错误", f"无法创建数据目录:\n{session_data_folder}\n错误: {e}", parent=self.root)
                 return


        try:
            # Use os.startfile for cross-platform (though this is Windows specific)
            # On Windows, this opens the folder in File Explorer
            os.startfile(session_data_folder)
            self.log_message('info', f"已打开会话数据目录: {session_data_folder}")
            self.update_status(f"已打开数据目录: {session_data_folder}")
        except FileNotFoundError:
             self.log_message('error', f"无法打开目录: {session_data_folder}. 目录不存在。", exc_info=True)
             self.update_status("无法打开数据目录！")
             messagebox.showerror("错误", f"无法打开会话数据所在的文件夹。\n目录不存在: {session_data_folder}", parent=self.root)
        except Exception as e:
            self.log_message('error', f"打开会话数据目录时发生错误: {e}", exc_info=True)
            self.update_status("打开数据目录失败！")
            messagebox.showerror("错误", f"打开会话数据所在的文件夹时发生错误: {e}", parent=self.root)


# --- Main Execution ---
if __name__ == "__main__":
    # Check if the script is run with command-line arguments (likely from Task Scheduler)
    # If so, execute the corresponding core function and exit.
    # Otherwise, launch the GUI application.
    # Working directory is implicitly the script's directory because of sys._MEIPASS or os.path.dirname(sys.argv[0])

    if len(sys.argv) > 1:
        command = sys.argv[1].lower()
        # Ensure core functions use the loaded configuration, including SESSION_DATA_FILE
        # We need to load config even in CLI mode
        config = load_config() # Load config here again for CLI mode

        if command == "--save":
            # In CLI save mode, save to the default session name
            logger.info("脚本以命令行保存模式启动。")
            all_sessions = load_all_sessions() # Load existing sessions
            current_session_items = collect_session_data_core() # Collect current session data
            all_sessions[DEFAULT_SESSION_NAME] = current_session_items # Update default session
            save_all_sessions(all_sessions) # Save all sessions back
            logger.info("命令行保存模式执行完毕。")
            sys.exit()

        elif command == "--restore":
            # In CLI restore mode, restore the default session
            logger.info("脚本以命令行恢复模式启动。")
            # Add a small delay to allow system to settle on startup if running this way
            startup_delay = config.get("startup_delay_seconds", 2) # Add startup delay config?
            if startup_delay > 0:
                 logger.info(f"等待 {startup_delay} 秒以允许系统启动...")
                 time.sleep(startup_delay)

            all_sessions = load_all_sessions() # Load all sessions
            session_to_restore = all_sessions.get(DEFAULT_SESSION_NAME) # Get the default session items

            if session_to_restore is not None:
                restore_specific_session_core(session_to_restore)
            else:
                logger.warning(f"在命令行恢复模式下找不到默认会话 '{DEFAULT_SESSION_NAME}'。")

            logger.info("命令行恢复模式执行完毕。")
            sys.exit()

        elif command == "--manage":
            # CLI --manage mode opens the data folder
            logger.info("脚本以命令行管理模式启动 (打开数据目录)。")
            session_data_folder = os.path.dirname(SESSION_DATA_FILE)
            try:
                 # Ensure directory exists before trying to open
                 if not os.path.exists(session_data_folder):
                      os.makedirs(session_data_folder, exist_ok=True)
                      logger.info(f"创建会话数据目录: {session_data_folder}")

                 os.startfile(session_data_folder)
                 logger.info(f"已从命令行打开会话数据目录: {session_data_folder}")
            except FileNotFoundError:
                 logger.error(f"从命令行无法打开目录: {session_data_folder}. 目录不存在。", exc_info=True)
            except Exception as e:
                 logger.error(f"从命令行打开会话数据目录时发生错误: {e}", exc_info=True)
            logger.info("命令行管理模式执行完毕。")
            sys.exit()

        else:
            logger.warning(f"未知命令行参数: {sys.argv[1]}。启动GUI。用法: python get_windows.py [--save | --restore | --manage]")
            # Fall through to GUI

    # No command-line arguments, launch the GUI
    logger.info("脚本以GUI模式启动。")
    root = tk.Tk()
    app = SessionManagerApp(root)
    root.mainloop()
