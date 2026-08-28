# 260523FileTree

一个轻量的 Python 目录树生成工具。它可以扫描指定文件夹，在终端中预览目录结构，并导出为 TXT 或适合 WPS 思维导图的 Markdown。

这个项目源于整理个人资料目录和快速查看代码项目结构的实际需求，提供 GUI、交互式 CLI、参数式 CLI 和固定配置专用版四种使用方式。

```text
sample_project/
├── docs/
│   └── design.md
├── src/
│   └── main.py
└── README.md
```

## 功能特点

- 自定义目标目录和最大遍历深度，`0` 表示不限深度。
- 按文件夹名称、文件后缀和点号开头的隐藏项进行过滤。
- 被忽略的文件夹保留目录节点，但不继续扫描其子项。
- 支持终端字符树、UTF-8 TXT 和 WPS Markdown 输出。
- GUI 支持目录选择、忽略列表编辑、结果预览和多格式导出。
- CLI 同时支持人工交互和适合脚本、自动化工具调用的参数模式。
- 专用版通过本机 JSON 配置重复扫描固定目录，私人路径无需写入源码。
- Windows 终端无法显示 Emoji 等字符时使用 Unicode 转义，导出文件仍保留原字符。
- 运行时仅依赖 Python 标准库。

## 运行环境

- Python 3.10 或更高版本。
- GUI 需要 Python 自带的 Tkinter。
- 当前源码验证环境：Python 3.13.9、Tkinter 8.6。

克隆或下载项目后，在项目根目录运行以下命令。项目不需要安装第三方运行依赖。

## 快速开始

### GUI

```powershell
python -m file_tree.gui
```

GUI 左侧用于设置目标路径、输出路径、遍历深度和忽略规则，右侧显示目录树预览。TXT 和 Markdown 默认不勾选；不选择格式时只更新预览，不写入文件。

### 交互式 CLI

```powershell
python -m file_tree.cli_simple
```

程序会依次询问目标目录、遍历深度、忽略文件夹和输出方式。

### 参数式 CLI

查看完整参数：

```powershell
python -m file_tree.cli_simple --help
```

使用当前目录和默认配置，只在终端输出：

```powershell
python -m file_tree.cli_simple --non-interactive
```

指定扫描规则，并同时导出 TXT 和 Markdown：

```powershell
python -m file_tree.cli_simple "D:\Project" `
  --max-depth 5 `
  --ignore-dir .git `
  --ignore-ext pyc `
  --format txt `
  --format md `
  --output-dir ".\output"
```

只要传入任意参数，CLI 就不会读取交互输入。参数模式默认不启用任何忽略规则，需要过滤时请显式传入。TXT 和 Markdown 使用目标文件夹名称命名，同名文件会被覆盖。

### 固定配置专用版

专用版适合反复扫描同一个目录：

1. 将 `config/config.example.json` 复制为 `config/config.local.json`。
2. 在本机配置中填写 `root_path`、`output_dir` 和扫描规则。
3. 运行：

```powershell
python -m file_tree.dedicated
```

`config/config.local.json` 已被 Git 忽略，可以保存本机路径和私人规则。专用版每次生成带时间戳的 TXT、Markdown，并在终端输出目录树。

配置示例：

```json
{
  "root_path": ".",
  "output_dir": "./output",
  "max_depth": 5,
  "ignore_hidden": false,
  "ignore_dirs": [".git", "__pycache__", "build", "dist"],
  "ignore_exts": [".pyc"]
}
```

## Windows 一键运行

`tests/` 提供三个可直接双击的辅助脚本：

- `run_cli.bat`：启动交互式 CLI。
- `run_gui.bat`：启动 GUI，关闭窗口后显示退出码。
- `run_dedicated.bat`：使用本机 JSON 配置运行专用版。

这些脚本使用相对路径进入项目根目录，不包含开发者机器的绝对路径。

## 项目结构

```text
260523FileTree/
├── config/
│   └── config.example.json     # 可公开的专用版配置示例
├── docs/
│   └── Designments.md          # 当前设计、行为和已知限制
├── file_tree/
│   ├── __init__.py
│   ├── core.py                 # 扫描、节点与输出渲染
│   ├── cli_simple.py           # 交互式和参数式 CLI
│   ├── gui.py                  # Tkinter GUI
│   └── dedicated.py            # JSON 固定配置入口
├── tests/
│   ├── test_core.py
│   ├── test_entry_modes.py
│   └── run_*.bat
├── LICENSE
└── README.md
```

核心数据流如下：

```text
用户输入或 JSON 配置
    → TreeConfig
    → TreeGenerator.build_tree()
    → list[TreeNode]
    → 字符树或 Markdown 渲染
    → 终端、预览或文件
```

详细实现行为见 [`docs/Designments.md`](docs/Designments.md)。

## 测试

在项目根目录运行：

```powershell
python -m unittest discover -s tests -v
```

测试覆盖核心遍历边界、字符树连接符、交互式与参数式 CLI、GUI 预览和导出、专用版 JSON 配置、错误码、忽略目录语义及 Windows 终端字符兼容。

## 当前限制

- 扫描与导出仍在 GUI 主线程执行，扫描大型目录时界面可能暂时无响应。
- 文件夹名称和文件后缀采用精确匹配，当前不支持通配符或正则表达式。
- 子目录读取失败时会保留目录节点并跳过其内容，不会在结果中附加错误说明。
- TXT 会记录被扫描目录的来源路径；分享生成文件前请检查是否包含个人路径。
- 暂不支持 JSON 输出和“忽略空文件夹”。

## 交流与反馈

这是一个由实际使用需求逐步迭代的小型 DIY 项目。如果你发现问题、有新的使用场景，或者对目录过滤和输出格式有改进建议，欢迎通过 GitHub Issues 交流。

## License

本项目采用 [MIT License](LICENSE)。
