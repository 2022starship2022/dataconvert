#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
统一入口：直接运行本文件即可启动 DataConvert CLI。
示例：
    python CLI_main.py --help
    python CLI_main.py convert data.csv out.xlsx --to excel
"""
import sys

try:
    # 复用已有的 CLI 主逻辑
    from cli.main import main as _main
except Exception:
    # 兼容备用路径：直接走 DataConverterCLI.run()
    from cli.main import DataConverterCLI as _CLI
    def _main():
        cli = _CLI()
        return cli.run()

if __name__ == "__main__":
    try:
        exit_code = _main()
        # 如果 _main 自行调用了 sys.exit，不会到这里；否则按返回码退出
        if isinstance(exit_code, int):
            sys.exit(exit_code)
    except SystemExit as e:
        sys.exit(e.code)
    except Exception as e:
        print(f"启动失败: {e}")
        sys.exit(1)