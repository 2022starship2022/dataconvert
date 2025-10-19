import os
import sys
import json
import csv
import subprocess
import unittest


class FlattenE2ETests(unittest.TestCase):
    def setUp(self):
        # 项目根目录与 CLI 入口（强制使用编译后的 exe）
        self.root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        candidates = [
            os.path.join(self.root, 'build_nuitka', 'cli_main.exe'),
            os.path.join(self.root, 'build_nuitka', 'cli_main.dist', 'cli_main.exe'),
        ]
        cmd_base = None
        for p in candidates:
            if os.path.exists(p):
                cmd_base = [p]
                break
        if not cmd_base:
            self.fail('未找到编译后的 CLI 可执行文件，请先构建 Nuitka exe。')
        self.cmd_base = cmd_base
        # 临时输出目录
        self.tmp_dir = os.path.join(self.root, 'tests_e2e', 'tmp')
        os.makedirs(self.tmp_dir, exist_ok=True)

    def run_cli_convert(self, args, timeout=60):
        cmd = self.cmd_base + ['convert'] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=self.root)
        if res.returncode != 0:
            print('STDOUT:', res.stdout)
            print('STDERR:', res.stderr)
            self.fail(f"CLI failed with code {res.returncode}")
        return res

    def test_flatten_json_to_csv(self):
        src = os.path.join(self.root, 'tests_e2e', 'input', 'nested.json')
        dest = os.path.join(self.tmp_dir, 'nested_flat.csv')
        self.run_cli_convert([src, dest, '-t', 'csv', '--flat-nested', '--flat-sep', '.'])
        self.assertTrue(os.path.exists(dest), '输出CSV未创建')
        with open(dest, 'r', encoding='utf-8', newline='') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
        self.assertGreaterEqual(len(rows), 2)
        # 列断言（顺序不保证，但必须包含以下列）
        expected_cols = {'id', 'user.name', 'user.contact.email', 'user.contact.phone', 'tags', 'scores.math', 'scores.english'}
        self.assertTrue(expected_cols.issubset(set(reader.fieldnames)))
        # 第一行具体值断言
        r1 = rows[0]
        self.assertEqual(r1['user.name'], 'Alice')
        self.assertEqual(r1['user.contact.email'], 'alice@example.com')
        self.assertEqual(int(float(r1['scores.math'])), 95)
        self.assertEqual(int(float(r1['scores.english'])), 88)
        self.assertEqual(json.loads(r1['tags']), ['x', 'y'])
        # 第二行 phone 为空（缺失）
        r2 = rows[1]
        self.assertEqual(r2.get('user.contact.phone', ''), '')
        self.assertEqual(r2['user.name'], 'Bob')
        self.assertEqual(r2['user.contact.email'], 'bob@example.com')
        self.assertEqual(int(float(r2['scores.math'])), 78)
        self.assertEqual(int(float(r2['scores.english'])), 91)


if __name__ == '__main__':
    unittest.main()