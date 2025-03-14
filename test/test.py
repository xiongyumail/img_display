import unittest
import sys
import os
from unittest.mock import patch, MagicMock
# 将项目根目录添加到系统路径
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_args, ConfigGUI
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