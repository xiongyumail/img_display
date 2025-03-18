import unittest
import sys
import os
from unittest.mock import patch, MagicMock, PropertyMock
from flask import json
import argparse
from collections import defaultdict
from urllib.parse import quote

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

if __name__ == '__main__':
    unittest.main()