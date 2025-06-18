#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Windows会话管理器 - 一个用于保存和恢复Windows工作环境的工具
"""

import os
import sys
import argparse
import logging
import tkinter as tk
from tkinter import messagebox
import winshell
from pathlib import Path
import traceback

from session_manager.config import load_config, update_config, USER_DATA_DIR
from session_manager.core import SessionManager
from session_manager.gui import SessionManagerApp, GuiLogHandler
import session_manager.utils as utils

VERSION = "1.0.0"
APP_NAME = "Windows会话管理器"

def setup_logging(config):
    """设置日志记录"""
    log_handlers = []
    
    # 文件日志处理器
    try:
        file_handler = logging.FileHandler(
            config['log_file'], 
            encoding='utf-8', 
            mode='a'
        )
        file_formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        file_handler.setFormatter(file_formatter)
        log_handlers.append(file_handler)
    except Exception as e:
        print(f"警告: 无法设置文件日志: {e}")
    
    # 控制台日志处理器
    console = logging.StreamHandler()
    console_formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    console.setFormatter(console_formatter)
    log_handlers.append(console)
    
    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)
    
    # 清除现有处理器并添加新处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    for handler in log_handlers:
        root_logger.addHandler(handler)
    
    return root_logger

def create_shortcut():
    """创建桌面快捷方式"""
    try:
        desktop = winshell.desktop()
        shortcut_path = os.path.join(desktop, f"{APP_NAME}.lnk")
        
        if os.path.exists(shortcut_path):
            return True  # 已存在，无需创建
            
        target = sys.executable
        if target.endswith('python.exe') or target.endswith('pythonw.exe'):
            # 开发模式运行时
            script_path = os.path.abspath(__file__)
            icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
            
            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = target
                shortcut.arguments = f'"{script_path}"'
                shortcut.working_directory = os.path.dirname(script_path)
                if os.path.exists(icon):
                    shortcut.icon_location = (icon, 0)
        else:
            # 打包后的exe
            icon = target
            
            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = target
                shortcut.working_directory = os.path.dirname(target)
                shortcut.icon_location = (icon, 0)
        
        return True
    except Exception as e:
        logging.error(f"创建快捷方式失败: {e}")
        return False

def create_startup_shortcut(enable=True):
    """创建/删除开机启动快捷方式"""
    try:
        startup_folder = winshell.startup()
        shortcut_path = os.path.join(startup_folder, f"{APP_NAME}.lnk")
        
        if not enable:
            if os.path.exists(shortcut_path):
                os.remove(shortcut_path)
            return True
            
        target = sys.executable
        
        if target.endswith('python.exe') or target.endswith('pythonw.exe'):
            # 开发模式运行时
            script_path = os.path.abspath(__file__)
            icon = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
            
            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = target
                shortcut.arguments = f'"{script_path}" --minimized'
                shortcut.working_directory = os.path.dirname(script_path)
                if os.path.exists(icon):
                    shortcut.icon_location = (icon, 0)
        else:
            # 打包后的exe
            icon = target
            
            with winshell.shortcut(shortcut_path) as shortcut:
                shortcut.path = target
                shortcut.arguments = "--minimized"
                shortcut.working_directory = os.path.dirname(target)
                shortcut.icon_location = (icon, 0)
        
        return True
    except Exception as e:
        logging.error(f"创建开机启动快捷方式失败: {e}")
        return False

def parse_arguments():
    """解析命令行参数"""
    parser = argparse.ArgumentParser(description=f'{APP_NAME} - 一个用于保存和恢复Windows工作环境的工具')
    parser.add_argument('-v', '--version', action='store_true', help='显示版本信息')
    parser.add_argument('--minimized', action='store_true', help='以最小化方式启动')
    parser.add_argument('--restore', type=str, help='恢复指定的会话')
    parser.add_argument('--restore-last', action='store_true', help='恢复上次使用的会话')
    parser.add_argument('--save', type=str, help='保存当前窗口状态到指定会话')
    parser.add_argument('--create-desktop-shortcut', action='store_true', help='创建桌面快捷方式')
    parser.add_argument('--enable-autostart', action='store_true', help='启用开机自启动')
    parser.add_argument('--disable-autostart', action='store_true', help='禁用开机自启动')
    
    return parser.parse_args()

def handle_exception(exc_type, exc_value, exc_traceback):
    """处理未捕获的异常"""
    # 如果日志已初始化，则记录异常
    if logging.getLogger().handlers:
        logging.critical("未捕获异常:", exc_info=(exc_type, exc_value, exc_traceback))
    
    # 如果不是在控制台中运行，则显示错误对话框
    if sys.stderr.isatty():
        sys.__excepthook__(exc_type, exc_value, exc_traceback)
    else:
        error_msg = ''.join(traceback.format_exception(exc_type, exc_value, exc_traceback))
        tk.messagebox.showerror(f"{APP_NAME} 错误", 
                               f"程序遇到了未处理的错误，请将以下信息报告给开发者：\n\n{error_msg}")

def main():
    """主函数"""
    # 设置异常处理
    sys.excepthook = handle_exception
    
    # 解析命令行参数
    args = parse_arguments()
    
    # 显示版本信息
    if args.version:
        print(f"{APP_NAME} 版本 {VERSION}")
        sys.exit(0)
    
    # 加载配置
    config = load_config()
    
    # 设置日志
    logger = setup_logging(config)
    logger.info(f"启动 {APP_NAME} v{VERSION}")
    logger.info(f"用户数据目录: {USER_DATA_DIR}")
    
    # 创建桌面快捷方式
    if args.create_desktop_shortcut:
        success = create_shortcut()
        print(f"{'成功' if success else '失败'}创建桌面快捷方式")
        if not args.minimized and not args.restore and not args.restore_last and not args.save:
            sys.exit(0)
    
    # 处理自启动设置
    if args.enable_autostart:
        success = create_startup_shortcut(True)
        update_config({"startup": {"autostart": True}})
        print(f"{'成功' if success else '失败'}启用开机自启动")
        if not args.minimized and not args.restore and not args.restore_last and not args.save:
            sys.exit(0)
    
    if args.disable_autostart:
        success = create_startup_shortcut(False)
        update_config({"startup": {"autostart": False}})
        print(f"{'成功' if success else '失败'}禁用开机自启动")
        if not args.minimized and not args.restore and not args.restore_last and not args.save:
            sys.exit(0)
    
    # 实例化会话管理器
    session_manager = SessionManager(config["session_data_file"])
    
    # 处理命令行操作
    if args.save:
        # 保存会话
        from session_manager.core import collect_session_data_core
        session_data = collect_session_data_core(config)
        session_manager.set_session(args.save, session_data)
        session_manager.save_sessions()
        print(f"已保存会话: {args.save}")
        sys.exit(0)
    
    if args.restore:
        # 恢复会话
        session_name = args.restore
        session_data = session_manager.get_session(session_name)
        if session_data:
            from session_manager.core import restore_specific_session_core
            restore_specific_session_core(session_data, config)
            update_config({"startup": {"last_session": session_name}})
            print(f"已恢复会话: {session_name}")
        else:
            print(f"找不到会话: {session_name}")
        sys.exit(0)
    
    if args.restore_last:
        # 恢复上次会话
        session_name = config["startup"]["last_session"]
        if session_name:
            session_data = session_manager.get_session(session_name)
            if session_data:
                from session_manager.core import restore_specific_session_core
                restore_specific_session_core(session_data, config)
                print(f"已恢复上次会话: {session_name}")
            else:
                print(f"找不到上次会话: {session_name}")
        else:
            print("没有上次会话记录")
        sys.exit(0)
    
    # 启动GUI
    root = tk.Tk()
    root.title(f"{APP_NAME} v{VERSION}")
    
    # 设置图标
    icon_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "resources", "icon.ico")
    if os.path.exists(icon_path):
        root.iconbitmap(icon_path)
    
    # 创建应用实例
    app = SessionManagerApp(root, config, session_manager)
    
    # 添加 GUI 日志 handler
    gui_handler = GuiLogHandler(app)
    gui_handler.setLevel(logging.INFO)
    logging.getLogger().addHandler(gui_handler)
    
    # 如果配置了自动恢复上次会话
    if config["startup"]["restore_last_session"] and config["startup"]["last_session"]:
        session_name = config["startup"]["last_session"]
        session_data = session_manager.get_session(session_name)
        if session_data:
            logger.info(f"自动恢复上次会话: {session_name}")
            app.restore_session(session_name)
    
    # 如果指定最小化启动
    if args.minimized or config["startup"]["minimized"]:
        root.iconify()
        app.minimize_to_tray()
    
    # 启动主循环
    root.mainloop()

if __name__ == "__main__":
    main()
