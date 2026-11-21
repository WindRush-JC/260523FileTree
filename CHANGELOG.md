# 版本记录

本项目从 V2.1.0 起按语义化版本记录变更。更早的版本只保留阶段概述，详细过程见项目内部开发记录。

## [未发布]

- 暂无。

## [v2.1.0] - 2026-08-28

### 新增

- CLI 参数模式：支持可选的 `--non-interactive` 显式无值开关，适合脚本和自动化调用。
- `tests/test_entry_modes.py`：覆盖交互式 CLI、参数式 CLI、GUI 和专用版四个入口。
- 三个 Windows 一键启动脚本 `tests/run_cli.bat`、`run_gui.bat`、`run_dedicated.bat`。

### 修复

- 修复复杂兄弟节点下 `├──`、`└──` 和前置 `│` 的连接符判断错误。
- 目录读取异常策略统一：子目录读取失败时保留节点并跳过子项，根目录读取失败时由入口明确报错并返回非零退出码。
- GBK 终端无法打印 Emoji 等字符的问题：终端输出改用 `\\U...` 转义，UTF-8 导出的文件仍保留原字符。

### 改进

- GUI 从上下布局改为左右布局，默认窗口调整为 `1100×700`，最小尺寸 `900×650`。
- 忽略文件夹语义统一为“保留目录节点但不展开子项”，GUI 和专用版默认忽略列表加入 `.stfolder`。
- 单点云以外的三个入口共用相同的扫描边界行为，并新增了一致性测试。

## [v2.0.0] - 2026-08-27

### 新增

- CLI 增加 `--max-depth`、`--ignore-dir`、`--ignore-ext`、`--ignore-hidden`、`--format`、`--output-dir` 参数。
- 专用版支持 `config/config.example.json` 示例配置和 `config/config.local.json` 本机配置。
- 三种使用方式：交互式 CLI、Tkinter GUI 和固定配置专用版。

### 变更

- 重构项目结构：扫描参数集中到 `TreeConfig`，目录节点集中到 `TreeNode`，遍历与渲染集中到 `core.py`。
- 移除未经实际导入验证的幕布式 Markdown 输出，只保留 TXT 和 WPS Markdown。

## [v1.0.0] - 2026-07-11

### 新增

- 首个可用版本：扫描指定目录，在终端输出字符树，支持导出 TXT 和 Markdown。
