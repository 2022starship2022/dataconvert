#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
命令行参数解析器
"""

import argparse
import sys
from typing import List, Optional


class ArgumentParser:
    """命令行参数解析器"""

    def __init__(self):
        self.parser = None

    def create_parser(self) -> argparse.ArgumentParser:
        """创建主参数解析器"""
        parser = argparse.ArgumentParser(
            prog='dataconvert',
            description='数据转换工具CLI版本 - 支持多种数据格式转换和合并',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            add_help=False,
            epilog="""
示例:
  dataconvert convert data.csv output.xlsx --to excel
  dataconvert convert data.mmkv output.json --from mmkv --to json
  dataconvert convert tmp/sample.pb tmp/out.json --from protobuf --to json --schema-file tmp/schema.desc --message-type package.Message
  dataconvert convert ./dir ./out --dir-in --dir-out --from json --to csv --recursive --flat-dir
  dataconvert merge file1.csv file2.csv merged.csv --mode join
  dataconvert info data.mmkv --schema

  # 多表读写与导出
  dataconvert convert tmp/multi.xlsx tmp/multi_out.xlsx --to excel --all-sheets
  dataconvert convert tmp/multi.xlsx tmp/multi.db --to sqlite --all-sheets
  dataconvert convert tmp/multi.db tmp/sqlite_out.xlsx --from sqlite --to excel --all-tables
  dataconvert convert tmp/multi.xlsx tmp/merged.csv --to csv --all-sheets --multi-action merge
  dataconvert convert tmp/multi.xlsx tmp/sheets_out --to csv --all-sheets --multi-action split --split-dir tmp/sheets_out --split-format csv

            """
        )

        # 自定义帮助与版本选项（中文释义）
        parser.add_argument(
            '-h', '--help',
            action='help',
            help='显示帮助信息并退出'
        )

        # 版本选项，使用包版本号
        try:
            from __init__ import __version__ as _VERSION
        except Exception:
            _VERSION = 'unknown'
        parser.add_argument(
            '--version',
            action='version',
            version=f'dataconvert {_VERSION}',
            help='显示程序版本号并退出'
        )

        # 全局选项
        self._add_global_options(parser)

        # 子命令
        subparsers = parser.add_subparsers(
            dest='command',
            help='可用命令',
            metavar='<command>'
        )

        # 添加各种命令（原4个 + mmkv/proto）
        self.add_convert_args(subparsers)
        self.add_merge_args(subparsers)
        self.add_info_args(subparsers)
        self.add_validate_args(subparsers)
        # 额外注册：MMKV 与 Protobuf 顶级子命令
        self.add_mmkv_args(subparsers)
        self.add_proto_args(subparsers)

        self.parser = parser
        return parser

    def _add_global_options(self, parser: argparse.ArgumentParser):
        """添加全局选项"""
        parser.add_argument(
            '--config', '-c',
            type=str,
            metavar='PATH',
            help='配置文件路径 (YAML格式)'
        )

        parser.add_argument(
            '--verbose', '-v',
            action='store_true',
            help='详细输出模式'
        )

        parser.add_argument(
            '--quiet', '-q',
            action='store_true',
            help='静默模式，只输出错误信息'
        )

        parser.add_argument(
            '--log-level',
            choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
            default='INFO',
            help='日志级别 (默认: INFO)'
        )

        parser.add_argument(
            '--no-color',
            action='store_true',
            help='禁用彩色输出'
        )

    def add_convert_args(self, subparsers):
        """添加转换命令参数"""
        convert_parser = subparsers.add_parser(
            'convert',
            help='数据格式转换',
            description='将数据文件从一种格式转换为另一种格式',
            add_help=False
        )
        convert_parser.add_argument('-h','--help', action='help', help='显示帮助信息并退出')

        # 输入输出参数
        convert_parser.add_argument(
            'input',
            help='输入文件路径'
        )

        convert_parser.add_argument(
            'output',
            help='输出文件路径 (批量模式下可省略)'
        )

        # 格式参数（统一为 --from / --to）
        format_group = convert_parser.add_argument_group('格式选项')

        format_group.add_argument(
            '--to', '-t',
            dest='to_format',
            choices=['csv', 'excel', 'json', 'xml', 'sqlite', 'sql', 'mmkv'],
            help='显式指定输出格式 (默认: 依据输出扩展名)'
        )

        format_group.add_argument(
            '--from', '-f',
            dest='from_format',
            choices=['csv', 'excel', 'json', 'xml', 'sqlite', 'mmkv', 'protobuf'],
            help='显式指定输入格式 (目录模式或歧义时必需)'
        )

        format_group.add_argument(
            '--encoding', '-e',
            default='utf-8',
            help='文件编码 (支持: auto/utf-8/utf-8-sig/gbk/big5/shift_jis 等，默认: utf-8)'
        )

        # Protobuf 基于 schema 的解码参数
        format_group.add_argument(
            '--schema-file',
            help='Protobuf 描述集(.desc)或 .proto 文件路径'
        )
        format_group.add_argument(
            '--message-type',
            help='消息类型全名 (例如 package.MessageName)'
        )

        # CSV特定选项
        csv_group = convert_parser.add_argument_group('CSV选项')

        csv_group.add_argument(
            '--delimiter', '-d',
            default=',',
            help='CSV分隔符 (默认: ,)'
        )

        csv_group.add_argument(
            '--quote-char',
            default='"',
            help='CSV引号字符 (默认: ")'
        )
        
        csv_group.add_argument(
            '--types',
            help='指定列数据类型 (逗号分隔，如: int,str,float,date,bool)'
        )

        csv_group.add_argument(
            '--csv-bom',
            action='store_true',
            help='写入UTF-8 BOM到CSV文件'
        )

        # Excel特定选项
        excel_group = convert_parser.add_argument_group('Excel选项')

        excel_group.add_argument(
            '--sheet-name', '-s',
            help='Excel工作表名称'
        )

        excel_group.add_argument(
            '--all-sheets',
            action='store_true',
            help='读取 Excel 文件内所有工作表'
        )

        # XML特定选项
        xml_group = convert_parser.add_argument_group('XML选项')

        xml_group.add_argument(
            '--xml-root-tag',
            help='XML根元素名称 (默认: root)'
        )

        xml_group.add_argument(
            '--xml-row-tag',
            help='XML数据行元素名称 (默认: row)'
        )

        xml_group.add_argument(
            '--xml-pretty',
            action='store_true',
            help='XML输出美化缩进'
        )

        xml_group.add_argument(
            '--xml-use-lxml',
            action='store_true',
            help='优先使用lxml解析/写入XML'
        )

        # 数据库特定选项
        db_group = convert_parser.add_argument_group('数据库选项')

        db_group.add_argument(
            '--table-name',
            help='数据库表名称'
        )

        db_group.add_argument(
            '--all-tables',
            action='store_true',
            help='读取数据库内所有数据表'
        )

        # SQL脚本选项
        sql_group = convert_parser.add_argument_group('SQL脚本选项')

        sql_group.add_argument(
            '--sql-dialect',
            choices=['sqlite', 'mysql', 'postgres'],
            default='sqlite',
            help='SQL方言 (默认: sqlite)'
        )

        sql_group.add_argument(
            '--sql-table-name',
            help='生成SQL脚本的表名 (默认: 自动推断)'
        )

        sql_group.add_argument(
            '--sql-create',
            action='store_true',
            help='在脚本中包含CREATE TABLE语句'
        )

        sql_group.add_argument(
            '--sql-drop',
            action='store_true',
            help='在脚本中包含DROP TABLE IF EXISTS语句'
        )

        sql_group.add_argument(
            '--sql-if-not-exists',
            action='store_true',
            help='在CREATE TABLE中加入IF NOT EXISTS'
        )

        sql_group.add_argument(
            '--sql-batch-rows',
            type=int,
            default=1,
            help='每条INSERT语句包含的行数 (默认: 1)'
        )

        # 处理选项
        process_group = convert_parser.add_argument_group('处理选项')

        process_group.add_argument(
            '--overwrite',
            action='store_true',
            help='覆盖已存在的输出文件'
        )

        process_group.add_argument(
            '--backup',
            action='store_true',
            help='创建输出文件备份'
        )

        # 新增：嵌套扁平化选项
        process_group.add_argument(
            '--flat-nested',
            action='store_true',
            help='将嵌套字段扁平为点号分隔键 (例如 A.B.C)'
        )
        process_group.add_argument(
            '--flat-sep',
            default='.',
            help='嵌套键的分隔符 (默认: .)'
        )
        process_group.add_argument(
            '--flat-max-depth',
            type=int,
            help='扁平化的最大层级 (默认: 不限制)'
        )

        # 目录模式选项
        dir_group = convert_parser.add_argument_group('目录模式')
        dir_group.add_argument('--dir-in', action='store_true', help='将 input 作为目录处理')
        dir_group.add_argument('--dir-out', action='store_true', help='将 output 作为目录处理')
        dir_group.add_argument('--flat-dir', action='store_true', help='扁平化输出文件到根目录')
        dir_group.add_argument('--filter', help='目录模式下的文件通配过滤 (glob)')
        dir_group.add_argument('--parallel', type=int, default=1, help='目录模式并行处理线程数')
        dir_group.add_argument('--recursive', '-r', action='store_true', help='递归处理目录')

        process_group.add_argument(
            '--batch',
            action='store_true',
            help='批量处理模式'
        )

        process_group.add_argument(
            '--output-dir', '-o',
            help='输出目录 (批量模式)'
        )

        # 多表处理选项
        multi_group = convert_parser.add_argument_group('多表选项')
        multi_group.add_argument(
            '--multi-action',
            choices=['merge', 'split'],
            default='merge',
            help='多表导出为单表时的策略: merge 合并或 split 拆分到文件夹'
        )
        multi_group.add_argument(
            '--split-format',
            choices=['csv', 'json', 'excel'],
            help='拆分到文件夹时每张表的文件格式'
        )
        multi_group.add_argument(
            '--split-dir',
            help='拆分输出的目标文件夹路径 (默认: 由输出路径派生)'
        )
        
        
        # 验证选项
        validate_group = convert_parser.add_argument_group('验证选项')

        validate_group.add_argument(
            '--validate',
            action='store_true',
            help='验证输出文件'
        )

        validate_group.add_argument(
            '--metadata',
            action='store_true',
            help='生成元数据文件'
        )

        # 进度选项
        progress_group = convert_parser.add_argument_group('进度选项')

        progress_group.add_argument(
            '--progress',
            action='store_true',
            help='显示进度条'
        )

        return convert_parser

    def add_merge_args(self, subparsers):
        """添加合并命令参数"""
        merge_parser = subparsers.add_parser(
            'merge',
            help='数据文件合并',
            description='将多个数据文件合并为一个文件',
            add_help=False
        )
        merge_parser.add_argument('-h','--help', action='help', help='显示帮助信息并退出')

        # 输入输出参数
        merge_parser.add_argument(
            'input_files',
            nargs='+',
            help='输入文件路径'
        )

        merge_parser.add_argument(
            'output',
            help='输出文件路径'
        )

        # 合并选项
        merge_group = merge_parser.add_argument_group('合并选项')

        merge_group.add_argument(
            '--mode', '-m',
            choices=['append', 'join', 'update', 'cross'],
            default='append',
            help='合并模式 (默认: append)'
        )

        merge_group.add_argument(
            '--key-fields', '-k',
            help='关键字段 (逗号分隔)'
        )

        merge_group.add_argument(
            '--mapping-file',
            help='字段映射文件路径 (JSON格式)'
        )

        merge_group.add_argument(
            '--auto-map',
            action='store_true',
            help='自动字段映射'
        )

        # 预览选项
        preview_group = merge_parser.add_argument_group('预览选项')

        preview_group.add_argument(
            '--preview', '-p',
            action='store_true',
            help='预览合并结果'
        )

        preview_group.add_argument(
            '--preview-rows', '-n',
            type=int,
            default=50,
            help='预览行数 (默认: 50)'
        )

        # 性能选项
        performance_group = merge_parser.add_argument_group('性能选项')

        performance_group.add_argument(
            '--arrow',
            action='store_true',
            help='使用Arrow加速'
        )

        performance_group.add_argument(
            '--parallel',
            type=int,
            default=1,
            help='并行处理数量 (默认: 1)'
        )

        # 容错选项
        tolerant_group = merge_parser.add_argument_group('容错选项')

        tolerant_group.add_argument(
            '--tolerant',
            action='store_true',
            help='容错模式，跳过错误数据'
        )

        tolerant_group.add_argument(
            '--ignore-case',
            action='store_true',
            help='忽略大小写'
        )

        return merge_parser

    def add_info_args(self, subparsers):
        """添加信息查询命令参数"""
        info_parser = subparsers.add_parser(
            'info',
            help='文件信息查询',
            description='显示数据文件的详细信息',
            add_help=False
        )
        info_parser.add_argument('-h','--help', action='help', help='显示帮助信息并退出')

        # 输入文件
        info_parser.add_argument(
            'file_path',
            help='文件路径'
        )

        # 信息选项
        info_group = info_parser.add_argument_group('信息选项')

        info_group.add_argument(
            '--from',
            dest='from_format',
            choices=['csv', 'excel', 'json', 'xml', 'sqlite', 'mmkv', 'protobuf'],
            help='显式指定输入格式 (用于 .pb 等难以检测的格式)'
        )

        info_group.add_argument(
            '--schema', '-s',
            action='store_true',
            help='显示数据结构'
        )

        info_group.add_argument(
            '--stats',
            action='store_true',
            help='显示统计信息'
        )

        info_group.add_argument(
            '--sample', '-n',
            type=int,
            default=10,
            help='显示样本数据行数 (默认: 10)'
        )

        info_group.add_argument(
            '--analyze',
            action='store_true',
            help='深度分析'
        )

        # 输出选项
        output_group = info_parser.add_argument_group('输出选项')

        output_group.add_argument(
            '--export-info',
            help='导出信息到文件 (JSON格式)'
        )

        output_group.add_argument(
            '--output-format',
            choices=['text', 'json', 'yaml'],
            default='text',
            help='输出格式 (默认: text)'
        )

        return info_parser

    def add_validate_args(self, subparsers):
        """添加验证命令参数"""
        validate_parser = subparsers.add_parser(
            'validate',
            help='数据文件验证',
            description='验证数据文件的格式和内容',
            add_help=False
        )
        validate_parser.add_argument('-h','--help', action='help', help='显示帮助信息并退出')

        # 输入文件
        validate_parser.add_argument(
            'file_path',
            help='要验证的文件路径'
        )

        # 验证选项
        validation_group = validate_parser.add_argument_group('验证选项')

        validation_group.add_argument(
            '--format', '-f',
            choices=['csv', 'json', 'xml', 'excel', 'sqlite'],
            help='指定文件格式 (默认: 自动检测)'
        )

        validation_group.add_argument(
            '--schema',
            help='Schema文件路径 (用于结构验证)'
        )

        validation_group.add_argument(
            '--strict',
            action='store_true',
            help='严格模式验证'
        )

        validation_group.add_argument(
            '--sample-only',
            action='store_true',
            help='仅验证样本数据 (提高大文件验证速度)'
        )

        validation_group.add_argument(
            '--sample-size',
            type=int,
            default=100,
            help='样本大小 (默认: 100)'
        )

        # 输出选项
        output_group = validate_parser.add_argument_group('输出选项')

        output_group.add_argument(
            '--output', '-o',
            help='输出验证结果到文件'
        )

        output_group.add_argument(
            '--format-output',
            choices=['text', 'json', 'xml'],
            default='text',
            help='输出格式 (默认: text)'
        )

        return validate_parser

    def add_mmkv_args(self, subparsers):
        """添加MMKV命令参数"""
        mmkv_parser = subparsers.add_parser(
            'mmkv',
            help='MMKV文件处理',
            description='MMKV格式文件的读取、转换和创建'
        )

        # 子命令
        mmkv_subparsers = mmkv_parser.add_subparsers(
            dest='mmkv_command',
            help='MMKV操作命令'
        )

        # 转换命令
        convert_parser = mmkv_subparsers.add_parser(
            'convert',
            help='转换MMKV文件'
        )
        convert_parser.add_argument('input_file', help='输入MMKV文件')
        convert_parser.add_argument('output_file', help='输出文件')
        convert_parser.add_argument('--format', '-f', choices=['csv', 'json', 'excel'],
                                  default='json', help='输出格式')

        # 信息命令
        info_parser = mmkv_subparsers.add_parser(
            'info',
            help='显示MMKV信息'
        )
        info_parser.add_argument('file_path', help='MMKV文件路径')
        info_parser.add_argument('--keys', action='store_true', help='显示所有键')
        info_parser.add_argument('--types', action='store_true', help='显示类型分布')

        # 提取命令
        extract_parser = mmkv_subparsers.add_parser(
            'extract',
            help='提取指定键值'
        )
        extract_parser.add_argument('file_path', help='MMKV文件路径')
        extract_parser.add_argument('keys', nargs='+', help='要提取的键')
        extract_parser.add_argument('--output', '-o', help='输出文件路径')

        # 创建命令
        create_parser = mmkv_subparsers.add_parser(
            'create',
            help='创建MMKV文件'
        )
        create_parser.add_argument('input_file', help='输入文件 (JSON/CSV)')
        create_parser.add_argument('output_file', help='输出MMKV文件')
        create_parser.add_argument('--key-column', default='key', help='键列名')
        create_parser.add_argument('--value-column', default='value', help='值列名')

        return mmkv_parser

    def add_proto_args(self, subparsers):
        """添加Protobuf命令参数"""
        proto_parser = subparsers.add_parser(
            'proto',
            help='Protobuf文件处理',
            description='Protobuf格式文件的解析和转换'
        )

        # 子命令
        proto_subparsers = proto_parser.add_subparsers(
            dest='proto_command',
            help='Protobuf操作命令'
        )

        # 转换命令
        convert_parser = proto_subparsers.add_parser(
            'convert',
            help='转换Protobuf文件'
        )
        convert_parser.add_argument('input_file', help='输入Protobuf文件')
        convert_parser.add_argument('output_file', help='输出文件')
        convert_parser.add_argument('--format', '-f', choices=['json', 'csv', 'xml'],
                                  default='json', help='输出格式')
        convert_parser.add_argument('--parse-mode', choices=['binary', 'text', 'auto'],
                                   default='auto', help='解析模式')

        # 信息命令
        info_parser = proto_subparsers.add_parser(
            'info',
            help='显示Protobuf信息'
        )
        info_parser.add_argument('file_path', help='Protobuf文件路径')
        info_parser.add_argument('--schema', action='store_true', help='生成schema')
        info_parser.add_argument('--analyze', action='store_true', help='深度分析')

        # 解码命令
        decode_parser = proto_subparsers.add_parser(
            'decode',
            help='解码二进制数据'
        )
        decode_parser.add_argument('input_file', help='输入二进制文件')
        decode_parser.add_argument('--schema-file', required=True,
                                   help='必需：描述集(.desc)文件路径')
        decode_parser.add_argument('--message-type', required=True,
                                   help='必需：消息类型全名（例如 package.MessageName）')
        decode_parser.add_argument('--output', '-o', help='输出文件路径')

        return proto_parser

    def parse_args(self, args: Optional[List[str]] = None) -> argparse.Namespace:
        """解析命令行参数"""
        if not self.parser:
            self.create_parser()

        parsed_args = self.parser.parse_args(args)

        # 参数验证
        self._validate_args(parsed_args)

        return parsed_args

    def _validate_args(self, args: argparse.Namespace):
        """验证参数"""
        # 检查是否有命令
        if not args.command:
            self.parser.print_help()
            sys.exit(1)

        # 检查verbose和quiet冲突
        if args.verbose and args.quiet:
            print("错误: --verbose 和 --quiet 选项不能同时使用")
            sys.exit(1)

        # 转换命令验证
        if args.command == 'convert':
            self._validate_convert_args(args)
        elif args.command == 'merge':
            self._validate_merge_args(args)
        elif args.command == 'info':
            self._validate_info_args(args)
        elif args.command == 'validate':
            self._validate_validate_args(args)

    def _validate_convert_args(self, args: argparse.Namespace):
        """验证转换命令参数"""
        # 目录模式与并行参数
        if getattr(args, 'parallel', 1) < 1:
            print("错误: 并行处理数量必须大于0")
            sys.exit(1)

        if getattr(args, 'dir_in', False):
            # input 必须是目录
            import os
            if not os.path.isdir(args.input):
                print("错误: --dir-in 需要 input 为目录路径")
                sys.exit(1)

        if getattr(args, 'dir_out', False):
            # output 建议是目录（运行时创建），此处不强校验存在
            pass

        # Protobuf 解码要求 schema 与 message type
        if getattr(args, 'from_format', None) == 'protobuf':
            if not args.schema_file or not args.message_type:
                print("错误: --from protobuf 需要指定 --schema-file 与 --message-type")
                sys.exit(1)

    def _validate_merge_args(self, args: argparse.Namespace):
        """验证合并命令参数"""
        # 检查关键字段
        if args.mode in ['join', 'update'] and not args.key_fields:
            print(f"错误: {args.mode} 模式需要指定 --key-fields")
            sys.exit(1)

        # 检查输入文件数量
        if len(args.input_files) < 2:
            print("错误: 合并操作至少需要2个输入文件")
            sys.exit(1)

    def _validate_info_args(self, args: argparse.Namespace):
        """验证信息查询命令参数"""
        # 文件必须存在
        import os
        if not os.path.isfile(args.file_path):
            print("错误: 指定的文件不存在")
            sys.exit(1)

        # 样本行数必须非负
        if hasattr(args, 'sample') and args.sample < 0:
            print("错误: --sample 必须为非负整数")
            sys.exit(1)

    def _validate_validate_args(self, args: argparse.Namespace):
        """验证数据文件验证命令参数"""
        import os
        # 文件必须存在
        if not os.path.isfile(args.file_path):
            print("错误: 要验证的文件不存在")
            sys.exit(1)

        # 样本大小必须为正整数
        if hasattr(args, 'sample_size') and args.sample_size <= 0:
            print("错误: --sample-size 必须为正整数")
            sys.exit(1)

        # 如果提供 schema 路径，需存在
        if hasattr(args, 'schema') and args.schema:
            if not os.path.isfile(args.schema):
                print("错误: 提供的 --schema 文件不存在")