import json
import os
import math
from functools import lru_cache
from flask import Flask, render_template, send_from_directory, abort, request, url_for, jsonify, Response, redirect, session
from urllib.parse import quote, unquote
import threading
from typing import Tuple, Dict, List, Any
from queue import Queue, Empty
from collections import defaultdict
from datetime import datetime
from config import get_config
import random

class WebApp:
    def __init__(self, args):
        self.args = args
        self.json_files = args.input_json  # 存储多个JSON文件路径
        self.replace_rules = args.replace if args.replace else []
        self.app = Flask(__name__)
        self.app.secret_key = os.urandom(24)  # 启用session
        self.app.config['PER_PAGE'] = args.per_page
        self.data_lock = threading.Lock()
        self.save_queue = Queue()
        self.save_thread_running = True
        self.cached_raw_data = {}  # 缓存各JSON文件数据 {path: data}
        self.save_consumer_thread = threading.Thread(target=self.save_consumer, daemon=True)
        self.save_consumer_thread.start()
        self.setup_routes()

    def apply_replace_rules(self, data):
        if not self.replace_rules:
            return data
        data_str = json.dumps(data)
        for old, new in self.replace_rules:
            data_str = data_str.replace(old, new)
        return json.loads(data_str)

    def reverse_replace_rules(self, data):
        if not self.replace_rules:
            return data
        data_str = json.dumps(data)
        for old, new in reversed(self.replace_rules):
            data_str = data_str.replace(new, old)
        return json.loads(data_str)

    def setup_routes(self):
        self.app.route('/')(self.show_categories)
        self.app.route('/all')(self.show_all_images)
        self.app.route('/category/<path:category>/page/<int:page>')(self.category_view)
        self.app.route('/category/<path:category>', defaults={'page': 1})(self.category_view)
        self.app.route('/like_image', methods=['POST'])(self.like_image)
        self.app.route('/shutdown', methods=['GET', 'POST'])(self.shutdown)
        self.app.route('/image/<category>/<path:filename>')(self.serve_image)
        self.app.route('/select_json/<int:json_index>')(self.select_json)

    def get_current_json_path(self):
        current_index = session.get('current_json_index', 0)
        if current_index >= len(self.json_files):
            current_index = 0
            session['current_json_index'] = current_index
        return self.json_files[current_index]

    def load_image_data(self) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        json_path = self.get_current_json_path()
        
        with self.data_lock:
            if json_path not in self.cached_raw_data:
                try:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        raw_data = json.load(f)
                        self.cached_raw_data[json_path] = self.apply_replace_rules(raw_data)
                except Exception as e:
                    self.app.logger.error(f"Load data failed for {json_path}: {str(e)}")
                    return defaultdict(list), {}

            img_data = self.cached_raw_data[json_path].get('img', {})
            category_map = defaultdict(list)
            file_map = {}

            def walk_tree(node, current_rel_path, base_abs):
                for key, value in node.items():
                    if isinstance(value, dict):
                        if 'face_scores' in value:
                            if not value.get('face_scores'):
                                continue

                            abs_path = os.path.normpath(os.path.join(base_abs, current_rel_path, key))
                            parent_relative_dir = current_rel_path.replace('\\', '/')
                            dir_name = os.path.basename(base_abs) if parent_relative_dir == "" else parent_relative_dir
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
                            walk_tree(value, os.path.join(current_rel_path, key), base_abs)

            for base in img_data:
                base_abs = os.path.abspath(os.path.normpath(base))
                walk_tree(img_data[base], "", base_abs)

            return category_map, file_map

    def select_json(self, json_index):
        if 0 <= json_index < len(self.json_files):
            session['current_json_index'] = json_index
        return redirect(request.referrer or url_for('show_categories'))

    def serve_image(self, category: str, filename: str):
        category_map, file_map = self.load_image_data()
        unique_id = f"{unquote(category)}/{filename}"
        
        if unique_id not in file_map:
            abort(404, description="Image not found")
            
        return send_from_directory(
            os.path.dirname(file_map[unique_id]),
            os.path.basename(file_map[unique_id])
        )

    def render_category_view(self, page: int, category: str = None, seed: str = None) -> str:
        category_map, _ = self.load_image_data()
        sorted_categories = sorted(category_map.keys())

        if category == '_favorites':
            items = [img for cat_imgs in category_map.values() for img in cat_imgs if img.get('like')]
        elif category == '_unfavorites':
            items = [img for cat_imgs in category_map.values() for img in cat_imgs if not img.get('like', False)]
        else:
            items = category_map.get(category, []) if category else [img for cat in sorted_categories for img in category_map.get(cat, [])]

        if seed and category in ('_favorites', '_unfavorites'):
            try:
                random.seed(int(seed))
                random.shuffle(items)
            except ValueError:
                random.shuffle(items)

        paginated, total_pages = self.paginate(items, page, self.app.config['PER_PAGE'])
        return render_template('index.html',
                               images=paginated,
                               current_page=page,
                               total_pages=total_pages,
                               category=category,
                               all_categories=sorted_categories,
                               json_files=self.json_files,
                               current_json_index=session.get('current_json_index', 0),
                               seed=seed)

    def show_categories(self) -> str:
        page = request.args.get('page', 1, type=int)
        category_map, _ = self.load_image_data()
        categories, total_pages = self.paginate(sorted(category_map.keys()), page, self.app.config['PER_PAGE'])
        
        category_list = [{
            'name': cat,
            'thumb_url': url_for('serve_image', category=cat, filename=self.get_category_thumbnail(cat).get('filename', '')),
            'url': url_for('category_view', category=cat, page=1)
        } for cat in categories]

        return render_template('categories.html',
                               categories=category_list,
                               current_page=page,
                               total_pages=total_pages,
                               json_files=self.json_files,
                               current_json_index=session.get('current_json_index', 0))

    def show_all_images(self) -> str:
        page = request.args.get('page', 1, type=int)
        return self.render_category_view(page)

    def category_view(self, category: str, page: int) -> str:
        try:
            current_category = unquote(category)
        except UnicodeDecodeError:
            abort(404, description="Invalid category name")

        seed = request.args.get('seed', default=None, type=str)
        if current_category in ('_favorites', '_unfavorites') and not seed:
            seed = str(random.randint(0, 999999999))
            return redirect(url_for('category_view', category=current_category, page=page, seed=seed))
        
        return self.render_category_view(page, current_category, seed)

    def like_image(self) -> Response:
        json_path = self.get_current_json_path()
        try:
            data = request.get_json()
            req_path = os.path.normpath(data.get('path'))
            action = data.get('action', 'like')

            with self.data_lock:
                if json_path not in self.cached_raw_data:
                    with open(json_path, 'r', encoding='utf-8') as f:
                        self.cached_raw_data[json_path] = json.load(f)
                
                img_data = self.cached_raw_data[json_path].setdefault('img', {})
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
                        self.cached_raw_data[json_path]['date_updated'] = datetime.now().astimezone().isoformat()
                        found = True
                        break

                if not found:
                    return jsonify({'success': False, 'message': 'Image not found'}), 404

                self.save_queue.put((json_path, self.cached_raw_data[json_path].copy()))
                return jsonify({'success': True, 'action': action})

        except Exception as e:
            self.app.logger.error(f"Like error: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

    def save_consumer(self):
        while self.save_thread_running:
            try:
                json_path, data = self.save_queue.get(timeout=1)
                with self.data_lock:
                    reversed_data = self.reverse_replace_rules(data)
                    with open(json_path, 'w', encoding='utf-8') as f:
                        json.dump(reversed_data, f, ensure_ascii=False, indent=4)
                self.save_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self.app.logger.error(f"Async save failed: {str(e)}")

    def shutdown(self) -> str:
        self.save_thread_running = False
        self.save_queue.join()
        shutdown_func = request.environ.get('werkzeug.server.shutdown')
        if shutdown_func:
            shutdown_func()
            return 'Server shutting down...'
        os._exit(0)
        return 'Server forced to shutdown.'

    @staticmethod
    def paginate(items: List[Any], page: int, per_page: int) -> Tuple[List[Any], int]:
        if not items:
            return [], 1  # 处理空列表的情况
        start = (page - 1) * per_page
        end = start + per_page
        result = items[start:end]
        total_pages = math.ceil(len(items) / per_page)
        return result, total_pages

    def get_category_thumbnail(self, category: str) -> Dict:
        category_map, _ = self.load_image_data()
        return category_map.get(category, [{}])[0]