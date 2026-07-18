import unittest
from unittest.mock import Mock

from mouse_random_move.click_through_app import (
    RESTORE_KEY,
    WS_EX_LAYERED,
    WS_EX_TRANSPARENT,
    ClickThroughApp,
    click_through_style,
)


class ClickThroughStyleTests(unittest.TestCase):
    def test_enabling_adds_transparent_and_layered_styles(self) -> None:
        updated = click_through_style(0x100, True)
        self.assertTrue(updated & WS_EX_TRANSPARENT)
        self.assertTrue(updated & WS_EX_LAYERED)

    def test_disabling_only_removes_click_through_style(self) -> None:
        current = 0x100 | WS_EX_TRANSPARENT | WS_EX_LAYERED
        updated = click_through_style(current, False)
        self.assertFalse(updated & WS_EX_TRANSPARENT)
        self.assertTrue(updated & WS_EX_LAYERED)
        self.assertTrue(updated & 0x100)

    def test_restore_shortcut_does_not_use_function_key(self) -> None:
        self.assertEqual(RESTORE_KEY, "Ctrl + Shift + Alt + X")

    def test_poll_restores_on_main_loop_when_requested(self) -> None:
        app = ClickThroughApp.__new__(ClickThroughApp)
        app._restore_requested = True
        app._restore_click_through = Mock()
        app.root = Mock()
        app.root.after.return_value = "poll-1"

        app._poll_restore_request()

        self.assertFalse(app._restore_requested)
        app._restore_click_through.assert_called_once_with()
        self.assertEqual(app._restore_poll_job, "poll-1")

    def test_restore_turns_off_click_through(self) -> None:
        app = ClickThroughApp.__new__(ClickThroughApp)
        app.click_through = Mock()
        app.click_through.get.return_value = True
        app._unregister_restore_hotkey = Mock()
        app._apply_click_through = Mock()

        app._restore_click_through()

        app.click_through.set.assert_called_once_with(False)
        app._unregister_restore_hotkey.assert_called_once_with()
        app._apply_click_through.assert_called_once_with(False)


if __name__ == "__main__":
    unittest.main()
