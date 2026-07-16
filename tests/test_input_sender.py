import unittest
from unittest.mock import Mock

from mouse_random_move.win32.chrome_windows import ChromeWindow
from mouse_random_move.win32.input_sender import TargetWindowError, WindowInputSender


class WindowInputSenderFocusTests(unittest.TestCase):
    def test_focus_validates_and_activates_selected_window(self) -> None:
        sender = WindowInputSender.__new__(WindowInputSender)
        sender.window_service = Mock()
        sender.window_service.inspect.return_value = ChromeWindow(
            hwnd=123,
            title="Example",
            display_name="Example",
        )
        sender._activate = Mock()

        sender.focus(123)

        sender.window_service.inspect.assert_called_once_with(123)
        sender._activate.assert_called_once_with(123)

    def test_focus_rejects_closed_window(self) -> None:
        sender = WindowInputSender.__new__(WindowInputSender)
        sender.window_service = Mock()
        sender.window_service.inspect.return_value = None
        sender._activate = Mock()

        with self.assertRaises(TargetWindowError):
            sender.focus(123)

        sender._activate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
