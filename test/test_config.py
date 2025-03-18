import unittest
import sys
import os
from unittest.mock import patch, MagicMock
import argparse

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import parse_args, ConfigGUI

class TestConfig(unittest.TestCase):
    def test_parse_args(self):
        args = parse_args()
        self.assertEqual(args.per_page, 20)
        self.assertEqual(args.host, '0.0.0.0')
        self.assertEqual(args.port, 5000)

class TestConfigGUI(unittest.TestCase):
    @patch('tkinter.Tk')
    @patch('tkinter.filedialog.askopenfilenames')
    def test_add_files(self, mock_askopenfilenames, mock_tk):
        mock_askopenfilenames.return_value = ('file1.json', 'file2.json')
        args = parse_args()
        gui = ConfigGUI(args)
        gui.add_files()
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
        gui.file_listbox.get = MagicMock(return_value=('file2.json',))
        self.assertEqual(gui.file_listbox.get(0, 'end'), ('file2.json',))

    @patch('tkinter.Tk')
    @patch('tkinter.messagebox.showerror')
    def test_submit_params_no_files(self, mock_showerror, mock_tk):
        args = parse_args()
        gui = ConfigGUI(args)
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
        gui.file_listbox.get = MagicMock(return_value=('test.json',))
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
        gui.file_listbox.get = MagicMock(return_value=('test.json',))
        gui.port_entry.get = MagicMock(return_value='abc')
        gui.submit_params()
        mock_showerror.assert_called_with("错误", "端口号必须是0-65535之间的整数")

if __name__ == '__main__':
    unittest.main()