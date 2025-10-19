import os
import sys
import unittest
import subprocess
import pandas as pd


class ExcelSheetsE2ETests(unittest.TestCase):
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

    def test_xlsx_to_csv_with_sheet_name(self):
        # 构造包含两个工作表的 Excel 文件
        xlsx_path = os.path.join(self.tmp_dir, 'sheets_input.xlsx')
        df_a = pd.DataFrame({'id': [1, 2], 'name': ['A1', 'A2']})
        df_b = pd.DataFrame({'id': [10, 20], 'name': ['B10', 'B20']})
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            df_a.to_excel(writer, sheet_name='SheetA', index=False)
            df_b.to_excel(writer, sheet_name='SheetB', index=False)
        self.assertTrue(os.path.exists(xlsx_path), '输入 Excel 未生成')

        # 仅选择 SheetB 转换为 CSV
        out_csv = os.path.join(self.tmp_dir, 'sheet_b.csv')
        self.run_cli_convert([xlsx_path, out_csv, '-t', 'csv', '--sheet-name', 'SheetB'])
        self.assertTrue(os.path.exists(out_csv), '输出 CSV 未生成')

        # 断言 CSV 内容来自 SheetB
        import csv
        with open(out_csv, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 2)
        self.assertEqual(rows[0]['id'], '10')
        self.assertEqual(rows[0]['name'], 'B10')
        self.assertEqual(rows[1]['id'], '20')
        self.assertEqual(rows[1]['name'], 'B20')

    def test_xlsx_to_sqlite_all_sheets_and_roundtrip_excel(self):
        # 构造多表 Excel
        xlsx_path = os.path.join(self.tmp_dir, 'book_multi.xlsx')
        df_a = pd.DataFrame({'id': [1, 2], 'name': ['A1', 'A2']})
        df_b = pd.DataFrame({'id': [10, 20], 'name': ['B10', 'B20']})
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            df_a.to_excel(writer, sheet_name='SheetA', index=False)
            df_b.to_excel(writer, sheet_name='SheetB', index=False)
        self.assertTrue(os.path.exists(xlsx_path), '输入 Excel 未生成')

        # Excel 所有表 -> SQLite 多表
        sqlite_out = os.path.join(self.tmp_dir, 'book_multi.sqlite')
        self.run_cli_convert([xlsx_path, sqlite_out, '-t', 'sqlite', '--all-sheets'])
        self.assertTrue(os.path.exists(sqlite_out), 'SQLite 输出未生成')

        # SQLite 所有表 -> Excel 多表
        roundtrip_xlsx = os.path.join(self.tmp_dir, 'book_multi_roundtrip.xlsx')
        self.run_cli_convert([sqlite_out, roundtrip_xlsx, '-f', 'sqlite', '-t', 'excel', '--all-tables'])
        self.assertTrue(os.path.exists(roundtrip_xlsx), '回转 Excel 输出未生成')

        # 读取回转Excel并断言两个工作表存在且数据一致
        sheets = pd.read_excel(roundtrip_xlsx, sheet_name=None, engine='openpyxl')
        self.assertIn('SheetA', sheets)
        self.assertIn('SheetB', sheets)
        df_a_rt = sheets['SheetA']
        df_b_rt = sheets['SheetB']
        self.assertEqual(df_a_rt.shape, df_a.shape)
        self.assertEqual(df_b_rt.shape, df_b.shape)
        self.assertListEqual(list(df_a_rt['name']), list(df_a['name']))
        self.assertListEqual(list(df_b_rt['name']), list(df_b['name']))


if __name__ == '__main__':
    unittest.main()