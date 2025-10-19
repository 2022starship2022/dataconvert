import os
import sys
import json
import subprocess
import unittest


class EncodingE2ETests(unittest.TestCase):
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

    def run_cli(self, args, timeout=60):
        cmd = self.cmd_base + ['convert'] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=self.root)
        if res.returncode != 0:
            print('STDOUT:', res.stdout)
            print('STDERR:', res.stderr)
            self.fail(f"CLI failed with code {res.returncode}")
        return res

    def test_gbk_auto_detection_csv_to_json(self):
        # 使用样例 GBK CSV，自动检测编码后转为 JSON
        src = os.path.join(self.root, 'samples', 'sample_gbk.csv')
        dest = os.path.join(self.tmp_dir, 'out_gbk.json')
        self.run_cli([src, dest, '-e', 'auto', '-t', 'json'])
        with open(dest, 'r', encoding='utf-8') as f:
            data = json.load(f)
        self.assertIsInstance(data, list)
        self.assertGreaterEqual(len(data), 2)
        self.assertEqual(data[0]['名字'], '张三')
        self.assertEqual(data[0]['城市'], '北京')
        self.assertEqual(data[1]['名字'], '李四')
        self.assertEqual(data[1]['城市'], '上海')

    def test_json_to_csv_with_utf8_bom(self):
        # 将 JSON 转 CSV，并写入 UTF-8 BOM
        src = os.path.join(self.root, 'tests_e2e', 'input', 'data.json')
        dest = os.path.join(self.tmp_dir, 'out_bom.csv')
        self.run_cli([src, dest, '-t', 'csv', '--csv-bom'])
        with open(dest, 'rb') as f:
            head = f.read(3)
        self.assertEqual(head, b'\xef\xbb\xbf')


if __name__ == '__main__':
    unittest.main()