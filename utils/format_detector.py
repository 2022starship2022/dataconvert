#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
格式检测模块
提供文件格式检测功能
"""

import os
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Union


class FormatDetector:
    """格式检测器 - 简化版，只通过扩展名判断格式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(FormatDetector, cls).__new__(cls)
            # 扩展名映射，兼容大小写
            cls._instance.extension_mapping = {
                '.csv': 'csv',
                '.tsv': 'csv',  # 将TSV也映射到csv
                '.json': 'json',
                '.jsonl': 'json',  # JSON Lines格式
                '.ndjson': 'json',  # Newline Delimited JSON
                '.xml': 'xml',
                '.xhtml': 'xml',  # XHTML格式
                '.svg': 'xml',  # SVG格式
                '.xlsx': 'excel',
                '.xls': 'excel',
                '.xlsm': 'excel',  # Excel宏文件
                '.sqlite': 'sqlite',
                '.db': 'sqlite',
                '.sqlite3': 'sqlite',  # SQLite3格式
                '.txt': 'text',
                '.log': 'text',
                '.parquet': 'parquet',
                '.feather': 'feather',
                '.hdf5': 'hdf5',
                '.h5': 'hdf5',
                '.mmkv': 'mmkv',
                '.pb': 'protobuf',
                '.proto': 'protobuf'
            }
        return cls._instance
    
    def __init__(self):
        pass
    
    def detect_by_extension(self, file_path: str) -> Optional[str]:
        """
        根据文件扩展名检测格式
        
        Args:
            file_path: 文件路径
            
        Returns:
            检测到的格式，如果无法识别则返回None
        """
        ext = Path(file_path).suffix.lower()
        # 直接查找扩展名映射
        return self.extension_mapping.get(ext, None)
    
    @classmethod
    def detect_format(cls, file_path: str, **kwargs) -> str:
        """
        检测文件格式（类方法）
        
        Args:
            file_path: 文件路径
            **kwargs: 其他参数（忽略）
            
        Returns:
            检测到的格式
            
        Raises:
            ValueError: 如果无法识别格式
        """
        instance = cls()
        detected_format = instance.detect_by_extension(file_path)
        
        if detected_format is None:
            raise ValueError("无法识别的格式")
            
        return detected_format
    
    def _detect_format_with_confidence(self, file_path: str, **kwargs) -> Dict[str, Union[str, float]]:
        """
        检测文件格式并返回置信度
        
        Args:
            file_path: 文件路径
            **kwargs: 其他参数（忽略）
            
        Returns:
            包含格式和置信度的字典
        """
        format_name = self.detect_by_extension(file_path)
        
        if format_name is None:
            raise ValueError("无法识别的格式")
        
        return {
            'format': format_name,
            'confidence': 1.0,  # 基于扩展名的检测置信度为1.0
            'method': 'extension'
        }
    
    def detect_batch(self, file_paths: List[str], **kwargs) -> Dict[str, str]:
        """
        批量检测文件格式
        
        Args:
            file_paths: 文件路径列表
            **kwargs: 传递给detect_format的参数
            
        Returns:
            文件路径到格式的映射字典
            
        Raises:
            ValueError: 如果有文件无法识别格式
        """
        results = {}
        for file_path in file_paths:
            result = self.__class__.detect_format(file_path, **kwargs)
            results[file_path] = result
        return results
    
    @classmethod
    def detect_format_with_confidence(cls, file_path: str, **kwargs) -> Tuple[str, float]:
        """
        检测文件格式并返回置信度（类方法）
        
        Args:
            file_path: 文件路径
            **kwargs: 其他参数
            
        Returns:
            元组：(格式, 置信度)
            
        Raises:
            ValueError: 如果无法识别格式
        """
        instance = cls()
        result = instance._detect_format_with_confidence(file_path, **kwargs)
        format_name = result['format']
        return format_name, result['confidence']
    
    @classmethod
    def get_supported_formats(cls) -> List[str]:
        """
        获取支持的格式列表（类方法）
        
        Returns:
            支持的格式列表
        """
        instance = cls()
        return list(set(instance.extension_mapping.values()))
    
    @classmethod
    def is_format_supported(cls, format_name: str) -> bool:
        """
        检查格式是否支持（类方法）
        
        Args:
            format_name: 格式名称
            
        Returns:
            是否支持
        """
        return format_name.lower() in cls.get_supported_formats()
    
    def get_supported_formats_info(self) -> Dict[str, Dict[str, Union[str, List[str]]]]:
        """
        获取支持的格式信息
        
        Returns:
            支持的格式信息字典
        """
        return {
            'csv': {
                'description': '逗号分隔值文件',
                'extensions': ['.csv', '.tsv'],
                'mime_types': ['text/csv', 'text/tab-separated-values'],
                'features': ['表格数据', '简单结构', '广泛支持']
            },
            'json': {
                'description': 'JavaScript对象表示法',
                'extensions': ['.json', '.jsonl', '.ndjson'],
                'mime_types': ['application/json'],
                'features': ['结构化数据', '嵌套支持', '轻量级']
            },
            'xml': {
                'description': '可扩展标记语言',
                'extensions': ['.xml', '.xhtml', '.svg'],
                'mime_types': ['application/xml', 'text/xml'],
                'features': ['结构化数据', '自定义标签', '元数据支持']
            },
            'excel': {
                'description': 'Microsoft Excel电子表格',
                'extensions': ['.xlsx', '.xls', '.xlsm'],
                'mime_types': ['application/vnd.openxmlformats-officedocument.spreadsheetml.sheet', 
                              'application/vnd.ms-excel'],
                'features': ['表格数据', '公式支持', '多工作表']
            },
            'sqlite': {
                'description': 'SQLite数据库文件',
                'extensions': ['.sqlite', '.db', '.sqlite3'],
                'mime_types': ['application/x-sqlite3'],
                'features': ['关系型数据', 'SQL查询', '事务支持']
            },
            'text': {
                'description': '纯文本文件',
                'extensions': ['.txt', '.log'],
                'mime_types': ['text/plain'],
                'features': ['纯文本', '简单格式', '广泛支持']
            },
            'parquet': {
                'description': 'Apache Parquet列式存储格式',
                'extensions': ['.parquet'],
                'mime_types': ['application/octet-stream'],
                'features': ['列式存储', '高效压缩', '大数据处理']
            },
            'feather': {
                'description': 'Feather文件格式',
                'extensions': ['.feather'],
                'mime_types': ['application/octet-stream'],
                'features': ['高效读写', '语言无关', '内存映射']
            },
            'hdf5': {
                'description': '分层数据格式',
                'extensions': ['.hdf5', '.h5'],
                'mime_types': ['application/octet-stream'],
                'features': ['分层数据', '元数据', '大数据存储']
            },
            'mmkv': {
                'description': 'MMKV键值存储格式',
                'extensions': ['.mmkv'],
                'mime_types': ['application/octet-stream'],
                'features': ['键值存储', '高性能', '跨平台']
            },
            'protobuf': {
                'description': 'Protocol Buffers序列化格式',
                'extensions': ['.pb', '.proto'],
                'mime_types': ['application/octet-stream'],
                'features': ['高效序列化', '跨语言', '版本兼容']
            }
        }
    
    def validate_format(self, file_path: str, expected_format: str) -> Dict[str, Union[bool, str, float]]:
        """
        验证文件格式是否符合预期
        
        Args:
            file_path: 文件路径
            expected_format: 预期格式
            
        Returns:
            验证结果字典
        """
        try:
            detection = self.__class__.detect_format(file_path)
            is_valid = detection.lower() == expected_format.lower()
            
            return {
                'is_valid': is_valid,
                'detected_format': detection,
                'expected_format': expected_format,
                'confidence': 1.0,
                'method': 'extension'
            }
        except ValueError:
            return {
                'is_valid': False,
                'detected_format': 'unknown',
                'expected_format': expected_format,
                'confidence': 0.0,
                'method': 'extension',
                'error': '无法识别的格式'
            }


def detect_format(file_path: str, **kwargs) -> Dict[str, Union[str, float]]:
    """
    检测文件格式（便捷函数）
    
    Args:
        file_path: 文件路径
        **kwargs: 传递给FormatDetector.detect_format的参数
        
    Returns:
        包含格式和置信度的字典
        
    Raises:
        ValueError: 如果无法识别格式
    """
    instance = FormatDetector()
    result = instance._detect_format_with_confidence(file_path, **kwargs)
    return result