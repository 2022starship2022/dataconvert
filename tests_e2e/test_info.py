import os
import sys
import json
import subprocess
import unittest


class InfoE2ETests(unittest.TestCase):
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

    def run_cli_info(self, args, timeout=60):
        cmd = self.cmd_base + ['info'] + args
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout, cwd=self.root)
        if res.returncode != 0:
            print('STDOUT:', res.stdout)
            print('STDERR:', res.stderr)
            self.fail(f"CLI failed with code {res.returncode}")
        return res

    def test_info_json_stdout(self):
        src = os.path.join(self.root, 'tests_e2e', 'input', 'data.json')
        res = self.run_cli_info([src, '--output-format', 'json'])
        out = res.stdout
        # 提取JSON主体，避免混入日志
        start = out.find('{')
        end = out.rfind('}')
        self.assertTrue(start != -1 and end != -1 and end > start, '未检测到JSON输出')
        json_text = out[start:end+1]
        info = json.loads(json_text)
        # 基本结构断言
        self.assertEqual(info.get('file_path'), src)
        self.assertEqual(info.get('format'), 'JSON')
        self.assertIn('stats', info)
        self.assertEqual(info['stats'].get('record_count'), 3)
        self.assertEqual(info['stats'].get('field_count'), 4)
        self.assertIn('columns', info)
        self.assertEqual(info['columns'], ['id', 'name', 'score', 'active'])
        self.assertIn('sample_data', info)
        self.assertGreaterEqual(len(info['sample_data']), 1)

    def test_info_export_info_file(self):
        src = os.path.join(self.root, 'tests_e2e', 'input', 'data.json')
        dest = os.path.join(self.tmp_dir, 'info_data.json')
        # 使用文本输出到控制台，同时导出 JSON 文件
        self.run_cli_info([src, '--output-format', 'text', '--export-info', dest])
        self.assertTrue(os.path.exists(dest), '导出文件未创建')
        with open(dest, 'r', encoding='utf-8') as f:
            info = json.load(f)
        self.assertEqual(info.get('file_path'), src)
        self.assertEqual(info.get('format'), 'JSON')
        # 统计与列信息应存在
        self.assertIn('stats', info)
        self.assertEqual(info['stats'].get('record_count'), 3)
        self.assertEqual(info['stats'].get('field_count'), 4)
        self.assertIn('columns', info)


if __name__ == '__main__':
    unittest.main()