import json
import os
import math
from functools import lru_cache
from flask import Flask, render_template, send_from_directory, abort, request, url_for, jsonify, Response, redirect
from urllib.parse import quote, unquote
import webbrowser
import threading
from typing import Tuple, Dict, List, Any
import requests
from queue import Queue, Empty
from collections import defaultdict
from datetime import datetime
from config import get_config
import random

class ImageGalleryApp:
    def __init__(self):
        self.args = get_config()
        self.app = Flask(__name__)
        self.app.config.update({
            'PER_PAGE': self.args.per_page,
            'JSON_PATH': os.path.normpath(os.path.join(os.path.dirname(__file__), self.args.input_json))
        })
        self.app.jinja_env.filters['urlencode'] = lambda s: quote(s.encode('utf-8'))
        self.data_lock = threading.Lock()
        self.save_queue = Queue()
        self.save_thread_running = True
        self.cached_raw_data = None
        self.save_consumer_thread = threading.Thread(target=self.save_consumer, daemon=True)
        self.save_consumer_thread.start()
        self.setup_routes()

    def setup_routes(self):
        self.app.route('/')(self.show_categories)
        self.app.route('/all')(self.show_all_images)
        self.app.route('/category/<path:category>/page/<int:page>')(self.category_view)
        self.app.route('/category/<path:category>', defaults={'page': 1})(self.category_view)
        self.app.route('/like_image', methods=['POST'])(self.like_image)
        self.app.route('/shutdown', methods=['GET', 'POST'])(self.shutdown)
        self.app.route('/image/<category>/<path:filename>')(self.serve_image)

    def save_consumer(self):
        while self.save_thread_running:
            try:
                data = self.save_queue.get(timeout=1)
                with self.data_lock:
                    with open(self.app.config['JSON_PATH'], 'w', encoding='utf-8') as f:
                        json.dump(data, f, ensure_ascii=False, indent=4)
                self.save_queue.task_done()
            except Empty:
                continue
            except Exception as e:
                self.app.logger.error(f"Async save failed: {str(e)}")

    @lru_cache(maxsize=1)
    def load_image_data(self) -> Tuple[Dict[str, List[Dict]], Dict[str, str]]:
        with self.data_lock:
            if self.cached_raw_data is None:
                try:
                    with open(self.app.config['JSON_PATH'], 'r', encoding='utf-8') as f:
                        self.cached_raw_data = json.load(f)
                except Exception as e:
                    self.app.logger.error(f"Load initial data failed: {str(e)}")
                    return {}, {}

        category_map: Dict[str, List[Dict]] = defaultdict(list)
        file_map: Dict[str, str] = {}

        img_data = self.cached_raw_data.get('img', {})

        def walk_tree(node, current_rel_path, base_abs):
            for key, value in node.items():
                if isinstance(value, dict):
                    if 'face_scores' in value:
                        if not value.get('face_scores'):
                            continue

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

    def get_category_thumbnail(self, category: str) -> Dict:
        category_map, _ = self.load_image_data()
        return category_map.get(category, [{}])[0]

    def serve_image(self, category: str, filename: str):
        _, file_map = self.load_image_data()
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
            items = [img for cat_imgs in category_map.values()
                     for img in cat_imgs if img.get('like')]
        elif category == '_unfavorites':
            items = [img for cat_imgs in category_map.values()
                     for img in cat_imgs if not img.get('like', False)]
        else:
            items = category_map.get(category, []) if category else \
                [img for cat in sorted_categories for img in category_map.get(cat, [])]

        if category in ('_favorites', '_unfavorites') and seed:
            try:
                random.seed(int(seed))
                random.shuffle(items)
            except ValueError:
                random.shuffle(items)

        paginated, total_pages = Paginator.paginate(items, page, self.app.config['PER_PAGE'])

        return render_template('index.html',
                              images=paginated,
                              current_page=page,
                              total_pages=total_pages,
                              category=category,
                              all_categories=sorted_categories,
                              seed=seed)

    def show_categories(self) -> str:
        page = request.args.get('page', 1, type=int)
        category_map, _ = self.load_image_data()

        categories, total_pages = Paginator.paginate(
            sorted(category_map.keys()), page, self.app.config['PER_PAGE'])

        category_list = [{
            'name': cat,
            'thumb_url': url_for('serve_image',
                                category=cat,
                                filename=self.get_category_thumbnail(cat).get('filename', '')),
            'url': url_for('category_view', category=cat, page=1)
        } for cat in categories]

        return render_template('categories.html',
                              categories=category_list,
                              current_page=page,
                              total_pages=total_pages)

    def show_all_images(self) -> str:
        page = request.args.get('page', 1, type=int)
        return self.render_category_view(page)

    def category_view(self, category: str, page: int) -> str:
        try:
            current_category = unquote(category)
        except UnicodeDecodeError:
            abort(404, description="Invalid category name")

        seed = request.args.get('seed', default=None, type=str)
        if current_category in ('_favorites', '_unfavorites'):
            if not seed:
                seed = str(random.randint(0, 999999999))
                return redirect(url_for('category_view',
                                       category=current_category,
                                       page=page,
                                       seed=seed))

        return self.render_category_view(page, current_category, seed)

    def like_image(self) -> Response:
        try:
            data = request.get_json()
            req_path = os.path.normpath(data.get('path'))
            action = data.get('action', 'like')

            if not req_path:
                return jsonify({'success': False, 'message': 'Missing path'}), 400

            with self.data_lock:
                if self.cached_raw_data is None:
                    with open(self.app.config['JSON_PATH'], 'r', encoding='utf-8') as f:
                        self.cached_raw_data = json.load(f)

                img_data = self.cached_raw_data.setdefault('img', {})
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
                        self.cached_raw_data['date_updated'] = datetime.now().astimezone().isoformat()
                        break

                if not found:
                    return jsonify({'success': False, 'message': 'Image not found'}), 404

                self.save_queue.put(self.cached_raw_data.copy())
                self.load_image_data.cache_clear()

                return jsonify({'success': True, 'action': action})

        except Exception as e:
            self.app.logger.error(f"Like error: {str(e)}")
            return jsonify({'success': False, 'message': str(e)}), 500

    def shutdown(self) -> str:
        self.save_thread_running = False
        self.save_queue.join()
        shutdown_func = request.environ.get('werkzeug.server.shutdown')
        if shutdown_func:
            try:
                shutdown_func()
                return 'Server shutting down...'
            except Exception as e:
                self.app.logger.error(f"正常关闭失败: {e}")
        os._exit(0)
        return 'Server forced to shutdown.'

    def input_listener(self) -> None:
        print('Press Q to quit...')
        while True:
            if input().lower() == 'q':
                try:
                    requests.post(f'http://127.0.0.1:{self.args.port}/shutdown')
                except Exception as e:
                    self.app.logger.error(f"Shutdown failed: {str(e)}")
                finally:
                    break

    def run(self):
        threading.Timer(1, lambda: webbrowser.open(f'http://127.0.0.1:{self.args.port}')).start()
        input_thread = threading.Thread(target=self.input_listener, daemon=True)
        input_thread.start()
        self.app.run(host=self.args.host, port=self.args.port, debug=self.args.debug, use_reloader=False)

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

if __name__ == '__main__':
    app = ImageGalleryApp()
    app.run()