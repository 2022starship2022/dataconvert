import json
import os
import subprocess
import tempfile
import unittest

class TestMMKVCLI(unittest.TestCase):
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
        self.tmp_dir = tempfile.mkdtemp(prefix="mmkv_cli_test_")

    def run_cli_convert(self, args, expect_success=True):
        cmd = self.cmd_base + ['convert'] + args
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=self.root)
        if expect_success:
            assert result.returncode == 0, f"convert 命令失败: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        else:
            assert result.returncode != 0, "预期 convert 命令失败但返回码为 0"
        return result

    def run_cli_info(self, args, expect_success=True):
        cmd = self.cmd_base + ['info'] + args
        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True, cwd=self.root)
        if expect_success:
            assert result.returncode == 0, f"info 命令失败: {result.returncode}\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}"
        else:
            assert result.returncode != 0, "预期 info 命令失败但返回码为 0"
        return result

    def test_mmkv_create_and_convert_to_json_roundtrip(self):
        # 1) 从 JSON 创建 MMKV 文件（使用通用 convert）
        input_json = os.path.join(self.tmp_dir, "input.json")
        with open(input_json, "w", encoding="utf-8") as f:
            json.dump({"k_bool": True, "k_int": 42, "k_str": "hello"}, f, ensure_ascii=False)

        mmkv_path = os.path.join(self.tmp_dir, "data.mmkv")
        self.run_cli_convert([input_json, mmkv_path, '-t', 'mmkv'])
        assert os.path.exists(mmkv_path), "MMKV 文件未创建"

        # 2) 将 MMKV 转回 JSON（使用通用 convert）
        roundtrip_json = os.path.join(self.tmp_dir, "roundtrip.json")
        self.run_cli_convert([mmkv_path, roundtrip_json, '-t', 'json'])
        assert os.path.exists(roundtrip_json), "roundtrip.json 未生成"

        with open(roundtrip_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        # Unified JSON 输出可能是对象或数组，这里统一支持两种结构
        if isinstance(data, list):
            # 转换为键值视图
            kv = {item["key"]: item.get("value") for item in data if isinstance(item, dict) and "key" in item}
        elif isinstance(data, dict):
            kv = data
        else:
            raise AssertionError("不支持的 JSON 结构")

        assert kv.get("k_bool") is True
        assert kv.get("k_int") == 42
        assert kv.get("k_str") == "hello"

    def test_mmkv_info_text_contains_format_and_path(self):
        # 先创建一个 MMKV 文件
        input_json = os.path.join(self.tmp_dir, "info_input.json")
        with open(input_json, "w", encoding="utf-8") as f:
            json.dump({"foo": 1}, f, ensure_ascii=False)
        mmkv_path = os.path.join(self.tmp_dir, "info.mmkv")
        self.run_cli_convert([input_json, mmkv_path, '-t', 'mmkv'])

        # 调用通用 info
        info_res = self.run_cli_info([mmkv_path])
        output_text = info_res.stdout
        # 文本信息通常包含格式和路径
        assert "MMKV" in output_text or "mmkv" in output_text, "info 输出未包含格式 MMKV"
        assert os.path.basename(mmkv_path) in output_text, "info 输出未包含文件路径"

    def test_mmkv_extract_selected_keys_to_file(self):
        # 仍然通过通用 convert 将 MMKV 转为 JSON，然后在测试内筛选键
        input_json = os.path.join(self.tmp_dir, "extract_input.json")
        with open(input_json, "w", encoding="utf-8") as f:
            json.dump({"k_bool": True, "k_int": 42, "k_str": "hello", "k_extra": "x"}, f, ensure_ascii=False)
        mmkv_path = os.path.join(self.tmp_dir, "extract.mmkv")
        self.run_cli_convert([input_json, mmkv_path, '-t', 'mmkv'])

        # 将 MMKV 转换为 JSON 文件
        all_json = os.path.join(self.tmp_dir, "all.json")
        self.run_cli_convert([mmkv_path, all_json, '-t', 'json'])
        assert os.path.exists(all_json), "转换后的 JSON 文件未生成"

        with open(all_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, list):
            kv = {item["key"]: item.get("value") for item in data if isinstance(item, dict) and "key" in item}
        elif isinstance(data, dict):
            kv = data
        else:
            raise AssertionError("不支持的 JSON 结构")

        # 在测试内做提取校验：确认选定键出现在转换结果中
        assert kv.get("k_bool") is True
        assert kv.get("k_str") == "hello"
        assert "k_int" in kv