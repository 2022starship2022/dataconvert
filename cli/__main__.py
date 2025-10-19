#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI模块入口点
"""
from cli.main import DataConverterCLI

if __name__ == "__main__":
    import sys
    cli = DataConverterCLI()
    sys.exit(cli.run())