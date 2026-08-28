# 当前设计

> 只记录已实现或已确定的行为；未完成事项见私有项目中的 `Todo.md`。

## 1. 定位与数据流

项目扫描指定目录，将文件和文件夹转换为通用节点列表，再渲染为终端字符树、TXT 或 WPS Markdown。GUI 是主要人工入口，CLI 兼顾交互操作与自动调用，专用版通过 JSON 固定重复任务。

```text
用户输入或 JSON 配置
    → TreeConfig
    → TreeGenerator.build_tree()
    → list[TreeNode]
    → format_*()
    → 预览、终端或文件
```

运行时仅使用 Python 标准库。

## 2. 核心模块 `file_tree/core.py`

### 2.1 数据结构

`TreeConfig` 统一保存扫描参数：

| 字段 | 类型 | 默认值 | 作用 |
|---|---|---:|---|
| `root_path` | `str` | 必填 | 目标目录 |
| `max_depth` | `int` | `5` | 最大深度，`0` 表示不限 |
| `ignore_hidden` | `bool` | `False` | 忽略名称以 `.` 开头的项目 |
| `ignore_dirs` | `list[str]` | 空列表 | 按名称精确匹配文件夹 |
| `ignore_exts` | `list[str]` | 空列表 | 按后缀精确匹配文件 |

`TreeNode` 保存节点名称、是否为文件夹和深度。`build_tree()` 返回深度优先前序的扁平节点列表，不与具体输出格式绑定。

### 2.2 遍历与忽略语义

- 根节点深度为 `0`；达到最大深度后停止继续递归。
- 命中 `ignore_dirs` 的文件夹仍输出真实目录节点，但不遍历子项。
- `ignore_hidden=True` 会完全排除名称以 `.` 开头的文件和文件夹。
- 后缀和文件夹名称当前按字符串精确比较。
- 读取子目录触发 `OSError` 时保留目录节点并静默跳过子项；根目录读取失败时由入口明确报错并停止。

### 2.3 渲染与输出

- `format_lines()` 生成 `├──` / `└──` 字符树。
- `format_markdown()` 生成适合 WPS 思维导图的缩进列表。
- `export_txt()` 以 UTF-8 导出并记录来源路径。
- `export_markdown()` 以 UTF-8 导出 WPS Markdown。
- 终端编码不支持某字符时，`print_tree()` 将其转为 `\U...` 形式；文件导出仍保留原字符。

## 3. CLI `file_tree/cli_simple.py`

### 3.1 模式切换

- 不传参数：进入原有交互循环。
- 传入任意参数：执行一次非交互任务。
- `--non-interactive`：在不传其他设置时，明确使用当前目录和默认值运行。

### 3.2 参数模式

支持可选目标目录、`--max-depth`、可重复的 `--ignore-dir` 与 `--ignore-ext`、`--ignore-hidden`、可重复的 `--format` 和 `--output-dir`。

- 省略目标目录时使用当前目录。
- 省略 `--format` 时只输出到终端。
- TXT 或 Markdown 格式必须同时提供 `--output-dir`。
- 导出文件使用目标文件夹名称，同名文件直接覆盖。
- 参数模式默认不启用任何忽略列表。
- 正常完成、运行失败、参数错误分别返回 `0`、`1`、`2`。

## 4. GUI `file_tree/gui.py`

GUI 使用 Tkinter，左侧为配置区，右侧为可滚动预览区。默认窗口为 `1100×700`，最小尺寸为 `900×650`。

- 支持目标目录、输出目录、深度、隐藏项、忽略文件夹和忽略后缀。
- TXT 和 WPS Markdown 默认不勾选；不选格式时只更新预览。
- 默认忽略文件夹包括 `.stfolder`、`.git`、Python 缓存与虚拟环境、`node_modules`、`build` 和 `dist`。
- 扫描和导出当前仍在 GUI 主线程执行。

## 5. 专用版 `file_tree/dedicated.py`

专用版不提供交互界面，从 `config/config.local.json` 读取配置，每次导出带时间戳的 TXT 和 WPS Markdown，然后在终端打印目录树。

- `config/config.example.json` 是可公开示例。
- `config/config.local.json` 保存本机路径和私有规则，已被 Git 忽略。
- 源码运行时从 `config/` 读取配置。
- 单文件 EXE 运行时优先使用 EXE 同目录的外部配置，否则使用打包时内嵌配置。
- 配置加载会校验 JSON 格式、字段类型、深度和目标目录。

## 6. 打包与公开边界

- `packaging/` 保存三个本机 PyInstaller spec，其中 GUI spec 包含当前本机 Tkinter 路径。
- 专用版 spec 将 `config/config.local.json` 嵌入单文件 EXE。
- `packaging/`、开发记录、私人笔记和辅助工具通过 `export-ignore` 或 `.gitignore` 排除，不进入公开副本。
- 当前 `dist/` 中的旧 EXE 早于最近的 GUI、忽略语义和 CLI 改动，发布前必须重新打包和验证。

## 7. 测试与已知限制

`tests/test_entry_modes.py` 和 `tests/test_core.py` 使用临时目录，当前共十四项测试且全部通过，覆盖：

- CLI 交互导出；
- `--non-interactive` 默认执行；
- CLI 多格式覆盖导出、后缀规范化和错误码；
- GUI 预览与 TXT/Markdown 导出；
- 专用版 JSON 配置与时间戳文件；
- 忽略文件夹保留节点但不输出子项；
- GBK 终端安全转义和 UTF-8 文件原字符保留；
- 最大深度边界仍保留边界层节点；
- 空目录仍作为目录节点输出；
- 子目录读取异常静默跳过、根目录读取异常明确失败；
- 交互式 CLI 和专用版能接收并报告根目录扫描错误；
- CLI、GUI 和专用版在同一配置下生成一致的完整目录树。

复杂兄弟节点的连接符缺陷已经修复：格式化器只在离开当前父节点范围前寻找同层兄弟，不再把其他父目录下的同深度节点误判为当前节点的兄弟。

`tests/run_cli.bat`、`run_gui.bat` 和 `run_dedicated.bat` 是 Windows 手动启动入口。它们使用相对路径进入项目根目录，运行后显示退出码并暂停，不代替自动化测试。

尚未系统覆盖更多特殊文件名。JSON 输出和忽略空文件夹也尚未实现。
