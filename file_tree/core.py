import os
import sys
from dataclasses import dataclass, field


@dataclass
class TreeNode:
    """目录树中的一个节点"""

    name: str  # 文件/文件夹名
    is_dir: bool  # 是否为文件夹
    depth: int  # 深度（根为 0）


@dataclass
class TreeConfig:
    """目录树生成配置"""

    root_path: str  # 目标目录
    max_depth: int = 5  # 最大遍历深度（0 = 不限）
    ignore_hidden: bool = False  # 是否忽略隐藏文件/文件夹
    ignore_dirs: list[str] = field(default_factory=list)  # 要忽略的文件夹名列表
    ignore_exts: list[str] = field(default_factory=list)  # 要忽略的文件后缀（如 [".pyc", ".log"]）


# 树形符号常量
INDENT = "│   "
BRANCH = "├── "
LAST_BRANCH = "└── "


def _terminal_safe_text(text: str) -> str:
    """按当前终端编码转换文本，无法显示的字符使用 Unicode 转义。"""
    # 打包成 EXE 后 stdout 只剩 ASCII 编码名，此时按系统首选编码处理，
    # 中文 Windows 为 GBK；否则整棵字符树都会被转义成 \u251c 之类。
    encoding = getattr(sys.stdout, "encoding", None)
    if not encoding or encoding.lower().replace("-", "") == "ascii":
        encoding = "mbcs" if sys.platform == "win32" else "utf-8"
    try:
        return text.encode(encoding, errors="backslashreplace").decode(encoding)
    except LookupError:
        return text


class TreeGenerator:
    """目录树生成器"""

    def __init__(self, config: TreeConfig):
        self.config = config

    # ── 核心：唯一递归 ────────────────────────────────

    def build_tree(self) -> list[TreeNode]:
        """递归遍历目录，返回 TreeNode 列表（DFS 前序）"""
        config = self.config
        nodes = []
        root_name = os.path.basename(os.path.abspath(config.root_path))
        nodes.append(TreeNode(name=root_name, is_dir=True, depth=0))

        def walk(path: str, depth: int):
            if config.max_depth > 0 and depth > config.max_depth:   # 超过遍历深度
                return

            try:
                items = sorted(os.listdir(path))
            except OSError:
                if depth == 1:
                    raise
                return

            for item in items:
                if config.ignore_hidden and item.startswith("."):   # 忽略隐藏文件
                    continue

                full = os.path.join(path, item)
                is_dir = os.path.isdir(full)
                ignored_dir = is_dir and item in config.ignore_dirs

                if not is_dir and config.ignore_exts:   # 忽略指定后缀文件
                    ext = os.path.splitext(item)[1]
                    if ext in config.ignore_exts:
                        continue

                nodes.append(TreeNode(name=item, is_dir=is_dir, depth=depth))

                if is_dir and not ignored_dir:  # 被忽略的目录保留节点，但不递归子项
                    walk(full, depth + 1)

        walk(config.root_path, 1)
        return nodes    # list[TreeNode]

    # ── 渲染函数：TreeNode -> list[str] ──────────────

    @staticmethod
    def format_lines(nodes: list[TreeNode]) -> list[str]:
        """渲染为 ├── 字符树"""
        if not nodes:   # 防御性编程
            return []

        lines = [f"{nodes[0].name}/"]   # list[str]，根节点
        rest = nodes[1:]

        def has_later_sibling(index: int, depth: int) -> bool:
            """判断离开当前父节点范围前，后面是否还有同层兄弟节点。"""
            for later in rest[index + 1 :]:
                if later.depth < depth:
                    return False
                if later.depth == depth:
                    return True
            return False

        for i, node in enumerate(rest):
            # 前缀：每层判断是否有后续兄弟节点
            prefix = ""
            for d in range(1, node.depth):
                prefix += INDENT if has_later_sibling(i, d) else "    "

            # 连接符：判断是否为该层最后一个节点
            is_last = not has_later_sibling(i, node.depth)
            connector = LAST_BRANCH if is_last else BRANCH

            display = node.name + "/" if node.is_dir else node.name

            lines.append(prefix + connector + display)

        return lines

    @staticmethod
    def format_markdown(nodes: list[TreeNode]) -> list[str]:
        """渲染为 Markdown 缩进列表"""
        if not nodes:
            return []
        lines = [f"- {nodes[0].name}/"]
        for node in nodes[1:]:
            indent = "  " * node.depth
            display = node.name + "/" if node.is_dir else node.name
            lines.append(f"{indent}- {display}")
        return lines

    # ── 输出方法 ─────────────────────────────────────

    def build_lines(self) -> list[str]:
        """[兼容] 直接返回字符树行列表"""
        return self.format_lines(self.build_tree())

    def print_tree(self):
        """打印字符树到终端"""
        for line in self.build_lines():
            print(_terminal_safe_text(line))
        print("\n--- 目录树输出完成 ---")

    def export_txt(self, save_path: str):
        """导出字符树为 TXT"""
        lines = self.build_lines()
        lines.insert(0, f"来源：{self.config.root_path}")   # 加路径
        lines.insert(1, "")
        self._ensure_dir(save_path)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n[OK] TXT 已导出到：{save_path}")

    def export_markdown(self, save_path: str):
        """导出 Markdown（WPS 思维导图）"""
        nodes = self.build_tree()
        lines = self.format_markdown(nodes)
        self._ensure_dir(save_path)
        with open(save_path, "w", encoding="utf-8") as f:
            f.write("\n".join(lines))
        print(f"\n[OK] Markdown 已导出到：{save_path}")

    # ── 工具 ─────────────────────────────────────────

    @staticmethod
    def _ensure_dir(file_path: str):    # 保证输出路径存在
        save_dir = os.path.dirname(os.path.abspath(file_path))
        if save_dir:
            os.makedirs(save_dir, exist_ok=True)
