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


if __name__ == "__main__":
    unittest.main()

