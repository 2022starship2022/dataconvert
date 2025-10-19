#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
工具模块包初始化
保持最小化，仅在需要时导入具体子模块。
"""

# 仅保留被核心使用的检测器
from .format_detector import FormatDetector

__all__ = [
    'FormatDetector'
]