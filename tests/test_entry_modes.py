import builtins
import io
import json
import tempfile
import tkinter as tk
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from file_tree import cli_simple, dedicated
from file_tree.core import TreeConfig, TreeGenerator
from file_tree.gui import (
    CONFIG_PANEL_MIN_WIDTH,
    MIN_WINDOW_SIZE,
    WINDOW_SIZE,
    Application,
)


class EntryModeTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="file_tree_modes_")
        self.base = Path(self.temp_dir.name)
        self.target = self.base / "sample_project"
        self.target.mkdir()
        (self.target / "src").mkdir()
        (self.target / "src" / "main.py").write_text("print('ok')", encoding="utf-8")
        (self.target / "README.md").write_text("# Sample", encoding="utf-8")
        (self.target / ".git").mkdir()
        (self.target / ".git" / "ignored-child.txt").write_text(
            "ignored", encoding="utf-8"
        )

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_cli_interactive_mode_exports_wps_markdown(self):
        output_path = self.base / "cli_result.md"
        answers = iter([
            str(self.target),
            "2",
            ".git",
            "2",
            str(output_path),
            "n",
        ])

        with patch.object(builtins, "input", side_effect=lambda _="": next(answers)):
            with redirect_stdout(io.StringIO()):
                exit_code = cli_simple.main([])

        self.assertEqual(exit_code, 0)
        self.assertTrue(output_path.is_file())
        content = output_path.read_text(encoding="utf-8")
        self.assertIn("- sample_project/", content)
        self.assertIn("- main.py", content)
        self.assertIn("- .git/", content)
        self.assertNotIn("ignored-child.txt", content)

    def test_gui_mode_previews_then_exports_txt_and_markdown(self):
        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk GUI is unavailable: {exc}")

        root.withdraw()
        try:
            app = Application(root)
            app.pack(fill="both", expand=True)
            self.assertEqual(WINDOW_SIZE, "1100x700")
            self.assertEqual(MIN_WINDOW_SIZE, (900, 650))
            self.assertEqual(CONFIG_PANEL_MIN_WIDTH, 380)
            self.assertEqual(int(app.config_panel.grid_info()["column"]), 0)
            self.assertEqual(int(app.preview_panel.grid_info()["column"]), 1)
            self.assertEqual(int(app.ignore_dirs.grid_info()["row"]), 0)
            self.assertEqual(int(app.ignore_exts.grid_info()["row"]), 1)
            app.target_entry.insert(0, str(self.target))

            with patch.object(app, "_show_success") as show_success, patch.object(
                app, "_show_error"
            ) as show_error:
                app._run()

            show_error.assert_not_called()
            show_success.assert_called_once()
            preview = app.preview_text.get("1.0", tk.END)
            self.assertIn("sample_project/", preview)
            self.assertIn("main.py", preview)
            self.assertIn(".git/", preview)
            self.assertNotIn("ignored-child.txt", preview)

            output_dir = self.base / "gui_output"
            app.output_entry.insert(0, str(output_dir))
            app.txt_var.set(True)
            app.md_var.set(True)

            with patch.object(app, "_show_success") as show_success, patch.object(
                app, "_show_error"
            ) as show_error:
                app._run()

            show_error.assert_not_called()
            show_success.assert_called_once()
            self.assertTrue((output_dir / "sample_project.txt").is_file())
            self.assertTrue((output_dir / "sample_project.md").is_file())
        finally:
            root.destroy()

    def test_dedicated_mode_uses_json_and_exports_two_files(self):
        output_dir = self.base / "dedicated_output"
        config_path = self.base / "config.local.json"
        config_path.write_text(
            json.dumps(
                {
                    "root_path": str(self.target),
                    "output_dir": str(output_dir),
                    "max_depth": 2,
                    "ignore_hidden": False,
                    "ignore_dirs": [".git", "__pycache__"],
                    "ignore_exts": [".pyc"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )

        with patch.object(dedicated, "find_config_path", return_value=config_path):
            with redirect_stdout(io.StringIO()):
                exit_code = dedicated.main()

        self.assertEqual(exit_code, 0)
        txt_files = list(output_dir.glob("tree_*.txt"))
        md_files = list(output_dir.glob("tree_*.md"))
        self.assertEqual(len(txt_files), 1)
        self.assertEqual(len(md_files), 1)
        txt_content = txt_files[0].read_text(encoding="utf-8")
        md_content = md_files[0].read_text(encoding="utf-8")
        self.assertIn("main.py", txt_content)
        self.assertIn(".git/", txt_content)
        self.assertNotIn("ignored-child.txt", txt_content)
        self.assertIn("- main.py", md_content)
        self.assertIn("- .git/", md_content)
        self.assertNotIn("ignored-child.txt", md_content)

    def test_cli_non_interactive_flag_uses_defaults_without_prompting(self):
        stdout = io.StringIO()
        with patch.object(cli_simple.Path, "cwd", return_value=self.target), patch.object(
            builtins,
            "input",
            side_effect=AssertionError("parameter mode must not call input"),
        ):
            with redirect_stdout(stdout):
                exit_code = cli_simple.main(["--non-interactive"])

        self.assertEqual(exit_code, 0)
        self.assertIn("sample_project/", stdout.getvalue())
        self.assertIn("main.py", stdout.getvalue())

    def test_cli_parameter_mode_exports_multiple_formats_and_overwrites(self):
        output_dir = self.base / "parameter_output"
        output_dir.mkdir()
        (self.target / "cache.pyc").write_bytes(b"compiled")
        txt_path = output_dir / "sample_project.txt"
        txt_path.write_text("old content", encoding="utf-8")

        with patch.object(
            builtins,
            "input",
            side_effect=AssertionError("parameter mode must not call input"),
        ):
            with redirect_stdout(io.StringIO()):
                exit_code = cli_simple.main([
                    str(self.target),
                    "--max-depth", "2",
                    "--ignore-dir", ".git",
                    "--ignore-ext", "pyc",
                    "--format", "txt",
                    "--format", "md",
                    "--output-dir", str(output_dir),
                ])

        self.assertEqual(exit_code, 0)
        md_path = output_dir / "sample_project.md"
        self.assertTrue(md_path.is_file())
        txt_content = txt_path.read_text(encoding="utf-8")
        md_content = md_path.read_text(encoding="utf-8")
        self.assertNotIn("old content", txt_content)
        self.assertIn(".git/", txt_content)
        self.assertNotIn("ignored-child.txt", txt_content)
        self.assertNotIn("cache.pyc", txt_content)
        self.assertIn("- .git/", md_content)

    def test_cli_parameter_mode_reports_argument_and_path_errors(self):
        with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            with self.assertRaises(SystemExit) as missing_output:
                cli_simple.main([str(self.target), "--format", "txt"])
        self.assertEqual(missing_output.exception.code, 2)

        stderr = io.StringIO()
        with redirect_stderr(stderr):
            exit_code = cli_simple.main([
                str(self.base / "missing"),
                "--non-interactive",
            ])
        self.assertEqual(exit_code, 1)
        self.assertIn("目标路径不存在", stderr.getvalue())

    def test_interactive_cli_and_dedicated_report_root_scan_errors(self):
        answers = iter([str(self.target), "2", "", "0"])
        cli_stderr = io.StringIO()
        with patch.object(builtins, "input", side_effect=lambda _="": next(answers)):
            with patch(
                "file_tree.core.os.listdir",
                side_effect=OSError("root scan failed"),
            ):
                with redirect_stdout(io.StringIO()), redirect_stderr(cli_stderr):
                    cli_exit_code = cli_simple.main([])

        self.assertEqual(cli_exit_code, 1)
        self.assertIn("执行失败", cli_stderr.getvalue())

        output_dir = self.base / "dedicated_error_output"
        config_path = self.base / "error_config.local.json"
        config_path.write_text(
            json.dumps(
                {
                    "root_path": str(self.target),
                    "output_dir": str(output_dir),
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        dedicated_stdout = io.StringIO()
        with patch.object(dedicated, "find_config_path", return_value=config_path):
            with patch(
                "file_tree.core.os.listdir",
                side_effect=OSError("root scan failed"),
            ):
                with redirect_stdout(dedicated_stdout):
                    dedicated_exit_code = dedicated.main()

        self.assertEqual(dedicated_exit_code, 1)
        self.assertIn("执行失败", dedicated_stdout.getvalue())

    def test_terminal_output_escapes_characters_unsupported_by_gbk(self):
        emoji_name = "look_👀.txt"
        (self.target / emoji_name).write_text("emoji", encoding="utf-8")
        generator = TreeGenerator(TreeConfig(root_path=str(self.target)))

        output_buffer = io.BytesIO()
        gbk_stdout = io.TextIOWrapper(
            output_buffer,
            encoding="gbk",
            errors="strict",
        )
        with redirect_stdout(gbk_stdout):
            generator.print_tree()
        gbk_stdout.flush()
        terminal_text = output_buffer.getvalue().decode("gbk")
        gbk_stdout.detach()

        self.assertIn("look_\\U0001f440.txt", terminal_text)

        txt_path = self.base / "unicode_result.txt"
        with redirect_stdout(io.StringIO()):
            generator.export_txt(str(txt_path))
        self.assertIn(emoji_name, txt_path.read_text(encoding="utf-8"))

    def test_three_entry_modes_produce_the_same_tree_for_one_config(self):
        (self.target / "cache.pyc").write_bytes(b"compiled")
        common_config = TreeConfig(
            root_path=str(self.target),
            max_depth=2,
            ignore_hidden=False,
            ignore_dirs=[".git"],
            ignore_exts=[".pyc"],
        )
        expected_lines = TreeGenerator(common_config).build_lines()

        cli_output = self.base / "consistency_cli"
        with redirect_stdout(io.StringIO()):
            cli_exit_code = cli_simple.main([
                str(self.target),
                "--max-depth", "2",
                "--ignore-dir", ".git",
                "--ignore-ext", ".pyc",
                "--format", "txt",
                "--output-dir", str(cli_output),
            ])
        self.assertEqual(cli_exit_code, 0)
        cli_lines = (cli_output / "sample_project.txt").read_text(
            encoding="utf-8"
        ).splitlines()[2:]

        try:
            root = tk.Tk()
        except tk.TclError as exc:
            self.skipTest(f"Tk GUI is unavailable: {exc}")

        root.withdraw()
        try:
            app = Application(root)
            app.pack(fill="both", expand=True)
            app.target_entry.insert(0, str(self.target))
            app.depth_entry.delete(0, tk.END)
            app.depth_entry.insert(0, "2")
            app.hidden_var.set(False)
            app.ignore_dirs.set_items([".git"])
            app.ignore_exts.set_items([".pyc"])
            with patch.object(app, "_show_success"), patch.object(
                app,
                "_show_error",
            ) as show_error:
                app._run()
            show_error.assert_not_called()
            gui_lines = app.preview_text.get("1.0", "end-1c").splitlines()
        finally:
            root.destroy()

        dedicated_output = self.base / "consistency_dedicated"
        config_path = self.base / "consistency_config.json"
        config_path.write_text(
            json.dumps(
                {
                    "root_path": str(self.target),
                    "output_dir": str(dedicated_output),
                    "max_depth": 2,
                    "ignore_hidden": False,
                    "ignore_dirs": [".git"],
                    "ignore_exts": [".pyc"],
                },
                ensure_ascii=False,
            ),
            encoding="utf-8",
        )
        with patch.object(dedicated, "find_config_path", return_value=config_path):
            with redirect_stdout(io.StringIO()):
                dedicated_exit_code = dedicated.main()
        self.assertEqual(dedicated_exit_code, 0)
        dedicated_txt = next(dedicated_output.glob("tree_*.txt"))
        dedicated_lines = dedicated_txt.read_text(encoding="utf-8").splitlines()[2:]

        self.assertEqual(cli_lines, expected_lines)
        self.assertEqual(gui_lines, expected_lines)
        self.assertEqual(dedicated_lines, expected_lines)


if __name__ == "__main__":
    unittest.main()
