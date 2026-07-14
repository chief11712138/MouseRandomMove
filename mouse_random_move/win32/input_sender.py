from __future__ import annotations

import ctypes
import random
import string
import sys
import time
from dataclasses import asdict, dataclass
from ctypes import wintypes

from .chrome_windows import ChromeWindowService


SW_RESTORE = 9
MOUSEEVENTF_LEFTDOWN = 0x0002
MOUSEEVENTF_LEFTUP = 0x0004
MOUSEEVENTF_WHEEL = 0x0800
KEYEVENTF_KEYUP = 0x0002
INPUT_MOUSE = 0
INPUT_KEYBOARD = 1
WHEEL_DELTA = 120


class TargetWindowError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ActionResult:
    action: str
    description: str
    expected_browser_event: str
    x: int | None = None
    y: int | None = None
    wheel_notches: int | None = None
    text: str = ""
    browser_confirmation_supported: bool = False

    def to_log_dict(self) -> dict[str, object]:
        return asdict(self)


if sys.platform == "win32":
    ULONG_PTR = ctypes.c_size_t

    class MOUSEINPUT(ctypes.Structure):
        _fields_ = [
            ("dx", wintypes.LONG),
            ("dy", wintypes.LONG),
            ("mouseData", wintypes.DWORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class KEYBDINPUT(ctypes.Structure):
        _fields_ = [
            ("wVk", wintypes.WORD),
            ("wScan", wintypes.WORD),
            ("dwFlags", wintypes.DWORD),
            ("time", wintypes.DWORD),
            ("dwExtraInfo", ULONG_PTR),
        ]

    class HARDWAREINPUT(ctypes.Structure):
        _fields_ = [
            ("uMsg", wintypes.DWORD),
            ("wParamL", wintypes.WORD),
            ("wParamH", wintypes.WORD),
        ]

    class INPUTUNION(ctypes.Union):
        _fields_ = [("mi", MOUSEINPUT), ("ki", KEYBDINPUT), ("hi", HARDWAREINPUT)]

    class INPUT(ctypes.Structure):
        _anonymous_ = ("union",)
        _fields_ = [("type", wintypes.DWORD), ("union", INPUTUNION)]

    class POINT(ctypes.Structure):
        _fields_ = [("x", wintypes.LONG), ("y", wintypes.LONG)]

    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", wintypes.LONG),
            ("top", wintypes.LONG),
            ("right", wintypes.LONG),
            ("bottom", wintypes.LONG),
        ]


class WindowInputSender:
    """Send one input action to one explicitly selected Chrome window."""

    def __init__(self, window_service: ChromeWindowService, rng: random.Random) -> None:
        if sys.platform != "win32":
            raise TargetWindowError("Input sending requires Windows.")

        self.window_service = window_service
        self.rng = rng
        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._configure_signatures()
        self._last_point_by_hwnd: dict[int, tuple[int, int]] = {}

    def send(self, hwnd: int, action: str) -> ActionResult:
        target = self.window_service.inspect(hwnd)
        if target is None:
            raise TargetWindowError("选定的 Chrome 窗口已经关闭或不可用。")

        confirmation_supported = target.is_test_page

        self._activate(hwnd)
        left, top, right, bottom = self._get_safe_page_area(hwnd)
        x, y = self._next_point(hwnd, left, top, right, bottom)

        if action == "move":
            self._set_cursor(x, y)
            return ActionResult(
                action="move",
                description=f"移动指针到目标页面 ({x}, {y})",
                expected_browser_event="mousemove",
                x=x,
                y=y,
                browser_confirmation_supported=confirmation_supported,
            )

        if action == "click":
            self._set_cursor(x, y)
            self._mouse_click()
            return ActionResult(
                action="click",
                description=f"在目标页面 ({x}, {y}) 单击",
                expected_browser_event="click",
                x=x,
                y=y,
                browser_confirmation_supported=confirmation_supported,
            )

        if action == "wheel":
            self._set_cursor(x, y)
            notches = self.rng.choice((-1, 1)) * self.rng.randint(3, 7)
            self._mouse_wheel(notches)
            direction = "向上" if notches > 0 else "向下"
            return ActionResult(
                action="wheel",
                description=f"在目标页面 ({x}, {y}) {direction}滚动 {abs(notches)} 格",
                expected_browser_event="wheel",
                x=x,
                y=y,
                wheel_notches=notches,
                browser_confirmation_supported=confirmation_supported,
            )

        if action == "keyboard":
            # Click the page first so the address bar or another application cannot retain focus.
            self._set_cursor(x, y)
            self._mouse_click()
            text = "".join(
                self.rng.choice(string.ascii_lowercase + string.digits)
                for _ in range(self.rng.randint(3, 6))
            )
            self._send_ascii_text(text)
            return ActionResult(
                action="keyboard",
                description=f'向目标页面发送字符 "{text}"',
                expected_browser_event="keydown",
                x=x,
                y=y,
                text=text,
                browser_confirmation_supported=confirmation_supported,
            )

        raise ValueError(f"Unknown action: {action}")

    def _activate(self, hwnd: int) -> None:
        native = wintypes.HWND(hwnd)
        self.user32.ShowWindow(native, SW_RESTORE)
        self.user32.BringWindowToTop(native)
        if not self.user32.SetForegroundWindow(native):
            raise TargetWindowError("Windows 阻止了目标窗口激活。请手动点击目标 Chrome 窗口后重试。")
        time.sleep(0.18)

    def _get_safe_page_area(self, hwnd: int) -> tuple[int, int, int, int]:
        rect = RECT()
        if not self.user32.GetClientRect(wintypes.HWND(hwnd), ctypes.byref(rect)):
            raise ctypes.WinError(ctypes.get_last_error())

        origin = POINT(0, 0)
        if not self.user32.ClientToScreen(wintypes.HWND(hwnd), ctypes.byref(origin)):
            raise ctypes.WinError(ctypes.get_last_error())

        width = rect.right - rect.left
        height = rect.bottom - rect.top
        if width < 420 or height < 360:
            raise TargetWindowError("目标 Chrome 窗口过小，请先将其放大。")

        # Chrome's toolbar is part of the client area. Stay in the central page zone.
        page_top_offset = min(max(int(height * 0.20), 130), 230)
        left = origin.x + max(60, int(width * 0.18))
        right = origin.x + width - max(60, int(width * 0.18))
        top = origin.y + page_top_offset + 40
        bottom = origin.y + height - max(70, int(height * 0.12))

        if right <= left or bottom <= top:
            raise TargetWindowError("无法计算目标页面的安全操作区域。")
        return left, top, right, bottom

    def _next_point(
        self,
        hwnd: int,
        left: int,
        top: int,
        right: int,
        bottom: int,
    ) -> tuple[int, int]:
        previous = self._last_point_by_hwnd.get(hwnd)
        if previous is None:
            x = (left + right) // 2
            y = (top + bottom) // 2
        else:
            dx = self.rng.choice((-1, 1)) * self.rng.randint(25, 70)
            dy = self.rng.choice((-1, 1)) * self.rng.randint(20, 55)
            x = max(left, min(previous[0] + dx, right))
            y = max(top, min(previous[1] + dy, bottom))
        self._last_point_by_hwnd[hwnd] = (x, y)
        return x, y

    def _set_cursor(self, x: int, y: int) -> None:
        if not self.user32.SetCursorPos(x, y):
            raise ctypes.WinError(ctypes.get_last_error())
        time.sleep(0.05)

    def _mouse_click(self) -> None:
        inputs = (INPUT * 2)(
            INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dwFlags=MOUSEEVENTF_LEFTDOWN)),
            INPUT(type=INPUT_MOUSE, mi=MOUSEINPUT(dwFlags=MOUSEEVENTF_LEFTUP)),
        )
        self._send_inputs(inputs)

    def _mouse_wheel(self, notches: int) -> None:
        wheel_data = ctypes.c_ulong(notches * WHEEL_DELTA).value
        inputs = (INPUT * 1)(
            INPUT(
                type=INPUT_MOUSE,
                mi=MOUSEINPUT(mouseData=wheel_data, dwFlags=MOUSEEVENTF_WHEEL),
            )
        )
        self._send_inputs(inputs)

    def _send_ascii_text(self, text: str) -> None:
        for character in text:
            virtual_key = self.user32.VkKeyScanW(character) & 0xFF
            if virtual_key == 0xFF:
                raise TargetWindowError(f"无法发送字符：{character}")
            inputs = (INPUT * 2)(
                INPUT(type=INPUT_KEYBOARD, ki=KEYBDINPUT(wVk=virtual_key)),
                INPUT(
                    type=INPUT_KEYBOARD,
                    ki=KEYBDINPUT(wVk=virtual_key, dwFlags=KEYEVENTF_KEYUP),
                ),
            )
            self._send_inputs(inputs)
            time.sleep(self.rng.uniform(0.035, 0.075))

    def _send_inputs(self, inputs: ctypes.Array[INPUT]) -> None:
        sent = self.user32.SendInput(len(inputs), inputs, ctypes.sizeof(INPUT))
        if sent != len(inputs):
            raise ctypes.WinError(ctypes.get_last_error())

    def _configure_signatures(self) -> None:
        self.user32.ShowWindow.argtypes = [wintypes.HWND, ctypes.c_int]
        self.user32.ShowWindow.restype = wintypes.BOOL
        self.user32.BringWindowToTop.argtypes = [wintypes.HWND]
        self.user32.BringWindowToTop.restype = wintypes.BOOL
        self.user32.SetForegroundWindow.argtypes = [wintypes.HWND]
        self.user32.SetForegroundWindow.restype = wintypes.BOOL
        self.user32.GetClientRect.argtypes = [wintypes.HWND, ctypes.POINTER(RECT)]
        self.user32.GetClientRect.restype = wintypes.BOOL
        self.user32.ClientToScreen.argtypes = [wintypes.HWND, ctypes.POINTER(POINT)]
        self.user32.ClientToScreen.restype = wintypes.BOOL
        self.user32.SetCursorPos.argtypes = [ctypes.c_int, ctypes.c_int]
        self.user32.SetCursorPos.restype = wintypes.BOOL
        self.user32.SendInput.argtypes = [wintypes.UINT, ctypes.POINTER(INPUT), ctypes.c_int]
        self.user32.SendInput.restype = wintypes.UINT
        self.user32.VkKeyScanW.argtypes = [wintypes.WCHAR]
        self.user32.VkKeyScanW.restype = ctypes.c_short

