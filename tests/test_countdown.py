import unittest
from datetime import datetime, timedelta

from mouse_random_move.app import countdown_seconds


class CountdownTests(unittest.TestCase):
    def test_rounds_up_partial_seconds(self) -> None:
        now = datetime(2026, 7, 14, 12, 0, 0)
        deadline = now + timedelta(seconds=10, milliseconds=1)
        self.assertEqual(countdown_seconds(deadline, now), 11)

    def test_never_returns_negative_seconds(self) -> None:
        now = datetime(2026, 7, 14, 12, 0, 0)
        self.assertEqual(countdown_seconds(now - timedelta(seconds=2), now), 0)


if __name__ == "__main__":
    unittest.main()
