import unittest

from mouse_random_move.config import ConfigError, RunConfig


class RunConfigTests(unittest.TestCase):
    def test_reversed_delays_are_normalized(self) -> None:
        config = RunConfig.from_values(
            min_delay="20",
            max_delay="10",
            duration_minutes="0",
            enable_move=True,
            enable_click=False,
            enable_wheel=False,
            enable_keyboard=False,
        )
        self.assertEqual(config.min_delay_seconds, 10)
        self.assertEqual(config.max_delay_seconds, 20)

    def test_at_least_one_action_is_required(self) -> None:
        with self.assertRaises(ConfigError):
            RunConfig.from_values(
                min_delay="10",
                max_delay="20",
                duration_minutes="0",
                enable_move=False,
                enable_click=False,
                enable_wheel=False,
                enable_keyboard=False,
            )

    def test_regular_key_shortcut_is_normalized(self) -> None:
        config = RunConfig.from_values(
            min_delay="10",
            max_delay="20",
            duration_minutes="0",
            enable_move=False,
            enable_click=False,
            enable_wheel=False,
            enable_keyboard=True,
            shortcut_ctrl=True,
            shortcut_shift=True,
            shortcut_key=" m ",
        )

        self.assertEqual(config.shortcut_modifiers, ("CTRL", "SHIFT"))
        self.assertEqual(config.shortcut_key, "M")
        self.assertEqual(config.shortcut_text, "CTRL+SHIFT+M")

    def test_function_key_is_rejected(self) -> None:
        with self.assertRaises(ConfigError):
            RunConfig.from_values(
                min_delay="10",
                max_delay="20",
                duration_minutes="0",
                enable_move=False,
                enable_click=False,
                enable_wheel=False,
                enable_keyboard=True,
                shortcut_ctrl=True,
                shortcut_key="F8",
            )

    def test_shortcut_requires_modifier_and_regular_key(self) -> None:
        with self.assertRaises(ConfigError):
            RunConfig.from_values(
                min_delay="10",
                max_delay="20",
                duration_minutes="0",
                enable_move=False,
                enable_click=False,
                enable_wheel=False,
                enable_keyboard=True,
                shortcut_key="M",
            )
        with self.assertRaises(ConfigError):
            RunConfig.from_values(
                min_delay="10",
                max_delay="20",
                duration_minutes="0",
                enable_move=False,
                enable_click=False,
                enable_wheel=False,
                enable_keyboard=True,
                shortcut_ctrl=True,
            )

    def test_shortcut_is_ignored_when_keyboard_is_disabled(self) -> None:
        config = RunConfig.from_values(
            min_delay="10",
            max_delay="20",
            duration_minutes="0",
            enable_move=True,
            enable_click=False,
            enable_wheel=False,
            enable_keyboard=False,
            shortcut_ctrl=True,
            shortcut_key="M",
        )

        self.assertEqual(config.shortcut_modifiers, ())
        self.assertEqual(config.shortcut_key, "")


if __name__ == "__main__":
    unittest.main()
