"""
gui.py
会话管理器图形界面。
"""

import os
import sys
import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext
import logging
import threading
import time
import json
import queue
from datetime import datetime
from functools import partial
import webbrowser
from ttkthemes import ThemedTk
import keyboard
from PIL import Image, ImageTk, ImageDraw
import winshell
import pygetwindow as gw
from session_manager.utils import get_process_path_from_hwnd
import win32gui
import win32process
import psutil
import win32con

from . import config
from .core import collect_session_data, restore_session

# 日志记录器
logger = logging.getLogger(__name__)

# 全局样式常量
PADDING = 5
LARGE_PADDING = 10
BUTTON_WIDTH = 15
FONT = ("Segoe UI", 10)
TITLE_FONT = ("Segoe UI", 12, "bold")
HEADER_FONT = ("Segoe UI", 11, "bold")
DEFAULT_THEME = "vista"  # 可选: 'winnative', 'clam', 'alt', 'default', 'classic', 'vista', 'xpnative'

# 颜色方案
COLORS = {
    "light": {
        "bg": "#f0f0f0",
        "fg": "#333333",
        "button_bg": "#e1e1e1",
        "highlight_bg": "#dae5f4",
        "highlight_fg": "#2e5c8a",
        "session_bg": "#ffffff",
        "session_fg": "#333333",
        "border": "#cccccc",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
        "info": "#2196f3"
    },
    "dark": {
        "bg": "#2d2d2d",
        "fg": "#e0e0e0",
        "button_bg": "#444444",
        "highlight_bg": "#364859",
        "highlight_fg": "#81b3e0",
        "session_bg": "#383838",
        "session_fg": "#e0e0e0",
        "border": "#555555",
        "success": "#4caf50",
        "warning": "#ff9800",
        "error": "#f44336",
        "info": "#2196f3"
    }
}

class GuiLogHandler(logging.Handler):
    """将日志信息发送到GUI"""
    def __init__(self, app):
        super().__init__()
        self.app = app
        self.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.log_queue = queue.Queue()
        self.start_queue_listener()

    def emit(self, record):
        log_entry = self.format(record)
        self.log_queue.put((record.levelno, log_entry))
    
    def start_queue_listener(self):
        """启动一个线程监听日志队列"""
        def check_queue():
            try:
                while True:
                    try:
                        level, message = self.log_queue.get_nowait()
                        if hasattr(self.app, 'add_log_message'):
                            self.app.add_log_message(level, message)
                        self.log_queue.task_done()
                    except queue.Empty:
                        break
            except Exception as e:
                print(f"日志队列处理错误: {e}")
            finally:
                # 每100ms检查一次队列
                self.app.root.after(100, check_queue)
        
        # 开始首次检查
        self.app.root.after(100, check_queue)

class SessionManagerApp:
    def __init__(self, root, config, session_manager):
        """初始化GUI"""
        self.root = root
        self.config = config
        self.session_manager = session_manager
        
        # 设置初始会话
        self.current_session_items = []
        session_names = self.session_manager.get_session_names()
        if session_names:
            self.current_session_name = session_names[0]
            self.current_session_items = self.session_manager.get_session(self.current_session_name)
        else:
            self.current_session_name = self.session_manager.default_session_name
        
        # 设置主题
        self.setup_theme()
        
        # 设置图标
        self.setup_icons()

        # 美化界面
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('微软雅黑', 10), padding=6)
        style.configure('TLabel', font=('微软雅黑', 10))
        style.configure('Treeview.Heading', font=('微软雅黑', 10, 'bold'))

        # 菜单栏
        menubar = tk.Menu(self.root)
        file_menu = tk.Menu(menubar, tearoff=0)
        file_menu.add_command(label="导入会话", command=self.import_session)
        file_menu.add_command(label="导出会话", command=self.export_session)
        file_menu.add_separator()
        file_menu.add_command(label="退出", command=self.root.quit)
        menubar.add_cascade(label="文件", menu=file_menu)
        session_menu = tk.Menu(menubar, tearoff=0)
        session_menu.add_command(label="新建会话", command=self.create_session)
        session_menu.add_command(label="重命名会话", command=self.rename_session)
        session_menu.add_command(label="删除会话", command=self.delete_session)
        session_menu.add_command(label="清空会话", command=self.clear_session)
        menubar.add_cascade(label="会话", menu=session_menu)
        
        # 添加调试菜单
        debug_menu = tk.Menu(menubar, tearoff=0)
        debug_menu.add_command(label="枚举所有窗口", command=self.enum_all_windows_and_children)
        debug_menu.add_command(label="显示主要窗口", command=self.enum_filtered_windows)
        debug_menu.add_command(label="查找特殊应用窗口", command=self.find_special_app_windows)
        debug_menu.add_command(label="列出所有进程", command=self.list_all_processes)
        debug_menu.add_separator()
        debug_menu.add_command(label="刷新窗口列表", command=self.refresh_windows)
        menubar.add_cascade(label="调试", menu=debug_menu)
        
        help_menu = tk.Menu(menubar, tearoff=0)
        help_menu.add_command(label="使用说明", command=self.show_help)
        help_menu.add_command(label="关于", command=self.show_about)
        menubar.add_cascade(label="帮助", menu=help_menu)
        self.root.config(menu=menubar)

        # 主体布局：左右分栏
        main_frame = ttk.Frame(root, padding="10")
        main_frame.pack(fill=tk.BOTH, expand=True)
        main_frame.columnconfigure(0, weight=1, minsize=180)
        main_frame.columnconfigure(1, weight=3)
        main_frame.rowconfigure(0, weight=1)
        main_frame.rowconfigure(1, weight=0)

        # 左侧会话列表
        left_frame = ttk.Frame(main_frame)
        left_frame.grid(row=0, column=0, sticky="nsew", padx=(0, 10))
        ttk.Label(left_frame, text="会话列表").pack(anchor="w")
        self.session_list = tk.Listbox(left_frame, font=('微软雅黑', 10), height=20)
        self.session_list.pack(fill=tk.BOTH, expand=True)
        self.session_list.bind("<<ListboxSelect>>", self.on_session_select)
        self.refresh_session_list()

        # 右侧应用列表
        right_frame = ttk.Frame(main_frame)
        right_frame.grid(row=0, column=1, sticky="nsew")
        ttk.Label(right_frame, text="当前会话应用").pack(anchor="w")
        
        # 使用Treeview代替原来的app_tree，重命名为window_listbox
        self.window_listbox = ttk.Treeview(right_frame, columns=("类型", "路径"), show="tree headings")
        self.window_listbox.heading("#0", text="标题/名称")
        self.window_listbox.heading("类型", text="类型")
        self.window_listbox.heading("路径", text="路径")
        self.window_listbox.column("#0", width=250, anchor=tk.W)
        self.window_listbox.column("类型", width=80, anchor=tk.CENTER)
        self.window_listbox.column("路径", width=350)
        self.window_listbox.pack(fill=tk.BOTH, expand=True)
        
        # 添加双击事件处理
        self.window_listbox.bind("<Double-1>", self.on_item_double_click)

        # 操作按钮区
        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=1, column=0, columnspan=2, pady=10, sticky="ew")
        ttk.Button(btn_frame, text="保存会话", command=self.save_session).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="恢复会话", command=self.restore_session).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="导入会话", command=self.import_session).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="导出会话", command=self.export_session).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="重命名", command=self.rename_session).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="删除", command=self.delete_session).pack(side="left", padx=5)
        ttk.Button(btn_frame, text="清空", command=self.clear_session).pack(side="left", padx=5)

        # 日志输出区
        log_frame = ttk.LabelFrame(root, text="日志输出", padding="10")
        log_frame.pack(fill=tk.BOTH, expand=False, padx=10, pady=(0, 10))
        self.log_text = scrolledtext.ScrolledText(log_frame, state='disabled', height=6, wrap=tk.WORD, font=('微软雅黑', 9))
        self.log_text.pack(fill=tk.BOTH, expand=True)

        # 状态栏和退出按钮区域
        bottom_frame = ttk.Frame(root)
        bottom_frame.pack(side=tk.BOTTOM, fill=tk.X)
        
        # 状态栏
        self.status_bar = ttk.Label(bottom_frame, text="准备就绪", anchor="w", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.LEFT, fill=tk.X, expand=True)
        
        # 退出按钮
        exit_btn = ttk.Button(bottom_frame, text="退出", command=self.root.quit)
        exit_btn.pack(side=tk.RIGHT, padx=10, pady=2)
        
        # 刷新应用列表
        self.refresh_window_list()

    # 下面实现各操作方法
    def refresh_session_list(self):
        self.session_list.delete(0, tk.END)
        names = self.session_manager.get_session_names()
        for name in names:
            self.session_list.insert(tk.END, name)
        if names:
            self.session_list.selection_set(0)

    def on_session_select(self, event):
        idx = self.session_list.curselection()
        if idx:
            name = self.session_list.get(idx[0])
            self.current_session_name = name
            self.current_session_items = self.session_manager.get_session(name)
            self.refresh_window_list()
            self.status_bar.config(text=f"已切换到会话：{name}")

    def save_session(self):
        try:
            items = collect_session_data(self.config)
            self.session_manager.set_session(self.current_session_name, items)
            self.current_session_items = items
            self.refresh_window_list()
            self.status_bar.config(text=f"会话 '{self.current_session_name}' 已保存。")
            messagebox.showinfo("保存成功", f"会话 '{self.current_session_name}' 已保存。")
        except Exception as e:
            logger.error(f"保存会话时出错: {e}", exc_info=True)
            self.log_to_gui(f"保存会话失败: {e}")
            messagebox.showerror("保存失败", f"保存会话时出错: {e}")

    def restore_session(self):
        try:
            if not self.current_session_items:
                messagebox.showwarning("恢复失败", "当前会话没有可恢复的应用。")
                return
                
            success_count, fail_count = restore_session(self.current_session_items, self.config)
            
            if success_count == 0 and fail_count == 0:
                self.status_bar.config(text=f"会话 '{self.current_session_name}' 没有内容可恢复。")
                messagebox.showinfo("恢复完成", f"会话 '{self.current_session_name}' 没有内容可恢复。")
            else:
                self.status_bar.config(text=f"会话 '{self.current_session_name}' 恢复完成。成功: {success_count}, 失败: {fail_count}")
                messagebox.showinfo("恢复完成", f"会话 '{self.current_session_name}' 已尝试恢复。\n成功: {success_count}, 失败: {fail_count}")
        except Exception as e:
            logger.error(f"恢复会话时出错: {e}", exc_info=True)
            self.log_to_gui(f"恢复会话失败: {e}")
            messagebox.showerror("恢复失败", f"恢复会话时出错: {e}")

    def import_session(self):
        file_path = filedialog.askopenfilename(
            title="导入会话",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        new_name = simpledialog.askstring("导入会话", "请输入导入会话的名称：", parent=self.root)
        if not new_name:
            return
        if self.session_manager.import_session(file_path, new_name):
            self.refresh_session_list()
            self.status_bar.config(text=f"会话 '{new_name}' 已导入。")
            messagebox.showinfo("导入成功", f"会话 '{new_name}' 已导入。")
        else:
            messagebox.showerror("导入失败", "导入会话失败，请检查文件格式或日志。")

    def export_session(self):
        if not self.current_session_name:
            messagebox.showwarning("导出失败", "请先选择要导出的会话。")
            return
        file_path = filedialog.asksaveasfilename(
            title="导出会话",
            defaultextension=".json",
            filetypes=[("JSON 文件", "*.json"), ("所有文件", "*.*")]
        )
        if not file_path:
            return
        if self.session_manager.export_session(self.current_session_name, file_path):
            self.status_bar.config(text=f"会话 '{self.current_session_name}' 已导出。")
            messagebox.showinfo("导出成功", f"会话已导出到 {file_path}")
        else:
            messagebox.showerror("导出失败", "导出会话失败，请检查日志。")

    def create_session(self):
        new_name = simpledialog.askstring("新建会话", "请输入新会话名称：", parent=self.root)
        if not new_name:
            return
        if new_name in self.session_manager.get_session_names():
            messagebox.showwarning("新建失败", "会话名称已存在。")
            return
        self.session_manager.set_session(new_name, [])
        self.refresh_session_list()
        self.session_list.selection_clear(0, tk.END)
        idx = self.session_manager.get_session_names().index(new_name)
        self.session_list.selection_set(idx)
        self.on_session_select(None)
        self.status_bar.config(text=f"新会话 '{new_name}' 已创建。")
        messagebox.showinfo("新建成功", f"新会话 '{new_name}' 已创建。")

    def rename_session(self):
        if not self.current_session_name:
            messagebox.showwarning("重命名失败", "请先选择要重命名的会话。")
            return
        new_name = simpledialog.askstring("重命名会话", "请输入新会话名称：", initialvalue=self.current_session_name, parent=self.root)
        if not new_name or new_name == self.current_session_name:
            return
        if new_name in self.session_manager.get_session_names():
            messagebox.showwarning("重命名失败", "会话名称已存在。")
            return
        items = self.session_manager.get_session(self.current_session_name)
        self.session_manager.set_session(new_name, items)
        self.session_manager.delete_session(self.current_session_name)
        self.refresh_session_list()
        idx = self.session_manager.get_session_names().index(new_name)
        self.session_list.selection_set(idx)
        self.on_session_select(None)
        self.status_bar.config(text=f"会话已重命名为 '{new_name}'。")
        messagebox.showinfo("重命名成功", f"会话已重命名为 '{new_name}'。")

    def delete_session(self):
        if not self.current_session_name:
            messagebox.showwarning("删除失败", "请先选择要删除的会话。")
            return
        if not messagebox.askyesno("确认删除", f"确定要删除会话 '{self.current_session_name}' 吗？此操作不可恢复。"):
            return
        self.session_manager.delete_session(self.current_session_name)
        self.refresh_session_list()
        session_names = self.session_manager.get_session_names()
        if session_names:
            self.current_session_name = session_names[0]
            self.current_session_items = self.session_manager.get_session(self.current_session_name)
        else:
            default_name = self.session_manager.default_session_name
            self.session_manager.set_session(default_name, [])
            self.current_session_name = default_name
            self.current_session_items = []
            self.refresh_session_list()
        self.refresh_window_list()
        self.status_bar.config(text=f"会话已删除。")
        messagebox.showinfo("删除成功", "会话已删除。")

    def clear_session(self):
        if not self.current_session_name:
            messagebox.showwarning("清空失败", "请先选择要清空的会话。")
            return
        if not messagebox.askyesno("确认清空", f"确定要清空会话 '{self.current_session_name}' 的所有应用吗？"):
            return
        self.session_manager.clear_session(self.current_session_name)
        self.current_session_items = []
        self.refresh_window_list()
        self.status_bar.config(text=f"会话 '{self.current_session_name}' 已清空。")
        messagebox.showinfo("清空成功", f"会话 '{self.current_session_name}' 已清空。")

    def show_help(self):
        messagebox.showinfo("使用说明", "1. 选择会话，右侧显示应用列表。\n2. 可保存/恢复/导入/导出/重命名/删除/清空会话。\n3. 右键支持更多操作。")

    def show_about(self):
        messagebox.showinfo("关于", "Windows 会话管理器\n版本：1.0\n作者：您的名字\nGitHub: https://github.com/rait-winter/windows-session-manager")

    def log_to_gui(self, msg):
        """向GUI日志区输出信息"""
        self.log_text.config(state='normal')
        self.log_text.insert(tk.END, msg + '\n')
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled')

    def refresh_windows(self):
        windows = gw.getAllWindows()
        for w in windows:
            try:
                print(f"窗口标题: {w.title}, HWND: {w._hWnd}, 可见: {w.visible}")
                path = get_process_path_from_hwnd(w._hWnd)
                print(f"进程路径: {path}")
            except Exception as e:
                print(f"窗口信息获取异常: {e}")

    def get_window_info(self, hwnd):
        """获取窗口详细信息"""
        info = {
            'hwnd': hwnd,
            'title': win32gui.GetWindowText(hwnd),
            'class_name': win32gui.GetClassName(hwnd),
            'visible': win32gui.IsWindowVisible(hwnd),
            'style': win32gui.GetWindowLong(hwnd, win32con.GWL_STYLE),
            'rect': win32gui.GetWindowRect(hwnd)
        }
        try:
            _, pid = win32process.GetWindowThreadProcessId(hwnd)
            proc = psutil.Process(pid)
            info['pid'] = pid
            info['exe'] = proc.exe()
            info['name'] = proc.name()
        except Exception:
            info['pid'] = None
            info['exe'] = "未知"
            info['name'] = "未知"
        return info

    def format_window_info(self, info, depth=0):
        """格式化窗口信息输出"""
        indent = "  " * depth
        style_flags = []
        if info['style'] & win32con.WS_VISIBLE:
            style_flags.append("可见")
        if info['style'] & win32con.WS_CHILD:
            style_flags.append("子窗口")
        if info['style'] & win32con.WS_POPUP:
            style_flags.append("弹出窗口")
        
        rect = info['rect']
        size = f"{rect[2]-rect[0]}x{rect[3]-rect[1]}"
        
        return (
            f"{indent}窗口信息:\n"
            f"{indent}  HWND: {info['hwnd']}\n"
            f"{indent}  标题: {info['title'] or '(无标题)'}\n"
            f"{indent}  类名: {info['class_name']}\n"
            f"{indent}  PID: {info['pid']}\n"
            f"{indent}  进程: {info['name']}\n"
            f"{indent}  路径: {info['exe']}\n"
            f"{indent}  位置: ({rect[0]},{rect[1]}) 大小: {size}\n"
            f"{indent}  样式: {', '.join(style_flags)}\n"
        )

    def enum_all_windows_and_children(self):
        def log_window(hwnd, depth=0):
            """递归记录窗口信息"""
            info = self.get_window_info(hwnd)
            self.log_text.insert(tk.END, self.format_window_info(info, depth) + "\n")
            # 枚举子窗口
            win32gui.EnumChildWindows(hwnd, lambda h, _: log_window(h, depth+1), None)

        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)  # 清空之前的日志
        self.log_text.insert(tk.END, '\n[开始递归枚举所有窗口和子窗口]\n' + '='*50 + '\n\n')
        win32gui.EnumWindows(lambda hwnd, _: log_window(hwnd), None)
        self.log_text.insert(tk.END, '\n' + '='*50 + '\n[枚举完成]\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)

    def is_interesting_window(self, info):
        """判断窗口是否值得关注"""
        # 忽略不可见窗口
        if not (info['style'] & win32con.WS_VISIBLE):
            return False
            
        # 特殊处理：即使是子窗口，如果有标题且尺寸合理，也可能是值得关注的窗口
        is_child = info['style'] & win32con.WS_CHILD
        rect = info['rect']
        window_width = rect[2] - rect[0]
        window_height = rect[3] - rect[1]
        has_reasonable_size = window_width > 100 and window_height > 100
        
        # 如果是子窗口但有标题且尺寸合理，仍然考虑
        if is_child and (not info['title'] or not has_reasonable_size):
            return False
            
        # 忽略特定类名的系统窗口
        ignored_classes = {
            'Shell_TrayWnd',  # 任务栏
            'DV2ControlHost',  # 系统控件
            'Windows.UI.Core.CoreWindow',  # UWP核心窗口
            # 保留ApplicationFrameWindow，因为一些UWP应用使用这个类名
        }
        if info['class_name'] in ignored_classes:
            return False
            
        # 忽略特定进程的窗口
        ignored_processes = {
            'SearchApp.exe',
            'TextInputHost.exe',
            # 只有在标题为空时才忽略explorer.exe
        }
        if info['name'] in ignored_processes and not info['title']:
            return False
            
        # 特殊处理：某些应用可能没有标准窗口样式但仍需要被捕获
        # 如果窗口有标题且尺寸合理，即使不是标准窗口也考虑
        if info['title'] and has_reasonable_size:
            return True
            
        # 如果窗口没有标题但进程名看起来是应用程序，也考虑
        if not info['title'] and info['name'] not in ['explorer.exe', 'dwm.exe', 'ApplicationFrameHost.exe']:
            # 检查窗口尺寸是否合理
            if has_reasonable_size:
                return True
                
        return True

    def get_window_type(self, info):
        """获取窗口类型"""
        exe_lower = info['exe'].lower() if info['exe'] != "未知" else ""
        
        # 浏览器检测
        if 'chrome.exe' in exe_lower:
            return 'browser'
        elif 'msedge.exe' in exe_lower:
            return 'browser'
        elif 'firefox.exe' in exe_lower:
            return 'browser'
        
        # 特殊应用检测
        if 'pixpin' in exe_lower:
            return 'application'
        elif 'fastorange' in exe_lower:
            return 'application'
        
        # 文件资源管理器
        elif 'explorer.exe' in exe_lower and info['title']:
            return 'explorer'
            
        # 其他应用程序
        elif info['style'] & win32con.WS_POPUP:
            return 'popup'
        else:
            return 'application'

    def enum_filtered_windows(self):
        """枚举并按类型分类显示感兴趣的窗口"""
        windows_by_type = {}
        
        def collect_window(hwnd, lparam):
            try:
                info = self.get_window_info(hwnd)
                if self.is_interesting_window(info):
                    window_type = self.get_window_type(info)
                    if window_type not in windows_by_type:
                        windows_by_type[window_type] = []
                    windows_by_type[window_type].append(info)
                    
                    # 记录日志，帮助调试
                    self.log_to_gui(f"发现窗口: {info['title']} (HWND: {info['hwnd']}, 类名: {info['class_name']}, 进程: {info['name']})")
            except Exception as e:
                self.log_to_gui(f"处理窗口时出错: {e}")
            return True  # 继续枚举
        
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, '\n[按类型显示感兴趣的窗口]\n' + '='*50 + '\n\n')
        
        # 枚举窗口
        win32gui.EnumWindows(collect_window, None)
        
        # 显示结果
        for window_type, windows in sorted(windows_by_type.items()):
            self.log_text.insert(tk.END, f"\n== {window_type} ==\n")
            for info in windows:
                self.log_text.insert(tk.END, self.format_window_info(info) + "\n")
        
        self.log_text.insert(tk.END, '\n' + '='*50 + '\n[枚举完成]\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END) 

    def find_special_app_windows(self):
        """使用多种方法查找特殊应用的窗口"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, '\n[开始查找特殊应用窗口]\n' + '='*50 + '\n\n')
        
        # 1. 通过进程名查找
        special_apps = ['PixPin', 'FastOrange']
        found_windows = []
        
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
                
                if is_special:
                    self.log_text.insert(tk.END, f"发现特殊应用进程: {proc_name} (PID: {proc_info['pid']}, 路径: {proc_exe})\n")
                    
                    # 2. 尝试查找该进程的所有窗口
                    def enum_windows_callback(hwnd, pid):
                        try:
                            _, win_pid = win32process.GetWindowThreadProcessId(hwnd)
                            if win_pid == pid:
                                window_info = self.get_window_info(hwnd)
                                found_windows.append(window_info)
                                self.log_text.insert(tk.END, f"找到窗口: {window_info['title'] or '(无标题)'} "
                                                           f"(HWND: {hwnd}, 类名: {window_info['class_name']})\n")
                                
                                # 3. 查找子窗口
                                def enum_child_callback(child_hwnd, _):
                                    try:
                                        child_info = self.get_window_info(child_hwnd)
                                        found_windows.append(child_info)
                                        self.log_text.insert(tk.END, f"  子窗口: {child_info['title'] or '(无标题)'} "
                                                                   f"(HWND: {child_hwnd}, 类名: {child_info['class_name']})\n")
                                    except Exception as e:
                                        self.log_text.insert(tk.END, f"  获取子窗口信息出错: {e}\n")
                                    return True
                                
                                win32gui.EnumChildWindows(hwnd, enum_child_callback, None)
                        except Exception as e:
                            self.log_text.insert(tk.END, f"枚举窗口时出错: {e}\n")
                        return True
                    
                    win32gui.EnumWindows(lambda hwnd, lParam: enum_windows_callback(hwnd, proc_info['pid']), None)
            except Exception as e:
                self.log_text.insert(tk.END, f"处理进程时出错: {e}\n")
        
        # 4. 尝试使用其他方法查找窗口
        self.log_text.insert(tk.END, '\n[尝试使用其他方法查找特殊窗口]\n')
        
        # 使用窗口类名的部分匹配
        def find_by_class_partial_match(hwnd, _):
            try:
                class_name = win32gui.GetClassName(hwnd)
                title = win32gui.GetWindowText(hwnd)
                
                for app in special_apps:
                    if (app.lower() in class_name.lower() or 
                        (title and app.lower() in title.lower())):
                        window_info = self.get_window_info(hwnd)
                        if window_info not in found_windows:
                            found_windows.append(window_info)
                            self.log_text.insert(tk.END, f"通过类名/标题匹配找到窗口: {title or '(无标题)'} "
                                               f"(HWND: {hwnd}, 类名: {class_name})\n")
            except Exception as e:
                pass  # 忽略错误
            return True
        
        win32gui.EnumWindows(find_by_class_partial_match, None)
        
        # 5. 总结结果
        self.log_text.insert(tk.END, f"\n[查找结果]\n找到 {len(found_windows)} 个可能的特殊应用窗口\n")
        
        if found_windows:
            self.log_text.insert(tk.END, "\n详细信息:\n")
            for info in found_windows:
                self.log_text.insert(tk.END, self.format_window_info(info) + "\n")
        
        self.log_text.insert(tk.END, '\n' + '='*50 + '\n[查找完成]\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END)
        
        return found_windows 

    def list_all_processes(self):
        """列出系统中的所有进程"""
        self.log_text.config(state='normal')
        self.log_text.delete(1.0, tk.END)
        self.log_text.insert(tk.END, '\n[系统进程列表]\n' + '='*50 + '\n\n')
        
        try:
            processes = []
            
            for proc in psutil.process_iter(['pid', 'name', 'exe', 'cmdline']):
                try:
                    proc_info = proc.info
                    pid = proc_info['pid']
                    name = proc_info['name'] if 'name' in proc_info else "未知"
                    exe = proc_info['exe'] if 'exe' in proc_info else "未知"
                    
                    # 收集进程信息
                    processes.append({
                        'pid': pid,
                        'name': name,
                        'exe': exe
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                    pass
            
            # 按名称排序
            processes.sort(key=lambda x: x['name'].lower())
            
            # 显示进程信息
            for proc in processes:
                self.log_text.insert(tk.END, f"PID: {proc['pid']}, 名称: {proc['name']}\n")
                self.log_text.insert(tk.END, f"  路径: {proc['exe']}\n")
                self.log_text.insert(tk.END, "-"*50 + "\n")
                
            self.log_text.insert(tk.END, f"\n总共找到 {len(processes)} 个进程\n")
        except Exception as e:
            self.log_text.insert(tk.END, f"获取进程列表时出错: {e}\n")
        
        self.log_text.insert(tk.END, '\n' + '='*50 + '\n[列表完成]\n')
        self.log_text.config(state='disabled')
        self.log_text.see(tk.END) 

    def add_log_message(self, level, message):
        """添加日志消息到GUI"""
        self.log_text.config(state='normal')
        
        # 根据日志级别选择颜色
        tag = None
        if level >= logging.ERROR:
            tag = "error"
            self.log_text.tag_config("error", foreground="red")
        elif level >= logging.WARNING:
            tag = "warning"
            self.log_text.tag_config("warning", foreground="orange")
        elif level >= logging.INFO:
            tag = "info"
            self.log_text.tag_config("info", foreground="blue")
        
        # 插入日志消息
        self.log_text.insert(tk.END, message + '\n', tag)
        self.log_text.see(tk.END)
        self.log_text.config(state='disabled') 

    def get_session_data(self, session_name):
        """获取会话数据"""
        return self.session_manager.get_session(session_name)

    def refresh_window_list(self):
        """刷新窗口列表"""
        if not self.current_session_name:
            return
            
        # 清空列表
        for i in self.window_listbox.get_children():
            self.window_listbox.delete(i)
            
        # 获取当前会话数据
        session_data = self.get_session_data(self.current_session_name)
        if not session_data:
            self.log_to_gui("会话数据为空")
            return
            
        # 兼容旧版会话数据格式
        if isinstance(session_data, list):
            # 按类型分组：浏览器和应用程序
            browsers = []
            applications = []
            
            for window_info in session_data:
                if not isinstance(window_info, dict):
                    self.log_to_gui(f"警告：会话数据中存在非法项（类型：{type(window_info)}，值：{window_info}），已跳过。")
                    continue
                    
                window_type = window_info.get("type", "unknown")
                if window_type == "browser":
                    browsers.append(window_info)
                else:
                    applications.append(window_info)
        else:
            # 新版会话数据格式：包含applications和browser_windows两个键
            browsers = session_data.get("browser_windows", [])
            applications = session_data.get("applications", [])
                
        # 添加浏览器窗口到列表
        for browser_info in browsers:
            if not isinstance(browser_info, dict):
                continue
                
            # 适配不同的数据结构
            window_title = browser_info.get("title", "未知浏览器")
            window_path = browser_info.get("path") or browser_info.get("process_path", "")
            
            # 处理标签页：兼容不同的键名
            if "tabs" in browser_info:
                urls = browser_info["tabs"]
            elif "urls" in browser_info:
                urls = browser_info["urls"]
            else:
                urls = []
                
            has_tabs = len(urls) > 0
            
            # 添加浏览器主条目
            browser_icon = self.get_icon_for_type("browser")
            browser_id = self.window_listbox.insert("", "end", text=window_title, 
                                       values=("browser", window_path),
                                       image=browser_icon,
                                       open=False)  # 默认折叠
            
            # 如果有标签页，添加为子条目
            if has_tabs:
                # 第一个子条目显示标签页总数
                tab_count_id = self.window_listbox.insert(browser_id, "end", 
                                       text=f"包含 {len(urls)} 个标签页", 
                                       values=("tab_count", ""),
                                       image=self.get_icon_for_type("info"))
                
                # 添加各个标签页
                for i, tab in enumerate(urls):
                    # 兼容不同的标签页数据结构
                    if isinstance(tab, dict):
                        tab_title = tab.get("title", "无标题")
                        tab_url = tab.get("url", "")
                    elif isinstance(tab, str):
                        tab_title = f"标签页 {i+1}"
                        tab_url = tab
                    else:
                        continue
                    
                    # 截断过长的标题
                    if len(tab_title) > 50:
                        tab_title = tab_title[:47] + "..."
                        
                    # 添加标签页条目
                    self.window_listbox.insert(browser_id, "end", 
                                     text=tab_title,
                                     values=("tab", tab_url),
                                     image=self.get_icon_for_type("tab"))
        
        # 添加其他应用到列表
        for app_info in applications:
            if not isinstance(app_info, dict):
                continue
                
            # 适配不同的数据结构
            window_title = app_info.get("title", "未知应用")
            window_path = app_info.get("path") or app_info.get("process_path", "")
            window_type = app_info.get("type", "application")
            
            # 添加应用条目
            app_icon = self.get_icon_for_type(window_type)
            self.window_listbox.insert("", "end", 
                               text=window_title, 
                               values=(window_type, window_path),
                               image=app_icon)

    def get_icon_for_type(self, item_type):
        """根据项目类型获取图标"""
        if item_type == "browser":
            return self.browser_icon
        elif item_type == "application":
            return self.app_icon
        elif item_type == "tab":
            return self.tab_icon
        elif item_type == "more":
            return self.more_icon
        elif item_type == "info":
            return self.info_icon
        else:
            return self.default_icon

    def setup_icons(self):
        """设置图标"""
        # 默认图标
        self.default_icon = self.create_colored_square((16, 16), "#cccccc")
        
        # 应用图标
        self.app_icon = self.create_colored_square((16, 16), "#4285F4")
        
        # 浏览器图标
        self.browser_icon = self.create_colored_square((16, 16), "#34A853")
        
        # 标签页图标
        self.tab_icon = self.create_colored_square((16, 16), "#FBBC05", radius=8)
        
        # 更多图标
        self.more_icon = self.create_colored_square((16, 16), "#EA4335", radius=8)
        
        # 信息图标
        self.info_icon = self.create_colored_square((16, 16), "#4FC3F7", radius=4)

    def create_colored_square(self, size, color, radius=0):
        """创建彩色方块图标"""
        img = Image.new('RGBA', size, (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)
        
        if radius > 0:
            # 绘制圆形
            draw.ellipse([0, 0, size[0]-1, size[1]-1], fill=color)
        else:
            # 绘制方形
            draw.rectangle([0, 0, size[0]-1, size[1]-1], fill=color)
            
        return ImageTk.PhotoImage(img) 

    def setup_theme(self):
        """设置应用主题"""
        style = ttk.Style()
        style.theme_use('clam')
        style.configure('TButton', font=('微软雅黑', 10), padding=6)
        style.configure('TLabel', font=('微软雅黑', 10))
        style.configure('Treeview.Heading', font=('微软雅黑', 10, 'bold'))
        
        self.root.title("会话管理器")
        self.root.geometry("900x600")
        self.root.minsize(700, 500) 

    def on_item_double_click(self, event):
        """处理项目双击事件"""
        item_id = self.window_listbox.identify_row(event.y)
        if not item_id:
            return
            
        # 获取项目信息
        item_values = self.window_listbox.item(item_id, "values")
        if not item_values:
            return
            
        item_type = item_values[0]
        item_path = item_values[1]
        
        # 如果是标签页，打开URL
        if item_type == "tab" and item_path:
            try:
                self.log_to_gui(f"正在打开URL: {item_path}")
                webbrowser.open(item_path)
            except Exception as e:
                self.log_to_gui(f"打开URL失败: {e}") 