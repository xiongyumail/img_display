import unittest
import sys
import os
# 将项目根目录添加到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_args
from web import Paginator

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
        result, total_pages = Paginator.paginate(items, page, per_page)
        self.assertEqual(len(result), per_page)

if __name__ == '__main__':
    unittest.main()