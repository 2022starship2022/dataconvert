import os
import sys
import json
import subprocess
import unittest


class QuoteCharE2ETests(unittest.TestCase):
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

    def test_roundtrip_json_csv_with_custom_quotechar(self):
        # 构造包含分隔符的字符串字段，确保触发引号
        data = [
            {"id": 1, "name": "Alice, A", "score": 95.5, "active": True},
            {"id": 2, "name": "Bob", "score": 82.0, "active": False},
            {"id": 3, "name": "Carl, C", "score": 71.25, "active": True},
        ]
        src_json = os.path.join(self.tmp_dir, 'quote_input.json')
        with open(src_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        # JSON -> CSV 使用自定义引号字符 `$`
        out_csv = os.path.join(self.tmp_dir, 'out_quotechar.csv')
        self.run_cli_convert([src_json, out_csv, '-t', 'csv', '--quote-char', '$'])
        self.assertTrue(os.path.exists(out_csv), 'CSV 输出文件未生成')

        # 检查 CSV 文本中存在使用 `$` 包裹的需要引用的字段
        with open(out_csv, 'r', encoding='utf-8') as f:
            csv_text = f.read()
        # name 含逗号的行应被 $ 包裹
        self.assertIn(',$Alice, A$,', csv_text)
        self.assertIn(',$Carl, C$,', csv_text)

        # CSV -> JSON 读取时提供相同的 quotechar，确保解析正确
        back_json = os.path.join(self.tmp_dir, 'out_quotechar_back.json')
        self.run_cli_convert([out_csv, back_json, '-f', 'csv', '-t', 'json', '--quote-char', '$'])
        self.assertTrue(os.path.exists(back_json), '回转 JSON 输出文件未生成')

        with open(back_json, 'r', encoding='utf-8') as f:
            back_data = json.load(f)
        self.assertIsInstance(back_data, list)
        self.assertEqual(len(back_data), 3)
        # 验证字符串字段按原样解析
        names = [r['name'] for r in back_data]
        self.assertIn('Alice, A', names)
        self.assertIn('Carl, C', names)
        self.assertIn('Bob', names)


if __name__ == '__main__':
    unittest.main()