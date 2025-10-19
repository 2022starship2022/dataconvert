#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
默认配置
"""

DEFAULT_CONFIG = {
    'global': {
        'log_level': 'INFO',
        'encoding': 'utf-8',
        'temp_dir': './temp',
        'backup_enabled': True,
        'parallel_workers': 4,
        'progress_enabled': True,
        'color_output': True
    },
    'convert': {
        'default_output_format': 'csv',
        'csv_delimiter': ',',
        'csv_quote_char': '"',
        'excel_sheet_name': 'Sheet1',
        'sqlite_table_name': 'data',
        'json_orient': 'records',
        'xml_root_element': 'data',
        'overwrite': False,
        'validate_output': True,
        'generate_metadata': False
    },
    'merge': {
        'default_mode': 'append',
        'auto_map_fields': True,
        'preview_rows': 50,
        'use_arrow': False,
        'tolerant_mode': False,
        'ignore_case': False,
        'key_fields': []
    },
    'mmkv': {
        'include_metadata': True,
        'flatten_nested': True,
        'max_key_length': 1000,
        'key_column': 'key',
        'value_column': 'value'
    },
    'protobuf': {
        'parse_mode': 'auto',
        'max_messages': 1000,
        'include_raw_data': False,
        'flatten_nested': True,
        'output_format': 'json'
    },
    'formats': {
        'csv': {
            'enabled': True,
            'libraries': ['pandas', 'csv'],
            'extensions': ['.csv', '.tsv', '.txt']
        },
        'excel': {
            'enabled': True,
            'libraries': ['openpyxl', 'xlrd'],
            'extensions': ['.xlsx', '.xls']
        },
        'json': {
            'enabled': True,
            'libraries': ['json', 'orjson'],
            'extensions': ['.json', '.jsonl', '.ndjson']
        },
        'xml': {
            'enabled': True,
            'libraries': ['lxml', 'xml.etree'],
            'extensions': ['.xml']
        },
        'sqlite': {
            'enabled': True,
            'libraries': ['sqlite3'],
            'extensions': ['.sqlite', '.db', '.sqlite3']
        },
        'mmkv': {
            'enabled': True,
            'libraries': ['mmkv_handler'],
            'extensions': ['.mmkv']
        },
        'protobuf': {
            'enabled': True,
            'libraries': ['protobuf_handler'],
            'extensions': ['.pb', '.protobuf', '.proto']
        }
    }
}