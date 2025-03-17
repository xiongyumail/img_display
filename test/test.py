import unittest
import sys
import os
from unittest.mock import patch, MagicMock, call
from flask import json
# 将项目根目录添加到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_args, ConfigGUI
from web import WebApp
import argparse
from collections import defaultdict

class TestConfig(unittest.TestCase):
    def test_parse_args(self):
        args = parse_args()
        self.assertEqual(args.per_page, 20)
        self.assertEqual(args.host, '0.0.0.0')
        self.assertEqual(args.port, 5000)

class TestPaginator(unittest.TestCase):
    def test_paginate(self):
        items = list(range(100))
        page = 1
        per_page = 10
        # 调用WebApp的静态paginate方法
        result, total_pages = WebApp.paginate(items, page, per_page)
        self.assertEqual(len(result), per_page)

    def test_paginate_empty_list(self):
        items = []
        page = 1
        per_page = 10
        # 调用WebApp的静态paginate方法
        result, total_pages = WebApp.paginate(items, page, per_page)
        self.assertEqual(len(result), 0)
        self.assertEqual(total_pages, 1)

class TestWebApp(unittest.TestCase):
    def setUp(self):
        # 创建一个模拟的参数对象
        args = argparse.Namespace(
            per_page=20,
            host='0.0.0.0',
            port=5000,
            input_json=['test.json'],  # 修改为列表形式
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
        """测试批量点赞多个路径的情况"""
        # 模拟路径处理
        mock_abspath.side_effect = lambda x: x
        mock_commonpath.side_effect = lambda paths: paths[0] if len(paths) == 2 else os.path.commonpath(paths)
        
        # 设置测试数据
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
        
        # 构造请求
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
        
        # 验证响应
        self.assertEqual(response.status_code, 200)
        response_data = json.loads(response.data)
        self.assertEqual(len(response_data['found']), 2)
        self.assertEqual(len(response_data['not_found']), 1)
        
        # 验证数据更新
        self.assertTrue(
            self.web_app.cached_raw_data[json_path]['img']['base1']['file1.jpg']['like']
        )
        self.assertTrue(
            self.web_app.cached_raw_data[json_path]['img']['base1']['subdir']['file2.jpg']['like']
        )

    def test_like_image_no_paths(self):
        """测试未提供路径时返回错误"""
        with self.web_app.app.test_client() as client:
            response = client.post('/like_image', json={'action': 'like'})
        
        self.assertEqual(response.status_code, 400)
        response_data = json.loads(response.data)
        self.assertEqual(response_data['message'], 'No paths provided')

    @patch('os.path.commonpath')
    @patch('os.path.abspath')
    def test_like_image_all_not_found(self, mock_abspath, mock_commonpath):
        """测试所有路径均未找到的情况"""
        mock_abspath.side_effect = lambda x: x
        mock_commonpath.side_effect = lambda paths: 'invalid_base'
        
        # 设置测试数据
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
        """测试总图片数正确传递到模板"""
        mock_render.return_value = ''
        test_items = [{'filename': f'img{i}.jpg'} for i in range(30)]
        
        # 模拟数据加载
        self.web_app.load_image_data = MagicMock(return_value=(
            defaultdict(list, {'test_cat': test_items}),
            {}
        ))
        
        with self.web_app.app.test_request_context('/'):
            self.web_app.render_category_view(page=1, category='test_cat')
            args, kwargs = mock_render.call_args
            self.assertEqual(kwargs['total_images'], 30)

    def test_select_json_valid_index(self):
        """测试选择有效的JSON文件索引"""
        with self.web_app.app.test_client() as client:
            client.get('/select_json/0')
            with client.session_transaction() as sess:
                self.assertEqual(sess['current_json_index'], 0)

    def test_select_json_invalid_index(self):
        """测试选择无效的JSON文件索引时重置为0"""
        with self.web_app.app.test_client() as client:
            # 初始索引设为有效值
            with client.session_transaction() as sess:
                sess['current_json_index'] = 0
            # 请求超出范围的索引
            client.get('/select_json/999')
            with client.session_transaction() as sess:
                self.assertEqual(sess['current_json_index'], 0)

    def test_serve_image_not_found(self):
        """测试请求不存在的图片返回404"""
        # 模拟空数据
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
        """测试收藏夹分类只显示标记为喜欢的图片"""
        mock_render.return_value = ''
        # 模拟数据：3个喜欢，2个不喜欢，并添加必要字段
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
            # 检查传递给模板的图片数量应为3
            args, kwargs = mock_render.call_args
            self.assertEqual(len(kwargs['images']), 3)  # 确保此处断言正确

    @patch('web.render_template')
    def test_render_category_with_seed(self, mock_render):
        """测试相同种子生成相同的随机顺序"""
        mock_render.return_value = ''
        test_items = [{'filename': f'img{i}.jpg'} for i in range(50)]
        category_map = defaultdict(list, {'test_cat': test_items})
        self.web_app.load_image_data = MagicMock(return_value=(category_map, {}))
        
        # 使用相同种子两次调用，检查顺序是否一致
        seed = '12345'
        with self.web_app.app.test_request_context(f'/?seed={seed}'):
            self.web_app.render_category_view(page=1, seed=seed)
            first_call_images = mock_render.call_args[1]['images']
        
        # 重置mock，再次调用
        mock_render.reset_mock()
        with self.web_app.app.test_request_context(f'/?seed={seed}'):
            self.web_app.render_category_view(page=1, seed=seed)
            second_call_images = mock_render.call_args[1]['images']
        
        self.assertEqual([img['filename'] for img in first_call_images],
                         [img['filename'] for img in second_call_images])

    def test_paginate_out_of_range_page(self):
        """测试超出范围的页码返回空列表"""
        items = list(range(50))  # 共50项，每页20条，总页数3
        page = 5  # 有效页为1-3
        per_page = 20
        result, total_pages = WebApp.paginate(items, page, per_page)
        self.assertEqual(len(result), 0)
        self.assertEqual(total_pages, 3)

    def test_get_category_thumbnail(self):
        """测试获取分类缩略图"""
        # 模拟分类有图片
        test_items = [{'filename': 'thumb.jpg'}, {'filename': 'img2.jpg'}]
        category_map = defaultdict(list, {'test_cat': test_items})
        self.web_app.load_image_data = MagicMock(return_value=(category_map, {}))
        thumbnail = self.web_app.get_category_thumbnail('test_cat')
        self.assertEqual(thumbnail['filename'], 'thumb.jpg')

    def test_get_category_thumbnail_empty(self):
        """测试空分类返回默认缩略图"""
        self.web_app.load_image_data = MagicMock(return_value=(defaultdict(list), {}))
        thumbnail = self.web_app.get_category_thumbnail('empty_cat')
        self.assertEqual(thumbnail, {})

class TestConfigGUI(unittest.TestCase):
    @patch('tkinter.Tk')
    @patch('tkinter.filedialog.askopenfilenames')
    def test_add_files(self, mock_askopenfilenames, mock_tk):
        mock_askopenfilenames.return_value = ('file1.json', 'file2.json')
        args = parse_args()
        gui = ConfigGUI(args)
        gui.add_files()
        # 正确模拟Listbox的get方法
        gui.file_listbox.get = MagicMock(return_value=('file1.json', 'file2.json'))
        self.assertEqual(gui.file_listbox.get(0, 'end'), ('file1.json', 'file2.json'))

    @patch('tkinter.Tk')
    @patch('tkinter.filedialog.askopenfilenames')
    def test_remove_files(self, mock_askopenfilenames, mock_tk):
        mock_askopenfilenames.return_value = ('file1.json', 'file2.json')
        args = parse_args()
        gui = ConfigGUI(args)
        gui.add_files()
        gui.file_listbox.selection_set(0)
        gui.remove_files()
        # 正确模拟Listbox的get方法
        gui.file_listbox.get = MagicMock(return_value=('file2.json',))
        self.assertEqual(gui.file_listbox.get(0, 'end'), ('file2.json',))

    @patch('tkinter.Tk')
    @patch('tkinter.messagebox.showerror')
    def test_submit_params_no_files(self, mock_showerror, mock_tk):
        args = parse_args()
        gui = ConfigGUI(args)
        # 确保Listbox为空
        gui.file_listbox.get = MagicMock(return_value=())
        gui.submit_params()
        mock_showerror.assert_called_with("错误", "必须选择至少一个JSON文件")

    @patch('tkinter.Tk')
    @patch('tkinter.messagebox.showerror')
    @patch('os.path.isfile')
    def test_submit_params_invalid_per_page(self, mock_isfile, mock_showerror, mock_tk):
        mock_isfile.return_value = True
        args = parse_args()
        gui = ConfigGUI(args)
        # 添加一些JSON文件路径以通过文件路径验证
        gui.file_listbox.get = MagicMock(return_value=('test.json',))
        # 设置无效的每页数量
        gui.per_page_entry.get = MagicMock(return_value='abc')
        gui.submit_params()
        mock_showerror.assert_called_with("错误", "每页数量必须是正整数")

    @patch('tkinter.Tk')
    @patch('tkinter.messagebox.showerror')
    @patch('os.path.isfile')
    def test_submit_params_invalid_port(self, mock_isfile, mock_showerror, mock_tk):
        mock_isfile.return_value = True
        args = parse_args()
        gui = ConfigGUI(args)
        # 添加一些JSON文件路径以通过文件路径验证
        gui.file_listbox.get = MagicMock(return_value=('test.json',))
        # 设置无效的端口号
        gui.port_entry.get = MagicMock(return_value='abc')
        gui.submit_params()
        mock_showerror.assert_called_with("错误", "端口号必须是0-65535之间的整数")


if __name__ == '__main__':
    unittest.main()