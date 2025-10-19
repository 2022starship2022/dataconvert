import os
import sys
import json
import csv
import shutil
import unittest
import subprocess


class DirectoryModeE2ETests(unittest.TestCase):
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

    def _write_json(self, path, data):
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

    def test_dir_in_out_recursive_filter_to_csv_structure_preserved(self):
        # 构造输入目录，包含子目录与多 JSON 文件
        in_dir = os.path.join(self.tmp_dir, 'dir_in_recursive')
        out_dir = os.path.join(self.tmp_dir, 'dir_out_recursive')
        if os.path.exists(in_dir):
            shutil.rmtree(in_dir)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(in_dir, exist_ok=True)

        animals = [
            {"id": 1, "name": "cat"},
            {"id": 2, "name": "dog"},
        ]
        numbers = [
            {"n": 10, "parity": "even"},
            {"n": 11, "parity": "odd"},
        ]
        self._write_json(os.path.join(in_dir, 'animals.json'), animals)
        sub = os.path.join(in_dir, 'sub')
        self._write_json(os.path.join(sub, 'numbers.json'), numbers)
        # 非匹配文件应被忽略
        with open(os.path.join(sub, 'skip.txt'), 'w', encoding='utf-8') as f:
            f.write('ignore me')

        # 递归 + 过滤 *.json，输出为 CSV，保留子目录结构
        self.run_cli_convert([
            in_dir, out_dir, '--dir-in', '--dir-out', '-r', '--filter', '*.json', '-t', 'csv'
        ])

        # 验证输出文件存在（结构保留）
        animals_csv = os.path.join(out_dir, 'animals.csv')
        numbers_csv = os.path.join(out_dir, 'sub', 'numbers.csv')
        self.assertTrue(os.path.exists(animals_csv), 'animals.csv 未生成')
        self.assertTrue(os.path.exists(numbers_csv), 'sub/numbers.csv 未生成')
        self.assertFalse(os.path.exists(os.path.join(out_dir, 'sub', 'skip.csv')), '不应生成 skip.csv')

        # 验证内容
        with open(animals_csv, newline='', encoding='utf-8') as fa:
            rows_a = list(csv.DictReader(fa))
        with open(numbers_csv, newline='', encoding='utf-8') as fn:
            rows_n = list(csv.DictReader(fn))
        self.assertEqual([r['name'] for r in rows_a], ['cat', 'dog'])
        self.assertEqual([int(r['n']) for r in rows_n], [10, 11])
        self.assertEqual([r['parity'] for r in rows_n], ['even', 'odd'])

    def test_dir_in_out_recursive_flat_dir_outputs_flat(self):
        # 构造输入目录与子目录
        in_dir = os.path.join(self.tmp_dir, 'dir_in_flat')
        out_dir = os.path.join(self.tmp_dir, 'dir_out_flat')
        if os.path.exists(in_dir):
            shutil.rmtree(in_dir)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(in_dir, exist_ok=True)

        animals = [
            {"id": 1, "name": "bird"},
            {"id": 2, "name": "fish"},
        ]
        numbers = [
            {"n": 100, "parity": "even"},
            {"n": 101, "parity": "odd"},
        ]
        self._write_json(os.path.join(in_dir, 'animals.json'), animals)
        sub = os.path.join(in_dir, 'sub')
        self._write_json(os.path.join(sub, 'numbers.json'), numbers)

        # 递归 + 过滤 *.json + 扁平化输出
        self.run_cli_convert([
            in_dir, out_dir, '--dir-in', '--dir-out', '-r', '--filter', '*.json', '--flat-dir', '-t', 'csv'
        ])

        # 验证输出扁平化：均在根目录
        animals_csv = os.path.join(out_dir, 'animals.csv')
        numbers_csv = os.path.join(out_dir, 'numbers.csv')
        self.assertTrue(os.path.exists(animals_csv), 'animals.csv 未生成')
        self.assertTrue(os.path.exists(numbers_csv), 'numbers.csv 未生成')
        # 子目录不应被创建或至少不包含输出文件
        self.assertFalse(os.path.exists(os.path.join(out_dir, 'sub', 'numbers.csv')))

        with open(animals_csv, newline='', encoding='utf-8') as fa:
            rows_a = list(csv.DictReader(fa))
        with open(numbers_csv, newline='', encoding='utf-8') as fn:
            rows_n = list(csv.DictReader(fn))
        self.assertEqual([r['name'] for r in rows_a], ['bird', 'fish'])
        self.assertEqual([int(r['n']) for r in rows_n], [100, 101])

    def test_dir_in_out_non_recursive_filter_only_root(self):
        # 构造输入目录（子目录含 JSON，但不开启递归）
        in_dir = os.path.join(self.tmp_dir, 'dir_in_norec')
        out_dir = os.path.join(self.tmp_dir, 'dir_out_norec')
        if os.path.exists(in_dir):
            shutil.rmtree(in_dir)
        if os.path.exists(out_dir):
            shutil.rmtree(out_dir)
        os.makedirs(in_dir, exist_ok=True)

        root_data = [
            {"id": 1, "name": "root"},
            {"id": 2, "name": "r2"},
        ]
        child_data = [
            {"id": 3, "name": "child"}
        ]
        self._write_json(os.path.join(in_dir, 'root.json'), root_data)
        sub = os.path.join(in_dir, 'sub')
        self._write_json(os.path.join(sub, 'child.json'), child_data)

        # 无 -r，仅过滤根目录 *.json
        self.run_cli_convert([
            in_dir, out_dir, '--dir-in', '--dir-out', '--filter', '*.json', '-t', 'csv'
        ])

        root_csv = os.path.join(out_dir, 'root.csv')
        child_csv = os.path.join(out_dir, 'sub', 'child.csv')
        self.assertTrue(os.path.exists(root_csv), 'root.csv 未生成')
        self.assertFalse(os.path.exists(child_csv), '不应生成子目录 child.csv')

        with open(root_csv, newline='', encoding='utf-8') as fr:
            rows_r = list(csv.DictReader(fr))
        self.assertEqual([r['name'] for r in rows_r], ['root', 'r2'])


if __name__ == '__main__':
    unittest.main()