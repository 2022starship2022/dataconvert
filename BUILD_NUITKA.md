# Nuitka 打包与 "hard import ctypes" 解决方案

本项目入口：`c:\nuitka_build\dataconvert\cli_main.py`

## 快速验证（30 秒）
1. 将 `python3xx.dll`（如 `python312.dll`）与 `_ctypes.pyd` 拷贝到生成的 `xxx.exe` 同目录后再运行。
   - 不再报错 → 属于运行时找不到 `_ctypes.pyd` 及依赖。
   - 仍报错 → 继续下述补救与打包方式。

## 推荐打包方式（PowerShell 脚本）
使用 `scripts/build_nuitka.ps1`，自动探测并显式打包 `_ctypes.pyd` 与 `libffi-*.dll`，同时强制包含 `google.protobuf` 与 `ctypes`：

```powershell
# 一键单文件（默认带控制台）
./scripts/build_nuitka.ps1 -Entry cli_main.py -OutputDir build_nuitka

# 先 standalone 验证，再改回 onefile
./scripts/build_nuitka.ps1 -Entry cli_main.py -OutputDir build_nuitka -Standalone

# 若已安装 VS2022，建议使用 MSVC 工具链以避开 MinGW 的 ctypes 问题
./scripts/build_nuitka.ps1 -Entry cli_main.py -OutputDir build_nuitka -UseMSVC
```

脚本内部等价于：
```powershell
python -m nuitka --onefile --windows-console-mode=force `
  --include-package=google.protobuf `
  --include-module=ctypes `
  --include-data-file="<Python DLLs>\_ctypes.pyd=_ctypes.pyd" `
  --include-data-file="<Python DLLs>\libffi-*.dll=libffi-*.dll" `
  --output-dir=build_nuitka cli_main.py
```
> `libffi` 版本：Python 3.11 常见 `libffi-8.dll`；Python 3.12 可能是 `libffi-7.dll`。脚本会自动搜寻匹配。

## 另一种一键模板（命令行）
如需手工执行而非脚本，可参考：
```powershell
python -m nuitka --onefile --windows-console-mode=force `
  --include-data-file="$(python -c "import sys,os;print(os.path.join(sys.base_prefix,'DLLs','_ctypes.pyd'))")=_ctypes.pyd" `
  --include-data-file="$(Get-ChildItem (python -c "import sys,os;print(os.path.join(sys.base_prefix,'DLLs'))") -Filter libffi-*.dll | Select -First 1).FullName=$(Get-ChildItem (python -c "import sys,os;print(os.path.join(sys.base_prefix,'DLLs'))") -Filter libffi-*.dll | Select -First 1).Name" `
  --include-package=google.protobuf `
  --include-module=ctypes `
  --output-dir=build_nuitka c:\nuitka_build\dataconvert\cli_main.py
```

## 遇到仍然 "IMPORT_HARD_CTYPES" 的补救
- 升级 Nuitka 至最新稳定版；若为 rc 版，建议改回稳定版。
- 先 `--standalone` 验证，再切换 `--onefile`。
- 已装 VS2022：加入 `--msvc=latest`。
- 仍失败：可回退到 `nuitka==0.6.18.4` 或去掉 `--follow-stdlib`（若你曾添加）。

## 成功指征
- 双击 exe 后不再出现 `IMPORT_HARD_CTYPES`，直接进入 CLI 帮助或业务日志。
- 若代码里用到 `ctypes.windll` 调用，也应能正常返回句柄。