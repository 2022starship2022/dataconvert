#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
日志配置模块
提供结构化日志记录和性能日志功能
"""

import os
import sys
import logging
import logging.handlers
import json
import time
import functools
import threading
from typing import Any, Dict, List, Optional, Callable
from pathlib import Path
from datetime import datetime
from contextlib import contextmanager

# 日志级别映射
LOG_LEVELS = {
    'DEBUG': logging.DEBUG,
    'INFO': logging.INFO,
    'WARNING': logging.WARNING,
    'ERROR': logging.ERROR,
    'CRITICAL': logging.CRITICAL
}

class StructuredFormatter(logging.Formatter):
    """结构化日志格式化器"""

    def __init__(self, include_extra: bool = True):
        super().__init__()
        self.include_extra = include_extra

    def format(self, record: logging.LogRecord) -> str:
        """格式化日志记录"""
        log_data = {
            'timestamp': datetime.fromtimestamp(record.created).isoformat(),
            'level': record.levelname,
            'logger': record.name,
            'message': record.getMessage(),
            'module': record.module,
            'function': record.funcName,
            'line': record.lineno
        }

        # 添加异常信息
        if record.exc_info:
            log_data['exception'] = self.formatException(record.exc_info)

        # 添加额外字段
        if self.include_extra and hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key not in ['name', 'msg', 'args', 'levelname', 'levelno',
                              'pathname', 'filename', 'module', 'lineno',
                              'funcName', 'created', 'msecs', 'relativeCreated',
                              'thread', 'threadName', 'processName', 'process',
                              'getMessage', 'exc_info', 'exc_text', 'stack_info']:
                    log_data[key] = value

        return json.dumps(log_data, ensure_ascii=False, default=str)

class ColoredFormatter(logging.Formatter):
    """彩色日志格式化器（控制台输出）"""

    # ANSI颜色代码
    COLORS = {
        'DEBUG': '\033[36m',    # 青色
        'INFO': '\033[32m',     # 绿色
        'WARNING': '\033[33m',  # 黄色
        'ERROR': '\033[31m',    # 红色
        'CRITICAL': '\033[35m', # 紫色
        'RESET': '\033[0m'      # 重置
    }

    def __init__(self, use_color: bool = True):
        super().__init__()
        self.use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        """格式化彩色日志"""
        if self.use_color:
            color = self.COLORS.get(record.levelname, self.COLORS['RESET'])
            reset = self.COLORS['RESET']
        else:
            color = ''
            reset = ''

        # 基本格式
        log_format = (
            f"{color}[{datetime.fromtimestamp(record.created).strftime('%H:%M:%S')}] "
            f"{record.levelname:8} "
            f"[{record.name}] "
            f"{record.getMessage()}{reset}"
        )

        # 添加异常信息
        if record.exc_info:
            log_format += f"\n{self.formatException(record.exc_info)}"

        return log_format

class PerformanceLogger:
    """性能日志记录器"""

    def __init__(self, logger_name: str = 'performance'):
        self.logger = logging.getLogger(logger_name)
        self._timers = {}
        self._lock = threading.Lock()

    def start_timer(self, name: str) -> None:
        """开始计时"""
        with self._lock:
            self._timers[name] = time.time()

    def end_timer(self, name: str, extra_data: Dict[str, Any] = None) -> float:
        """结束计时并记录"""
        with self._lock:
            if name not in self._timers:
                self.logger.warning(f"计时器未启动: {name}")
                return 0.0

            duration = time.time() - self._timers[name]
            del self._timers[name]

            # 记录性能日志
            log_data = {
                'operation': name,
                'duration': duration,
                'unit': 'seconds'
            }
            if extra_data:
                log_data.update(extra_data)

            self.logger.info(f"Performance: {name} took {duration:.4f}s", extra=log_data)
            return duration

    @contextmanager
    def timer(self, name: str, extra_data: Dict[str, Any] = None):
        """计时上下文管理器"""
        self.start_timer(name)
        try:
            yield
        finally:
            self.end_timer(name, extra_data)

def setup_structured_logging(
    log_level: str = 'INFO',
    log_file: str = None,
    log_dir: str = 'logs',
    console_output: bool = True,
    structured_format: bool = False,
    use_color: bool = True,
    max_file_size: int = 10 * 1024 * 1024,  # 10MB
    backup_count: int = 5
) -> None:
    """
    设置结构化日志

    Args:
        log_level: 日志级别
        log_file: 日志文件名
        log_dir: 日志目录
        console_output: 是否输出到控制台
        structured_format: 是否使用结构化格式
        max_file_size: 最大文件大小
        backup_count: 备份文件数量
    """
    # 获取根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(LOG_LEVELS.get(log_level.upper(), logging.INFO))

    # 清除现有处理器
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # 创建日志目录
    if log_file or log_dir:
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)

    # 设置控制台处理器
    if console_output:
        # 将控制台日志重定向到 stderr，避免干扰stdout结构化输出
        console_handler = logging.StreamHandler(sys.stderr)
        if structured_format:
            console_handler.setFormatter(StructuredFormatter())
        else:
            console_handler.setFormatter(ColoredFormatter(use_color=use_color))
        root_logger.addHandler(console_handler)

    # 设置文件处理器
    if log_file:
        file_path = log_path / log_file

        if structured_format:
            # 结构化JSON格式
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            file_handler.setFormatter(StructuredFormatter())
        else:
            # 普通文本格式
            file_handler = logging.handlers.RotatingFileHandler(
                file_path,
                maxBytes=max_file_size,
                backupCount=backup_count,
                encoding='utf-8'
            )
            formatter = logging.Formatter(
                '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
            )
            file_handler.setFormatter(formatter)

        root_logger.addHandler(file_handler)

    # 设置错误日志文件
    if log_file:
        error_file_path = log_path / f"error_{log_file}"
        error_handler = logging.handlers.RotatingFileHandler(
            error_file_path,
            maxBytes=max_file_size,
            backupCount=backup_count,
            encoding='utf-8'
        )
        error_handler.setLevel(logging.ERROR)
        error_handler.setFormatter(StructuredFormatter())
        root_logger.addHandler(error_handler)

def get_logger(name: str) -> logging.Logger:
    """
    获取日志记录器

    Args:
        name: 日志记录器名称

    Returns:
        日志记录器实例
    """
    return logging.getLogger(name)

def performance_logger(name: str = 'performance') -> PerformanceLogger:
    """
    获取性能日志记录器

    Args:
        name: 性能日志记录器名称

    Returns:
        性能日志记录器实例
    """
    return PerformanceLogger(name)

def log_function_call(logger: logging.Logger = None):
    """
    函数调用日志装饰器

    Args:
        logger: 日志记录器
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            func_logger = logger or logging.getLogger(func.__module__)
            func_name = f"{func.__module__}.{func.__name__}"

            # 记录函数调用
            func_logger.debug(f"调用函数: {func_name}")

            try:
                start_time = time.time()
                result = func(*args, **kwargs)
                duration = time.time() - start_time

                # 记录函数执行完成
                func_logger.debug(
                    f"函数执行完成: {func_name}, 耗时: {duration:.4f}s",
                    extra={
                        'function': func_name,
                        'duration': duration,
                        'args_count': len(args),
                        'kwargs_count': len(kwargs)
                    }
                )
                return result

            except Exception as e:
                # 记录函数执行异常
                func_logger.error(
                    f"函数执行异常: {func_name}, 错误: {str(e)}",
                    extra={
                        'function': func_name,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                raise

        return wrapper
    return decorator

def log_method_call(logger: logging.Logger = None):
    """
    方法调用日志装饰器

    Args:
        logger: 日志记录器
    """
    def decorator(method: Callable) -> Callable:
        @functools.wraps(method)
        def wrapper(self, *args, **kwargs):
            method_logger = logger or logging.getLogger(self.__class__.__module__)
            class_name = self.__class__.__name__
            method_name = f"{class_name}.{method.__name__}"

            # 记录方法调用
            method_logger.debug(f"调用方法: {method_name}")

            try:
                start_time = time.time()
                result = method(self, *args, **kwargs)
                duration = time.time() - start_time

                # 记录方法执行完成
                method_logger.debug(
                    f"方法执行完成: {method_name}, 耗时: {duration:.4f}s",
                    extra={
                        'class': class_name,
                        'method': method.__name__,
                        'duration': duration,
                        'args_count': len(args),
                        'kwargs_count': len(kwargs)
                    }
                )
                return result

            except Exception as e:
                # 记录方法执行异常
                method_logger.error(
                    f"方法执行异常: {method_name}, 错误: {str(e)}",
                    extra={
                        'class': class_name,
                        'method': method.__name__,
                        'error_type': type(e).__name__,
                        'error_message': str(e)
                    },
                    exc_info=True
                )
                raise

        return wrapper
    return decorator

def configure_logging_for_development():
    """为开发环境配置日志"""
    setup_structured_logging(
        log_level='DEBUG',
        log_file='app.log',
        console_output=True,
        structured_format=False
    )

def configure_logging_for_production():
    """为生产环境配置日志"""
    setup_structured_logging(
        log_level='INFO',
        log_file='production.log',
        console_output=False,
        structured_format=True
    )

# 便捷的性能计时装饰器
def timer(name: str = None, logger: PerformanceLogger = None):
    """
    性能计时装饰器

    Args:
        name: 计时名称
        logger: 性能日志记录器
    """
    def decorator(func: Callable) -> Callable:
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            perf_logger = logger or performance_logger()
            timer_name = name or f"{func.__module__}.{func.__name__}"

            with perf_logger.timer(timer_name):
                return func(*args, **kwargs)

        return wrapper
    return decorator

# 上下文管理器支持
from contextlib import contextmanager

@contextmanager
def log_context(operation: str, logger: logging.Logger = None, level: int = logging.INFO):
    """
    日志上下文管理器

    Args:
        operation: 操作名称
        logger: 日志记录器
        level: 日志级别
    """
    log = logger or logging.getLogger()
    start_time = time.time()

    log.log(level, f"开始操作: {operation}")
    try:
        yield
        duration = time.time() - start_time
        log.log(level, f"完成操作: {operation}, 耗时: {duration:.4f}s")
    except Exception as e:
        duration = time.time() - start_time
        log.error(f"操作失败: {operation}, 耗时: {duration:.4f}s, 错误: {str(e)}")
        raise