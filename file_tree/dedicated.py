"""dedicated — 使用 JSON 配置的非交互式目录树生成器。"""

import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any

from file_tree.core import TreeConfig, TreeGenerator


CONFIG_NAME = "config.local.json"
CONFIG_DIR_NAME = "config"


class ConfigError(ValueError):
    """配置文件缺失或内容无效。"""


def _source_root() -> Path:
    return Path(__file__).resolve().parent.parent


def _config_candidates() -> list[Path]:
    """按优先级返回外部配置和单文件 EXE 内嵌配置。"""
    if getattr(sys, "frozen", False):
        executable_dir = Path(sys.executable).resolve().parent
        bundled_dir = Path(getattr(sys, "_MEIPASS", executable_dir))
        return [executable_dir / CONFIG_NAME, bundled_dir / CONFIG_NAME]
    return [_source_root() / CONFIG_DIR_NAME / CONFIG_NAME]


def find_config_path() -> Path:
    for path in _config_candidates():
        if path.is_file():
            return path
    searched = "\n".join(f"  - {path}" for path in _config_candidates())
    raise ConfigError(
        f"未找到 {CONFIG_NAME}。\n"
        "请复制 config/config.example.json 为 config/config.local.json，"
        "并填写本机配置。\n"
        f"已检查：\n{searched}"
    )


def _require_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ConfigError(f"配置项 {key!r} 必须是非空字符串。")
    return value


def _string_list(data: dict[str, Any], key: str) -> list[str]:
    value = data.get(key, [])
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ConfigError(f"配置项 {key!r} 必须是字符串数组。")
    return value


def load_config(path: Path | None = None) -> tuple[TreeConfig, Path]:
    """读取并校验 JSON，返回核心扫描配置和输出目录。"""
    config_path = path or find_config_path()
    try:
        with config_path.open("r", encoding="utf-8") as file:
            data = json.load(file)
    except json.JSONDecodeError as exc:
        raise ConfigError(
            f"配置文件不是有效 JSON：第 {exc.lineno} 行，第 {exc.colno} 列。"
        ) from exc
    except OSError as exc:
        raise ConfigError(f"无法读取配置文件：{exc}") from exc

    if not isinstance(data, dict):
        raise ConfigError("配置文件顶层必须是 JSON 对象。")

    root_path = Path(_require_string(data, "root_path")).expanduser()
    output_dir = Path(_require_string(data, "output_dir")).expanduser()

    max_depth = data.get("max_depth", 5)
    if isinstance(max_depth, bool) or not isinstance(max_depth, int) or max_depth < 0:
        raise ConfigError("配置项 'max_depth' 必须是非负整数。")

    ignore_hidden = data.get("ignore_hidden", False)
    if not isinstance(ignore_hidden, bool):
        raise ConfigError("配置项 'ignore_hidden' 必须是布尔值。")

    if not root_path.is_absolute():
        root_path = (config_path.parent / root_path).resolve()
    if not output_dir.is_absolute():
        output_dir = (config_path.parent / output_dir).resolve()

    if not root_path.is_dir():
        raise ConfigError(f"目标目录不存在或不是文件夹：{root_path}")

    config = TreeConfig(
        root_path=str(root_path),
        max_depth=max_depth,
        ignore_hidden=ignore_hidden,
        ignore_dirs=_string_list(data, "ignore_dirs"),
        ignore_exts=_string_list(data, "ignore_exts"),
    )
    return config, output_dir


def main() -> int:
    try:
        config, output_dir = load_config()
        output_dir.mkdir(parents=True, exist_ok=True)
    except (ConfigError, OSError) as exc:
        print(f"[ERROR] {exc}")
        return 1

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    generator = TreeGenerator(config)

    try:
        txt_path = output_dir / f"tree_{timestamp}.txt"
        generator.export_txt(str(txt_path))

        md_path = output_dir / f"tree_{timestamp}.md"
        generator.export_markdown(str(md_path))

        print("\n===== 终端输出 =====")
        generator.print_tree()
    except OSError as exc:
        print(f"[ERROR] 执行失败：{exc}")
        return 1

    print(f"\n全部文件已保存至：{output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
