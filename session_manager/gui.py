"""
gui.py
Tkinter 图形界面相关模块。
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext
from session_manager.core import collect_session_data_core, restore_specific_session_core
import logging
import pygetwindow as gw
from session_manager.utils import get_process_path_from_hwnd
import win32gui
import win32process
import psutil
import win32con

class GuiLogHandler(logging.Handler):
    def __init__(self, gui_app):
        super().__init__()
        self.gui_app = gui_app

    def emit(self, record):
        msg = self.format(record)
        # 线程安全地写入 GUI
        self.gui_app.root.after(0, self.gui_app.log_to_gui, msg)

class SessionManagerApp:
    def __init__(self, root, config, session_manager):
        self.root = root
        self.config = config
        self.session_manager = session_manager
        self.current_session_name = self.session_manager.get_session_names()[0]
        self.current_session_items = self.session_manager.get_session(self.current_session_name)
        root.title("会话管理器")
        root.geometry("900x600")
        root.minsize(700, 500)

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
        self.app_tree = ttk.Treeview(right_frame, columns=("类型", "标题", "路径"), show="headings")
        self.app_tree.heading("类型", text="类型")
        self.app_tree.heading("标题", text="标题")
        self.app_tree.heading("路径", text="路径")
        self.app_tree.column("类型", width=80, anchor=tk.CENTER)
        self.app_tree.column("标题", width=200)
        self.app_tree.column("路径", width=350)
        self.app_tree.pack(fill=tk.BOTH, expand=True)
        self.refresh_app_tree()

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

    # 下面实现各操作方法
    def refresh_session_list(self):
        self.session_list.delete(0, tk.END)
        names = self.session_manager.get_session_names()
        for name in names:
            self.session_list.insert(tk.END, name)
        if names:
            self.session_list.selection_set(0)

    def refresh_app_tree(self):
        self.app_tree.delete(*self.app_tree.get_children())
        for item in self.current_session_items:
            if isinstance(item, dict):
                self.app_tree.insert("", tk.END, values=(item.get("type", ""), item.get("title", ""), item.get("path", "")))
            else:
                self.log_to_gui(f"警告：会话数据中存在非法项（类型：{type(item)}，值：{item}），已跳过。")

    def on_session_select(self, event):
        idx = self.session_list.curselection()
        if idx:
            name = self.session_list.get(idx[0])
            self.current_session_name = name
            self.current_session_items = self.session_manager.get_session(name)
            self.refresh_app_tree()
            self.status_bar.config(text=f"已切换到会话：{name}")

    def save_session(self):
        items = collect_session_data_core(self.config)
        self.session_manager.set_session(self.current_session_name, items)
        self.current_session_items = items
        self.refresh_app_tree()
        self.status_bar.config(text=f"会话 '{self.current_session_name}' 已保存。")
        messagebox.showinfo("保存成功", f"会话 '{self.current_session_name}' 已保存。")

    def restore_session(self):
        if not self.current_session_items:
            messagebox.showwarning("恢复失败", "当前会话没有可恢复的应用。")
            return
        restore_specific_session_core(self.current_session_items, self.config)
        self.status_bar.config(text=f"会话 '{self.current_session_name}' 恢复完成。")
        messagebox.showinfo("恢复完成", f"会话 '{self.current_session_name}' 已尝试恢复。")

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
        self.refresh_app_tree()
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
        self.refresh_app_tree()
        self.status_bar.config(text=f"会话 '{self.current_session_name}' 已清空。")
        messagebox.showinfo("清空成功", f"会话 '{self.current_session_name}' 已清空。")

    def show_help(self):
        messagebox.showinfo("使用说明", "1. 选择会话，右侧显示应用列表。\n2. 可保存/恢复/导入/导出/重命名/删除/清空会话。\n3. 右键支持更多操作。")

    def show_about(self):
        messagebox.showinfo("关于", "Windows 会话管理器\n版本：1.0\n作者：您的名字\nGitHub: https://github.com/rait-winter/windows-session-manager")

    def log_to_gui(self, msg):
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