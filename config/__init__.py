#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置模块
提供配置管理功能
"""

from .settings import Config
from .defaults import DEFAULT_CONFIG

def get_config(config_file=None):
    """获取配置实例"""
    return Config(config_file)

__all__ = ['Config', 'DEFAULT_CONFIG', 'get_config']