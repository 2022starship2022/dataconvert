import os
import subprocess
import tempfile
import unittest

class TestProtobufDecodeCLI(unittest.TestCase):
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
        self.tmp_dir = tempfile.mkdtemp(prefix="proto_cli_test_")

    def run_cli_convert(self, args, expect_success=True):
        cmd = self.cmd_base + ['convert'] + args
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=self.root)
        if expect_success:
            assert result.returncode == 0, f"convert 命令失败: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        else:
            assert result.returncode != 0, "预期 convert 命令失败但返回码为 0"
        return result

    def test_decode_missing_message_type_errors(self):
        # 构造一个假的 pb 输入文件
        pb_path = os.path.join(self.tmp_dir, 'input.pb')
        with open(pb_path, 'wb') as f:
            f.write(b'\x0a\x03abc')
        # 缺少 --message-type，预期 convert 验证失败
        out_json = os.path.join(self.tmp_dir, 'out.json')
        res = self.run_cli_convert([pb_path, out_json, '-f', 'protobuf', '--schema-file', 'dummy.desc'], expect_success=False)
        err_text = res.stderr + res.stdout
        assert ('--message-type' in err_text) or ('message-type' in err_text), '错误输出未提示缺少 --message-type'

    def test_decode_missing_schema_file_errors(self):
        # 构造一个假的 pb 输入文件
        pb_path = os.path.join(self.tmp_dir, 'input2.pb')
        with open(pb_path, 'wb') as f:
            f.write(b'\x0a\x03xyz')
        # 缺少 --schema-file，预期 convert 验证失败
        out_json = os.path.join(self.tmp_dir, 'out2.json')
        res = self.run_cli_convert([pb_path, out_json, '-f', 'protobuf', '--message-type', 'pkg.Msg'], expect_success=False)
        err_text = res.stderr + res.stdout
        assert ('--schema-file' in err_text) or ('schema-file' in err_text), '错误输出未提示缺少 --schema-file'


if __name__ == '__main__':
    unittest.main()