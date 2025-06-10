"""
gui.py
Tkinter 图形界面相关模块。
"""

import tkinter as tk
from tkinter import ttk, messagebox, filedialog, simpledialog, scrolledtext
from session_manager.core import collect_session_data_core, restore_specific_session_core
import logging

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

        # 状态栏
        self.status_bar = ttk.Label(root, text="准备就绪", anchor="w", relief=tk.SUNKEN)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

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