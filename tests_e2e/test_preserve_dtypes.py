import os
import sys
import json
import subprocess
import unittest


class PreserveDtypesE2ETests(unittest.TestCase):
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
        # 输出目录
        self.tmp_dir = os.path.join(self.root, 'tests_e2e', 'tmp')
        os.makedirs(self.tmp_dir, exist_ok=True)

    def run_cli_convert(self, input_path, output_path, extra_args=None, config_path=None, expect_success=True):
        base = list(self.cmd_base)
        cmd = base
        if config_path:
            cmd += ['--config', config_path]
        cmd += ['convert', input_path, output_path, '-t', 'csv']
        if extra_args:
            cmd += list(extra_args)
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.root)
        if expect_success:
            if result.returncode != 0:
                print('STDOUT:', result.stdout)
                print('STDERR:', result.stderr)
            self.assertEqual(result.returncode, 0)
        return result

    def _make_typed_json(self, path):
        data = [
            {"id": 1, "name": "Alice", "score": 95.5, "active": True},
            {"id": 2, "name": "Bob", "score": 82.0, "active": False},
            {"id": 3, "name": "Carl", "score": 71.25, "active": True},
        ]
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def test_csv_writes_dtypes_metadata_when_enabled(self):
        # 准备带类型的 JSON 输入
        src_json = os.path.join(self.tmp_dir, 'typed_input.json')
        self._make_typed_json(src_json)

        # 使用 e2e 配置（已启用 csv.preserve_dtypes=true）
        config_path = os.path.join(os.path.dirname(__file__), 'config.yaml')
        out_csv = os.path.join(self.tmp_dir, 'out_preserve_true.csv')

        self.run_cli_convert(src_json, out_csv, config_path=config_path)
        self.assertTrue(os.path.exists(out_csv), 'CSV 输出文件未生成')

        with open(out_csv, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        self.assertTrue(first_line.startswith('#dtypes:'), '第一行未包含 #dtypes: 元数据')

    def test_csv_writes_no_dtypes_metadata_when_disabled(self):
        # 准备带类型的 JSON 输入
        src_json = os.path.join(self.tmp_dir, 'typed_input_no_meta.json')
        self._make_typed_json(src_json)

        # 在临时目录写入禁用 preserve_dtypes 的配置
        config_no_meta = os.path.join(self.tmp_dir, 'config_no_dtypes.yaml')
        with open(config_no_meta, 'w', encoding='utf-8') as f:
            f.write('csv:\n  preserve_dtypes: false\n')

        out_csv = os.path.join(self.tmp_dir, 'out_preserve_false.csv')
        self.run_cli_convert(src_json, out_csv, config_path=config_no_meta)
        self.assertTrue(os.path.exists(out_csv), 'CSV 输出文件未生成')

        with open(out_csv, 'r', encoding='utf-8') as f:
            first_line = f.readline().strip()
        self.assertFalse(first_line.startswith('#dtypes:'), '第一行不应包含 #dtypes: 元数据')


if __name__ == '__main__':
    unittest.main()