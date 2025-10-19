# dataconvert CLI

通用数据转换与处理命令行工具，面向日常数据清洗、格式互转、脚本生成与批量处理场景。

## 功能概述

- 格式转换：JSON、CSV、Excel（xlsx）、SQLite、XML、SQL 脚本、MMKV、Protobuf
- 模式支持：单文件、目录模式（递归/过滤/扁平）、批处理与多表合并/拆分
- 类型与编码：CSV 类型元数据（首行 `#dtypes:`）、自定义分隔符、引号、BOM、编码
- 结构处理：嵌套 JSON 扁平化（分隔符与最大深度可配）
- SQL 生成：方言（sqlite/mysql/postgres）、表名、DROP/CREATE/IF NOT EXISTS、批量写入
- 表格处理：Excel 多工作表、SQLite 多表读写与导出
- 二进制/协议：MMKV 转换与创建、Protobuf 基于 schema 的解码
- 信息与校验：文件结构、样本与统计、格式与内容校验

## 入口与构建

- 推荐入口（发布/测试）：`build_nuitka/cli_main.exe` 或 `build_nuitka/cli_main.dist/cli_main.exe`
- 开发入口（调试）：`python -m cli.main ...`
- 构建：`python scripts\build_nuitka.py --entry cli_main.py --output-dir build_nuitka`

## 快速开始

- CSV→Excel：
  - `cli_main.exe convert tests_e2e/input/data.csv tests_e2e/output/data.xlsx --to excel`
- Excel 全表→SQLite：
  - `cli_main.exe convert tests_e2e/tmp/sheets_input.xlsx tests_e2e/tmp/direct_book.sqlite --to sqlite --all-sheets`
- JSON→XML（自定义标签）：
  - `cli_main.exe convert tests_e2e/input/data.json tests_e2e/output/data.xml --to xml --xml-root-tag data --xml-row-tag item --xml-pretty`
- 目录模式（递归过滤并扁平输出）：
  - `cli_main.exe convert tests_e2e/dir_in tests_e2e/dir_out --to csv --dir-in --dir-out --recursive --filter "*.json" --flat-dir`

## 全局选项

- `--config PATH`：载入 YAML 配置（请优先使用 `--config`，避免 `-c` 触发编译器自执行检测）
- `--verbose`/`--quiet`：详细日志或静默模式
- `--log-level {DEBUG,INFO,WARNING,ERROR}`：日志级别（默认 `INFO`）
- `--no-color`：禁用彩色输出

## 命令与用法

### convert（格式转换）
- 位置参数：`input`、`output`
- 常用选项：
  - 格式：`--to {csv,excel,json,xml,sqlite,sql,mmkv}`、`--from {csv,excel,json,xml,sqlite,mmkv,protobuf}`、`--encoding`
  - CSV：`--delimiter`、`--quote-char`、`--types`、`--csv-bom`
  - Excel：`--sheet-name`、`--all-sheets`
  - XML：`--xml-root-tag`、`--xml-row-tag`、`--xml-pretty`、`--xml-use-lxml`
  - DB：`--table-name`、`--all-tables`
  - SQL 脚本：`--sql-dialect {sqlite,mysql,postgres}`、`--sql-table-name`、`--sql-create`、`--sql-drop`、`--sql-if-not-exists`、`--sql-batch-rows`
  - 处理：`--overwrite`、`--backup`、`--validate`、`--metadata`
  - 扁平化：`--flat-nested`、`--flat-sep`、`--flat-max-depth`
  - 目录/批量：`--dir-in`、`--dir-out`、`--recursive`、`--filter`、`--flat-dir`、`--parallel`、`--batch`、`--output-dir`
- 用例：
  - MMKV→JSON：`cli_main.exe convert tests_e2e/tmp/mmkv_debug.mmkv tests_e2e/tmp/mmkv_debug_out.json --from mmkv --to json`
  - Protobuf→JSON（需 schema 与 type）：`cli_main.exe convert tests_e2e/tmp/dummy.pb tests_e2e/tmp/out.json --from protobuf --schema-file tests_e2e/tmp/schema.desc --message-type pkg.Message`
  - 嵌套扁平化：`cli_main.exe convert tests_e2e/input/nested.json tests_e2e/output/nested_flat.csv --to csv --flat-nested --flat-sep '_' --flat-max-depth 3`
  - SQL 生成：`cli_main.exe convert tests_e2e/input/data.json tests_e2e/tmp/t_pg.sql --to sql --sql-dialect postgres --sql-table-name users --sql-create --sql-drop --sql-if-not-exists --sql-batch-rows 100`

### merge（数据合并）
- 位置参数：`input_files...`（≥2）、`output`
- 选项：`--mode {append,join,update,cross}`、`--key-fields`、`--mapping-file`、`--auto-map`、`--preview`/`--preview-rows`、`--arrow`、`--parallel`、`--tolerant`、`--ignore-case`
- 用例：`cli_main.exe merge tests_e2e/input/data.csv tests_e2e/input/data2.csv tests_e2e/output/merged.csv -m join -k id --preview -n 20`

### info（文件信息）
- 位置参数：`file_path`
- 选项：`--from {csv,excel,json,xml,sqlite,mmkv,protobuf}`、`--schema`、`--stats`、`--sample`、`--analyze`、`--export-info`、`--output-format {text,json,yaml}`
- 用例：
  - `cli_main.exe info tests_e2e/input/data.csv --schema --stats --sample 5 --analyze`
  - PB 元数据：`cli_main.exe info tests_e2e/tmp/dummy.pb --from protobuf`

### validate（格式与内容校验）
- 位置参数：`file_path`
- 选项：`--format {csv,json,xml,excel,sqlite}`、`--schema`、`--strict`、`--sample-only`、`--sample-size`、`--output`、`--format-output {text,json,xml}`
- 用例：`cli_main.exe validate tests_e2e/input/data.csv -f csv --strict --sample-only --sample-size 200 --output tests_e2e/tmp/validate_out_exe.json --format-output json`

## MMKV 与 Protobuf 指南

- 顶级子命令 `mmkv`、`proto` 的参数已在解析器中定义，但当前主入口以 `convert --from mmkv|protobuf` 的方式统一处理；推荐按上文 convert 用例使用。
- Protobuf 无 schema 的直接解析已禁用；请提供 `--schema-file` 与 `--message-type`。

## 配置文件

- 通过 `--config PATH` 载入 YAML 配置，示例键：
  - `delimiter`（全局 CSV 分隔符）、`csv.preserve_dtypes`（类型保留）、`excel.sheet_name`、`sql.dialect` 等。
- 示例：`cli_main.exe convert data.csv out.sql --to sql --config tests_e2e/config.yaml`

## 注意事项

- 统一使用编译后的入口；发布与测试建议固定使用 `build_nuitka/cli_main.exe`。
- 为规避编译器的自执行拦截，请使用 `--config` 而非 `-c`。
- 目录模式的 `--parallel` 当前退化为顺序处理；可在任务层自行并发调用。
- Protobuf 场景需提供完整 schema 与消息类型。

## 帮助与版本

- `cli_main.exe --version`、`cli_main.exe -h`、`cli_main.exe <command> -h`