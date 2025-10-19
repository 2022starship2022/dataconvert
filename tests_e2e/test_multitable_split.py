import os
import sys
import csv
import unittest
import subprocess
import pandas as pd


class MultiTableSplitE2ETests(unittest.TestCase):
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

    def test_excel_all_sheets_split_to_csv_dir(self):
        # 构造多表 Excel
        xlsx_path = os.path.join(self.tmp_dir, 'split_book.xlsx')
        df_a = pd.DataFrame({'id': [1, 2], 'name': ['A1', 'A2']})
        df_b = pd.DataFrame({'id': [10, 20], 'name': ['B10', 'B20']})
        with pd.ExcelWriter(xlsx_path, engine='openpyxl') as writer:
            df_a.to_excel(writer, sheet_name='SheetA', index=False)
            df_b.to_excel(writer, sheet_name='SheetB', index=False)
        self.assertTrue(os.path.exists(xlsx_path), '输入 Excel 未生成')

        # 多表拆分到目录（CSV 格式）
        split_dir = os.path.join(self.tmp_dir, 'split_out')
        if os.path.exists(split_dir):
            # 清理目录
            import shutil
            shutil.rmtree(split_dir)
        os.makedirs(split_dir, exist_ok=True)

        dummy_out = os.path.join(self.tmp_dir, 'dummy.csv')
        self.run_cli_convert([
            xlsx_path, dummy_out,
            '-t', 'csv', '--all-sheets',
            '--multi-action', 'split', '--split-format', 'csv', '--split-dir', split_dir
        ])

        # 检查拆分后的文件存在
        a_csv = os.path.join(split_dir, 'SheetA.csv')
        b_csv = os.path.join(split_dir, 'SheetB.csv')
        self.assertTrue(os.path.exists(a_csv), 'SheetA.csv 未生成')
        self.assertTrue(os.path.exists(b_csv), 'SheetB.csv 未生成')

        # 验证内容
        with open(a_csv, newline='', encoding='utf-8') as fa:
            rows_a = list(csv.DictReader(fa))
        with open(b_csv, newline='', encoding='utf-8') as fb:
            rows_b = list(csv.DictReader(fb))
        self.assertEqual([r['name'] for r in rows_a], ['A1', 'A2'])
        self.assertEqual([r['name'] for r in rows_b], ['B10', 'B20'])


if __name__ == '__main__':
    unittest.main()