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
        app.start_button_text = Mock()
        app._update_run_visual = Mock()
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


class AppWindowPreferenceTests(unittest.TestCase):
    def test_always_on_top_uses_selected_value(self) -> None:
        app = MouseRandomMoveApp.__new__(MouseRandomMoveApp)
        app.root = Mock()
        app.always_on_top = Mock()
        app.always_on_top.get.return_value = True

        app._set_always_on_top()

        app.root.attributes.assert_called_once_with("-topmost", True)

    def test_opacity_is_clamped_and_applied(self) -> None:
        app = MouseRandomMoveApp.__new__(MouseRandomMoveApp)
        app.root = Mock()
        app.opacity_text = Mock()

        app._set_opacity("20")

        app.opacity_text.set.assert_called_once_with("透明度 40%")
        app.root.attributes.assert_called_once_with("-alpha", 0.4)

    @patch("mouse_random_move.app.messagebox.showinfo")
    def test_help_is_available_in_a_dialog(self, showinfo: Mock) -> None:
        app = MouseRandomMoveApp.__new__(MouseRandomMoveApp)
        app.root = Mock()
        app.server = SimpleNamespace(url="http://127.0.0.1")
        app.logger = SimpleNamespace(log_dir="logs")

        app._show_help()

        showinfo.assert_called_once()

    def test_simple_mode_preserves_timer_and_controller_state(self) -> None:
        app = MouseRandomMoveApp.__new__(MouseRandomMoveApp)
        app.ui_mode = Mock()
        app.full_view = Mock()
        app.simple_view = Mock()
        app.header = Mock()
        app.simple_mode_button = Mock()
        app.full_mode_button = Mock()
        app.always_on_top = Mock()
        app._set_always_on_top = Mock()
        app._resize_window = Mock()
        app._simple_window_size = (540, 390)
        app._full_window_size = (1240, 720)
        app._schedule_job = "timer-42"
        app.controller = Mock()

        app._set_ui_mode("simple")

        self.assertEqual(app._schedule_job, "timer-42")
        app.controller.assert_not_called()
        app.header.pack_forget.assert_called_once()
        app.simple_view.pack.assert_called_once_with(fill="both", expand=True)
        app._resize_window.assert_called_once_with((540, 390), anchor_right=True)
        app.always_on_top.set.assert_called_once_with(True)


if __name__ == "__main__":
    unittest.main()
