"""
数据类型推断工具
用于推断和转换数据类型
"""
import datetime
import decimal
import json
import re
from typing import Any, List, Type, Dict, Set, Optional, Union


class TypeInference:
    """数据类型推断工具类"""
    
    # 类型层次结构，从具体到通用
    TYPE_HIERARCHY = {
        bool: {bool, int},         # bool可以兼容int
        int: {int, float},         # int可以兼容float
        float: {int, float, decimal.Decimal},  # float可以兼容int和decimal
        complex: {complex, float, int, str},  # complex可以兼容float和int和str
        decimal.Decimal: {float, decimal.Decimal, str},  # decimal可以兼容float和str
        str: {str},                # str是最通用的类型
        datetime.date: {datetime.date, datetime.datetime},  # date可以兼容datetime
        datetime.datetime: {datetime.date, datetime.datetime, str},  # datetime可以兼容date和str
        datetime.time: {datetime.time, str},  # time可以兼容str
        list: {list, str},         # list可以兼容str
        dict: {dict, str},         # dict可以兼容str
        type(None): {type(None), str}  # None可以兼容str
    }
    
    @classmethod
    def infer_type(cls, value: Any) -> Type:
        """
        推断值的类型
        
        Args:
            value: 要推断类型的值
            
        Returns:
            推断出的类型
        """
        # 处理None值
        if value is None:
            return type(None)
            
        # 处理numpy类型
        try:
            import numpy as np
            if isinstance(value, (np.int32, np.int64, np.uint32, np.float32, np.float64, np.bool_, np.string_, np.unicode_)):
                return type(value)
        except ImportError:
            pass
            
        # 如果已经是某种类型，直接返回
        if not isinstance(value, str):
            return type(value)
            
        # 处理字符串值
        value_str = value.strip()
        
        # 空字符串
        if not value_str:
            return str
            
        # None字符串
        if value_str.lower() in ['null', 'none']:
            return type(None)
            
        # 布尔值
        if value_str.lower() in ['true', 'false']:
            return bool
            
        # 特殊浮点数值
        if value_str.lower() in ['nan', 'infinity', '-infinity', '+infinity']:
            return float
            
        # 列表格式（JSON）
        if value_str.startswith('[') and value_str.endswith(']'):
            return list
            
        # 字典格式（JSON）
        if value_str.startswith('{') and value_str.endswith('}'):
            return dict
            
        # 日期时间
        if cls._is_datetime(value_str):
            return datetime.datetime
            
        # 日期
        if cls._is_date(value_str):
            return datetime.date
            
        # 时间
        if cls._is_time(value_str):
            return datetime.time
            
        # 复数
        if cls._is_complex(value_str):
            return complex
            
        # 高精度小数（优先于浮点数检查）
        if cls._is_decimal(value_str):
            return decimal.Decimal
            
        # 浮点数（包括科学计数法）
        if cls._is_float(value_str):
            return float
            
        # 整数
        if cls._is_integer(value_str):
            return int
            
        # 默认为字符串
        return str
    
    @classmethod
    def infer_type_from_samples(cls, samples: List[Any]) -> Type:
        """
        从样本数据中推断最合适的类型
        
        Args:
            samples: 样本数据列表
            
        Returns:
            推断出的最合适类型
        """
        if not samples:
            return str
            
        # 推断每个样本的类型
        types = [cls.infer_type(sample) for sample in samples]
        
        # 获取最具体的类型
        return cls.get_most_specific_type(types)
    
    @classmethod
    def convert_value(cls, value: Any, target_type: Type) -> Any:
        """
        将值转换为目标类型
        
        Args:
            value: 要转换的值
            target_type: 目标类型
            
        Returns:
            转换后的值
            
        Raises:
            ValueError: 转换失败时抛出
            decimal.InvalidOperation: 高精度小数转换失败时抛出
        """
        # 处理None值
        if value is None or (isinstance(value, str) and value.lower() in ['null', 'none']):
            return None
            
        # 如果已经是目标类型，直接返回
        if isinstance(value, target_type):
            return value
            
        # 字符串转换
        if isinstance(value, str):
            value_str = value.strip()
            
            # 转换为整数
            if target_type is int:
                try:
                    return int(value_str)
                except ValueError:
                    raise ValueError(f"无法将字符串 '{value_str}' 转换为整数")
                
            # 转换为浮点数
            if target_type is float:
                try:
                    return float(value_str)
                except ValueError:
                    raise ValueError(f"无法将字符串 '{value_str}' 转换为浮点数")
                
            # 转换为复数
            if target_type is complex:
                try:
                    return complex(value_str)
                except ValueError:
                    return value
                
            # 转换为布尔值
            if target_type is bool:
                if value_str.lower() in ['true', '1', 'yes', 'y']:
                    return True
                elif value_str.lower() in ['false', '0', 'no', 'n']:
                    return False
                else:
                    return value
                
            # 转换为日期
            if target_type is datetime.date:
                # 尝试多种日期格式
                for fmt in ['%Y-%m-%d', '%d/%m/%Y', '%m/%d/%Y', '%Y年%m月%d日']:
                    try:
                        return datetime.datetime.strptime(value_str, fmt).date()
                    except ValueError:
                        continue
                raise ValueError(f"无法将字符串 '{value_str}' 转换为日期")
                
            # 转换为日期时间
            if target_type is datetime.datetime:
                # 尝试多种日期时间格式
                for fmt in ['%Y-%m-%d %H:%M:%S', '%Y-%m-%dT%H:%M:%S', '%Y-%m-%d %H:%M:%S.%f']:
                    try:
                        return datetime.datetime.strptime(value_str, fmt)
                    except ValueError:
                        continue
                return value
                
            # 转换为高精度小数
            if target_type is decimal.Decimal:
                try:
                    return decimal.Decimal(value_str)
                except (ValueError, decimal.InvalidOperation):
                    raise decimal.InvalidOperation(f"无法将字符串 '{value_str}' 转换为高精度小数")
                
            # 转换为字符串
            if target_type is str:
                return value_str
                
            # 转换为字典或列表（JSON字符串）
            if target_type in (dict, list):
                try:
                    import json
                    parsed = json.loads(value_str)
                    if isinstance(parsed, target_type):
                        return parsed
                    else:
                        return value
                except (ValueError, json.JSONDecodeError):
                    return value
                
        # 非字符串转换
        else:
            # 转换为字符串
            if target_type is str:
                return str(value)
                
            # 浮点数到整数的转换（检查精度丢失）
            if target_type is int and isinstance(value, float):
                # 检查是否会丢失精度
                if value != int(value):
                    return value  # 返回原值，不进行转换
                return int(value)
                
            # 日期时间到日期的转换（检查信息丢失）
            if target_type is datetime.date and isinstance(value, datetime.datetime):
                # 这种转换会丢失时间信息，但在convert_value中我们仍然进行转换
                # is_compatible_type会根据业务逻辑决定是否兼容
                return value.date()
                
            # 日期到日期时间的转换
            if target_type is datetime.datetime and isinstance(value, datetime.date):
                # 将日期转换为当天的午夜时间
                return datetime.datetime.combine(value, datetime.time.min)
                
            # 其他类型转换
            try:
                return target_type(value)
            except (ValueError, TypeError) as e:
                # 如果转换失败，返回原值
                return value
                
        # 如果无法转换，抛出异常
        raise ValueError(f"不支持的转换: {type(value)} -> {target_type}")
    
    @classmethod
    def is_compatible_type(cls, value: Any, target_type: Type) -> bool:
        """
        检查值是否可以转换为目标类型
        
        Args:
            value: 要检查的值
            target_type: 目标类型
            
        Returns:
            如果兼容返回True，否则返回False
        """
        # 特殊情况：浮点数到整数（会丢失精度）
        if isinstance(value, float) and target_type is int:
            # 只有当浮点数是整数时才兼容
            return value == int(value)
            
        # 特殊情况：日期时间到日期（会丢失时间信息）
        if isinstance(value, datetime.datetime) and target_type is datetime.date:
            # 这种转换会丢失信息，所以认为不兼容
            return False
            
        try:
            converted_value = cls.convert_value(value, target_type)
            # 检查转换后的值是否是目标类型（或者是None，对于None类型）
            if target_type is type(None):
                return converted_value is None
            return isinstance(converted_value, target_type)
        except (ValueError, decimal.InvalidOperation, TypeError):
            return False
    
    @classmethod
    def get_type_hierarchy(cls) -> Dict[Type, Set[Type]]:
        """
        获取类型层次结构
        
        Returns:
            类型层次结构字典
        """
        return cls.TYPE_HIERARCHY
    
    @classmethod
    def get_most_specific_type(cls, types: List[Type]) -> Type:
        """
        从类型列表中获取最具体的类型
        
        Args:
            types: 类型列表
            
        Returns:
            最具体的类型
        """
        if not types:
            return str
            
        # 如果只有一个类型，直接返回
        if len(types) == 1:
            return types[0]
            
        # 特殊情况处理
        # 如果有str类型，直接返回str（通用类型）
        if str in types:
            return str
            
        # 特殊情况：float和bool的组合
        if float in types and bool in types:
            return float
            
        # 特殊情况：int、float和complex的组合
        if int in types and float in types and complex in types:
            return complex
            
        # 特殊情况：float和complex的组合
        if float in types and complex in types:
            return complex
            
        # 特殊情况：int和complex的组合
        if int in types and complex in types:
            return complex
            
        # 特殊情况：int和float的组合
        if int in types and float in types:
            return float
            
        # 特殊情况：bool和数字的组合
        if bool in types and int in types and float not in types:
            return str
            
        # 特殊情况：datetime和date的组合
        if datetime.datetime in types and datetime.date in types:
            return datetime.datetime
            
        # 计算每个类型的兼容性得分
        # 得分越高，类型越通用
        type_scores = {}
        for t in types:
            score = len(cls.TYPE_HIERARCHY.get(t, set()))
            type_scores[t] = score
            
        # 返回得分最低的类型（最具体的）
        return min(type_scores.items(), key=lambda x: x[1])[0]
    
    @classmethod
    def _is_complex(cls, value: str) -> bool:
        """检查字符串是否为复数"""
        # 复数必须包含'j'或'i'
        if 'j' not in value and 'i' not in value:
            return False
        try:
            complex(value)
            return True
        except ValueError:
            return False
    
    @classmethod
    def _is_integer(cls, value: str) -> bool:
        """检查字符串是否为整数"""
        try:
            int(value)
            # 排除以0开头的非零数字（可能是二进制或八进制表示）
            if len(value) > 1 and value.startswith('0') and value != '0':
                return False
            return True
        except ValueError:
            return False
    
    @classmethod
    def _is_float(cls, value: str) -> bool:
        """检查字符串是否为浮点数"""
        try:
            float(value)
            # 排除整数情况
            return '.' in value or 'e' in value.lower() or 'E' in value
        except ValueError:
            return False
    
    @classmethod
    def _is_decimal(cls, value: str) -> bool:
        """检查字符串是否为高精度小数"""
        # 排除科学计数法
        if 'e' in value.lower():
            return False
        try:
            decimal.Decimal(value)
            # 排除简单整数
            if '.' not in value:
                return False
            # 只有当小数位数超过浮点数精度限制时才认为是高精度小数
            # 或者明确包含超过15位有效数字时
            if '.' in value:
                # 获取小数部分
                decimal_part = value.split('.')[1]
                # 如果小数位数超过15位，认为是高精度小数
                if len(decimal_part) > 15:
                    return True
                # 如果总有效数字超过或等于16位，认为是高精度小数
                total_digits = len(value.replace('.', '').replace('-', ''))
                if total_digits >= 16:
                    return True
            return False
        except decimal.InvalidOperation:
            return False
    
    @classmethod
    def _is_date(cls, value: str) -> bool:
        """检查字符串是否为日期"""
        date_formats = [
            '%Y-%m-%d',
            '%d/%m/%Y',
            '%m/%d/%Y',
            '%Y年%m月%d日'
        ]
        
        for fmt in date_formats:
            try:
                datetime.datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False
    
    @classmethod
    def _is_time(cls, value: str) -> bool:
        """检查字符串是否为时间"""
        time_formats = [
            '%H:%M:%S',
            '%H:%M:%S.%f',
            '%H:%M'
        ]
        
        for fmt in time_formats:
            try:
                datetime.datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False
    
    @classmethod
    def _is_datetime(cls, value: str) -> bool:
        """检查字符串是否为日期时间"""
        datetime_formats = [
            '%Y-%m-%d %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S',
            '%Y-%m-%d %H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%S.%f',
            '%Y-%m-%dT%H:%M:%SZ'
        ]
        
        for fmt in datetime_formats:
            try:
                datetime.datetime.strptime(value, fmt)
                return True
            except ValueError:
                continue
        return False