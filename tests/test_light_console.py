import unittest

from mouse_random_move import light_console
from mouse_random_move.config import RunConfig
from mouse_random_move.light_console import LightControlConsoleApp


class LightConsoleTests(unittest.TestCase):
    def test_console_exposes_shortcut_configuration(self) -> None:
        self.assertIs(light_console.RunConfig, RunConfig)

    def test_shortcut_keys_exclude_function_keys(self) -> None:
        self.assertIn("M", RunConfig.SHORTCUT_KEYS)
        self.assertIn("0", RunConfig.SHORTCUT_KEYS)
        self.assertNotIn("F8", RunConfig.SHORTCUT_KEYS)

    def test_compact_console_uses_full_width_target_layout(self) -> None:
        self.assertEqual(LightControlConsoleApp.SIMPLE_SIZE, (760, 500))


if __name__ == "__main__":
    unittest.main()
