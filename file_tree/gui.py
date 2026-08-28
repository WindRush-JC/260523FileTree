"""gui.py — 完整功能 GUI 版

功能：路径浏览、忽略文件夹/后缀（可编辑删除）、多选输出格式、预览、一键运行
"""

import os
import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from file_tree.core import TreeConfig, TreeGenerator


WINDOW_SIZE = "1100x700"
MIN_WINDOW_SIZE = (900, 650)
CONFIG_PANEL_MIN_WIDTH = 380


class IgnoreListFrame(ttk.LabelFrame):
    """忽略列表组件（文件夹/后缀复用）"""

    def __init__(self, master, title="", **kwargs):
        super().__init__(master, text=title, **kwargs)
        self.items: list[str] = []

        # 输入行
        input_frame = ttk.Frame(self)
        input_frame.pack(fill="x", padx=5, pady=(5, 2))
        self.entry = ttk.Entry(input_frame)
        self.entry.pack(side="left", fill="x", expand=True, padx=(0, 5))
        ttk.Button(input_frame, text="添加", command=self._add).pack(side="right")

        # 列表
        list_frame = ttk.Frame(self)
        list_frame.pack(fill="both", expand=True, padx=5, pady=2)
        scrollbar = ttk.Scrollbar(list_frame, orient="vertical")
        self.listbox = tk.Listbox(
            list_frame, height=5,
            yscrollcommand=scrollbar.set,
            selectmode="single",
        )
        scrollbar.config(command=self.listbox.yview)
        scrollbar.pack(side="right", fill="y")
        self.listbox.pack(side="left", fill="both", expand=True)

        # 按钮行
        btn_frame = ttk.Frame(self)
        btn_frame.pack(fill="x", padx=5, pady=(0, 5))
        ttk.Button(btn_frame, text="替换", command=self._edit).pack(side="left", padx=(0, 5))
        ttk.Button(btn_frame, text="删除", command=self._delete).pack(side="left")

    def _add(self):
        val = self.entry.get().strip()
        if not val:
            return
        self.items.append(val)
        self.listbox.insert(tk.END, val)
        self.entry.delete(0, tk.END)

    def _edit(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        new_val = self.entry.get().strip()
        if not new_val:
            return
        self.items[idx] = new_val
        self.listbox.delete(idx)
        self.listbox.insert(idx, new_val)
        self.entry.delete(0, tk.END)

    def _delete(self):
        sel = self.listbox.curselection()
        if not sel:
            return
        idx = sel[0]
        self.items.pop(idx)
        self.listbox.delete(idx)

    def get_items(self) -> list[str]:
        return list(self.items)

    def set_items(self, items: list[str]):
        self.items.clear()
        self.listbox.delete(0, tk.END)
        for item in items:
            self.items.append(item)
            self.listbox.insert(tk.END, item)


class Application(ttk.Frame):
    """主应用"""

    def __init__(self, master):
        super().__init__(master)
        self.columnconfigure(0, minsize=CONFIG_PANEL_MIN_WIDTH)
        self.columnconfigure(1, weight=1)
        self.rowconfigure(0, weight=1)
        self._build_ui()

    def _build_ui(self):
        self.config_panel = ttk.Frame(self, padding=(5, 5))
        self.config_panel.grid(row=0, column=0, sticky="nsew", padx=(5, 2), pady=5)
        self.config_panel.columnconfigure(1, weight=1)
        self.config_panel.rowconfigure(3, weight=1)

        self.preview_panel = ttk.LabelFrame(self, text="预览")
        self.preview_panel.grid(row=0, column=1, sticky="nsew", padx=(2, 5), pady=5)
        self.preview_panel.columnconfigure(0, weight=1)
        self.preview_panel.rowconfigure(0, weight=1)

        self._build_path_section()
        self._build_ignore_section()
        self._build_output_section()
        self._build_preview()
        self._build_run_button()

    def _build_path_section(self):
        # 目标路径
        ttk.Label(self.config_panel, text="目标路径:").grid(
            row=0, column=0, sticky="w", padx=5, pady=3
        )
        self.target_entry = ttk.Entry(self.config_panel)
        self.target_entry.grid(row=0, column=1, sticky="ew", padx=5, pady=3)
        ttk.Button(
            self.config_panel,
            text="浏览",
            command=lambda: self._browse(self.target_entry),
        ).grid(
            row=0, column=2, padx=(0, 5), pady=3)

        # 输出路径
        ttk.Label(self.config_panel, text="输出路径:").grid(
            row=1, column=0, sticky="w", padx=5, pady=3
        )
        self.output_entry = ttk.Entry(self.config_panel)
        self.output_entry.grid(row=1, column=1, sticky="ew", padx=5, pady=3)
        ttk.Button(
            self.config_panel,
            text="浏览",
            command=lambda: self._browse(self.output_entry),
        ).grid(
            row=1, column=2, padx=(0, 5), pady=3)

        # 遍历深度 + 忽略隐藏
        depth_frame = ttk.Frame(self.config_panel)
        depth_frame.grid(row=2, column=0, columnspan=3, sticky="w", padx=5, pady=3)
        ttk.Label(depth_frame, text="遍历深度:").pack(side="left")
        self.depth_entry = ttk.Entry(depth_frame, width=8)
        self.depth_entry.insert(0, "5")
        self.depth_entry.pack(side="left", padx=(5, 25))
        self.hidden_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(depth_frame, text="忽略隐藏文件", variable=self.hidden_var).pack(side="left")

    def _build_ignore_section(self):
        ignore_frame = ttk.Frame(self.config_panel)
        ignore_frame.grid(row=3, column=0, columnspan=3, sticky="nsew", padx=5, pady=5)
        ignore_frame.columnconfigure(0, weight=1)
        ignore_frame.rowconfigure(0, weight=1)
        ignore_frame.rowconfigure(1, weight=1)

        self.ignore_dirs = IgnoreListFrame(ignore_frame, title="忽略文件夹")
        self.ignore_dirs.grid(row=0, column=0, sticky="nsew", pady=(0, 3))
        self.ignore_dirs.set_items([
            ".stfolder",
            ".git",
            "__pycache__",
            ".pytest_cache",
            ".mypy_cache",
            ".ruff_cache",
            ".venv",
            "venv",
            "node_modules",
            "build",
            "dist",
        ])

        self.ignore_exts = IgnoreListFrame(ignore_frame, title="忽略后缀")
        self.ignore_exts.grid(row=1, column=0, sticky="nsew", pady=(3, 0))

    def _build_output_section(self):
        out_frame = ttk.LabelFrame(self.config_panel, text="输出格式")
        out_frame.grid(row=4, column=0, columnspan=3, sticky="ew", padx=5, pady=5)

        self.txt_var = tk.BooleanVar(value=False)
        self.md_var = tk.BooleanVar(value=False)

        ttk.Checkbutton(out_frame, text="TXT", variable=self.txt_var).pack(side="left", padx=15, pady=5)
        ttk.Checkbutton(out_frame, text="MD (WPS)", variable=self.md_var).pack(side="left", padx=15, pady=5)

    def _build_preview(self):
        self.preview_text = tk.Text(
            self.preview_panel,
            wrap="none",
            state="disabled",
            font=("Consolas", 10),
        )
        self.preview_text.grid(row=0, column=0, sticky="nsew")

        v_scroll = ttk.Scrollbar(
            self.preview_panel,
            orient="vertical",
            command=self.preview_text.yview,
        )
        v_scroll.grid(row=0, column=1, sticky="ns")
        h_scroll = ttk.Scrollbar(
            self.preview_panel,
            orient="horizontal",
            command=self.preview_text.xview,
        )
        h_scroll.grid(row=1, column=0, sticky="ew")
        self.preview_text.configure(yscrollcommand=v_scroll.set, xscrollcommand=h_scroll.set)

    def _build_run_button(self):
        self.run_btn = ttk.Button(self.config_panel, text="运  行", command=self._run)
        self.run_btn.grid(row=5, column=0, columnspan=3, pady=10, ipadx=50)

    # ── 交互 ──

    @staticmethod
    def _browse(entry: ttk.Entry):
        path = filedialog.askdirectory()
        if path:
            entry.delete(0, tk.END)
            entry.insert(0, path)

    def _run(self):
        # 校验
        target = self.target_entry.get().strip()
        if not target or not os.path.isdir(target):
            self._show_error("目标路径无效或不存在。")
            return

        output = self.output_entry.get().strip()

        try:
            depth = int(self.depth_entry.get().strip())
            if depth < 0:
                raise ValueError
        except ValueError:
            self._show_error("遍历深度必须是非负整数。")
            return

        # 生成
        config = TreeConfig(
            root_path=target,
            max_depth=depth,
            ignore_hidden=self.hidden_var.get(),
            ignore_dirs=self.ignore_dirs.get_items(),
            ignore_exts=self.ignore_exts.get_items(),
        )

        try:
            gen = TreeGenerator(config)
            nodes = gen.build_tree()
            lines = gen.format_lines(nodes)
        except Exception as e:
            self._show_error(f"生成目录树失败：{e}")
            return

        # 预览
        self.preview_text.configure(state="normal")
        self.preview_text.delete("1.0", tk.END)
        self.preview_text.insert("1.0", "\n".join(lines))
        self.preview_text.configure(state="disabled")

        # 导出
        fmt_selected = []
        if self.txt_var.get():
            fmt_selected.append(("txt", gen.export_txt))
        if self.md_var.get():
            fmt_selected.append(("md", gen.export_markdown))

        if not fmt_selected:
            self._show_success("预览已更新，未选择导出格式。")
            return

        if not output:
            self._show_error("请选择输出路径。")
            return

        folder_name = os.path.basename(os.path.abspath(target))
        os.makedirs(output, exist_ok=True)

        saved = []
        for name, export_fn in fmt_selected:
            ext = ".txt" if name == "txt" else ".md"
            save_path = os.path.join(output, f"{folder_name}{ext}")
            try:
                export_fn(save_path)
                saved.append(save_path)
            except Exception as e:
                self._show_error(f"导出 {name.upper()} 失败：{e}")
                return

        self._show_success("生成完成！\n" + "\n".join(f"  {p}" for p in saved))

    @staticmethod
    def _show_error(msg: str):
        messagebox.showerror("错误", msg)

    @staticmethod
    def _show_success(msg: str):
        messagebox.showinfo("完成", msg)


def main():
    root = tk.Tk()
    root.title("目录树生成工具")
    root.geometry(WINDOW_SIZE)
    root.minsize(*MIN_WINDOW_SIZE)
    app = Application(root)
    app.pack(fill="both", expand=True)
    root.mainloop()


if __name__ == "__main__":
    main()
