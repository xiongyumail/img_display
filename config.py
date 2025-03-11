import argparse
import os
import tkinter as tk
from tkinter import filedialog, messagebox, ttk

def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Display image information using Flask app.')
    parser.add_argument('--per_page', type=int, default=20, help='Number of items per page.')
    parser.add_argument('--input_json', type=str, default=None, help='Input JSON file path.')
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
            # 创建主窗口
            config_root = tk.Tk()
            config_root.title("配置参数")
            
            # 创建带滚动条的容器
            main_frame = ttk.Frame(config_root)
            main_frame.pack(padx=10, pady=10, fill=tk.BOTH, expand=True)

            # 文件选择部分
            def browse_file():
                file_path = filedialog.askopenfilename(
                    title="选择JSON文件",
                    filetypes=[("JSON文件", "*.json"), ("所有文件", "*.*")]
                )
                if file_path:
                    file_entry.delete(0, tk.END)
                    file_entry.insert(0, file_path)

            ttk.Label(main_frame, text="JSON文件路径:").grid(row=0, column=0, padx=5, pady=5, sticky=tk.W)
            file_entry = ttk.Entry(main_frame, width=40)
            file_entry.grid(row=0, column=1, padx=5, pady=5)
            ttk.Button(main_frame, text="浏览...", command=browse_file).grid(row=0, column=2, padx=5)

            # 参数配置部分
            settings_frame = ttk.LabelFrame(main_frame, text="服务器配置")
            settings_frame.grid(row=1, column=0, columnspan=3, pady=10, sticky=tk.EW)

            # 每页数量
            ttk.Label(settings_frame, text="每页数量:").grid(row=0, column=0, padx=5, pady=5)
            per_page_entry = ttk.Entry(settings_frame)
            per_page_entry.insert(0, str(args.per_page))
            per_page_entry.grid(row=0, column=1, padx=5, pady=5)

            # 主机地址
            ttk.Label(settings_frame, text="主机地址:").grid(row=1, column=0, padx=5, pady=5)
            host_entry = ttk.Entry(settings_frame)
            host_entry.insert(0, args.host)
            host_entry.grid(row=1, column=1, padx=5, pady=5)

            # 端口号
            ttk.Label(settings_frame, text="端口号:").grid(row=2, column=0, padx=5, pady=5)
            port_entry = ttk.Entry(settings_frame)
            port_entry.insert(0, str(args.port))
            port_entry.grid(row=2, column=1, padx=5, pady=5)

            # 调试模式
            debug_var = tk.BooleanVar(value=args.debug)
            ttk.Checkbutton(settings_frame, text="调试模式", variable=debug_var).grid(row=3, columnspan=2, pady=5)

            # 是否自动打开浏览器
            no_browser_var = tk.BooleanVar(value=args.no_browser)
            ttk.Checkbutton(settings_frame, text="不自动打开浏览器", variable=no_browser_var).grid(row=4, columnspan=2, pady=5)

            # 替换字符串部分
            replace_frame = ttk.LabelFrame(main_frame, text="字符串替换")
            replace_frame.grid(row=3, column=0, columnspan=3, pady=10, sticky=tk.EW)

            replace_entries = []

            def add_replace_entry():
                entry_frame = ttk.Frame(replace_frame)
                entry_frame.pack(fill=tk.X, pady=2)
                entry1 = ttk.Entry(entry_frame, width=20)
                entry1.pack(side=tk.LEFT, padx=5)
                entry2 = ttk.Entry(entry_frame, width=20)
                entry2.pack(side=tk.LEFT, padx=5)
                replace_entries.append((entry1, entry2))

            ttk.Button(replace_frame, text="添加替换项", command=add_replace_entry).pack(pady=5)

            # 确认按钮
            def submit_params():
                # 验证文件路径
                file_path = file_entry.get().strip()
                if not file_path:
                    messagebox.showerror("错误", "必须选择JSON文件")
                    return
                if not os.path.isfile(file_path):
                    messagebox.showerror("错误", "文件路径无效")
                    return

                # 验证数值参数
                try:
                    args.per_page = int(per_page_entry.get())
                    if args.per_page <= 0:
                        raise ValueError
                except ValueError:
                    messagebox.showerror("错误", "每页数量必须是正整数")
                    return

                args.host = host_entry.get().strip()
                if not args.host:
                    messagebox.showerror("错误", "主机地址不能为空")
                    return

                try:
                    args.port = int(port_entry.get())
                    if not (0 <= args.port <= 65535):
                        raise ValueError
                except ValueError:
                    messagebox.showerror("错误", "端口号必须是0-65535之间的整数")
                    return

                args.debug = debug_var.get()
                args.no_browser = no_browser_var.get()  # 获取是否自动打开浏览器的选项
                args.input_json = file_path

                # 处理替换字符串
                args.replace = []
                for entry1, entry2 in replace_entries:
                    old_str = entry1.get().strip()
                    new_str = entry2.get().strip()
                    if old_str and new_str:
                        args.replace.append([old_str, new_str])

                config_root.destroy()

            btn_frame = ttk.Frame(main_frame)
            btn_frame.grid(row=4, column=0, columnspan=3, pady=10)
            ttk.Button(btn_frame, text="启动服务", command=submit_params).pack(side=tk.LEFT, padx=5)
            ttk.Button(btn_frame, text="退出", command=config_root.destroy).pack(side=tk.RIGHT, padx=5)

            # 窗口居中
            config_root.update_idletasks()
            width = config_root.winfo_width()
            height = config_root.winfo_height()
            x = (config_root.winfo_screenwidth() // 2) - (width // 2)
            y = (config_root.winfo_screenheight() // 2) - (height // 2)
            config_root.geometry(f'+{x}+{y}')

            config_root.mainloop()

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