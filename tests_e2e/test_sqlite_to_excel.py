import os
import sys
import unittest
import subprocess
import sqlite3
import pandas as pd


class SQLiteToExcelE2ETests(unittest.TestCase):
    def setUp(self):
        # 项目根目录与 CLI 入口（强制使用编译后的 exe）
        self.project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(self.project_root, 'build_nuitka', 'cli_main.exe'),
            os.path.join(self.project_root, 'build_nuitka', 'cli_main.dist', 'cli_main.exe'),
        ]
        cmd_base = None
        for p in candidates:
            if os.path.exists(p):
                cmd_base = [p]
                break
        if not cmd_base:
            self.fail('未找到编译后的 CLI 可执行文件，请先构建 Nuitka exe。')
        self.cmd_base = cmd_base
        self.tmp_dir = os.path.join(os.path.dirname(__file__), 'tmp')
        os.makedirs(self.tmp_dir, exist_ok=True)

    def run_cli_convert(self, args, expect_success=True):
        cmd = self.cmd_base + ['convert'] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        if expect_success:
            if result.returncode != 0:
                print('STDOUT:', result.stdout)
                print('STDERR:', result.stderr)
            self.assertEqual(result.returncode, 0)
        return result

    def test_sqlite_to_excel_all_tables(self):
        # 构造包含两个表的 SQLite 数据库
        sqlite_path = os.path.join(self.tmp_dir, 'direct_book.sqlite')
        if os.path.exists(sqlite_path):
            os.remove(sqlite_path)
        conn = sqlite3.connect(sqlite_path)
        try:
            df_a = pd.DataFrame({'id': [1, 2], 'name': ['A1', 'A2']})
            df_b = pd.DataFrame({'id': [10, 20], 'name': ['B10', 'B20']})
            df_a.to_sql('SheetA', conn, index=False, if_exists='replace')
            df_b.to_sql('SheetB', conn, index=False, if_exists='replace')
        finally:
            conn.close()
        self.assertTrue(os.path.exists(sqlite_path), '输入 SQLite 未生成')

        # 直接转换为 Excel，读取所有表
        excel_out = os.path.join(self.tmp_dir, 'direct_book.xlsx')
        self.run_cli_convert([sqlite_path, excel_out, '-f', 'sqlite', '-t', 'excel', '--all-tables'])
        self.assertTrue(os.path.exists(excel_out), '输出 Excel 未生成')

        # 验证 Excel 工作表及数据
        sheets = pd.read_excel(excel_out, sheet_name=None, engine='openpyxl')
        self.assertIn('SheetA', sheets)
        self.assertIn('SheetB', sheets)
        df_a_rt = sheets['SheetA']
        df_b_rt = sheets['SheetB']
        self.assertListEqual(list(df_a_rt['name']), ['A1', 'A2'])
        self.assertListEqual(list(df_b_rt['name']), ['B10', 'B20'])


if __name__ == '__main__':
    unittest.main()