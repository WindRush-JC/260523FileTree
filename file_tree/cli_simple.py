"""cli_simple — 兼容交互操作和参数调用的目录树生成器。"""

import argparse
import os
import sys
from pathlib import Path

from file_tree.core import TreeConfig, TreeGenerator


OUTPUT_FORMATS = ("terminal", "txt", "md")


def _non_negative_int(value: str) -> int:
    """argparse 类型：只接受非负整数。"""
    try:
        number = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("必须是整数") from exc
    if number < 0:
        raise argparse.ArgumentTypeError("必须是非负整数")
    return number


def _normalize_extension(value: str) -> str:
    """允许 `.pyc` 和 `pyc` 两种后缀写法。"""
    extension = value.strip()
    if not extension:
        raise argparse.ArgumentTypeError("忽略后缀不能为空")
    return extension if extension.startswith(".") else f".{extension}"


def build_parser() -> argparse.ArgumentParser:
    """构建适合脚本、自动化和 AI 调用的参数解析器。"""
    parser = argparse.ArgumentParser(
        prog="file-tree",
        description="扫描目录并输出目录树。不传参数时进入交互模式。",
        allow_abbrev=False,
    )
    parser.add_argument(
        "target",
        nargs="?",
        help="目标目录；参数模式下省略时使用当前目录",
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="不进入交互提问；适合只使用默认值的自动调用",
    )
    parser.add_argument(
        "--max-depth",
        type=_non_negative_int,
        default=5,
        metavar="N",
        help="最大遍历深度（默认 5，0 表示不限）",
    )
    parser.add_argument(
        "--ignore-dir",
        action="append",
        default=[],
        metavar="NAME",
        help="按名称忽略文件夹子项；可重复使用",
    )
    parser.add_argument(
        "--ignore-ext",
        action="append",
        default=[],
        type=_normalize_extension,
        metavar="EXT",
        help="忽略文件后缀；可重复使用，`.pyc` 和 `pyc` 均可",
    )
    parser.add_argument(
        "--ignore-hidden",
        action="store_true",
        help="忽略名称以 `.` 开头的项目",
    )
    parser.add_argument(
        "--format",
        action="append",
        choices=OUTPUT_FORMATS,
        dest="formats",
        metavar="FORMAT",
        help="输出格式：terminal、txt 或 md；可重复使用",
    )
    parser.add_argument(
        "--output-dir",
        metavar="DIR",
        help="TXT/Markdown 输出目录；选择文件格式时必填",
    )
    return parser


def get_user_input() -> TreeConfig:
    """获取用户输入，返回 TreeConfig
    目标目录、最大遍历深度、忽略文件夹列表"""

    # ── 1. 路径 ──
    while True:
        raw = input("请输入目标文件夹路径（回车 = 当前目录）: ").strip()
        path = raw if raw else os.getcwd()
        if os.path.isdir(path):
            break
        print("路径无效或不是文件夹，请重新输入。")

    # ── 2. 深度 ──
    while True:
        raw = input("请输入最大遍历深度（回车 = 5，输入 0 = 不限）: ").strip()
        if raw == "":
            depth = 5
            break
        try:
            depth = int(raw)
            if depth >= 0:
                break
        except ValueError:
            pass
        print("请输入非负整数。")

    # ── 3. 忽略文件夹 ──
    raw = input("请输入要忽略的文件夹名（多个用逗号隔开，回车跳过）: ").strip()
    ignore_dirs = [d.strip() for d in raw.split(",") if d.strip()]

    return TreeConfig(
        root_path=path,
        max_depth=depth,
        ignore_dirs=ignore_dirs,
    )


def choose_export(generator: TreeGenerator):
    """选择输出方式并执行"""

    print("\n输出方式：")
    print("  0 = 仅打印到终端")
    print("  1 = 导出 TXT")
    print("  2 = 导出 Markdown（WPS 思维导图）")

    while True:
        raw = input("请选择（回车默认 0）: ").strip()
        choice = raw if raw else "0"
        if choice in {"0", "1", "2"}:
            break
        print("无效选择，请输入 0、1 或 2。")

    if choice == "0":
        generator.print_tree()
        return

    # 导出格式 -> 文件后缀
    folder_name = os.path.basename(os.path.abspath(generator.config.root_path))
    ext_map = {"1": ".txt", "2": ".md"}
    name_map = {"1": f"{folder_name}.txt", "2": f"{folder_name}.md"}
    default_name = name_map[choice]
    suffix = ext_map[choice]

    # 打印（导出前让用户看到结果）
    generator.print_tree()

    while True:
        save_input = input(f"\n请输入导出保存路径（回车 = {default_name}）: ").strip()
        save_path = (
            os.path.join(os.getcwd(), default_name)
            if not save_input
            else os.path.abspath(save_input)
        )
        if not save_path.lower().endswith(suffix):
            save_path += suffix

        try:
            if choice == "1":
                generator.export_txt(save_path)
            else:
                generator.export_markdown(save_path)
            break
        except (PermissionError, OSError) as e:
            print(f"无法保存文件：{e}，请重新输入。")


def run_interactive() -> int:
    """保留原有交互流程。"""
    print("===== 文件树生成工具（简单版）=====")
    while True:
        config = get_user_input()
        generator = TreeGenerator(config)
        try:
            choose_export(generator)
        except OSError as exc:
            print(f"[ERROR] 执行失败：{exc}", file=sys.stderr)
            return 1

        again = input("\n是否继续？(Y/n，回车): ").strip().lower()
        if again not in {"", "y", "yes"}:
            print("程序已退出。")
            return 0
        print()


def run_with_args(argv: list[str]) -> int:
    """使用参数执行一次任务，全程不读取交互输入。"""
    parser = build_parser()
    args = parser.parse_args(argv)

    target_path = (
        Path(args.target).expanduser().resolve()
        if args.target
        else Path.cwd().resolve()
    )
    if not target_path.is_dir():
        print(f"[ERROR] 目标路径不存在或不是文件夹：{target_path}", file=sys.stderr)
        return 1

    formats = list(dict.fromkeys(args.formats or ["terminal"]))
    file_formats = [item for item in formats if item in {"txt", "md"}]
    if file_formats and not args.output_dir:
        parser.error("选择 txt 或 md 时必须同时提供 --output-dir")

    output_dir = Path(args.output_dir).expanduser().resolve() if args.output_dir else None
    try:
        if output_dir is not None:
            output_dir.mkdir(parents=True, exist_ok=True)

        config = TreeConfig(
            root_path=str(target_path),
            max_depth=args.max_depth,
            ignore_hidden=args.ignore_hidden,
            ignore_dirs=args.ignore_dir,
            ignore_exts=args.ignore_ext,
        )
        generator = TreeGenerator(config)
        folder_name = target_path.name or target_path.drive.rstrip(":\\/") or "root"

        for output_format in formats:
            if output_format == "terminal":
                generator.print_tree()
            elif output_format in {"txt", "md"}:
                if output_dir is None:
                    parser.error("选择 txt 或 md 时必须同时提供 --output-dir")

                if output_format == "txt":
                    generator.export_txt(str(output_dir / f"{folder_name}.txt"))
                else:
                    generator.export_markdown(str(output_dir / f"{folder_name}.md"))
    except OSError as exc:
        print(f"[ERROR] 执行失败：{exc}", file=sys.stderr)
        return 1

    return 0


def main(argv: list[str] | None = None) -> int:
    """无参数时交互运行，有参数时执行单次自动任务。"""
    arguments = sys.argv[1:] if argv is None else argv
    if not arguments:
        return run_interactive()
    return run_with_args(arguments)


if __name__ == "__main__":
    raise SystemExit(main())
