import unittest

from mouse_random_move.win32.chrome_windows import build_display_names


class WindowLabelTests(unittest.TestCase):
    def test_unique_titles_are_unchanged(self) -> None:
        labels = build_display_names(["Alpha - Google Chrome", "Beta - Google Chrome"])
        self.assertEqual(labels, ["Alpha - Google Chrome", "Beta - Google Chrome"])

    def test_duplicate_titles_get_readable_suffixes(self) -> None:
        labels = build_display_names(["Test", "Test", "Other"])
        self.assertEqual(labels, ["Test（同名窗口 1/2）", "Test（同名窗口 2/2）", "Other"])


if __name__ == "__main__":
    unittest.main()
