# E2E 测试说明

本项目的端到端（E2E）测试覆盖常见数据转换、合并、信息和校验场景，统一使用编译产物 `build_nuitka/cli_main.exe`（或 `build_nuitka/cli_main.dist/cli_main.exe`）作为 CLI 入口，确保与实际发布版本一致。

## 总览

- 所有 E2E 测试固定使用编译后的 `cli_main.exe`，不再回退到 `.venv/Scripts/python.exe` 或 `python -m`。
- 配置参数统一为 `--config <yaml>`，不使用 `-c`（避免 Nuitka 对 `-c` 的自执行检测）。
- 测试工作目录为项目根目录，输入样例位于 `tests_e2e/input`，运行时产物位于 `tests_e2e/tmp`。

## 运行环境

- 项目根目录：`c:\nuitka_build\dataconvert`
- CLI 入口：`build_nuitka/cli_main.exe` 或 `build_nuitka/cli_main.dist/cli_main.exe`
- 先决条件：需先构建 CLI 可执行文件，否则所有 E2E 测试会在 `setUp` 阶段失败。

## 快速开始

1. 构建编译产物（示例）：
   - `python scripts/build_nuitka.py`
   - 构建成功后应生成 `build_nuitka/cli_main.exe` 或 `build_nuitka/cli_main.dist/cli_main.exe`
2. 运行全部测试：
   - `pytest -q tests_e2e`
3. 运行单个文件（示例）：
   - SQL 方言与脚本：`pytest -q tests_e2e/test_sql_dialect_drop.py`
   - CSV 类型与引号：`pytest -q tests_e2e/test_csv_types_quotechar.py`

## 命令与参数覆盖

- 覆盖的命令：`convert`、`merge`、`info`、`validate`
- 常用参数：
  - 配置：`--config <yaml>`
  - 扁平化：`--flat-nested`、`--flat-sep`
  - SQL：`--sql-dialect`、`--sql-table-name`、`--sql-drop`、`--sql-create`、`--sql-if-not-exists`、`--sql-batch-rows`
  - CSV：`--quote-char`、`--csv-bom`（类型元数据通过配置启用 `csv.preserve_dtypes`）
  - Excel/SQLite：`--all-tables`、`--table-name`
  - XML：`--xml-root-tag`、`--xml-row-tag`、`--xml-pretty`

## 场景与文件

- 格式与类型
  - `tests_e2e/test_csv_types_quotechar.py`：JSON→CSV→JSON 回转，验证 `$` 引号与类型保持（配置启用 preserve_dtypes）
  - `tests_e2e/test_quotechar.py`：自定义引号字符的写入与解析
  - `tests_e2e/test_preserve_dtypes.py`：CSV 首行 `#dtypes:` 类型元数据的启用与禁用
  - `tests_e2e/test_encoding.py`：CSV BOM 与编码处理
- SQL 脚本与扁平化
  - `tests_e2e/test_sql_dialect_drop.py`：SQLite/MySQL/Postgres 方言；`DROP`/`CREATE`/`IF NOT EXISTS`；类型映射与布尔值写出
  - `tests_e2e/test_flatten.py`：嵌套 JSON 扁平化字段写出（含分隔符控制）
  - `tests_e2e/test_sql_xml_sqlite.py`：嵌套 JSON → SQL 脚本；CSV ↔ SQLite；CSV → XML（根/行标签、美化）
- 表格与多表
  - `tests_e2e/test_excel_sheets.py`：Excel 多工作表读写与一致性
  - `tests_e2e/test_multitable_split.py`：多表拆分输出
  - `tests_e2e/test_sqlite_to_excel.py`：SQLite → Excel（`--all-tables`）
- 二进制/协议
  - `tests_e2e/test_proto_decode.py`：Protobuf 解码与数据验证
  - `tests_e2e/test_mmkv.py`：MMKV 调试与数据解析
- 批量与目录模式
  - `tests_e2e/test_batch_mode.py`：批处理模式的执行与结果校验
  - `tests_e2e/test_directory_mode.py`：目录模式（递归/非递归、扁平输出、多文件类型）
- 信息与校验
  - `tests_e2e/test_info.py`：文件信息提取（字段、行数、示例数据）
  - `tests_e2e/test_info.py`：文件有效性校验与日志记录

## 常见问题与约定

- 必须使用 `--config` 传递配置；不要使用 `-c`。
- 若未构建 `cli_main.exe`，测试会在 `setUp` 阶段直接失败并提示先构建。
- 新增测试建议：
  - 始终以编译后的 exe 为入口；禁止 `python -m cli.main` 或 `.venv/Scripts/python.exe` 回退。
  - 将工作目录设为项目根目录，确保相对路径解析一致。
  - 断言失败时打印 `STDOUT`/`STDERR` 便于定位问题。

## 近期状态

- 最近一次执行：`pytest -q tests_e2e` 全部通过。
- `tests_e2e` 中所有 `setUp`/`run_cli*` 方法均已统一使用编译产物与 `--config`。