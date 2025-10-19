#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
字段映射器
提供自动字段映射和手动映射功能
"""

import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from difflib import SequenceMatcher

logger = logging.getLogger(__name__)


class FieldMapper:
    """字段映射器"""

    # 常见字段同义词映射
    COMMON_FIELD_MAPPINGS = {
        'id': ['id', 'ID', 'identifier', 'Identifier', 'user_id', 'user_id', 'customer_id'],
        'name': ['name', 'Name', 'full_name', 'fullname', '姓名', '名称'],
        'email': ['email', 'Email', 'email_address', '邮箱', '电子邮件'],
        'phone': ['phone', 'Phone', 'telephone', 'tel', '电话', '手机'],
        'address': ['address', 'Address', 'addr', '地址'],
        'date': ['date', 'Date', 'datetime', '时间', '日期', '创建时间', 'update_time'],
        'status': ['status', 'Status', 'state', '状态'],
        'type': ['type', 'Type', 'category', '类别', '类型'],
        'price': ['price', 'Price', 'amount', 'cost', '价格', '金额'],
        'quantity': ['quantity', 'Quantity', 'qty', 'num', '数量'],
        'description': ['description', 'Description', 'desc', '备注', '描述'],
        'created_at': ['created_at', 'Created', 'create_time', '创建时间'],
        'updated_at': ['updated_at', 'Updated', 'update_time', '更新时间']
    }

    @classmethod
    def auto_map_fields(cls, target_table: Any, source_tables: List[Any]) -> Dict[str, str]:
        """
        自动字段映射

        Args:
            target_table: 目标表
            source_tables: 源表列表

        Returns:
            字段映射字典 {target_field: source_field}
        """
        try:
            # 获取目标表字段
            target_fields = cls._get_table_fields(target_table)
            if not target_fields:
                return {}

            mappings = {}

            # 对每个源表进行映射
            for source_table in source_tables:
                source_fields = cls._get_table_fields(source_table)
                if not source_fields:
                    continue

                # 执行字段映射
                source_mappings = cls._find_best_mappings(target_fields, source_fields)
                mappings.update(source_mappings)

            logger.info(f"自动映射完成，映射数量: {len(mappings)}")
            return mappings

        except Exception as e:
            logger.error(f"自动字段映射失败: {e}")
            return {}

    @classmethod
    def calculate_mapping_confidence(cls, target_field: str, source_field: str) -> float:
        """
        计算字段映射置信度

        Args:
            target_field: 目标字段名
            source_field: 源字段名

        Returns:
            置信度 (0.0 - 1.0)
        """
        try:
            # 完全匹配
            if target_field.lower() == source_field.lower():
                return 1.0

            # 标准化字段名
            target_normalized = cls._normalize_field_name(target_field)
            source_normalized = cls._normalize_field_name(source_field)

            if target_normalized == source_normalized:
                return 0.9

            # 同义词匹配
            for standard_field, synonyms in cls.COMMON_FIELD_MAPPINGS.items():
                if (target_normalized in [cls._normalize_field_name(s) for s in synonyms] and
                    source_normalized in [cls._normalize_field_name(s) for s in synonyms]):
                    return 0.8

            # 模糊匹配
            similarity = SequenceMatcher(None, target_normalized, source_normalized).ratio()
            if similarity > 0.8:
                return 0.7

            # 部分匹配
            if (target_normalized in source_normalized or
                source_normalized in target_normalized):
                return 0.6

            # 前缀匹配
            if (target_normalized.startswith(source_normalized) or
                source_normalized.startswith(target_normalized)):
                return 0.5

            return similarity

        except Exception as e:
            logger.error(f"计算映射置信度失败: {e}")
            return 0.0

    @classmethod
    def find_field_matches(cls, target_field: str, source_fields: List[str],
                          min_confidence: float = 0.5) -> List[Tuple[str, float]]:
        """
        查找目标字段的匹配源字段

        Args:
            target_field: 目标字段名
            source_fields: 源字段列表
            min_confidence: 最小置信度

        Returns:
            匹配列表 [(source_field, confidence), ...]
        """
        matches = []

        for source_field in source_fields:
            confidence = cls.calculate_mapping_confidence(target_field, source_field)
            if confidence >= min_confidence:
                matches.append((source_field, confidence))

        # 按置信度排序
        matches.sort(key=lambda x: x[1], reverse=True)
        return matches

    @classmethod
    def suggest_field_name(cls, field_name: str) -> str:
        """
        建议标准字段名

        Args:
            field_name: 原始字段名

        Returns:
            建议的标准字段名
        """
        normalized = cls._normalize_field_name(field_name)

        # 查找同义词映射
        for standard_field, synonyms in cls.COMMON_FIELD_MAPPINGS.items():
            if normalized in [cls._normalize_field_name(s) for s in synonyms]:
                return standard_field

        return field_name

    @classmethod
    def validate_mapping(cls, target_fields: List[str], source_fields: List[str],
                        mapping: Dict[str, str]) -> Tuple[bool, List[str]]:
        """
        验证字段映射

        Args:
            target_fields: 目标字段列表
            source_fields: 源字段列表
            mapping: 映射字典

        Returns:
            (是否有效, 错误信息列表)
        """
        errors = []

        # 检查目标字段
        for target_field in mapping.keys():
            if target_field not in target_fields:
                errors.append(f"目标字段不存在: {target_field}")

        # 检查源字段
        for source_field in mapping.values():
            if source_field not in source_fields:
                errors.append(f"源字段不存在: {source_field}")

        # 检查重复映射
        source_field_counts = {}
        for source_field in mapping.values():
            source_field_counts[source_field] = source_field_counts.get(source_field, 0) + 1

        for source_field, count in source_field_counts.items():
            if count > 1:
                errors.append(f"源字段重复映射: {source_field}")

        return len(errors) == 0, errors

    @classmethod
    def _get_table_fields(cls, table: Any) -> List[str]:
        """获取表的字段列表"""
        try:
            if hasattr(table, 'columns'):
                # DataFrame
                return list(table.columns)
            elif hasattr(table, 'fields'):
                # 自定义表对象
                return list(table.fields)
            elif isinstance(table, dict):
                # 字典
                return list(table.keys())
            elif isinstance(table, (list, tuple)) and table:
                # 列表/元组，假设第一个元素是字典
                first_item = table[0]
                if isinstance(first_item, dict):
                    return list(first_item.keys())
            else:
                logger.warning(f"无法获取表的字段: {type(table)}")
                return []

        except Exception as e:
            logger.error(f"获取表字段失败: {e}")
            return []

    @classmethod
    def _find_best_mappings(cls, target_fields: List[str],
                           source_fields: List[str]) -> Dict[str, str]:
        """查找最佳字段映射"""
        mappings = {}
        used_source_fields = set()

        # 为每个目标字段找到最佳匹配
        for target_field in target_fields:
            matches = cls.find_field_matches(target_field, source_fields)

            # 选择未使用的最佳匹配
            for source_field, confidence in matches:
                if source_field not in used_source_fields and confidence >= 0.6:
                    mappings[target_field] = source_field
                    used_source_fields.add(source_field)
                    break

        return mappings

    @classmethod
    def _normalize_field_name(cls, field_name: str) -> str:
        """标准化字段名"""
        if not field_name:
            return ""

        # 转换为小写
        normalized = field_name.lower().strip()

        # 替换分隔符
        separators = ['_', '-', ' ', '.', ':']
        for sep in separators:
            normalized = normalized.replace(sep, '_')

        # 移除常见前缀
        prefixes = ['col', 'column', 'field', 'f_']
        for prefix in prefixes:
            if normalized.startswith(prefix + '_'):
                normalized = normalized[len(prefix) + 1:]
                break

        # 移除常见后缀
        suffixes = ['_col', '_column', '_field', '_id', '_num', '_str']
        for suffix in suffixes:
            if normalized.endswith(suffix):
                normalized = normalized[:-len(suffix)]
                break

        # 移除数字后缀
        normalized = re.sub(r'_\d+$', '', normalized)

        return normalized

    @classmethod
    def create_mapping_from_dict(cls, mapping_dict: Dict[str, str]) -> Dict[str, Dict[str, Any]]:
        """
        从字典创建详细映射信息

        Args:
            mapping_dict: 简单映射字典 {target: source}

        Returns:
            详细映射信息 {target: {source_field, confidence, type}}
        """
        detailed_mapping = {}

        for target_field, source_field in mapping_dict.items():
            confidence = cls.calculate_mapping_confidence(target_field, source_field)

            mapping_type = 'manual'
            if confidence >= 0.8:
                mapping_type = 'auto'
            elif confidence >= 0.6:
                mapping_type = 'suggested'

            detailed_mapping[target_field] = {
                'source_field': source_field,
                'confidence': confidence,
                'type': mapping_type
            }

        return detailed_mapping

    @classmethod
    def export_mapping(cls, mapping: Dict[str, Any], format: str = 'json') -> str:
        """
        导出字段映射

        Args:
            mapping: 映射字典
            format: 导出格式 (json, yaml, csv)

        Returns:
            导出字符串
        """
        try:
            if format == 'json':
                import json
                return json.dumps(mapping, indent=2, ensure_ascii=False, default=str)

            elif format == 'yaml':
                import yaml
                return yaml.dump(mapping, default_flow_style=False, allow_unicode=True)

            elif format == 'csv':
                lines = ['target_field,source_field,confidence,type']
                for target, info in mapping.items():
                    if isinstance(info, dict):
                        source = info.get('source_field', '')
                        confidence = info.get('confidence', 0)
                        mapping_type = info.get('type', 'manual')
                        lines.append(f"{target},{source},{confidence},{mapping_type}")
                    else:
                        lines.append(f"{target},{info},1.0,manual")
                return '\n'.join(lines)

            else:
                raise ValueError(f"不支持的导出格式: {format}")

        except Exception as e:
            logger.error(f"导出映射失败: {e}")
            return str(mapping)

    @classmethod
    def import_mapping(cls, mapping_str: str, format: str = 'json') -> Dict[str, Any]:
        """
        导入字段映射

        Args:
            mapping_str: 映射字符串
            format: 导入格式 (json, yaml, csv)

        Returns:
            映射字典
        """
        try:
            if format == 'json':
                import json
                return json.loads(mapping_str)

            elif format == 'yaml':
                import yaml
                return yaml.safe_load(mapping_str)

            elif format == 'csv':
                mapping = {}
                lines = mapping_str.strip().split('\n')
                for line in lines[1:]:  # 跳过标题行
                    parts = line.split(',')
                    if len(parts) >= 2:
                        target = parts[0].strip()
                        source = parts[1].strip()
                        if target and source:
                            mapping[target] = source
                return mapping

            else:
                raise ValueError(f"不支持的导入格式: {format}")

        except Exception as e:
            logger.error(f"导入映射失败: {e}")
            return {}