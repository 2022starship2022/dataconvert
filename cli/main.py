#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
CLI主入口
"""

import sys
import os
import logging
from typing import Optional, List

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from cli.parser import ArgumentParser
from config import Config, get_config
from core.logging_config import setup_structured_logging, get_logger


class DataConverterCLI:
    """数据转换工具CLI主类"""

    def __init__(self, config_file: Optional[str] = None):
        """
        初始化CLI

        Args:
            config_file: 配置文件路径
        """
        self.config = get_config(config_file)
        self.parser = ArgumentParser()
        self.logger = None

        # 初始化日志
        self._setup_logging()

        # 初始化引擎
        self._init_engines()

    def _setup_logging(self, quiet_mode=False):
        """设置日志"""
        try:
            log_level = self.config.get_global('log_level', 'INFO')
            log_file = None  # CLI版本默认不写文件日志

            # 如果不是静默模式，才设置控制台输出
            console_output = not quiet_mode

            setup_structured_logging(
                log_level=log_level,
                console_output=console_output,
                log_file=log_file,
                structured_format=False
            )

            self.logger = get_logger(__name__)
            # 不在这里输出日志，因为此时可能还未解析命令行参数
            # if not quiet_mode:
            #     self.logger.info("CLI启动，日志系统初始化完成")

        except Exception as e:
            # 如果日志初始化失败，使用基础配置
            if not quiet_mode:
                logging.basicConfig(
                    level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
                )
            self.logger = logging.getLogger(__name__)
            if not quiet_mode:
                self.logger.warning(f"使用基础日志配置: {e}")

    def _init_engines(self):
        """初始化处理引擎"""
        try:
            # 导入统一格式处理器
            from core.unified_format_processor import UnifiedFormatProcessor
            self.processor = UnifiedFormatProcessor()
            # 不在这里输出日志，因为此时可能还未解析命令行参数
            # self.logger.info("统一格式处理器初始化完成")

        except ImportError as e:
            self.logger.error(f"引擎初始化失败: {e}")
            raise

    def run(self, args: Optional[List[str]] = None) -> int:
        """
        运行CLI

        Args:
            args: 命令行参数列表

        Returns:
            退出码
        """
        try:
            # 解析参数
            try:
                parsed_args = self.parser.parse_args(args)
            except SystemExit as e:
                # argparse在处理--help和--version时会调用sys.exit()
                # 返回退出码0表示成功
                return 0 if e.code == 0 else e.code

            # 更新配置（如果有命令行配置选项）
            if parsed_args.config:
                self.config.load_config(parsed_args.config)

            # 如果是静默模式，重新设置日志
            if parsed_args.quiet:
                self._setup_logging(quiet_mode=True)
            else:
                # 应用命令行日志设置
                self._apply_cli_logging_settings(parsed_args)

            # 执行对应命令
            return self._execute_command(parsed_args)

        except KeyboardInterrupt:
            # 在异常情况下，parsed_args可能未定义，使用默认值
            try:
                quiet = getattr(parsed_args, 'quiet', False)
                if not quiet and self.logger:
                    self.logger.info("用户中断操作")
            except:
                pass
            return 130  # 标准的SIGINT退出码
        except Exception as e:
            # 在异常情况下，parsed_args可能未定义，使用默认值
            try:
                quiet = getattr(parsed_args, 'quiet', False)
                if not quiet and self.logger:
                    self.logger.error(f"CLI运行失败: {e}", exc_info=True)
            except:
                print(f"CLI运行失败: {e}")
            return 1

    def _apply_cli_logging_settings(self, args):
        """应用命令行日志设置"""
        # 更新日志级别
        if args.log_level:
            self.config.set('global.log_level', args.log_level)
            logging.getLogger().setLevel(getattr(logging, args.log_level))

        # 静默模式 - 完全禁用控制台输出
        if args.quiet:
            # 移除所有控制台处理器
            root_logger = logging.getLogger()
            for handler in root_logger.handlers[:]:
                if isinstance(handler, logging.StreamHandler):
                    root_logger.removeHandler(handler)

        # 详细模式
        if args.verbose:
            logging.getLogger().setLevel(logging.DEBUG)

        # 禁用彩色输出（仅控制台）
        if hasattr(args, 'no_color') and args.no_color and not args.quiet:
            # 重新配置日志以禁用彩色
            level = 'DEBUG' if args.verbose else (args.log_level or self.config.get_global('log_level', 'INFO'))
            setup_structured_logging(
                log_level=level,
                console_output=True,
                log_file=None,
                structured_format=False,
                use_color=False
            )
            self.logger = get_logger(__name__)

    def _execute_command(self, args) -> int:
        """执行命令"""
        command = args.command

        if command == 'convert':
            return self.convert_command(args)
        elif command == 'merge':
            return self.merge_command(args)
        elif command == 'info':
            return self.info_command(args)
        elif command == 'validate':
            return self.validate_command(args)
        else:
            self.logger.error(f"未知命令: {command}")
            return 1

    def convert_command(self, args) -> int:
        """转换命令处理"""
        try:
            self.logger.info(f"开始转换操作: {args.input}")

            # 构建转换选项
            options = self._build_convert_options(args)

            # 目录模式入口
            if getattr(args, 'dir_in', False) or getattr(args, 'dir_out', False):
                return self._convert_directory(args, options)

            if args.batch:
                # 批量转换
                self.logger.error("批量转换功能暂未实现")
                return 1
            else:
                # 单文件转换
                input_file = args.input
                output_file = args.output

                self.logger.info(f"输入文件: {input_file}")
                self.logger.info(f"输出文件: {output_file}")

                if not output_file:
                    self.logger.error("未指定输出文件")
                    return 1

                # 传递CSV分隔符/引号选项
                read_options = {}
                if 'sep' in options:
                    read_options['sep'] = options['sep']
                if 'encoding' in options:
                    read_options['encoding'] = options['encoding']
                if 'quotechar' in options:
                    read_options['quotechar'] = options['quotechar']
                # Excel/SQLite 多表读取选项映射
                if options.get('excel_all_sheets'):
                    read_options['sheet_name'] = None
                elif 'excel_sheet_name' in options:
                    read_options['sheet_name'] = options['excel_sheet_name']
                if options.get('db_all_tables'):
                    read_options['read_all_tables'] = True
                elif 'db_table_name' in options:
                    read_options['table_name'] = options['db_table_name']
                
                # 从配置中获取输入格式选项
                input_format = self.config.get('input_format')
                if input_format:
                    input_format_config = self.config.get(input_format.lower(), {})
                    if input_format_config:
                        # 将配置中的选项添加到读取选项
                        for key, value in input_format_config.items():
                            if key not in read_options:  # 不覆盖命令行选项
                                read_options[key] = value
                        self.logger.info(f"从配置加载输入格式选项: {input_format} -> {input_format_config}")
                
                # 从配置中获取编码选项
                encoding = self.config.get('encoding')
                if encoding and 'encoding' not in read_options:
                    read_options['encoding'] = encoding
                    self.logger.info(f"从配置加载编码选项: {encoding}")
                
                # 从配置中获取分隔符选项
                delimiter = self.config.get('delimiter')
                if delimiter and 'delimiter' not in read_options and 'sep' not in read_options:
                    read_options['sep'] = delimiter
                    self.logger.info(f"从配置加载分隔符选项: {delimiter}")
                
                # 输入格式显式指定（支持 protobuf/mmkv）
                from_format = getattr(args, 'from_format', None)
                to_format = getattr(args, 'to_format', None)

                # Protobuf 基于 schema 解码（禁用无 schema 读取）
                if from_format == 'protobuf' or (input_file.lower().endswith('.pb') and getattr(args, 'schema_file', None) and getattr(args, 'message_type', None)):
                    schema_file = getattr(args, 'schema_file', None)
                    message_type = getattr(args, 'message_type', None)
                    if not schema_file or not message_type:
                        self.logger.error("Protobuf 解码需要 --schema-file 与 --message-type")
                        return 1
                    self.logger.info(f"使用 schema 解码 Protobuf: schema={schema_file}, type={message_type}")
                    result = self.processor.decode_protobuf_with_schema(input_file, schema_file, message_type)
                else:
                    # 常规读取（包含 MMKV 在统一处理器中的读取）
                    result = self.processor.read(input_file, **read_options)

                # 转换格式名称
                format_hint = to_format or getattr(args, 'format', None)
                if format_hint:
                    # 映射格式名称
                    format_mapping = {
                        'csv': 'CSV',
                        'excel': 'Excel',
                        'json': 'JSON',
                        'xml': 'XML',
                        'sqlite': 'SQLite',
                        'sql': 'SQLScript'
                    }
                    format_hint = format_mapping.get(format_hint.lower(), format_hint.upper())
                else:
                    # 如果没有指定格式，从配置中获取输出格式
                    output_format = self.config.get('output_format')
                    if output_format:
                        format_mapping = {
                            'csv': 'CSV',
                            'excel': 'Excel',
                            'json': 'JSON',
                            'xml': 'XML',
                            'sqlite': 'SQLite',
                            'sql': 'SQLScript',
                            'mmkv': 'MMKV'
                        }
                        format_hint = format_mapping.get(output_format.lower(), output_format.upper())
                        self.logger.info(f"从配置加载输出格式: {output_format}")
                    elif output_file and '.' in output_file:
                        # 根据输出文件扩展名推断
                        ext = output_file.split('.')[-1].lower()
                        format_mapping = {
                            'csv': 'CSV',
                            'xlsx': 'Excel',
                            'xls': 'Excel',
                            'json': 'JSON',
                            'xml': 'XML',
                            'sqlite': 'SQLite',
                            'db': 'SQLite',
                            'sql': 'SQLScript',
                            'mmkv': 'MMKV'
                        }
                        format_hint = format_mapping.get(ext, None)
                        if format_hint:
                            self.logger.info(f"根据输出文件扩展名推断格式: {ext} -> {format_hint}")

                # 从配置中获取格式特定选项
                format_options = {}
                if format_hint:
                    format_key = format_hint.lower()
                    format_config = self.config.get(format_key, {})
                    if format_config:
                        format_options = format_config
                        self.logger.info(f"从配置加载格式选项: {format_key} -> {format_options}")

                # 合并命令行选项和配置文件选项（命令行优先）
                write_options = {**format_options, **options}
                self.logger.info(f"最终写入选项: {write_options}")
                
                # 多表结构处理：合并或拆分文件夹，或直接写入到多表格式
                try:
                    import pandas as pd
                except Exception:
                    pd = None

                is_df_dict = isinstance(result, dict) and (
                    pd is not None and all(isinstance(v, pd.DataFrame) for v in result.values())
                )

                if is_df_dict:
                    # 目标若为原生多表格式（Excel/SQLite），直接写入多表
                    if format_hint in ('Excel', 'SQLite'):
                        success = self.processor.write(result, output_file, format_hint=format_hint, **write_options)
                    else:
                        # 单表格式：根据策略合并或拆分到文件夹
                        multi_action = options.get('multi_action', 'merge')
                        if multi_action == 'split':
                            import os
                            split_dir = options.get('split_dir')
                            if not split_dir:
                                base = os.path.splitext(output_file)[0]
                                split_dir = base + "_tables"
                            os.makedirs(split_dir, exist_ok=True)

                            split_format = options.get('split_format') or (self.config.get('output_format') or 'csv')
                            ext_map = {'csv': 'csv', 'json': 'json', 'excel': 'xlsx'}
                            fmt_map = {'csv': 'CSV', 'json': 'JSON', 'excel': 'Excel'}
                            fmt_hint_split = fmt_map.get(split_format, split_format.upper())

                            success = True
                            for name, df in result.items():
                                safe_name = str(name).replace('/', '_').replace('\\', '_').replace(':', '_')
                                out_path = os.path.join(split_dir, f"{safe_name}.{ext_map.get(split_format, split_format)}")
                                extra_opts = {}
                                if fmt_hint_split == 'Excel':
                                    extra_opts['sheet_name'] = 'Sheet1'
                                ok = self.processor.write(df, out_path, format_hint=fmt_hint_split, **{**write_options, **extra_opts})
                                if not ok:
                                    success = False
                            if success:
                                self.logger.info(f"多表拆分输出完成: {split_dir}")
                        else:
                            # merge 合并为单表
                            merged_df = self._merge_tables_dict(result)
                            success = self.processor.write(merged_df, output_file, format_hint=format_hint, **write_options)
                else:
                    # 若目标为表格格式，确保将 Protobuf 解码后的 dict/list 转为 DataFrame
                    if format_hint in ('CSV', 'Excel'):
                        try:
                            if pd is None:
                                raise RuntimeError('pandas 未安装')
                            if isinstance(result, dict):
                                result = pd.DataFrame([result])
                            elif isinstance(result, list) and (len(result) == 0 or isinstance(result[0], dict)):
                                result = pd.DataFrame(result)
                        except Exception as e:
                            self.logger.warning(f"转换为表格结构失败，尝试直接写入: {e}")

                    success = self.processor.write(result, output_file, format_hint=format_hint, **write_options)

                if success:
                    self.logger.info(f"转换完成: {output_file}")
                    return 0
                else:
                    self.logger.error("转换失败")
                    return 1

        except Exception as e:
            self.logger.error(f"转换操作失败: {e}")
            return 1

    def merge_command(self, args) -> int:
        """合并命令处理"""
        try:
            self.logger.info(f"开始合并操作: {args.input_files}")

            # 预览模式
            if args.preview:
                self.logger.error("预览功能暂未实现")
                return 1

            # 智能合并
            if len(args.input_files) < 2:
                self.logger.error("合并操作至少需要2个输入文件")
                return 1

            # 构建读取选项
            options = self._build_convert_options(args)
            read_options = {}
            if 'sep' in options:
                read_options['sep'] = options['sep']

            # 读取第一个文件作为基础
            result = self.processor.read(args.input_files[0], **read_options)
            self.logger.info(f"基础文件: {args.input_files[0]}, 形状: {getattr(result, 'shape', 'N/A')}")

            # 追加其他文件
            for file_path in args.input_files[1:]:
                try:
                    data = self.processor.read(file_path, **read_options)
                    self.logger.info(f"合并文件: {file_path}, 形状: {getattr(data, 'shape', 'N/A')}")

                    # 智能合并策略
                    if hasattr(result, 'columns') and hasattr(data, 'columns'):
                        # 使用pandas concat进行智能合并
                        import pandas as pd
                        if set(result.columns) == set(data.columns) and list(result.columns) == list(data.columns):
                            # 列结构完全相同（包括顺序），直接追加
                            result = pd.concat([result, data], ignore_index=True)
                        else:
                            # 列名或顺序不同，触发智能合并以保留所有数据
                            self.logger.info(f"智能合并模式: 不同列结构处理")

                            # 获取所有列的并集
                            all_columns = set(result.columns) | set(data.columns)
                            self.logger.info(f"总列数: {len(all_columns)}")

                            # 添加来源标注列
                            result_copy = result.copy()
                            data_copy = data.copy()

                            source_col = '_merge_source'
                            result_copy[source_col] = f"base_file"
                            data_copy[source_col] = f"merge_file"

                            # 为缺失列添加标注
                            for col in all_columns:
                                if col not in result_copy.columns:
                                    result_copy[col] = f"[来自基础文件缺失]"
                                if col not in data_copy.columns:
                                    data_copy[col] = f"[来自合并文件缺失]"

                            # 重新排序列
                            all_cols_sorted = sorted(list(all_columns))
                            ordered_cols = [source_col] + all_cols_sorted

                            result_copy = result_copy[ordered_cols]
                            data_copy = data_copy[ordered_cols]

                            # 合并数据
                            result = pd.concat([result_copy, data_copy], ignore_index=True)
                            self.logger.info(f"智能合并完成，最终列数: {len(result.columns)}")
                    elif hasattr(result, 'concat'):
                        # 使用concat方法 (pandas兼容)
                        try:
                            result = result.concat(data, ignore_index=True)
                        except AttributeError:
                            # 兼容旧版本pandas
                            result = pd.concat([result, data], ignore_index=True)
                    else:
                        # 转换为DataFrame后合并
                        import pandas as pd
                        if not isinstance(result, pd.DataFrame):
                            result = pd.DataFrame(result)
                        if not isinstance(data, pd.DataFrame):
                            data = pd.DataFrame(data)

                        if set(result.columns) == set(data.columns):
                            result = result.concat(data, ignore_index=True)
                        else:
                            # 使用相同的智能合并策略
                            all_columns = set(result.columns) | set(data.columns)

                            result_copy = result.copy()
                            data_copy = data.copy()

                            # 添加来源标注
                            source_col = '_merge_source'
                            result_copy[source_col] = f"base_{args.input_files[0].split('/')[-1]}"
                            data_copy[source_col] = f"merge_{file_path.split('/')[-1]}"

                            # 为缺失列添加标注
                            for col in all_columns:
                                if col not in result_copy.columns:
                                    result_copy[col] = '[缺失]'
                                if col not in data_copy.columns:
                                    data_copy[col] = '[缺失]'

                            # 统一列顺序
                            common_cols = sorted(list(set(result_copy.columns) & set(data_copy.columns) - {source_col}))
                            base_only_cols = sorted([col for col in result_copy.columns if col not in data_copy.columns and col != source_col])
                            merge_only_cols = sorted([col for col in data_copy.columns if col not in result_copy.columns and col != source_col])

                            ordered_cols = [source_col] + common_cols + base_only_cols + merge_only_cols
                            result_copy = result_copy[ordered_cols]
                            data_copy = data_copy[[col for col in ordered_cols if col in data_copy.columns]]

                            result = result_copy.concat(data_copy, ignore_index=True)
                            self.logger.info(f"智能合并完成，保留所有{len(all_columns)}列 + 来源标注")

                except Exception as e:
                    self.logger.warning(f"合并文件 {file_path} 失败: {e}")
                    continue

            self.logger.info(f"合并结果形状: {getattr(result, 'shape', 'N/A')}")

            # 写入结果
            success = self.processor.write(result, args.output)

            if success:
                self.logger.info(f"合并完成: {args.output}")
                return 0
            else:
                self.logger.error("合并失败")
                return 1

        except Exception as e:
            self.logger.error(f"合并操作失败: {e}")
            return 1

    def info_command(self, args) -> int:
        """信息查询命令处理"""
        try:
            self.logger.info(f"查询文件信息: {args.file_path}")
            
            # 先获取元数据，避免对 .pb 直接读取
            metadata = self.processor.get_file_metadata(args.file_path)

            # 构建文件信息
            import os
            file_info = dict(metadata) if isinstance(metadata, dict) else {
                'file_path': args.file_path,
                'file_size': os.path.getsize(args.file_path),
                'format': args.file_path.split('.')[-1].upper() if '.' in args.file_path else 'Unknown'
            }

            # 根据格式自动分支：protobuf 不做直接读取
            from_format = getattr(args, 'from_format', None)
            is_pb = (from_format == 'protobuf') or args.file_path.lower().endswith('.pb')
            if not is_pb:
                try:
                    data = self.processor.read(args.file_path)
                    if hasattr(data, 'shape'):
                        file_info['stats'] = {
                            'record_count': data.shape[0],
                            'field_count': data.shape[1]
                        }
                    if hasattr(data, 'columns'):
                        file_info['columns'] = list(data.columns)
                    if hasattr(data, 'head') and args.sample:
                        file_info['sample_data'] = data.head(args.sample).to_dict('records')
                except Exception as e:
                    self.logger.warning(f"读取文件用于详情展示失败，返回基本元数据: {e}")

            # 如果请求导出信息到文件（JSON格式）
            export_path = getattr(args, 'export_info', None)
            if export_path:
                try:
                    import json
                    # 确保输出目录存在（如提供了目录）
                    out_dir = os.path.dirname(export_path)
                    if out_dir and not os.path.exists(out_dir):
                        os.makedirs(out_dir, exist_ok=True)
                    with open(export_path, 'w', encoding='utf-8') as f:
                        json.dump(file_info, f, indent=2, ensure_ascii=False)
                    self.logger.info(f"信息已导出到: {export_path}")
                except Exception as e:
                    self.logger.warning(f"导出信息到文件失败: {e}")

            # 输出信息
            return self._output_file_info(file_info, args)

        except Exception as e:
            self.logger.error(f"信息查询失败: {e}")
            return 1

    def validate_command(self, args) -> int:
        """验证命令处理"""
        try:
            self.logger.info(f"验证文件: {args.file_path}")
            
            # 读取文件
            data = self.processor.read(args.file_path)
            
            # 验证结果
            validation_result = {
                'file_path': args.file_path,
                'is_valid': True,
                'errors': [],
                'warnings': [],
                'stats': {}
            }
            
            # 基本验证
            if data is None:
                validation_result['is_valid'] = False
                validation_result['errors'].append("无法读取文件或文件为空")
                return self._output_validation_result(validation_result, args)
            
            # 检查数据是否为空
            if hasattr(data, 'empty') and data.empty:
                validation_result['warnings'].append("文件中没有数据")
            
            # 检查数据结构
            if hasattr(data, 'shape'):
                validation_result['stats']['record_count'] = data.shape[0]
                validation_result['stats']['field_count'] = data.shape[1]
            
            # 检查列名
            if hasattr(data, 'columns'):
                columns = list(data.columns)
                validation_result['stats']['columns'] = columns
                
                # 检查重复列名
                if len(columns) != len(set(columns)):
                    validation_result['warnings'].append("存在重复的列名")
                
                # 检查空列名
                empty_columns = [col for col in columns if not col or col.strip() == '']
                if empty_columns:
                    validation_result['warnings'].append(f"存在空列名: {empty_columns}")
            
            # 检查数据类型
            if hasattr(data, 'dtypes') and args.schema:
                validation_result['stats']['dtypes'] = data.dtypes.to_dict()
            
            # 严格模式下的额外检查
            if args.strict:
                # 检查缺失值
                if hasattr(data, 'isnull'):
                    missing_counts = data.isnull().sum()
                    if missing_counts.any():
                        validation_result['warnings'].append("存在缺失值")
                        validation_result['stats']['missing_values'] = missing_counts.to_dict()
                
                # 检查重复行
                if hasattr(data, 'duplicated'):
                    duplicate_count = data.duplicated().sum()
                    if duplicate_count > 0:
                        validation_result['warnings'].append(f"存在 {duplicate_count} 行重复数据")
            
            # 输出验证结果
            return self._output_validation_result(validation_result, args)
            
        except Exception as e:
            self.logger.error(f"验证失败: {e}")
            validation_result = {
                'file_path': args.file_path,
                'is_valid': False,
                'errors': [str(e)],
                'warnings': [],
                'stats': {}
            }
            return self._output_validation_result(validation_result, args)

    def mmkv_command(self, args) -> int:
        """MMKV命令处理"""
        try:
            # 使用统一格式处理器，不再单独实例化MMKV处理器
            processor = self.processor

            if args.mmkv_command == 'convert':
                return self._mmkv_convert(processor, args)
            elif args.mmkv_command == 'info':
                return self._mmkv_info(processor, args)
            elif args.mmkv_command == 'extract':
                return self._mmkv_extract(processor, args)
            elif args.mmkv_command == 'create':
                return self._mmkv_create(processor, args)
            else:
                self.logger.error(f"未知MMKV命令: {args.mmkv_command}")
                return 1

        except Exception as e:
            self.logger.error(f"MMKV操作失败: {e}")
            return 1

    def proto_command(self, args) -> int:
        """Protobuf命令处理"""
        try:
            # 使用统一格式处理器，不再单独实例化Protobuf处理器
            processor = self.processor

            if args.proto_command == 'convert':
                return self._proto_convert(processor, args)
            elif args.proto_command == 'info':
                return self._proto_info(processor, args)
            elif args.proto_command == 'decode':
                return self._proto_decode(processor, args)
            else:
                self.logger.error(f"未知Protobuf命令: {args.proto_command}")
                return 1

        except Exception as e:
            self.logger.error(f"Protobuf操作失败: {e}")
            return 1

    def _build_convert_options(self, args) -> dict:
        """构建转换选项"""
        options = {}

        # 格式选项
        if hasattr(args, 'to_format') and args.to_format:
            options['output_format'] = args.to_format
        if hasattr(args, 'from_format') and args.from_format:
            options['input_format'] = args.from_format

        # 编码选项
        if hasattr(args, 'encoding') and args.encoding:
            options['encoding'] = args.encoding

        # CSV选项
        if hasattr(args, 'delimiter') and args.delimiter:
            options['sep'] = args.delimiter
        if hasattr(args, 'quote_char') and args.quote_char:
            options['quotechar'] = args.quote_char
        if hasattr(args, 'types') and args.types:
            # 将类型字符串转换为字典
            types_list = args.types.split(',')
            options['dtype'] = types_list
        if hasattr(args, 'csv_bom') and args.csv_bom:
            options['csv_bom'] = True

        # Excel选项
        if hasattr(args, 'sheet_name') and args.sheet_name:
            options['excel_sheet_name'] = args.sheet_name
        if hasattr(args, 'all_sheets') and args.all_sheets:
            options['excel_all_sheets'] = True

        # XML选项
        if hasattr(args, 'xml_root_tag') and args.xml_root_tag:
            options['root_tag'] = args.xml_root_tag
        if hasattr(args, 'xml_row_tag') and args.xml_row_tag:
            options['row_tag'] = args.xml_row_tag
        if hasattr(args, 'xml_pretty') and args.xml_pretty:
            options['pretty'] = True
        if hasattr(args, 'xml_use_lxml') and args.xml_use_lxml:
            options['use_lxml'] = True

        # 数据库选项
        if hasattr(args, 'table_name') and args.table_name:
            options['db_table_name'] = args.table_name
        if hasattr(args, 'all_tables') and args.all_tables:
            options['db_all_tables'] = True

        # SQL脚本选项
        if hasattr(args, 'sql_dialect') and args.sql_dialect:
            options['sql_dialect'] = args.sql_dialect
        if hasattr(args, 'sql_table_name') and args.sql_table_name:
            options['sql_table_name'] = args.sql_table_name
        if hasattr(args, 'sql_create') and args.sql_create:
            options['sql_create'] = True
        if hasattr(args, 'sql_drop') and args.sql_drop:
            options['sql_drop'] = True
        if hasattr(args, 'sql_if_not_exists') and args.sql_if_not_exists:
            options['sql_if_not_exists'] = True
        if hasattr(args, 'sql_batch_rows') and args.sql_batch_rows:
            options['sql_batch_rows'] = args.sql_batch_rows

        # 处理选项
        if hasattr(args, 'overwrite') and args.overwrite:
            options['overwrite'] = True
        if hasattr(args, 'backup') and args.backup:
            options['backup'] = True
        if hasattr(args, 'validate') and args.validate:
            options['validate'] = True
        if hasattr(args, 'metadata') and args.metadata:
            options['metadata'] = True
        # 新增：嵌套扁平化选项传递
        if hasattr(args, 'flat_nested') and args.flat_nested:
            options['flat_nested'] = True
        if hasattr(args, 'flat_sep') and args.flat_sep:
            options['flat_sep'] = args.flat_sep
        if hasattr(args, 'flat_max_depth') and args.flat_max_depth is not None:
            options['flat_max_depth'] = args.flat_max_depth

        # 多表处理选项
        if hasattr(args, 'multi_action') and args.multi_action:
            options['multi_action'] = args.multi_action
        if hasattr(args, 'split_format') and args.split_format:
            options['split_format'] = args.split_format
        if hasattr(args, 'split_dir') and args.split_dir:
            options['split_dir'] = args.split_dir

        # 性能选项
        if hasattr(args, 'parallel') and args.parallel > 1:
            options['parallel_workers'] = args.parallel

        return options

    def _convert_directory(self, args, options) -> int:
        """目录模式转换实现"""
        try:
            in_dir = args.input
            out_dir = args.output
            if not in_dir or not out_dir:
                self.logger.error("目录模式需要提供输入与输出目录路径")
                return 1

            if not os.path.isdir(in_dir):
                self.logger.error(f"输入目录不存在: {in_dir}")
                return 1
            os.makedirs(out_dir, exist_ok=True)

            recursive = getattr(args, 'recursive', False)
            filter_pattern = getattr(args, 'filter', None)
            flat = getattr(args, 'flat_dir', False)
            parallel = getattr(args, 'parallel', 1)
            if parallel and parallel > 1:
                self.logger.warning("并行转换暂未实现，改为顺序处理")

            # 收集文件列表
            files = []
            if filter_pattern:
                import glob
                pattern = os.path.join(in_dir, '**', filter_pattern) if recursive else os.path.join(in_dir, filter_pattern)
                files = [p for p in glob.glob(pattern, recursive=recursive) if os.path.isfile(p)]
            else:
                for root, _, filenames in os.walk(in_dir):
                    for name in filenames:
                        full = os.path.join(root, name)
                        files.append(full)
                    if not recursive:
                        break

            if not files:
                self.logger.warning("目录中未找到待转换的文件")
                return 0

            # 输出扩展名映射
            ext_map = {
                'csv': 'csv',
                'excel': 'xlsx',
                'json': 'json',
                'xml': 'xml',
                'sqlite': 'sqlite',
                'sql': 'sql'
            }
            to_format = getattr(args, 'to_format', None)
            out_ext = ext_map.get(to_format, None)

            success_count = 0
            fail_count = 0

            for f in files:
                try:
                    rel = os.path.relpath(f, in_dir)
                    base_name = os.path.basename(rel)
                    name_wo_ext = os.path.splitext(base_name)[0]
                    if flat:
                        dest_dir = out_dir
                    else:
                        dest_dir = os.path.join(out_dir, os.path.dirname(rel))
                        os.makedirs(dest_dir, exist_ok=True)

                    # 目标扩展名推断
                    if out_ext:
                        dest_file = os.path.join(dest_dir, f"{name_wo_ext}.{out_ext}")
                    else:
                        # 若未显式指定，沿用原扩展名
                        dest_file = os.path.join(dest_dir, base_name)

                    # 读取选项（CSV编码等）
                    read_options = {}
                    if 'sep' in options:
                        read_options['sep'] = options['sep']
                    if 'encoding' in options:
                        read_options['encoding'] = options['encoding']

                    # from_format/protobuf 解码逻辑
                    from_format = getattr(args, 'from_format', None)
                    if from_format == 'protobuf' or (f.lower().endswith('.pb') and getattr(args, 'schema_file', None) and getattr(args, 'message_type', None)):
                        schema_file = getattr(args, 'schema_file', None)
                        message_type = getattr(args, 'message_type', None)
                        if not schema_file or not message_type:
                            self.logger.error(f"跳过(缺少 schema/type): {f}")
                            fail_count += 1
                            continue
                        result = self.processor.decode_protobuf_with_schema(f, schema_file, message_type)
                    else:
                        result = self.processor.read(f, **read_options)

                    # 格式提示
                    format_hint = None
                    if to_format:
                        fmt_map = {
                            'csv': 'CSV',
                            'excel': 'Excel',
                            'json': 'JSON',
                            'xml': 'XML',
                            'sqlite': 'SQLite',
                            'sql': 'SQLScript',
                            'mmkv': 'MMKV'
                        }
                        format_hint = fmt_map.get(to_format.lower(), to_format.upper())
                    else:
                        # 依据目标文件扩展名推断
                        ext = dest_file.split('.')[-1].lower() if '.' in dest_file else None
                        fmt_map = {
                            'csv': 'CSV',
                            'xlsx': 'Excel',
                            'xls': 'Excel',
                            'json': 'JSON',
                            'xml': 'XML',
                            'sqlite': 'SQLite',
                            'db': 'SQLite',
                            'sql': 'SQLScript',
                            'mmkv': 'MMKV'
                        }
                        format_hint = fmt_map.get(ext, None)

                    # 表格格式时，转换 dict/list 为 DataFrame
                    if format_hint in ('CSV', 'Excel'):
                        try:
                            import pandas as pd
                            if isinstance(result, dict):
                                result = pd.DataFrame([result])
                            elif isinstance(result, list) and (len(result) == 0 or isinstance(result[0], dict)):
                                result = pd.DataFrame(result)
                        except Exception as e:
                            self.logger.warning(f"{f} 转换为表格结构失败: {e}")

                    # 写出
                    write_options = dict(options)
                    ok = self.processor.write(result, dest_file, format_hint=format_hint, **write_options)
                    if ok:
                        success_count += 1
                        self.logger.info(f"转换完成: {f} -> {dest_file}")
                    else:
                        fail_count += 1
                        self.logger.error(f"转换失败: {f}")

                except Exception as e:
                    fail_count += 1
                    self.logger.error(f"处理文件失败 {f}: {e}")

            self.logger.info(f"目录模式转换完成: 成功 {success_count}, 失败 {fail_count}")
            return 0 if fail_count == 0 else (2 if success_count > 0 else 1)
        except Exception as e:
            self.logger.error(f"目录模式转换失败: {e}")
            return 1

    def _build_merge_config(self, args) -> dict:
        """构建合并配置"""
        config = {
            'mode': args.mode,
            'sources': args.input_files[1:],
            'target': args.input_files[0],
            'output': args.output
        }

        # 关键字段
        if args.key_fields:
            config['key_fields'] = [field.strip() for field in args.key_fields.split(',')]

        # 映射文件
        if args.mapping_file:
            config['mapping_file'] = args.mapping_file

        # 自动映射
        if args.auto_map:
            config['auto_map'] = True

        # 性能选项
        if args.arrow:
            config['use_arrow'] = True
        if args.parallel > 1:
            config['parallel_workers'] = args.parallel

        # 容错选项
        if args.tolerant:
            config['tolerant'] = True
        if args.ignore_case:
            config['ignore_case'] = True

        return config

    def _handle_convert_result(self, result) -> int:
        """处理转换结果"""
        if result.success:
            self.logger.info(f"转换完成: {result.output_file}")
            if result.stats:
                duration = result.stats.get('duration', 0)
                self.logger.info(f"耗时: {duration:.2f}秒")
            return 0
        else:
            self.logger.error(f"转换失败: {result.error_message}")
            return 1

    def _merge_tables_dict(self, tables: dict):
        """将 dict[name -> DataFrame] 多表结构纵向合并为单表。

        - 对齐列为所有表的并集，缺失列填充为 None
        - 添加来源标记列 `_merge_source`
        """
        try:
            import pandas as pd
        except Exception as e:
            self.logger.error(f"合并多表需要 pandas: {e}")
            raise

        source_col = '_merge_source'
        # 收集所有列
        all_columns = set()
        for df in tables.values():
            if hasattr(df, 'columns'):
                all_columns |= set(df.columns)
        ordered_cols = [source_col] + sorted(list(all_columns))

        frames = []
        for name, df in tables.items():
            if not hasattr(df, 'copy'):
                df = pd.DataFrame(df)
            df_work = df.copy()
            df_work[source_col] = str(name)
            for col in all_columns:
                if col not in df_work.columns:
                    df_work[col] = None
            # 统一列顺序
            df_work = df_work[ordered_cols]
            frames.append(df_work)

        merged = pd.concat(frames, ignore_index=True) if frames else pd.DataFrame(columns=ordered_cols)
        return merged

    def _handle_batch_results(self, results) -> int:
        """处理批量转换结果"""
        success_count = sum(1 for r in results if r.success)
        total_count = len(results)

        if success_count == total_count:
            self.logger.info(f"批量转换完成: {success_count}/{total_count} 成功")
            return 0
        else:
            self.logger.warning(f"批量转换部分失败: {success_count}/{total_count} 成功")
            # 显示失败的结果
            for result in results:
                if not result.success:
                    self.logger.error(f"失败: {result.input_file} - {result.error_message}")
            return 1 if success_count == 0 else 2

    def _handle_merge_result(self, result) -> int:
        """处理合并结果"""
        if result.success:
            self.logger.info(f"合并完成: {result.output_path}")
            if hasattr(result, 'stats'):
                self.logger.info(f"处理记录数: {result.stats.get('total_records', 'N/A')}")
            return 0
        else:
            self.logger.error(f"合并失败: {result.error_message}")
            return 1

    def _preview_merge(self, config: dict, preview_rows: int) -> int:
        """预览合并结果"""
        try:
            preview_data = self.merge_engine.preview_merge(config, preview_rows)

            if preview_data is not None and not preview_data.empty:
                # 显示预览数据
                print(f"\n合并预览 (前{preview_rows}行):")
                print(preview_data.to_string(index=False))
                print(f"\n总行数: {len(preview_data)}")
                return 0
            else:
                print("预览数据为空")
                return 1

        except Exception as e:
            self.logger.error(f"预览生成失败: {e}")
            return 1

    def _output_file_info(self, file_info: dict, args) -> int:
        """输出文件信息"""
        try:
            output_format = getattr(args, 'output_format', 'text')  # 使用正确的参数名
            # 检查是否使用英文输出，默认使用中文
            use_english = getattr(args, 'english', False)
            
            if output_format == 'json':
                import json
                print(json.dumps(file_info, indent=2, ensure_ascii=False))
            elif output_format == 'yaml':
                import yaml
                print(yaml.dump(file_info, default_flow_style=False, allow_unicode=True))
            else:
                # 文本格式
                self._print_file_info_text(file_info, not use_english)

            return 0

        except Exception as e:
            self.logger.error(f"输出文件信息失败: {e}")
            return 1

    def _output_validation_result(self, validation_result: dict, args) -> int:
        """输出验证结果"""
        try:
            # 获取输出格式，默认为text
            output_format = getattr(args, 'format_output', 'text')
            
            # 如果有输出文件参数，则写入文件
            if hasattr(args, 'output') and args.output:
                if output_format == 'json':
                    import json
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(validation_result, f, indent=2, ensure_ascii=False)
                else:
                    # 默认使用JSON格式写入文件
                    import json
                    with open(args.output, 'w', encoding='utf-8') as f:
                        json.dump(validation_result, f, indent=2, ensure_ascii=False)
                self.logger.info(f"验证结果已保存到: {args.output}")
            
            # 输出到控制台
            if output_format == 'json':
                import json
                print(json.dumps(validation_result, indent=2, ensure_ascii=False))
            elif output_format == 'yaml':
                import yaml
                print(yaml.dump(validation_result, default_flow_style=False, allow_unicode=True))
            else:
                # 文本格式
                self._print_validation_result_text(validation_result)

            # 返回验证状态
            return 0 if validation_result['is_valid'] else 1

        except Exception as e:
            self.logger.error(f"输出验证结果失败: {e}")
            return 1

    def _print_file_info_text(self, file_info: dict, use_chinese=True):
        """以文本格式输出文件信息"""
        if use_chinese:
            print(f"\n文件信息:")
            print(f"  路径: {file_info.get('file_path', 'N/A')}")
            print(f"  格式: {file_info.get('format', 'N/A')}")
            print(f"  大小: {file_info.get('file_size', 'N/A')} 字节")

            if 'stats' in file_info:
                stats = file_info['stats']
                print(f"  记录数: {stats.get('record_count', 'N/A')}")
                print(f"  字段数: {stats.get('field_count', 'N/A')}")

            if 'columns' in file_info:
                print(f"  字段: {', '.join(file_info['columns'])}")

            if 'sample_data' in file_info:
                print(f"\n样本数据:")
                sample_data = file_info['sample_data']
                if isinstance(sample_data, list) and sample_data:
                    # 打印表格头部
                    if isinstance(sample_data[0], dict):
                        headers = list(sample_data[0].keys())
                        print(f"  {' | '.join(headers)}")
                        print(f"  {'-+-'.join(['-' * len(h) for h in headers])}")
                        # 打印前几行数据
                        for row in sample_data[:5]:
                            values = [str(row.get(h, '')) for h in headers]
                            print(f"  {' | '.join(values)}")
        else:
            # 英文输出
            print(f"\nFile Information:")
            print(f"  Path: {file_info.get('file_path', 'N/A')}")
            print(f"  Format: {file_info.get('format', 'N/A')}")
            print(f"  Size: {file_info.get('file_size', 'N/A')} bytes")

            if 'stats' in file_info:
                stats = file_info['stats']
                print(f"  Rows: {stats.get('record_count', 'N/A')}")
                print(f"  Columns: {stats.get('field_count', 'N/A')}")

            if 'columns' in file_info:
                print(f"  Fields: {', '.join(file_info['columns'])}")

            if 'sample_data' in file_info:
                print(f"\nSample Data:")
                sample_data = file_info['sample_data']
                if isinstance(sample_data, list) and sample_data:
                    # 打印表格头部
                    if isinstance(sample_data[0], dict):
                        headers = list(sample_data[0].keys())
                        print(f"  {' | '.join(headers)}")
                        print(f"  {'-+-'.join(['-' * len(h) for h in headers])}")
                        # 打印前几行数据
                        for row in sample_data[:5]:
                            values = [str(row.get(h, '')) for h in headers]
                            print(f"  {' | '.join(values)}")

    def _print_validation_result_text(self, validation_result: dict):
        """以文本格式输出验证结果"""
        print(f"\n验证结果:")
        print(f"  文件: {validation_result.get('file_path', 'N/A')}")
        print(f"  状态: {'有效' if validation_result.get('is_valid', False) else '无效'}")

        # 输出错误信息
        errors = validation_result.get('errors', [])
        if errors:
            print(f"\n错误:")
            for error in errors:
                print(f"  - {error}")

        # 输出警告信息
        warnings = validation_result.get('warnings', [])
        if warnings:
            print(f"\n警告:")
            for warning in warnings:
                print(f"  - {warning}")

        # 输出统计信息
        stats = validation_result.get('stats', {})
        if stats:
            print(f"\n统计信息:")
            if 'record_count' in stats:
                print(f"  记录数: {stats['record_count']}")
            if 'field_count' in stats:
                print(f"  字段数: {stats['field_count']}")
            if 'columns' in stats:
                print(f"  字段: {', '.join(stats['columns'])}")
            if 'missing_values' in stats:
                print(f"  缺失值:")
                for col, count in stats['missing_values'].items():
                    if count > 0:
                        print(f"    {col}: {count}")
            if 'dtypes' in stats:
                print(f"  数据类型:")
                for col, dtype in stats['dtypes'].items():
                    print(f"    {col}: {dtype}")

    def _mmkv_convert(self, processor, args) -> int:
        """MMKV转换"""
        try:
            # 使用统一格式处理器读取MMKV数据
            data = self.processor.read(args.input_file)

            # 使用统一格式处理器写入目标格式，尊重 --format 提示
            fmt_map = {
                'csv': 'CSV',
                'json': 'JSON',
                'excel': 'EXCEL'
            }
            format_hint = fmt_map.get(getattr(args, 'format', None))
            self.processor.write_file(data, args.output_file, format_hint=format_hint)
            self.logger.info(f"MMKV转换完成: {args.input_file} -> {args.output_file}")
            return 0
        except Exception as e:
            self.logger.error(f"MMKV转换失败: {e}")
            return 1

    def _mmkv_info(self, processor, args) -> int:
        """MMKV信息"""
        try:
            metadata = processor.get_file_metadata(args.file_path)
            self._print_file_info_text(metadata)
            return 0
        except Exception as e:
            self.logger.error(f"获取MMKV信息失败: {e}")
            return 1

    def _mmkv_extract(self, processor, args) -> int:
        """MMKV提取"""
        try:
            data = processor.convert_to_dict(args.file_path)
            extracted = {key: data[key] for key in args.keys if key in data}

            if args.output:
                import json
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(extracted, f, indent=2, ensure_ascii=False)
                self.logger.info(f"提取结果已保存到: {args.output}")
            else:
                print(json.dumps(extracted, indent=2, ensure_ascii=False))

            return 0
        except Exception as e:
            self.logger.error(f"MMKV提取失败: {e}")
            return 1

    def _mmkv_create(self, processor, args) -> int:
        """MMKV创建"""
        try:
            # 读取输入文件（JSON/CSV等），交由统一处理器
            data = self.processor.read(args.input_file)

            # 透传键值列参数，支持多行按列映射；单行 DataFrame 自动列->值映射
            key_col = getattr(args, 'key_column', None)
            val_col = getattr(args, 'value_column', None)
            write_kwargs = {}
            if key_col:
                write_kwargs['key_column'] = key_col
            if val_col:
                write_kwargs['value_column'] = val_col

            # 使用统一处理器写入 MMKV，显式格式提示
            success = self.processor.write_file(
                data,
                args.output_file,
                format_hint='MMKV',
                **write_kwargs
            )
            if success:
                self.logger.info(f"MMKV文件创建完成: {args.output_file}")
                return 0
            else:
                self.logger.error("MMKV文件创建失败")
                return 1
        except Exception as e:
            self.logger.error(f"MMKV创建失败: {e}")
            return 1

    def _proto_convert(self, processor, args) -> int:
        """Protobuf转换"""
        try:
            # 统一处理器读取Protobuf，parse_mode=auto时不传format以便自动检测
            read_kwargs = {}
            if getattr(args, 'parse_mode', 'auto') and args.parse_mode != 'auto':
                # ProtobufProcessor.read 使用参数名 'format'
                read_kwargs['format'] = args.parse_mode
            data = self.processor.read(args.input_file, **read_kwargs)

            # 统一处理器写入目标格式，尊重 --format 提示
            fmt_map = {
                'csv': 'CSV',
                'json': 'JSON',
                'xml': 'XML'
            }
            format_hint = fmt_map.get(getattr(args, 'format', None))
            self.processor.write_file(data, args.output_file, format_hint=format_hint)
            self.logger.info(f"Protobuf转换完成: {args.input_file} -> {args.output_file}")
            return 0
        except Exception as e:
            self.logger.error(f"Protobuf转换失败: {e}")
            return 1

    def _proto_info(self, processor, args) -> int:
        """Protobuf信息"""
        try:
            metadata = processor.get_file_metadata(args.file_path)
            if args.schema:
                schema = processor.generate_protobuf_schema(args.file_path)
                print("\nGenerated Schema:")
                print(schema)
            else:
                self._print_file_info_text(metadata)
            return 0
        except Exception as e:
            self.logger.error(f"获取Protobuf信息失败: {e}")
            return 1

    def _proto_decode(self, processor, args) -> int:
        """Protobuf解码"""
        try:
            # 强制要求提供 Schema 文件和消息类型
            if not getattr(args, 'schema_file', None) or not getattr(args, 'message_type', None):
                self.logger.error("必须提供 --schema-file 与 --message-type 才能进行解码")
                return 1

            data = processor.decode_protobuf_with_schema(
                args.input_file,
                args.schema_file,
                args.message_type
            )

            import json
            if args.output:
                with open(args.output, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=2, ensure_ascii=False)
                self.logger.info(f"解码结果已保存到: {args.output}")
            else:
                print(json.dumps(data, indent=2, ensure_ascii=False))

            return 0
        except Exception as e:
            self.logger.error(f"Protobuf解码失败: {e}")
            return 1


def main():
    """主函数"""
    try:
        # 创建CLI实例
        cli = DataConverterCLI()

        # 运行CLI
        exit_code = cli.run()

        # 退出
        sys.exit(exit_code)

    except SystemExit as e:
        # 处理SystemExit异常，确保正确的退出码
        sys.exit(e.code)
    except Exception as e:
        print(f"程序启动失败: {e}")
        sys.exit(1)


if __name__ == '__main__':
    main()