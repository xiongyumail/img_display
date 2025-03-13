import unittest
import sys
import os
# 将项目根目录添加到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_args
from web import WebApp  # 导入WebApp以测试分页
import argparse

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

    def test_apply_replace_rules(self):
        data = {'key': 'old value'}
        result = self.web_app.apply_replace_rules(data)
        self.assertEqual(result['key'], 'new value')

    def test_reverse_replace_rules(self):
        data = {'key': 'new value'}
        result = self.web_app.reverse_replace_rules(data)
        self.assertEqual(result['key'], 'old value')

    def test_apply_replace_rules_no_rules(self):
        self.web_app.replace_rules = []
        data = {'key': 'old value'}
        result = self.web_app.apply_replace_rules(data)
        self.assertEqual(result, data)

    def test_reverse_replace_rules_no_rules(self):
        self.web_app.replace_rules = []
        data = {'key': 'old value'}
        result = self.web_app.reverse_replace_rules(data)
        self.assertEqual(result, data)

if __name__ == '__main__':
    unittest.main()