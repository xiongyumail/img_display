import unittest
import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock
from flask import json as flask_json, Response
import argparse
from collections import defaultdict
from urllib.parse import quote
import json

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from web import WebApp

class TestPaginator(unittest.TestCase):
    def test_paginate(self):
        items = list(range(100))
        page = 1
        per_page = 10
        result, total_pages = WebApp.paginate(items, page, per_page)
        self.assertEqual(len(result), per_page)

    def test_paginate_empty_list(self):
        items = []
        page = 1
        per_page = 10
        result, total_pages = WebApp.paginate(items, page, per_page)
        self.assertEqual(len(result), 0)
        self.assertEqual(total_pages, 1)

    def test_paginate_out_of_range_page(self):
        items = list(range(50))
        page = 5
        per_page = 20
        result, total_pages = WebApp.paginate(items, page, per_page)
        self.assertEqual(len(result), 0)
        self.assertEqual(total_pages, 3)

    def test_paginate_exact_multiple(self):
        items = list(range(100))
        page = 5
        per_page = 20
        result, total_pages = WebApp.paginate(items, page, per_page)
        self.assertEqual(total_pages, 5)
        self.assertEqual(len(result), 20)

    def test_paginate_invalid_page(self):
        items = list(range(10))  # [0-9]
        per_page = 5
        
        # 测试page=0时修正为1
        result, total_pages = WebApp.paginate(items, 0, per_page)
        self.assertEqual(result, [0,1,2,3,4])
        self.assertEqual(total_pages, 2)
        
        # 测试负数页码修正为1
        result, total_pages = WebApp.paginate(items, -3, per_page)
        self.assertEqual(result, [0,1,2,3,4])
        
        # 测试超过总页数的页数返回空列表
        result, total_pages = WebApp.paginate(items, 3, per_page)
        self.assertEqual(result, [])
        self.assertEqual(total_pages, 2)

    def test_paginate_zero_per_page(self):
        items = list(range(10))
        result, total_pages = WebApp.paginate(items, 1, 0)
        self.assertEqual(len(result), 0)
        self.assertEqual(total_pages, 0)  # 修改为期望0页

    def test_paginate_negative_per_page(self):
        items = list(range(10))
        result, total_pages = WebApp.paginate(items, 1, -5)
        self.assertEqual(len(result), 0)
        self.assertEqual(total_pages, 0)  # 修改为期望0页

class TestWebApp(unittest.TestCase):
    def setUp(self):
        args = argparse.Namespace(
            per_page=20,
            host='0.0.0.0',
            port=5000,
            input_json=['test.json'],
            replace=[('old', 'new')]
        )
        self.web_app = WebApp(args)
        self.web_app.app.testing = True

    def test_apply_replace_rules(self):
        data = {'key': 'old value'}
        result = self.web_app.apply_replace_rules(data)
        self.assertEqual(result['key'], 'new value')

    def test_reverse_replace_rules(self):
        data = {'key': 'new value'}
        result = self.web_app.reverse_replace_rules(data)
        self.assertEqual(result['key'], 'old value')

    @patch('os.path.commonpath')
    @patch('os.path.abspath')
    def test_like_image_multiple_paths(self, mock_abspath, mock_commonpath):
        mock_abspath.side_effect = lambda x: x
        mock_commonpath.side_effect = lambda paths: paths[0] if len(paths) == 2 else os.path.commonpath(paths)
        json_path = 'test.json'
        self.web_app.cached_raw_data[json_path] = {
            'img': {
                'base1': {
                    'file1.jpg': {'like': False},
                    'subdir': {
                        'file2.jpg': {'like': False}
                    }
                },
                'base2': {
                    'file3.jpg': {'like': True}
                }
            }
        }
        with self.web_app.app.test_client() as client:
            response = client.post(
                '/like_image',
                json={
                    'paths': [
                        'base1/file1.jpg',
                        'base1/subdir/file2.jpg',
                        'base2/invalid.jpg'
                    ],
                    'action': 'like'
                }
            )
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(len(response_data['found']), 2)
        self.assertEqual(len(response_data['not_found']), 1)
        self.assertTrue(
            self.web_app.cached_raw_data[json_path]['img']['base1']['file1.jpg']['like']
        )
        self.assertTrue(
            self.web_app.cached_raw_data[json_path]['img']['base1']['subdir']['file2.jpg']['like']
        )

    def test_like_image_no_paths(self):
        with self.web_app.app.test_client() as client:
            response = client.post('/like_image', json={'action': 'like'})
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['message'], 'No paths provided')

    @patch('os.path.commonpath')
    @patch('os.path.abspath')
    def test_like_image_all_not_found(self, mock_abspath, mock_commonpath):
        mock_abspath.side_effect = lambda x: x
        mock_commonpath.side_effect = lambda paths: 'invalid_base'
        json_path = 'test.json'
        self.web_app.cached_raw_data[json_path] = {'img': {}}
        with self.web_app.app.test_client() as client:
            response = client.post(
                '/like_image',
                json={
                    'paths': ['invalid/path1.jpg', 'invalid/path2.jpg'],
                    'action': 'like'
                }
            )
        self.assertEqual(response.status_code, 404)
        response_data = json.loads(response.data)
        self.assertEqual(len(response_data['not_found']), 2)

    @patch('web.render_template')
    def test_render_category_view_total_images(self, mock_render):
        mock_render.return_value = ''
        test_items = [{'filename': f'img{i}.jpg'} for i in range(30)]
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list, {'test_cat': test_items}),
            {}
        ))
        with self.web_app.app.test_request_context('/'):
            self.web_app.render_category_view(page=1, category='test_cat')
            args, kwargs = mock_render.call_args
            self.assertEqual(kwargs['total_images'], 30)

    def test_select_json_valid_index(self):
        with self.web_app.app.test_client() as client:
            client.get('/select_json/0')
            with client.session_transaction() as sess:
                self.assertEqual(sess['current_json_index'], 0)

    def test_select_json_invalid_index(self):
        with self.web_app.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['current_json_index'] = 0
            client.get('/select_json/999')
            with client.session_transaction() as sess:
                self.assertEqual(sess['current_json_index'], 0)

    def test_serve_image_not_found(self):
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list),
            {}
        ))
        with self.web_app.app.test_client() as client:
            response = client.get('/image/invalid_cat/nonexistent.jpg')
            self.assertEqual(response.status_code, 404)
            self.assertIn('Image not found', response.get_data(as_text=True))

    @patch('web.render_template')
    def test_render_favorites_category(self, mock_render):
        mock_render.return_value = ''
        test_items = [
            {'filename': 'img1.jpg', 'like': True, 'category': 'cat1', 'face_scores': []},
            {'filename': 'img2.jpg', 'like': False, 'category': 'cat1', 'face_scores': []},
            {'filename': 'img3.jpg', 'like': True, 'category': 'cat1', 'face_scores': []},
            {'filename': 'img4.jpg', 'like': True, 'category': 'cat1', 'face_scores': []},
            {'filename': 'img5.jpg', 'like': False, 'category': 'cat1', 'face_scores': []}
        ]
        category_map = defaultdict(list, {'cat1': test_items})
        self.web_app.load_image_data = MagicMock(return_value=(category_map, {}))
        with self.web_app.app.test_request_context('/category/_favorites'):
            self.web_app.render_category_view(page=1, category='_favorites')
            args, kwargs = mock_render.call_args
            self.assertEqual(len(kwargs['images']), 3)

    @patch('web.render_template')
    def test_render_category_with_seed(self, mock_render):
        mock_render.return_value = ''
        test_items = [{'filename': f'img{i}.jpg'} for i in range(50)]
        category_map = defaultdict(list, {'test_cat': test_items})
        self.web_app.load_image_data = MagicMock(return_value=(category_map, {}))
        seed = '12345'
        with self.web_app.app.test_request_context(f'/?seed={seed}'):
            self.web_app.render_category_view(page=1, seed=seed)
            first_call_images = mock_render.call_args[1]['images']
        mock_render.reset_mock()
        with self.web_app.app.test_request_context(f'/?seed={seed}'):
            self.web_app.render_category_view(page=1, seed=seed)
            second_call_images = mock_render.call_args[1]['images']
        self.assertEqual([img['filename'] for img in first_call_images],
                         [img['filename'] for img in second_call_images])

    def test_get_category_thumbnail(self):
        test_items = [{'filename': 'thumb.jpg'}, {'filename': 'img2.jpg'}]
        category_map = defaultdict(list, {'test_cat': test_items})
        self.web_app.load_image_data = MagicMock(return_value=(category_map, {}))
        thumbnail = self.web_app.get_category_thumbnail('test_cat')
        self.assertEqual(thumbnail['filename'], 'thumb.jpg')

    def test_get_category_thumbnail_empty(self):
        self.web_app.load_image_data = MagicMock(return_value=(defaultdict(list), {}))
        thumbnail = self.web_app.get_category_thumbnail('empty_cat')
        self.assertEqual(thumbnail, {})

    def test_serve_image_success(self):
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list),
            {'test_cat/test.jpg': '/mock/path/test.jpg'}
        ))
        with patch('web.send_from_directory') as mock_send:
            mock_send.return_value = 'image data'
            with self.web_app.app.test_client() as client:
                response = client.get('/image/test_cat/test.jpg')
                self.assertEqual(response.status_code, 200)
                mock_send.assert_called_with('/mock/path', 'test.jpg')

    def test_reverse_replace_rules_nested_data(self):
        test_data = {
            'message': 'new message',
            'items': [
                {'text': 'new item'},
                {'nested': {'value': 'new value'}}
            ]
        }
        expected_data = {
            'message': 'old message',
            'items': [
                {'text': 'old item'},
                {'nested': {'value': 'old value'}}
            ]
        }
        reversed_data = self.web_app.reverse_replace_rules(test_data)
        self.assertEqual(reversed_data, expected_data)

    def test_unlike_image(self):
        json_path = 'test.json'
        mock_base = os.path.abspath('mock_base')
        self.web_app.cached_raw_data[json_path] = {
            'img': {
                mock_base: {
                    'image.jpg': {'like': True, 'face_scores': [1]}
                }
            }
        }
        with self.web_app.app.test_client() as client:
            response = client.post('/like_image', json={
                'path': os.path.join(mock_base, 'image.jpg'),
                'action': 'unlike'
            })
            self.assertEqual(response.status_code, 200)
            self.assertFalse(
                self.web_app.cached_raw_data[json_path]['img'][mock_base]['image.jpg']['like']
            )

    def test_switch_json_files(self):
        self.web_app.json_files = ['first.json', 'second.json']
        self.web_app.cached_raw_data = {
            'first.json': {'img': {'base1': {}}},
            'second.json': {'img': {'base2': {}}}
        }
        with self.web_app.app.test_client() as client:
            client.get('/select_json/1')
            current_json = self.web_app.get_current_json_path()
            self.assertEqual(current_json, 'second.json')

    def test_select_json_out_of_range_index(self):
        self.web_app.json_files = ['test1.json', 'test2.json']
        with self.web_app.app.test_client() as client:
            with client.session_transaction() as sess:
                sess['current_json_index'] = 1
            client.get('/select_json/999')
            with client.session_transaction() as sess:
                self.assertEqual(sess['current_json_index'], 0)

    def test_multiple_replace_rules(self):
        self.web_app.replace_rules = [('a', 'b'), ('b', 'c')]
        data = {'key': 'a'}
        result = self.web_app.apply_replace_rules(data)
        self.assertEqual(result['key'], 'c')
        reversed_data = self.web_app.reverse_replace_rules({'key': 'c'})
        self.assertEqual(reversed_data['key'], 'a')

    @patch('web.WebApp.apply_replace_rules')
    def test_load_image_data_cache(self, mock_replace):
        mock_replace.return_value = {'img': {}}
        json_path = 'test.json'
        self.web_app.get_current_json_path = lambda: json_path
        self.web_app.load_image_data()
        self.assertTrue(mock_replace.called)
        mock_replace.reset_mock()
        self.web_app.load_image_data()
        self.assertFalse(mock_replace.called)

    def test_category_view_invalid_category(self):
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list, {'valid_cat': []}),
            {}
        ))
        with self.web_app.app.test_client() as client:
            response = client.get('/category/invalid_category')
            self.assertEqual(response.status_code, 404)

    @patch('web.open', side_effect=FileNotFoundError("File not found"))
    def test_load_image_data_file_not_found(self, mock_open):
        self.web_app.get_current_json_path = lambda: 'missing.json'
        
        # 使用patch.object模拟logger.error方法
        with patch.object(self.web_app.app.logger, 'error') as mock_error:
            category_map, file_map = self.web_app.load_image_data()
            # 验证日志调用
            mock_error.assert_called_with("Load data failed for missing.json: File not found")
        
        self.assertEqual(len(category_map), 0)
        self.assertEqual(len(file_map), 0)

    def test_like_image_invalid_json(self):
        with self.web_app.app.test_client() as client:
            # 发送无效JSON数据
            response = client.post('/like_image', 
                                data='{invalid json', 
                                content_type='application/json')
            self.assertEqual(response.status_code, 400)  # 现在应返回400而非500
            response_data = json.loads(response.data)
            self.assertFalse(response_data['success'])
            self.assertIn('Invalid JSON', response_data['message'])

    def test_serve_image_encoded_path(self):
        # 测试URL编码的路径参数
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list),
            {'测试分类/图片 1.jpg': '/mock/path/图片 1.jpg'}
        ))
        encoded_category = quote('测试分类')
        encoded_filename = quote('图片 1.jpg')
        with patch('web.send_from_directory') as mock_send:
            mock_send.return_value = 'image data'
            with self.web_app.app.test_client() as client:
                response = client.get(f'/image/{encoded_category}/{encoded_filename}')
                self.assertEqual(response.status_code, 200)
                mock_send.assert_called_with('/mock/path', '图片 1.jpg')

    def test_multiple_replace_rules_order(self):
        self.web_app.replace_rules = [('a', 'b'), ('b', 'c')]
        data = {'text': 'a'}
        replaced = self.web_app.apply_replace_rules(data)
        self.assertEqual(replaced['text'], 'c')
        reversed_data = self.web_app.reverse_replace_rules({'text': 'c'})
        self.assertEqual(reversed_data['text'], 'a')

    def test_category_thumbnail_with_empty_category(self):
        self.web_app.load_image_data = MagicMock(return_value=(defaultdict(list), {}))
        thumbnail = self.web_app.get_category_thumbnail('empty')
        self.assertEqual(thumbnail, {})

    def test_like_image_single_path(self):
        json_path = 'test.json'
        mock_base = os.path.abspath('mock_base')
        self.web_app.cached_raw_data[json_path] = {
            'img': {
                mock_base: {
                    'image.jpg': {'like': False}
                }
            }
        }
        with self.web_app.app.test_client() as client:
            response = client.post(
                '/like_image',
                json={
                    'path': os.path.join(mock_base, 'image.jpg'),
                    'action': 'like'
                }
            )
        self.assertEqual(response.status_code, 200)
        self.assertTrue(
            self.web_app.cached_raw_data[json_path]['img'][mock_base]['image.jpg']['like']
        )

    @patch('web.render_template')
    def test_seed_generates_random_order(self, mock_render):
        mock_render.return_value = ''
        test_items = [{'filename': f'img{i}.jpg'} for i in range(50)]
        category_map = defaultdict(list, {'test_cat': test_items})
        self.web_app.load_image_data = MagicMock(return_value=(category_map, {}))
        
        # 第一次请求生成seed
        with self.web_app.app.test_client() as client:
            response = client.get('/category/_favorites')
            self.assertEqual(response.status_code, 302)
            self.assertTrue('seed=' in response.location)
        
        # 使用相同seed两次请求结果应一致
        seed = '12345'
        with self.web_app.app.test_request_context(f'/category/_favorites?seed={seed}'):
            self.web_app.render_category_view(page=1, category='_favorites', seed=seed)
            first_call_images = mock_render.call_args[1]['images']
        
        mock_render.reset_mock()
        
        with self.web_app.app.test_request_context(f'/category/_favorites?seed={seed}'):
            self.web_app.render_category_view(page=1, category='_favorites', seed=seed)
            second_call_images = mock_render.call_args[1]['images']
        
        self.assertEqual(
            [img['filename'] for img in first_call_images],
            [img['filename'] for img in second_call_images]
        )

    def test_serve_image_with_spaces(self):
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list),
            {'test cat/image 1.jpg': '/mock/path/image 1.jpg'}
        ))
        encoded_category = quote('test cat')
        encoded_filename = quote('image 1.jpg')
        with patch('web.send_from_directory') as mock_send:
            mock_send.return_value = 'image data'
            with self.web_app.app.test_client() as client:
                response = client.get(f'/image/{encoded_category}/{encoded_filename}')
                self.assertEqual(response.status_code, 200)
                mock_send.assert_called_with('/mock/path', 'image 1.jpg')

    def test_switch_json_and_data_loading(self):
        self.web_app.json_files = ['first.json', 'second.json']
        self.web_app.cached_raw_data = {
            'first.json': {'img': {'base1': {'img1.jpg': {'face_scores': [1]}}}},
            'second.json': {'img': {'base2': {'img2.jpg': {'face_scores': [1]}}}}
        }
        with self.web_app.app.test_client() as client:
            client.get('/select_json/1')
            current_json = self.web_app.get_current_json_path()
            self.assertEqual(current_json, 'second.json')
            category_map, _ = self.web_app.load_image_data()
            # 验证是否加载了第二个JSON的数据
            self.assertTrue(any('base2' in cat for cat in category_map.keys()))

    @patch('web.open')
    @patch('json.load', side_effect=json.JSONDecodeError("Syntax error", "doc", 0))
    def test_load_image_data_json_decode_error(self, mock_json_load, mock_open):
        self.web_app.get_current_json_path = lambda: 'invalid.json'
        with patch.object(self.web_app.app.logger, 'error') as mock_error:
            category_map, file_map = self.web_app.load_image_data()
            # 验证错误消息前缀匹配（忽略具体位置信息）
            mock_error.assert_called_once()
            args, _ = mock_error.call_args
            self.assertTrue(
                args[0].startswith("Load data failed for invalid.json: Syntax error"),
                f"Expected error message to start with 'Syntax error', but got: {args[0]}"
            )
        self.assertEqual(len(category_map), 0)
        self.assertEqual(len(file_map), 0)

    def test_serve_image_mime_type(self):
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list),
            {'test_cat/test.jpg': '/mock/path/test.jpg'}
        ))
        with patch('web.send_from_directory') as mock_send:
            # 创建真实的 Response 对象并设置 Content-Type
            mock_response = Response(
                response=b'mock image data',
                status=200,
                mimetype='image/jpeg'  # 直接设置 MIME 类型
            )
            mock_send.return_value = mock_response
            
            with self.web_app.app.test_client() as client:
                response = client.get('/image/test_cat/test.jpg')
                # 验证响应头
                self.assertEqual(response.mimetype, 'image/jpeg')
                # 验证调用参数
                mock_send.assert_called_with(
                    os.path.dirname('/mock/path/test.jpg'),
                    os.path.basename('/mock/path/test.jpg')
                )

    @patch('web.render_template')
    def test_show_categories_renders_template(self, mock_render):
        mock_render.return_value = ''
        # 确保分类包含至少一个图片
        test_categories = ['cat1', 'cat2']
        category_map = defaultdict(list, {
            'cat1': [{'filename': 'thumb1.jpg'}],
            'cat2': [{'filename': 'thumb2.jpg'}]
        })
        self.web_app.load_image_data = MagicMock(return_value=(category_map, {}))
        with self.web_app.app.test_client() as client:
            client.get('/')
            args, kwargs = mock_render.call_args
            # 验证每个分类都有缩略图
            for cat in kwargs['categories']:
                self.assertNotEqual(cat['thumb_url'], '')

    def test_shutdown_route_normal(self):
        """测试正常关闭流程（存在werkzeug的shutdown函数）"""
        # 创建模拟的队列对象
        mock_queue = MagicMock()
        self.web_app.save_queue = mock_queue
        
        with self.web_app.app.test_client() as client:
            # 注入shutdown_func到请求环境中
            response = client.get(
                '/shutdown',
                environ_overrides={'werkzeug.server.shutdown': lambda: None}
            )
            
            self.assertEqual(response.status_code, 200)
            self.assertIn('Server shutting down', response.get_data(as_text=True))
            self.assertFalse(self.web_app.save_thread_running)
            mock_queue.join.assert_called_once()  # 验证队列完成

    @patch('web.os._exit')
    def test_shutdown_route_forced(self, mock_exit):
        """测试强制关闭流程（无werkzeug的shutdown函数）"""
        mock_queue = MagicMock()
        self.web_app.save_queue = mock_queue
        
        with self.web_app.app.test_client() as client:
            response = client.get('/shutdown')
            self.assertEqual(response.status_code, 200)
            self.assertIn('Server forced to shutdown', response.get_data(as_text=True))
            mock_queue.join.assert_called_once()  # 验证队列完成
            mock_exit.assert_called_with(0)

    def test_show_all_images_pagination(self):
        """测试/all路由的分页是否正确"""
        # 模拟有75个图片数据，补充所有模板需要的字段
        test_items = [{
            'filename': f'img{i}.jpg',
            'face_scores': [],
            'landmark_scores': [],
            'like': False,
            'category': 'cat1',
            'path': f'/mock/path/img{i}.jpg'
        } for i in range(75)]
        
        # 使用Mock捕获渲染参数进行验证
        with patch('web.render_template') as mock_render:
            mock_render.return_value = ''
            self.web_app.load_image_data = MagicMock(return_value=(
                defaultdict(list, {'cat1': test_items}),
                {}
            ))
            with self.web_app.app.test_client() as client:
                # 测试第一页
                client.get('/all?page=1')
                
                # 验证分页参数
                args, kwargs = mock_render.call_args
                self.assertEqual(len(kwargs['images']), 20)     # 每页数量
                self.assertEqual(kwargs['current_page'], 1)       # 当前页码
                self.assertEqual(kwargs['total_pages'], 4)       # 总页数 75/20=3.75→4
                self.assertEqual(kwargs['total_images'], 75)     # 总图片数

    def test_apply_replace_rules_nested_list(self):
        """测试替换规则应用于嵌套列表结构"""
        self.web_app.replace_rules = [('old', 'new')]
        data = {
            'items': [
                {'name': 'old item'},
                {'subitems': [{'value': 'old value'}]}
            ]
        }
        result = self.web_app.apply_replace_rules(data)
        self.assertEqual(result['items'][0]['name'], 'new item')
        self.assertEqual(result['items'][1]['subitems'][0]['value'], 'new value')

    def test_reverse_replace_rules_complex_structure(self):
        """测试反转替换规则处理复杂结构"""
        self.web_app.replace_rules = [('a', 'b'), ('b', 'c')]
        data = {
            'key': 'c',
            'nested': {
                'list': ['c', 'd']
            }
        }
        expected = {
            'key': 'a',
            'nested': {
                'list': ['a', 'd']
            }
        }
        result = self.web_app.reverse_replace_rules(data)
        self.assertEqual(result, expected)

    def test_category_view_favorites_without_seed(self):
        """测试收藏夹视图是否自动生成随机种子并重定向"""
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list, {
                'cat1': [{'filename': 'img1.jpg', 'like': True}]
            }),
            {}
        ))
        with self.web_app.app.test_client() as client:
            response = client.get('/category/_favorites')
            self.assertEqual(response.status_code, 302)
            self.assertTrue('seed=' in response.location)

    def test_category_view_unfavorites_pagination(self):
        """测试非收藏夹视图的分页和总数统计"""
        # 构建测试数据（所有项like=False）
        test_items = [{
            'filename': f'img{i}.jpg',
            'face_scores': [0.9],
            'landmark_scores': [[1,2]],
            'like': False,  # 确保所有项未收藏
            'category': 'cat1',
            'path': f'/base/cat1/img{i}.jpg'
        } for i in range(35)]

        # 配置Mock数据
        with patch('web.render_template') as mock_render:
            mock_render.return_value = 'rendered content'
            
            # 模拟数据加载返回多个分类的数据
            self.web_app.load_image_data = MagicMock(return_value=(
                defaultdict(list, {
                    'cat1': test_items,
                    'cat2': [{'filename': 'other.jpg', 'like': True}]  # 其他分类不影响测试
                }),
                {f'cat1/img{i}.jpg': f'/base/cat1/img{i}.jpg' for i in range(35)}
            ))

            with self.web_app.app.test_client() as client:
                # 使用查询参数传递页码（关键修正点）
                response = client.get('/category/_unfavorites?page=2&seed=123')
                
                # 验证HTTP响应状态码
                self.assertEqual(response.status_code, 200)
                
                # 验证模板渲染参数
                args, kwargs = mock_render.call_args
                self.assertEqual(len(kwargs['images']), 15)  # 35-20=15
                self.assertEqual(kwargs['current_page'], 2)
                self.assertEqual(kwargs['total_pages'], 2)  # ceil(35/20)=2
                self.assertEqual(kwargs['total_images'], 35)

if __name__ == '__main__':
    unittest.main()