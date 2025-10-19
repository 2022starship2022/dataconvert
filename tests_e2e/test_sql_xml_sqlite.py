import os
import sys
import csv
import unittest
import subprocess
import xml.etree.ElementTree as ET


class SqlXmlSqliteE2ETests(unittest.TestCase):
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
        self.input_dir = os.path.join(os.path.dirname(__file__), 'input')
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

    def run_cli_merge(self, args, expect_success=True):
        cmd = self.cmd_base + ['merge'] + args
        result = subprocess.run(cmd, capture_output=True, text=True, cwd=self.project_root)
        if expect_success:
            if result.returncode != 0:
                print('STDOUT:', result.stdout)
                print('STDERR:', result.stderr)
            self.assertEqual(result.returncode, 0)
        return result

    def test_convert_csv_to_sqlite_and_back(self):
        src_csv = os.path.join(self.input_dir, 'data.csv')
        sqlite_out = os.path.join(self.tmp_dir, 'roundtrip.sqlite')
        csv_back = os.path.join(self.tmp_dir, 'roundtrip_back.csv')

        # CSV -> SQLite（默认表名 data）
        self.run_cli_convert([src_csv, sqlite_out, '-t', 'sqlite'])
        self.assertTrue(os.path.exists(sqlite_out), 'SQLite 输出文件未生成')

        # SQLite -> CSV，显式选择表名 data（与写入默认一致）
        self.run_cli_convert([sqlite_out, csv_back, '-f', 'sqlite', '-t', 'csv', '--table-name', 'data'])
        self.assertTrue(os.path.exists(csv_back), '回转 CSV 输出文件未生成')

        # 校验内容（行数、关键字段值）
        with open(csv_back, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 3)
        # 第一行
        self.assertEqual(rows[0]['id'], '1')
        self.assertEqual(rows[0]['name'], 'Alice')
        # 浮点值以字符串形式写回，直接比对文本
        self.assertEqual(rows[0]['score'], '95.5')
        # 布尔可能写为 True/False，忽略大小写
        self.assertIn(rows[0]['active'].lower(), ('true', 'false'))

    def test_convert_csv_to_xml_with_tags(self):
        src_csv = os.path.join(self.input_dir, 'data.csv')
        xml_out = os.path.join(self.tmp_dir, 'data.xml')

        # CSV -> XML，设置根/行标签并美化输出
        self.run_cli_convert([
            src_csv, xml_out, '-t', 'xml',
            '--xml-root-tag', 'dataset',
            '--xml-row-tag', 'record',
            '--xml-pretty'
        ])
        self.assertTrue(os.path.exists(xml_out), 'XML 输出文件未生成')

        # 解析并断言
        tree = ET.parse(xml_out)
        root = tree.getroot()
        self.assertEqual(root.tag, 'dataset')
        records = root.findall('record')
        self.assertEqual(len(records), 3)
        first = records[0]
        # 子元素文本均为字符串
        self.assertEqual(first.find('id').text, '1')
        self.assertEqual(first.find('name').text, 'Alice')
        self.assertEqual(first.find('score').text, '95.5')

    def test_convert_nested_json_to_sqlscript_with_flatten(self):
        src_json = os.path.join(self.input_dir, 'nested.json')
        sql_out = os.path.join(self.tmp_dir, 'nested.sql')

        # JSON -> SQL 脚本，启用扁平化+建表选项
        self.run_cli_convert([
            src_json, sql_out, '-t', 'sql',
            '--flat-nested', '--flat-sep', '.',
            '--sql-table-name', 'nested_table',
            '--sql-create', '--sql-if-not-exists',
            '--sql-batch-rows', '1'
        ])
        self.assertTrue(os.path.exists(sql_out), 'SQL 脚本输出文件未生成')

        # 读取 SQL 并断言关键片段
        with open(sql_out, encoding='utf-8') as f:
            sql_text = f.read()
        self.assertIn('CREATE TABLE IF NOT EXISTS "nested_table"', sql_text)
        # 扁平化列名示例
        self.assertIn('"user.name" TEXT', sql_text)
        self.assertIn('"user.contact.email" TEXT', sql_text)
        # 插入语句包含字段和示例值
        self.assertIn('INSERT INTO "nested_table" ("id", "user.name"', sql_text)
        self.assertIn("'alice@example.com'", sql_text)

    def test_merge_append_two_csvs(self):
        src1 = os.path.join(self.input_dir, 'data.csv')
        src2 = os.path.join(self.input_dir, 'data2.csv')
        merged_out = os.path.join(self.tmp_dir, 'merged.csv')

        # 纵向追加合并两个 CSV
        self.run_cli_merge([
            src1, src2,
            merged_out,
            '--mode', 'append'
        ])
        self.assertTrue(os.path.exists(merged_out), '合并后的 CSV 输出文件未生成')

        with open(merged_out, newline='', encoding='utf-8') as f:
            rows = list(csv.DictReader(f))
        self.assertEqual(len(rows), 5)
        # 验证包含新加入的记录
        names = {r['name'] for r in rows}
        self.assertTrue({'Diana', 'Eric'}.issubset(names))


if __name__ == '__main__':
    unittest.main()