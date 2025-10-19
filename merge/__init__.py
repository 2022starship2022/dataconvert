#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据合并模块
提供多种数据合并策略和实现
"""

from .engine import MergeEngine, MergeResult
from .config import MergeConfig
from .field_mapper import FieldMapper

__all__ = ['MergeEngine', 'MergeResult', 'MergeConfig', 'FieldMapper']