import argparse
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from version import __version__

class ConfigGUI:
    def __init__(self, args):
        self.args = args
        self.config_root = tk.Tk()
        self.config_root.title(f"配置参数 - 版本: {__version__}")
        self.main_frame = ttk.Frame(self.config_root)
        self.main_frame.pack(padx=20, pady=20, fill=tk.BOTH, expand=True)
        self.replace_entries = []
        self.create_widgets()

    def create_widgets(self):
        # 文件选择部分
        ttk.Label(self.main_frame, text="JSON文件路径:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        
        # 使用 Listbox 显示多文件路径
        self.file_listbox = tk.Listbox(self.main_frame, width=50, height=3, selectmode=tk.EXTENDED)
        self.file_listbox.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)
        
        # 文件操作按钮框架
        file_btn_frame = ttk.Frame(self.main_frame)
        file_btn_frame.grid(row=0, column=2, padx=5, sticky=tk.W)
        
        ttk.Button(file_btn_frame, text="添加...", command=self.add_files).pack(pady=2)
        ttk.Button(file_btn_frame, text="移除", command=self.remove_files).pack(pady=2)

        # 参数配置部分
        settings_frame = ttk.LabelFrame(self.main_frame, text="服务器配置")
        settings_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky=tk.EW)

        # 每页数量
        ttk.Label(settings_frame, text="每页数量:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
        self.per_page_entry = ttk.Entry(settings_frame)
        self.per_page_entry.insert(0, str(self.args.per_page))
        self.per_page_entry.grid(row=0, column=1, padx=5, pady=5, sticky=tk.W)

        # 调试模式
        self.debug_var = tk.BooleanVar(value=self.args.debug)
        ttk.Checkbutton(settings_frame, text="调试模式", variable=self.debug_var).grid(row=0, column=2, columnspan=2, padx=5, pady=5, sticky=tk.W)

        # 主机地址
        ttk.Label(settings_frame, text="主机地址:").grid(row=1, column=0, padx=5, pady=5, sticky=tk.W)
        self.host_entry = ttk.Entry(settings_frame)
        self.host_entry.insert(0, self.args.host)
        self.host_entry.grid(row=1, column=1, padx=5, pady=5, sticky=tk.W)

        # 端口号
        ttk.Label(settings_frame, text="端口号:").grid(row=1, column=2, padx=5, pady=5, sticky=tk.W)
        self.port_entry = ttk.Entry(settings_frame)
        self.port_entry.insert(0, str(self.args.port))
        self.port_entry.grid(row=1, column=3, padx=5, pady=5, sticky=tk.W)

        # 是否自动打开浏览器
        self.no_browser_var = tk.BooleanVar(value=self.args.no_browser)
        ttk.Checkbutton(settings_frame, text="不自动打开浏览器", variable=self.no_browser_var).grid(row=1, column=4, columnspan=2, pady=5, sticky=tk.W)

        # 替换字符串部分
        self.replace_frame = ttk.LabelFrame(self.main_frame, text="字符串替换")
        self.replace_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=tk.EW)

        ttk.Button(self.replace_frame, text="添加替换项", command=self.add_replace_entry).pack(pady=5)

        # 确认按钮
        btn_frame = ttk.Frame(self.main_frame)
        btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
        ttk.Button(btn_frame, text="启动服务", command=self.submit_params).pack(side=tk.LEFT, padx=5)
        ttk.Button(btn_frame, text="退出", command=self.config_root.destroy).pack(side=tk.RIGHT, padx=5)

        # 窗口居中（根据内容自动调整大小）
        self.config_root.update_idletasks()
        width = self.config_root.winfo_reqwidth()
        height = self.config_root.winfo_reqheight()
        x = (self.config_root.winfo_screenwidth() - width) // 2
        y = (self.config_root.winfo_screenheight() - height) // 2
        self.config_root.geometry(f'{width}x{height}+{x}+{y}')

    def add_files(self):
        file_paths = filedialog.askopenfilenames(
            title="选择JSON文件",
            filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
        )
        if file_paths:
            for path in file_paths:
                if path not in self.file_listbox.get(0, tk.END):
                    self.file_listbox.insert(tk.END, path)

    def remove_files(self):
        selected = self.file_listbox.curselection()
        for index in reversed(selected):
            self.file_listbox.delete(index)

    def add_replace_entry(self):
        entry_frame = ttk.Frame(self.replace_frame)
        entry_frame.pack(fill=tk.X, pady=2)  # 填充水平方向

        inner_frame = ttk.Frame(entry_frame)
        inner_frame.pack(expand=True)  # 在entry_frame中居中

        entry1 = ttk.Entry(inner_frame, width=20)
        entry1.pack(side=tk.LEFT, padx=5)
        entry2 = ttk.Entry(inner_frame, width=20)
        entry2.pack(side=tk.LEFT, padx=5)
        self.replace_entries.append((entry1, entry2))

        # 更新窗口大小并保持居中
        self.config_root.update_idletasks()
        width = self.config_root.winfo_reqwidth()
        height = self.config_root.winfo_reqheight()
        x = (self.config_root.winfo_screenwidth() - width) // 2
        y = (self.config_root.winfo_screenheight() - height) // 2
        self.config_root.geometry(f"{width}x{height}+{x}+{y}")

    def submit_params(self):
        # 验证文件路径
        file_paths = self.file_listbox.get(0, tk.END)
        if not file_paths:
            messagebox.showerror("错误", "必须选择至少一个JSON文件")
            return
        for path in file_paths:
            if not os.path.isfile(path):
                messagebox.showerror("错误", f"文件路径无效: {path}")
                return

        # 验证数值参数
        try:
            self.args.per_page = int(self.per_page_entry.get())
            if self.args.per_page <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "每页数量必须是正整数")
            return

        self.args.host = self.host_entry.get().strip()
        if not self.args.host:
            messagebox.showerror("错误", "主机地址不能为空")
            return

        try:
            self.args.port = int(self.port_entry.get())
            if not (0 <= self.args.port <= 65535):
                raise ValueError
        except ValueError:
            messagebox.showerror("错误", "端口号必须是0-65535之间的整数")
            return

        self.args.debug = self.debug_var.get()
        self.args.no_browser = self.no_browser_var.get()
        self.args.input_json = list(file_paths)  # 存储为列表

        # 处理替换字符串
        self.args.replace = []
        for entry1, entry2 in self.replace_entries:
            old_str = entry1.get().strip()
            new_str = entry2.get().strip()
            if old_str and new_str:
                self.args.replace.append([old_str, new_str])

        self.config_root.destroy()

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Display image information using Flask app.')
    parser.add_argument('--per_page', type=int, default=20, help='Number of items per page.')
    parser.add_argument('--input_json', type=str, nargs='+', default=None,  # 支持多个文件
                        help='Input JSON file paths (multiple allowed).')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Flask server host.')
    parser.add_argument('--port', type=int, default=5000, help='Flask server port.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    parser.add_argument('--replace', type=str, nargs=2, action='append',
                        help='Temporarily replace strings in input_json, e.g., "/abc" "/def"')
    parser.add_argument('--no_browser', action='store_true', help='Do not open the browser automatically.')
    return parser.parse_args()

def get_config() -> argparse.Namespace:
    args = parse_args()

    if args.input_json is None:
        try:
            gui = ConfigGUI(args)
            gui.config_root.mainloop()

            if not args.input_json:  # 用户直接关闭窗口的情况
                print("操作已取消")
                exit(0)

        except ImportError:
            print("错误：需要tkinter支持GUI文件选择。")
            exit(1)
        except Exception as e:
            print(f"无法打开文件对话框: {str(e)}")
            exit(1)

    return args