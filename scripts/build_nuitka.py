import os
import sys
import subprocess
from pathlib import Path
from typing import List, Optional

# 简单的 Python 版 Nuitka 构建脚本（Windows）
# - 自动检测 DLLs 目录并显式打包 _ctypes.pyd 与 libffi-*.dll
# - 强制包含 google.protobuf 与 ctypes 模块
# - 支持 onefile 与 standalone 模式、MSVC 工具链选择、控制台模式


def find_dlls_dir() -> Optional[Path]:
    base = Path(sys.base_prefix)
    dlls = base / "DLLs"
    return dlls if dlls.exists() else None


def find_ctypes_pyd(dlls_dir: Path) -> Optional[Path]:
    p = dlls_dir / "_ctypes.pyd"
    return p if p.exists() else None


def find_libffi(dlls_dir: Path) -> Optional[Path]:
    # 尝试 libffi-*.dll 与 libffi.dll
    for pattern in ("libffi-*.dll", "libffi.dll"):
        matches = list(dlls_dir.glob(pattern))
        if matches:
            return matches[0]
    return None


def build_args(
    entry: Path,
    output_dir: Path,
    standalone: bool,
    use_msvc: bool,
    force_console: bool,
    include_ctypes_data: bool = True,
    include_protobuf: bool = True,
    extra_args: Optional[List[str]] = None,
) -> List[str]:
    args: List[str] = [sys.executable, "-m", "nuitka"]

    # 模式
    args.append("--standalone" if standalone else "--onefile")

    # 控制台模式
    if force_console:
        args.append("--windows-console-mode=force")

    # 包含模块
    if include_protobuf:
        args.append("--include-package=google.protobuf")
    args.append("--include-module=ctypes")
    args.append("--noinclude-unittest-mode=nofollow")
    if sys.version_info >= (3, 13):
        args.append("--msvc=latest")

    # DLLs 显式打包
    dlls_dir = find_dlls_dir()
    if dlls_dir and include_ctypes_data:
        # 仅显式包含 libffi，_ctypes.pyd 由 Nuitka 自动收集为扩展模块，避免与数据文件冲突
        libffi = find_libffi(dlls_dir)
        if libffi:
            args.append(f"--include-data-file={libffi}={libffi.name}")

    # 输出目录
    args.append(f"--output-dir={output_dir}")

    # 工具链
    if use_msvc:
        args.append("--msvc=latest")

    # 额外参数
    if extra_args:
        args.extend(extra_args)

    # 入口
    args.append(str(entry))
    return args


def main(argv: List[str]) -> int:
    import argparse

    parser = argparse.ArgumentParser(description="Nuitka build helper (Python)")
    parser.add_argument("--entry", "-e", default="cli_main.py", help="入口脚本路径")
    parser.add_argument("--output-dir", "-o", default="build_nuitka", help="输出目录")
    parser.add_argument("--standalone", action="store_true", help="使用 standalone 模式（默认 onefile）")
    parser.add_argument("--msvc", action="store_true", help="使用 MSVC 最新工具链")
    console_group = parser.add_mutually_exclusive_group()
    console_group.add_argument("--force-console", action="store_true", help="强制控制台模式（默认）")
    console_group.add_argument("--no-console", action="store_true", help="禁用控制台模式")
    parser.add_argument("--no-protobuf", action="store_true", help="不强制包含 google.protobuf")
    parser.add_argument("--no-ctypes-data", action="store_true", help="不显式打包 _ctypes.pyd 与 libffi")
    parser.add_argument("--", dest="extra", nargs=argparse.REMAINDER, help="传递给 Nuitka 的额外参数")

    args = parser.parse_args(argv)

    # 路径与模式解析
    cwd = Path.cwd()
    entry_path = Path(args.entry)
    if not entry_path.is_absolute():
        entry_path = (cwd / entry_path).resolve()

    output_dir = Path(args.output_dir).resolve()

    # 控制台默认 True，除非用户显式禁用
    force_console = True
    if args.no_console:
        force_console = False
    elif args.force_console:
        force_console = True

    # 信息输出
    print(f"Python: {sys.version}")
    print(f"Executable: {sys.executable}")
    try:
        import nuitka  # type: ignore
        print(f"Nuitka: {getattr(nuitka, '__version__', 'unknown')}")
    except Exception as e:
        print("Nuitka 未安装或导入失败: ", e)
        print("请先执行: uv sync --extra build 或 pip install nuitka")
        return 1

    dlls_dir = find_dlls_dir()
    print(f"DLLs dir: {dlls_dir if dlls_dir else '未找到'}")

    # 构建参数
    build_cmd = build_args(
        entry=entry_path,
        output_dir=output_dir,
        standalone=args.standalone,
        use_msvc=args.msvc,
        force_console=force_console,
        include_ctypes_data=not args.no_ctypes_data,
        include_protobuf=not args.no_protobuf,
        extra_args=args.extra,
    )

    print("Command:")
    print(" "+" ".join(str(p) for p in build_cmd))

    # 执行构建
    proc = subprocess.run(build_cmd)
    if proc.returncode != 0:
        print(f"Nuitka 构建失败，退出码: {proc.returncode}")
        return proc.returncode

    print("构建完成")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))