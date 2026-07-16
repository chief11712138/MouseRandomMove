import unittest
from types import SimpleNamespace
from unittest.mock import Mock, patch

from mouse_random_move.app import MouseRandomMoveApp
from mouse_random_move.win32.chrome_windows import ChromeWindow
from mouse_random_move.win32.input_sender import TargetWindowError


class AppStartFocusTests(unittest.TestCase):
    def _build_app(self) -> tuple[MouseRandomMoveApp, object, ChromeWindow]:
        app = MouseRandomMoveApp.__new__(MouseRandomMoveApp)
        config = SimpleNamespace(
            duration_minutes=0,
            to_log_dict=lambda: {"duration_minutes": 0},
        )
        target = ChromeWindow(hwnd=123, title="Example", display_name="Example")

        app.running = False
        app._read_config_or_show_error = Mock(return_value=config)
        app._validate_selected_target = Mock(return_value=target)
        app.sender = Mock()
        app.controller = Mock()
        app.server = SimpleNamespace(store=Mock())
        app._set_target_controls_enabled = Mock()
        app.start_button = Mock()
        app.status_text = Mock()
        app.last_action_text = Mock()
        app.logger = Mock()
        app._schedule_next = Mock()
        app.root = Mock()
        return app, config, target

    def test_start_focuses_target_before_running(self) -> None:
        app, config, target = self._build_app()

        app.start()

        app.sender.focus.assert_called_once_with(target.hwnd)
        app.controller.lock_target.assert_called_once_with(target.hwnd)
        app._schedule_next.assert_called_once_with(config)
        self.assertTrue(app.running)

    @patch("mouse_random_move.app.messagebox.showerror")
    def test_start_aborts_when_target_cannot_be_focused(self, showerror: Mock) -> None:
        app, _config, target = self._build_app()
        app.sender.focus.side_effect = TargetWindowError("blocked")

        app.start()

        app.sender.focus.assert_called_once_with(target.hwnd)
        app.controller.lock_target.assert_not_called()
        app._schedule_next.assert_not_called()
        self.assertFalse(app.running)
        showerror.assert_called_once()


if __name__ == "__main__":
    unittest.main()
