import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from file_tree.core import TreeConfig, TreeGenerator, TreeNode


class CoreBehaviorTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory(prefix="file_tree_core_")
        self.root = Path(self.temp_dir.name) / "project"
        self.root.mkdir()

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_max_depth_keeps_boundary_nodes_without_deeper_children(self):
        level_one = self.root / "level_one"
        level_two = level_one / "level_two"
        level_two.mkdir(parents=True)
        (level_two / "too_deep.txt").write_text("hidden by depth", encoding="utf-8")
        (self.root / "root.txt").write_text("visible", encoding="utf-8")

        nodes = TreeGenerator(
            TreeConfig(root_path=str(self.root), max_depth=2)
        ).build_tree()
        by_name = {node.name: node for node in nodes}

        self.assertEqual(by_name["level_one"].depth, 1)
        self.assertEqual(by_name["level_two"].depth, 2)
        self.assertEqual(by_name["root.txt"].depth, 1)
        self.assertNotIn("too_deep.txt", by_name)

    def test_empty_directory_is_preserved_as_directory_node(self):
        (self.root / "empty").mkdir()

        generator = TreeGenerator(TreeConfig(root_path=str(self.root)))
        nodes = generator.build_tree()
        empty_node = next(node for node in nodes if node.name == "empty")

        self.assertTrue(empty_node.is_dir)
        self.assertEqual(empty_node.depth, 1)
        self.assertIn("└── empty/", generator.format_lines(nodes))

    def test_character_tree_connectors_follow_actual_parent_siblings(self):
        nodes = [
            TreeNode("project", True, 0),
            TreeNode("alpha", True, 1),
            TreeNode("a.txt", False, 2),
            TreeNode("nested", True, 2),
            TreeNode("deep.txt", False, 3),
            TreeNode("beta", True, 1),
            TreeNode("b.txt", False, 2),
            TreeNode("root.txt", False, 1),
        ]

        self.assertEqual(
            TreeGenerator.format_lines(nodes),
            [
                "project/",
                "├── alpha/",
                "│   ├── a.txt",
                "│   └── nested/",
                "│       └── deep.txt",
                "├── beta/",
                "│   └── b.txt",
                "└── root.txt",
            ],
        )

    def test_child_directory_oserror_keeps_node_and_skips_children(self):
        blocked = self.root / "blocked"
        blocked.mkdir()
        (blocked / "hidden.txt").write_text("hidden", encoding="utf-8")
        (self.root / "visible.txt").write_text("visible", encoding="utf-8")
        real_listdir = os.listdir

        def listdir_with_blocked_child(path):
            if Path(path) == blocked:
                raise OSError("child directory is unavailable")
            return real_listdir(path)

        with patch("file_tree.core.os.listdir", side_effect=listdir_with_blocked_child):
            nodes = TreeGenerator(TreeConfig(root_path=str(self.root))).build_tree()

        names = [node.name for node in nodes]
        self.assertIn("blocked", names)
        self.assertIn("visible.txt", names)
        self.assertNotIn("hidden.txt", names)

    def test_root_directory_oserror_is_raised(self):
        generator = TreeGenerator(TreeConfig(root_path=str(self.root)))

        with patch(
            "file_tree.core.os.listdir",
            side_effect=OSError("root directory is unavailable"),
        ):
            with self.assertRaisesRegex(OSError, "root directory is unavailable"):
                generator.build_tree()


if __name__ == "__main__":
    unittest.main()
