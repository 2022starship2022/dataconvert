#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置管理器
"""

import os
import yaml
import logging
from typing import Any, Dict, Optional
from pathlib import Path

from .defaults import DEFAULT_CONFIG

logger = logging.getLogger(__name__)


class Config:
    """配置管理器"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化配置管理器

        Args:
            config_file: 配置文件路径
        """
        self._config = DEFAULT_CONFIG.copy()
        self._config_file = config_file
        self._watchers = {}  # 存储监视器
        self._last_modified = None  # 存储最后修改时间

        # 确保测试所需的默认配置存在
        self._ensure_test_defaults()

        # 检查环境变量
        self._load_from_environment()

        if config_file:
            # 检查是否是继承配置
            self._load_config_with_inheritance(config_file)

    def _ensure_test_defaults(self):
        """确保测试所需的默认配置存在"""
        test_defaults = {
            'csv': {
                'delimiter': ',',
                'quotechar': '"',
                'encoding': 'utf-8'
            },
            'json': {
                'indent': None,
                'ensure_ascii': True
            },
            'xml': {
                'encoding': 'utf-8'
            },
            'excel': {
                'sheet_name': 'Sheet1'
            },
            'sqlite': {
                'table_name': 'data'
            }
        }
        
        for section, values in test_defaults.items():
            if section not in self._config:
                self._config[section] = {}
            for key, value in values.items():
                if key not in self._config[section]:
                    self._config[section][key] = value

    def _load_from_environment(self):
        """从环境变量加载配置"""
        env_mappings = {
            'DATACONVERT_CSV_DELIMITER': 'csv.delimiter',
            'DATACONVERT_JSON_INDENT': 'json.indent',
            'DATACONVERT_XML_ENCODING': 'xml.encoding'
        }
        
        for env_var, config_key in env_mappings.items():
            if env_var in os.environ:
                value = os.environ[env_var]
                # 尝试转换类型
                if config_key.endswith('.indent'):
                    try:
                        value = int(value)
                    except ValueError:
                        pass
                self.set(config_key, value)

    def _load_config_with_inheritance(self, config_file: str):
        """加载配置文件，支持继承"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.warning(f"配置文件不存在: {config_file}")
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                # 根据文件扩展名判断配置文件格式
                if config_path.suffix.lower() == '.json':
                    import json
                    user_config = json.load(f)
                else:
                    # 默认使用YAML格式
                    user_config = yaml.safe_load(f)

            # 检查是否有继承
            if '_extends' in user_config:
                base_config_file = user_config['_extends']
                self._load_config_with_inheritance(base_config_file)
                # 移除继承标记
                del user_config['_extends']

            if user_config:
                self._merge_config(self._config, user_config)
                logger.info(f"已加载配置文件: {config_file}")
                
            # 记录最后修改时间
            self._last_modified = config_path.stat().st_mtime
            
            # 加载配置文件后，再次加载环境变量，使环境变量优先级更高
            self._load_from_environment()

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise

    def load_config(self, config_file: str):
        """加载配置文件"""
        try:
            config_path = Path(config_file)
            if not config_path.exists():
                logger.warning(f"配置文件不存在: {config_file}")
                return

            with open(config_path, 'r', encoding='utf-8') as f:
                # 根据文件扩展名判断配置文件格式
                if config_path.suffix.lower() == '.json':
                    import json
                    user_config = json.load(f)
                else:
                    # 默认使用YAML格式
                    user_config = yaml.safe_load(f)

            if user_config:
                self._merge_config(self._config, user_config)
                logger.info(f"已加载配置文件: {config_file}")
                
            # 加载配置文件后，再次加载环境变量，使环境变量优先级更高
            self._load_from_environment()

        except Exception as e:
            logger.error(f"加载配置文件失败: {e}")
            raise

    def save_config(self, config_file: Optional[str] = None):
        """保存配置到文件"""
        output_file = config_file or self._config_file
        if not output_file:
            raise ValueError("未指定配置文件路径")

        try:
            config_path = Path(output_file)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            # 根据文件扩展名决定保存格式
            if config_path.suffix.lower() == '.json':
                import json
                with open(config_path, 'w', encoding='utf-8') as f:
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
            else:
                # 默认使用YAML格式
                with open(config_path, 'w', encoding='utf-8') as f:
                    yaml.dump(self._config, f, default_flow_style=False,
                             allow_unicode=True, indent=2)

            logger.info(f"配置已保存到: {output_file}")

        except Exception as e:
            logger.error(f"保存配置文件失败: {e}")
            raise

    def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键 (如: 'global.log_level')
            default: 默认值

        Returns:
            配置值
        """
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default

    def set(self, key: str, value: Any):
        """
        设置配置值

        Args:
            key: 配置键，支持点号分隔的嵌套键
            value: 配置值
        """
        keys = key.split('.')
        config = self._config

        # 导航到最后一级的父级
        for k in keys[:-1]:
            if k not in config:
                config[k] = {}
            config = config[k]

        # 设置最终值
        config[keys[-1]] = value

    def update(self, updates: Dict[str, Any]):
        """批量更新配置"""
        for key, value in updates.items():
            self.set(key, value)

    def get_global(self, key: str, default: Any = None) -> Any:
        """获取全局配置"""
        return self.get(f'global.{key}', default)

    def get_convert(self, key: str, default: Any = None) -> Any:
        """获取转换配置"""
        return self.get(f'convert.{key}', default)

    def get_merge(self, key: str, default: Any = None) -> Any:
        """获取合并配置"""
        return self.get(f'merge.{key}', default)

    def get_format_config(self, format_name: str) -> Dict[str, Any]:
        """获取格式配置"""
        return self.get(f'formats.{format_name}', {})

    def is_format_enabled(self, format_name: str) -> bool:
        """检查格式是否启用"""
        return self.get(f'formats.{format_name}.enabled', False)

    def get_supported_extensions(self, format_name: str) -> list:
        """获取格式支持的扩展名"""
        return self.get(f'formats.{format_name}.extensions', [])

    def _merge_config(self, base: Dict, update: Dict):
        """递归合并配置字典"""
        for key, value in update.items():
            if key in base and isinstance(base[key], dict) and isinstance(value, dict):
                self._merge_config(base[key], value)
            else:
                base[key] = value
        return base

    def create_default_config_file(self, file_path: str):
        """创建默认配置文件"""
        try:
            config_path = Path(file_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w', encoding='utf-8') as f:
                yaml.dump(DEFAULT_CONFIG, f, default_flow_style=False,
                         allow_unicode=True, indent=2)

            logger.info(f"默认配置文件已创建: {file_path}")

        except Exception as e:
            logger.error(f"创建默认配置文件失败: {e}")
            raise

    def validate_config(self, key=None, value=None, schema=None) -> bool:
        """
        验证配置有效性

        Args:
            key: 要验证的配置键，如果为None则验证整个配置
            value: 要验证的值，如果为None则验证当前配置中的值
            schema: 验证模式，当前未使用

        Returns:
            验证是否通过
        """
        try:
            # 如果提供了键和值，则验证特定键值对
            if key is not None and value is not None:
                return self._validate_key_value(key, value)
            
            # 如果提供了配置，则验证提供的配置
            elif key is not None and value is None:
                config_to_validate = key
            else:
                config_to_validate = self._config

            # 验证整个配置
            # 验证必需的配置项
            required_keys = [
                'global.log_level',
                'global.encoding',
                'convert.default_output_format',
                'merge.default_mode'
            ]

            for k in required_keys:
                keys = k.split('.')
                v = config_to_validate
                try:
                    for key in keys:
                        v = v[key]
                    if v is None:
                        logger.error(f"缺少必需的配置项: {k}")
                        return False
                except (KeyError, TypeError):
                    logger.error(f"缺少必需的配置项: {k}")
                    return False

            # 验证日志级别
            valid_log_levels = ['DEBUG', 'INFO', 'WARNING', 'ERROR']
            log_level = config_to_validate.get('global', {}).get('log_level')
            if log_level not in valid_log_levels:
                logger.error(f"无效的日志级别: {log_level}")
                return False

            # 验证输出格式
            valid_formats = ['csv', 'excel', 'json', 'xml', 'sqlite']
            output_format = config_to_validate.get('convert', {}).get('default_output_format')
            if output_format not in valid_formats:
                logger.error(f"无效的默认输出格式: {output_format}")
                return False

            # 验证合并模式
            valid_merge_modes = ['append', 'join', 'update', 'cross']
            merge_mode = config_to_validate.get('merge', {}).get('default_mode')
            if merge_mode not in valid_merge_modes:
                logger.error(f"无效的默认合并模式: {merge_mode}")
                return False

            logger.info("配置验证通过")
            return True

        except Exception as e:
            logger.error(f"配置验证失败: {e}")
            return False
            
    def _validate_key_value(self, key, value) -> bool:
        """验证特定键值对"""
        # 根据键验证值类型
        if key == "csv.delimiter":
            return isinstance(value, str)
        elif key == "csv.quotechar":
            return isinstance(value, str)
        elif key == "json.indent":
            return value is None or isinstance(value, int)
        elif key == "xml.encoding":
            return isinstance(value, str)
        else:
            # 默认情况下，任何值都是有效的
            return True

    def has(self, key: str) -> bool:
        """
        检查配置键是否存在

        Args:
            key: 配置键，支持点号分隔的嵌套键

        Returns:
            是否存在
        """
        keys = key.split('.')
        value = self._config

        try:
            for k in keys:
                value = value[k]
            # 键存在，无论值是否为None都返回True
            return True
        except (KeyError, TypeError):
            return False

    def get_section(self, section_name: str) -> Dict[str, Any]:
        """
        获取配置节

        Args:
            section_name: 节名称

        Returns:
            配置节字典
        """
        section = self.get(section_name)
        return section if isinstance(section, dict) else {}

    def update_section(self, section_name: str, section_data: Dict[str, Any]):
        """
        更新配置节

        Args:
            section_name: 节名称
            section_data: 节数据
        """
        current_section = self.get_section(section_name)
        current_section.update(section_data)
        self.set(section_name, current_section)

    def save(self, config_file: Optional[str] = None):
        """保存配置到文件（别名方法）"""
        self.save_config(config_file)

    def reload(self):
        """重新加载配置文件"""
        if self._config_file:
            # 重置为默认配置
            self._config = DEFAULT_CONFIG.copy()
            # 重新加载配置文件
            self.load_config(self._config_file)
        else:
            logger.warning("没有配置文件路径，无法重新加载")

    def reset_to_defaults(self):
        """重置为默认配置"""
        self._config = DEFAULT_CONFIG.copy()
        # 确保测试所需的默认配置存在
        self._ensure_test_defaults()

    def __getitem__(self, key: str) -> Any:
        """支持字典式访问"""
        return self.get(key)

    def __setitem__(self, key: str, value: Any):
        """支持字典式设置"""
        self.set(key, value)

    def __contains__(self, key: str) -> bool:
        """支持 in 操作符"""
        return self.get(key) is not None

    def merge(self, config: Dict[str, Any]):
        """
        合并配置字典

        Args:
            config: 要合并的配置字典
        """
        self._merge_config(self._config, config)

    def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置

        Returns:
            所有配置的字典
        """
        return self._config.copy()

    def watch(self, key=None, callback=None):
        """
        监视配置文件变化

        Args:
            key: 要监视的配置键，如果为None则监视所有变化
            callback: 变化回调函数
        """
        if key is not None and callback is not None:
            # 添加特定键的监视器
            self._watchers[key] = callback
        else:
            logger.warning("配置文件监视功能尚未完全实现")
            # 这里可以实现文件监视功能，但为了简单起见，只记录警告

    def check_for_changes(self):
        """检查配置文件是否有变化"""
        if not self._config_file:
            return
            
        try:
            config_path = Path(self._config_file)
            if not config_path.exists():
                return
                
            current_mtime = config_path.stat().st_mtime
            if self._last_modified and current_mtime > self._last_modified:
                # 文件已修改，重新加载
                old_config = self._config.copy()
                self._config = DEFAULT_CONFIG.copy()
                self._load_config_with_inheritance(self._config_file)
                
                # 检查哪些值发生了变化
                for key, callback in self._watchers.items():
                    old_value = self._get_nested_value(old_config, key)
                    new_value = self.get(key)
                    if old_value != new_value:
                        callback(key, old_value, new_value)
                        
                self._last_modified = current_mtime
        except Exception as e:
            logger.error(f"检查配置变化失败: {e}")
            
    def _get_nested_value(self, config, key):
        """获取嵌套配置值"""
        keys = key.split('.')
        value = config
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return None

    def export(self, file_path: str, format: str = 'yaml'):
        """
        导出配置到文件

        Args:
            file_path: 导出文件路径
            format: 导出格式 ('yaml', 'json', 'ini')
        """
        try:
            config_path = Path(file_path)
            config_path.parent.mkdir(parents=True, exist_ok=True)

            with open(config_path, 'w', encoding='utf-8') as f:
                if format.lower() == 'json':
                    import json
                    json.dump(self._config, f, indent=2, ensure_ascii=False)
                elif format.lower() == 'ini':
                    # 简单的INI格式导出
                    import configparser
                    config = configparser.ConfigParser()
                    
                    def flatten_dict(d, parent_key='', sep='_'):
                        items = []
                        for k, v in d.items():
                            new_key = f"{parent_key}{sep}{k}" if parent_key else k
                            if isinstance(v, dict):
                                items.extend(flatten_dict(v, new_key, sep=sep).items())
                            else:
                                items.append((new_key, str(v)))
                        return dict(items)
                    
                    flat_config = flatten_dict(self._config)
                    config['DEFAULT'] = flat_config
                    config.write(f)
                else:
                    # 默认使用YAML格式
                    yaml.dump(self._config, f, default_flow_style=False,
                             allow_unicode=True, indent=2)

            logger.info(f"配置已导出到: {file_path}")

        except Exception as e:
            logger.error(f"导出配置失败: {e}")
            raise

    def import_config(self, file_path: str, format: str = None):
        """
        从文件导入配置

        Args:
            file_path: 导入文件路径
            format: 导入格式，如果为None则根据文件扩展名判断
        """
        try:
            config_path = Path(file_path)
            if not config_path.exists():
                logger.warning(f"配置文件不存在: {file_path}")
                return

            # 如果没有指定格式，根据文件扩展名判断
            if format is None:
                if config_path.suffix.lower() == '.json':
                    format = 'json'
                elif config_path.suffix.lower() in ['.ini', '.cfg']:
                    format = 'ini'
                else:
                    format = 'yaml'

            with open(config_path, 'r', encoding='utf-8') as f:
                if format.lower() == 'json':
                    import json
                    user_config = json.load(f)
                elif format.lower() == 'ini':
                    # 简单的INI格式导入
                    import configparser
                    config = configparser.ConfigParser()
                    config.read(f)
                    
                    # 将扁平化的配置转换为嵌套字典
                    user_config = {}
                    for key, value in config['DEFAULT'].items():
                        self._set_nested_value(user_config, key, value)
                else:
                    # 默认使用YAML格式
                    user_config = yaml.safe_load(f)

            if user_config:
                self._merge_config(self._config, user_config)
                logger.info(f"已导入配置文件: {file_path}")

        except Exception as e:
            logger.error(f"导入配置文件失败: {e}")
            raise
            
    def _set_nested_value(self, config, key, value):
        """设置嵌套配置值"""
        keys = key.split('_')
        current = config
        
        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]
            
        # 尝试转换值类型
        try:
            if value.lower() in ['true', 'false']:
                value = value.lower() == 'true'
            elif value.isdigit():
                value = int(value)
            elif '.' in value and value.replace('.', '').isdigit():
                value = float(value)
        except (ValueError, AttributeError):
            pass
            
        current[keys[-1]] = value


def get_config(config_file: Optional[str] = None) -> Config:
    """
    获取配置实例

    Args:
        config_file: 配置文件路径

    Returns:
        Config实例
    """
    return Config(config_file)