import os
import sys
import json
import subprocess
import unittest


class CsvTypesQuoteCharE2ETests(unittest.TestCase):
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
        self.config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')

    def run_cli(self, argv, expect_success=True):
        base = list(self.cmd_base)
        result = subprocess.run(base + argv, capture_output=True, text=True, cwd=self.project_root)
        if expect_success:
            if result.returncode != 0:
                print('STDOUT:', result.stdout)
                print('STDERR:', result.stderr)
            self.assertEqual(result.returncode, 0)
        return result

    def test_json_csv_roundtrip_with_quotechar_and_preserve_types(self):
        # 构造带类型的 JSON 输入，包括含逗号的字符串，确保触发引号
        data = [
            {"id": 1, "name": "Alice, A", "score": 95.5, "active": True},
            {"id": 2, "name": "Bob", "score": 82.0, "active": False},
            {"id": 3, "name": "Carl, C", "score": 71.25, "active": True},
        ]
        src_json = os.path.join(self.tmp_dir, 'typed_quote_input.json')
        with open(src_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        # JSON -> CSV，启用 preserve_dtypes 并使用自定义引号字符
        out_csv = os.path.join(self.tmp_dir, 'typed_out_quotechar.csv')
        cmd1 = ['--config', self.config_path, 'convert', src_json, out_csv, '-t', 'csv', '--quote-char', '$']
        self.run_cli(cmd1)
        self.assertTrue(os.path.exists(out_csv), 'CSV 输出未生成')

        # 验证 CSV 第一行包含 dtypes 元数据，且文本中使用 $ 引号包裹
        with open(out_csv, 'r', encoding='utf-8') as f:
            text = f.read()
        self.assertTrue(text.splitlines()[0].startswith('#dtypes:'), 'CSV 未包含 #dtypes: 元数据')
        self.assertIn(',$Alice, A$,', text)
        self.assertIn(',$Carl, C$,', text)

        # CSV -> JSON 回转，提供相同的 quotechar，确保解析正确且类型恢复
        back_json = os.path.join(self.tmp_dir, 'typed_out_quotechar_back.json')
        cmd2 = ['--config', self.config_path, 'convert', out_csv, back_json, '-f', 'csv', '-t', 'json', '--quote-char', '$']
        self.run_cli(cmd2)
        self.assertTrue(os.path.exists(back_json), '回转 JSON 输出未生成')

        with open(back_json, 'r', encoding='utf-8') as f:
            back_data = json.load(f)
        self.assertIsInstance(back_data, list)
        self.assertEqual(len(back_data), 3)

        # 验证类型与内容：id 为 int，score 为 float，active 为 bool，name 保持字符串并正确解析逗号
        self.assertTrue(all(isinstance(row['id'], int) for row in back_data))
        self.assertTrue(all(isinstance(row['score'], float) for row in back_data))
        self.assertTrue(all(isinstance(row['active'], bool) for row in back_data))
        names = [row['name'] for row in back_data]
        self.assertIn('Alice, A', names)
        self.assertIn('Bob', names)
        self.assertIn('Carl, C', names)


if __name__ == '__main__':
    unittest.main()