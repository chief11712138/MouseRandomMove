import sys
import unittest
from unittest.mock import Mock

from mouse_random_move.win32.chrome_windows import ChromeWindow
from mouse_random_move.win32.input_sender import (
    KEYEVENTF_KEYUP,
    TargetWindowError,
    WindowInputSender,
)


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


class WindowInputSenderKeyboardTests(unittest.TestCase):
    def test_regular_key_shortcut_is_sent_and_reported(self) -> None:
        sender = WindowInputSender.__new__(WindowInputSender)
        sender.window_service = Mock()
        sender.window_service.inspect.return_value = ChromeWindow(
            hwnd=123,
            title="Example",
            display_name="Example",
        )
        sender._activate = Mock()
        sender._get_safe_page_area = Mock(return_value=(10, 20, 30, 40))
        sender._next_point = Mock(return_value=(20, 30))
        sender._set_cursor = Mock()
        sender._mouse_click = Mock()
        sender._send_shortcut = Mock()

        result = sender.send(123, "keyboard", shortcut="CTRL+SHIFT+M")

        sender._send_shortcut.assert_called_once_with(("CTRL", "SHIFT"), "M")
        self.assertEqual(result.text, "Ctrl+Shift+M")
        self.assertIn("Ctrl+Shift+M", result.description)

    def test_shortcut_parser_accepts_modifiers_and_regular_key(self) -> None:
        modifiers, key = WindowInputSender._parse_shortcut("CTRL+SHIFT+M")
        self.assertEqual(modifiers, ("CTRL", "SHIFT"))
        self.assertEqual(key, "M")

    def test_shortcut_parser_rejects_function_keys(self) -> None:
        with self.assertRaises(TargetWindowError):
            WindowInputSender._parse_shortcut("CTRL+F8")

    @unittest.skipUnless(sys.platform == "win32", "SendInput structures require Windows")
    def test_shortcut_uses_balanced_key_down_and_key_up_events(self) -> None:
        sender = WindowInputSender.__new__(WindowInputSender)
        sender._send_inputs = Mock()

        sender._send_shortcut(("CTRL", "SHIFT"), "M")

        inputs = sender._send_inputs.call_args.args[0]
        self.assertEqual(
            [item.ki.wVk for item in inputs],
            [0x11, 0x10, ord("M"), ord("M"), 0x10, 0x11],
        )
        self.assertEqual(
            [item.ki.dwFlags for item in inputs],
            [0, 0, 0, KEYEVENTF_KEYUP, KEYEVENTF_KEYUP, KEYEVENTF_KEYUP],
        )


if __name__ == "__main__":
    unittest.main()
