import os
import sys
import json
import unittest
import subprocess


class SqlDialectDropE2ETests(unittest.TestCase):
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

    def test_generate_sql_script_with_dialect_and_drop(self):
        # 构造包含多类型字段的 JSON 输入
        data = [
            {"id": 1, "name": "Alice", "score": 95.5, "active": True},
            {"id": 2, "name": "Bob", "score": 82.0, "active": False},
        ]
        src_json = os.path.join(self.tmp_dir, 'sql_dialect_input.json')
        with open(src_json, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False)

        cases = [
            {
                'dialect': 'sqlite',
                'table': 't_sqlite',
                'out': os.path.join(self.tmp_dir, 't_sqlite.sql'),
                'expect_quotes': '"',  # sqlite 使用双引号
                'type_map_checks': ['"id" INTEGER', '"score" REAL', '"active" INTEGER'],
                'bool_values': [', 1)', ', 0)']
            },
            {
                'dialect': 'mysql',
                'table': 't_mysql',
                'out': os.path.join(self.tmp_dir, 't_mysql.sql'),
                'expect_quotes': '`',  # mysql 使用反引号
                'type_map_checks': ['`id` INT', '`score` DOUBLE', '`active` BOOLEAN'],
                'bool_values': [', 1)', ', 0)']
            },
            {
                'dialect': 'postgres',
                'table': 't_pg',
                'out': os.path.join(self.tmp_dir, 't_pg.sql'),
                'expect_quotes': '"',  # postgres 使用双引号
                'type_map_checks': ['"id" INTEGER', '"score" DOUBLE PRECISION', '"active" BOOLEAN'],
                'bool_values': [', 1)', ', 0)']
            },
        ]

        for c in cases:
            # 生成 SQL 脚本，包含 DROP/CREATE/IF NOT EXISTS
            self.run_cli_convert([
                src_json, c['out'], '-t', 'sql',
                '--sql-dialect', c['dialect'], '--sql-table-name', c['table'],
                '--sql-drop', '--sql-create', '--sql-if-not-exists', '--sql-batch-rows', '1'
            ])
            self.assertTrue(os.path.exists(c['out']), f"{c['out']} 未生成")

            with open(c['out'], 'r', encoding='utf-8') as f:
                sql_text = f.read()

            # 断言包含 DROP TABLE IF EXISTS 语句且标识符引号样式正确
            drop_line = f"DROP TABLE IF EXISTS {c['expect_quotes']}{c['table']}{c['expect_quotes']};"
            self.assertIn(drop_line, sql_text)

            # 断言 CREATE TABLE IF NOT EXISTS 语句
            create_prefix = f"CREATE TABLE IF NOT EXISTS {c['expect_quotes']}{c['table']}{c['expect_quotes']}"
            self.assertIn(create_prefix, sql_text)

            # 断言类型映射
            for frag in c['type_map_checks']:
                self.assertIn(frag, sql_text)

            # 断言 INSERT 语句中的布尔值表达
            # 注意：INSERT 行可能包含多个值，检查有 TRUE/FALSE 或 1/0
            bool_any = any(b in sql_text for b in c['bool_values'])
            self.assertTrue(bool_any, f"{c['dialect']} 布尔值表示未出现预期片段")


if __name__ == '__main__':
    unittest.main()