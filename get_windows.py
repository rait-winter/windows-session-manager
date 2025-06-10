# =============================================
# 迁移计划：
# 本文件已精简为主入口，仅负责启动。
# =============================================

import tkinter as tk
from session_manager.config import load_config
from session_manager.core import SessionManager
from session_manager.gui import SessionManagerApp, GuiLogHandler
from session_manager.utils import is_window_relevant, is_browser_process, get_process_path_from_hwnd, get_browser_tabs
import logging

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s"
)

if __name__ == "__main__":
    config = load_config()
    session_manager = SessionManager(config["session_data_file"])
    root = tk.Tk()
    app = SessionManagerApp(root, config, session_manager)

    # 添加 GUI 日志 handler
    gui_handler = GuiLogHandler(app)
    gui_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(gui_handler)

    root.mainloop()
