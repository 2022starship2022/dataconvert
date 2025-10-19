import os
import sys
import unittest
import subprocess


class BatchModeE2ETests(unittest.TestCase):
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

    def run_cli(self, argv, expect_success=True):
        result = subprocess.run(self.cmd_base + argv, capture_output=True, text=True, cwd=self.project_root)
        if expect_success:
            if result.returncode != 0:
                print('STDOUT:', result.stdout)
                print('STDERR:', result.stderr)
            self.assertEqual(result.returncode, 0)
        return result

    def test_batch_mode_unimplemented_returns_error(self):
        # 准备输入与输出参数（批量模式暂未实现，应返回错误）
        in_path = os.path.join(self.project_root, 'tests_e2e', 'input', 'data.csv')
        out_dir = os.path.join(self.tmp_dir, 'batch_out')
        os.makedirs(out_dir, exist_ok=True)
        out_path_placeholder = os.path.join(out_dir, 'placeholder.csv')

        # 运行 convert --batch/--output-dir
        result = self.run_cli(['convert', in_path, out_path_placeholder, '--batch', '--output-dir', out_dir], expect_success=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn('批量转换功能暂未实现', result.stderr)


if __name__ == '__main__':
    unittest.main()