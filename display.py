# display.py
import json
import os
import math
from functools import lru_cache
from flask import Flask, render_template, send_from_directory, abort, request, url_for, jsonify, Response
from urllib.parse import quote, unquote
import webbrowser
import argparse
import threading
from typing import Tuple, Dict, List, Any
import requests
from queue import Queue, Empty
from collections import defaultdict
from datetime import datetime

cached_raw_data = None
data_lock = threading.Lock()
save_queue = Queue()
save_thread_running = True

# 配置命令行参数解析
def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description='Display image information using Flask app.')
    parser.add_argument('--per_page', type=int, default=20, help='Number of items per page.')
    parser.add_argument('--input_json', type=str, default=None, help='Input JSON file path.')
    parser.add_argument('--host', type=str, default='0.0.0.0', help='Flask server host.')
    parser.add_argument('--port', type=int, default=5000, help='Flask server port.')
    parser.add_argument('--debug', action='store_true', help='Enable debug mode.')
    return parser.parse_args()

args = parse_args()

if args.input_json is None:
    try:
        import tkinter as tk
        from tkinter import filedialog, messagebox, ttk
        
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
            args.input_json = file_path
            config_root.destroy()

        btn_frame = ttk.Frame(main_frame)
        btn_frame.grid(row=2, column=0, columnspan=3, pady=10)
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

app = Flask(__name__)
app.config.update({
    'PER_PAGE': args.per_page,
    'JSON_PATH': os.path.normpath(os.path.join(os.path.dirname(__file__), args.input_json))
})

app.jinja_env.filters['urlencode'] = lambda s: quote(s.encode('utf-8'))

class Paginator:
    @staticmethod
    def paginate(items: List[Any], page: int, per_page: int) -> Tuple[List[Any], int]:
        total = len(items)
        if total == 0:
            return [], 1
        total_pages = math.ceil(total / per_page)
        page = max(1, min(page, total_pages))
        start = (page - 1) * per_page
        return items[start:start+per_page], total_pages

# 新增数据保存消费者线程
def save_consumer():
    global save_thread_running
    while save_thread_running:
        try:
            data = save_queue.get(timeout=1)
            with data_lock:
                with open(app.config['JSON_PATH'], 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=4)
            save_queue.task_done()
        except Empty:
            continue
        except Exception as e:
            app.logger.error(f"Async save failed: {str(e)}")

# 启动消费者线程
save_consumer_thread = threading.Thread(target=save_consumer, daemon=True)
save_consumer_thread.start()

@lru_cache(maxsize=1)
def load_image_data() -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
    global cached_raw_data
    with data_lock:
        if cached_raw_data is None:
            try:
                with open(app.config['JSON_PATH'], 'r', encoding='utf-8') as f:
                    cached_raw_data = json.load(f)
            except Exception as e:
                app.logger.error(f"Load initial data failed: {str(e)}")
                return {}, {}
    
    category_map: Dict[str, List[Dict]] = defaultdict(list)
    file_map: Dict[str, str] = {}

    img_data = cached_raw_data.get('img', {})

    def walk_tree(node, current_rel_path, base_abs):
        for key, value in node.items():
            if isinstance(value, dict):
                if 'face_scores' in value:
                    # 过滤条件：仅保留face_scores不为空的条目
                    if not value.get('face_scores'):
                        continue  # 跳过空数据
                            
                    abs_path = os.path.normpath(os.path.join(base_abs, current_rel_path, key))
                    parent_relative_dir = current_rel_path.replace('\\', '/')
                    if parent_relative_dir == "":
                        dir_name = os.path.basename(base_abs)
                    else:
                        dir_name = parent_relative_dir
                    img_info = {
                        'filename': key,
                        'category': dir_name,
                        'path': abs_path,
                        'face_scores': value.get('face_scores', []),
                        'landmark_scores': value.get('face_landmark_scores_68', []),
                        'like': value.get('like', False)
                    }
                    category_map[dir_name].append(img_info)
                    file_map[f"{dir_name}/{key}"] = abs_path
                else:
                    new_rel = os.path.join(current_rel_path, key)
                    walk_tree(value, new_rel, base_abs)

    for base in img_data:
        base_abs = os.path.abspath(os.path.normpath(base))
        walk_tree(img_data[base], "", base_abs)

    return category_map, file_map

def get_category_thumbnail(category: str) -> Dict:
    """获取分类的缩略图信息"""
    category_map, _ = load_image_data()
    return category_map.get(category, [{}])[0]

@app.route('/image/<category>/<path:filename>')
def serve_image(category: str, filename: str):
    """提供图像文件服务"""
    _, file_map = load_image_data()
    unique_id = f"{unquote(category)}/{filename}"
    
    if unique_id not in file_map:
        abort(404, description="Image not found")
    
    return send_from_directory(
        os.path.dirname(file_map[unique_id]),
        os.path.basename(file_map[unique_id])
    )

def render_category_view(page: int, category: str = None) -> str:
    """渲染分类视图模板"""
    category_map, _ = load_image_data()
    sorted_categories = sorted(category_map.keys())
    
    # 新增已收藏分类处理逻辑
    if category == '_favorites':
        # 收集所有喜欢的图片
        items = []
        for cat_imgs in category_map.values():
            for img in cat_imgs:
                if img.get('like'):
                    items.append(img)
    else:
        items = category_map.get(category, []) if category else \
                [img for cat in sorted_categories for img in category_map.get(cat, [])]
    
    paginated, total_pages = Paginator.paginate(items, page, app.config['PER_PAGE'])
    
    return render_template('index.html',
                        images=paginated,
                        current_page=page,
                        total_pages=total_pages,
                        category=category,
                        all_categories=sorted_categories)

@app.route('/')
def show_categories() -> str:
    """显示分类视图"""
    page = request.args.get('page', 1, type=int)
    category_map, _ = load_image_data()
    
    categories, total_pages = Paginator.paginate(
        sorted(category_map.keys()), page, app.config['PER_PAGE'])
    
    category_list = [{
        'name': cat,
        'thumb_url': url_for('serve_image', 
                            category=cat, 
                            filename=get_category_thumbnail(cat).get('filename', '')),
        'url': url_for('category_view', category=cat, page=1)
    } for cat in categories]
    
    return render_template('categories.html',
                         categories=category_list,
                         current_page=page,
                         total_pages=total_pages)

@app.route('/all')
def show_all_images() -> str:
    """显示所有图片"""
    page = request.args.get('page', 1, type=int)
    return render_category_view(page)

@app.route('/category/<path:category>/page/<int:page>')
@app.route('/category/<path:category>', defaults={'page': 1})
def category_view(category: str, page: int) -> str:
    """分类详情视图"""
    try:
        current_category = unquote(category)
    except UnicodeDecodeError:
        abort(404, description="Invalid category name")
    
    return render_category_view(page, current_category)

@app.route('/like_image', methods=['POST'])
def like_image() -> Response:
    global cached_raw_data
    try:
        data = request.get_json()
        req_path = os.path.normpath(data.get('path'))
        action = data.get('action', 'like')
        
        if not req_path:
            return jsonify({'success': False, 'message': 'Missing path'}), 400
        
        with data_lock:
            if cached_raw_data is None:
                with open(app.config['JSON_PATH'], 'r', encoding='utf-8') as f:
                    cached_raw_data = json.load(f)
            
            img_data = cached_raw_data.setdefault('img', {})
            found = False

            for base in list(img_data.keys()):
                base_abs = os.path.abspath(os.path.normpath(base))
                if os.path.commonpath([base_abs, req_path]) != base_abs:
                    continue
                
                rel_path = os.path.relpath(req_path, base_abs).replace('\\', '/')
                parts = rel_path.split('/')
                current = img_data[base]
                for part in parts[:-1]:
                    current = current.setdefault(part, {})
                file_node = current.get(parts[-1])
                if file_node:
                    file_node['like'] = (action == 'like')
                    found = True
                    cached_raw_data['date_updated'] = datetime.now().astimezone().isoformat()
                    break

            if not found:
                return jsonify({'success': False, 'message': 'Image not found'}), 404
            
            save_queue.put(cached_raw_data.copy())
            load_image_data.cache_clear()
            
            return jsonify({'success': True, 'action': action})
        
    except Exception as e:
        app.logger.error(f"Like error: {str(e)}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/shutdown', methods=['GET', 'POST'])
def shutdown() -> str:
    global save_thread_running
    save_thread_running = False
    # 等待保存队列完成
    save_queue.join()
    shutdown_func = request.environ.get('werkzeug.server.shutdown')
    if shutdown_func:
        try:
            shutdown_func()
            return 'Server shutting down...'
        except Exception as e:
            app.logger.error(f"正常关闭失败: {e}")
    os._exit(0)
    return 'Server forced to shutdown.'

def input_listener() -> None:
    """监听用户输入"""
    print('Press Q to quit...')
    while True:
        if input().lower() == 'q':
            try:
                requests.post(f'http://127.0.0.1:{args.port}/shutdown')
            except Exception as e:
                app.logger.error(f"Shutdown failed: {str(e)}")
            finally:
                break

if __name__ == '__main__':
    # 启动浏览器
    threading.Timer(1, lambda: webbrowser.open(f'http://127.0.0.1:{args.port}')).start()
    
    # 启动输入监听
    input_thread = threading.Thread(target=input_listener, daemon=True)
    input_thread.start()
    
    # 运行Flask应用
    app.run(host=args.host, port=args.port, debug=args.debug, use_reloader=False)