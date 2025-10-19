#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
合并配置
"""

from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


@dataclass
class MergeConfig:
    """合并配置"""

    # 基本配置
    mode: str = 'append'  # append, join, update, cross
    sources: List[str] = None
    target: Optional[str] = None
    output: str = ''

    # 字段映射
    key_fields: List[str] = None
    field_mappings: Dict[str, str] = None
    mapping_file: Optional[str] = None
    auto_map: bool = True

    # 性能选项
    use_arrow: bool = False
    parallel_workers: int = 1
    chunk_size: int = 10000

    # 容错选项
    tolerant: bool = False
    ignore_case: bool = False
    handle_duplicates: str = 'keep_first'  # keep_first, keep_last, merge

    # 输出选项
    output_format: Optional[str] = None
    encoding: str = 'utf-8'
    create_backup: bool = False

    def __post_init__(self):
        """初始化后处理"""
        if self.sources is None:
            self.sources = []
        if self.key_fields is None:
            self.key_fields = []
        if self.field_mappings is None:
            self.field_mappings = {}

    def validate(self) -> tuple[bool, str]:
        """验证配置有效性"""
        # 检查模式
        valid_modes = ['append', 'join', 'update', 'cross']
        if self.mode not in valid_modes:
            return False, f"无效的合并模式: {self.mode}，支持的模式: {valid_modes}"

        # 检查输入文件
        if not self.sources:
            return False, "未指定源文件"

        # 检查输出文件
        if not self.output:
            return False, "未指定输出文件"

        # 检查关键字段
        if self.mode in ['join', 'update'] and not self.key_fields:
            return False, f"{self.mode}模式需要指定关键字段"

        # 检查并行工作数
        if self.parallel_workers < 1:
            return False, "并行工作数必须大于0"

        return True, ""

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'mode': self.mode,
            'sources': self.sources,
            'target': self.target,
            'output': self.output,
            'key_fields': self.key_fields,
            'field_mappings': self.field_mappings,
            'mapping_file': self.mapping_file,
            'auto_map': self.auto_map,
            'use_arrow': self.use_arrow,
            'parallel_workers': self.parallel_workers,
            'chunk_size': self.chunk_size,
            'tolerant': self.tolerant,
            'ignore_case': self.ignore_case,
            'handle_duplicates': self.handle_duplicates,
            'output_format': self.output_format,
            'encoding': self.encoding,
            'create_backup': self.create_backup
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MergeConfig':
        """从字典创建配置"""
        return cls(**data)

    def update(self, **kwargs):
        """更新配置"""
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
            else:
                logger.warning(f"未知的配置项: {key}")

    def copy(self) -> 'MergeConfig':
        """创建配置副本"""
        return MergeConfig.from_dict(self.to_dict())


@dataclass
class MergeResult:
    """合并结果"""

    success: bool
    output_path: str
    message: str = ""

    # 统计信息
    total_records: int = 0
    processed_records: int = 0
    skipped_records: int = 0
    error_records: int = 0

    # 性能信息
    duration: float = 0.0
    memory_usage: float = 0.0

    # 详细信息
    warnings: List[str] = None
    errors: List[str] = None

    def __post_init__(self):
        """初始化后处理"""
        if self.warnings is None:
            self.warnings = []
        if self.errors is None:
            self.errors = []

    def add_warning(self, message: str):
        """添加警告"""
        self.warnings.append(message)
        logger.warning(message)

    def add_error(self, message: str):
        """添加错误"""
        self.errors.append(message)
        logger.error(message)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典"""
        return {
            'success': self.success,
            'output_path': self.output_path,
            'message': self.message,
            'total_records': self.total_records,
            'processed_records': self.processed_records,
            'skipped_records': self.skipped_records,
            'error_records': self.error_records,
            'duration': self.duration,
            'memory_usage': self.memory_usage,
            'warnings': self.warnings,
            'errors': self.errors
        }