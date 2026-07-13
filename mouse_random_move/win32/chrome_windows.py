from __future__ import annotations

import ctypes
import sys
from collections import Counter, defaultdict
from dataclasses import dataclass
from ctypes import wintypes


TEST_PAGE_TITLE_MARKER = "Mouse Random Move Test"
CHROME_WINDOW_CLASS_PREFIX = "Chrome_WidgetWin_"


class WindowsPlatformError(RuntimeError):
    pass


@dataclass(frozen=True, slots=True)
class ChromeWindow:
    hwnd: int
    title: str
    display_name: str

    @property
    def is_test_page(self) -> bool:
        return TEST_PAGE_TITLE_MARKER in self.title


def build_display_names(titles: list[str]) -> list[str]:
    """Create readable labels while keeping HWNDs out of the user interface."""
    totals = Counter(titles)
    seen: dict[str, int] = defaultdict(int)
    labels: list[str] = []

    for title in titles:
        seen[title] += 1
        if totals[title] == 1:
            labels.append(title)
        else:
            labels.append(f"{title}（同名窗口 {seen[title]}/{totals[title]}）")
    return labels


class ChromeWindowService:
    def __init__(self) -> None:
        if sys.platform != "win32":
            raise WindowsPlatformError("Chrome window enumeration requires Windows.")

        self.user32 = ctypes.WinDLL("user32", use_last_error=True)
        self._enum_proc_type = ctypes.WINFUNCTYPE(
            wintypes.BOOL, wintypes.HWND, wintypes.LPARAM
        )
        self._configure_signatures()

    def list_windows(self) -> list[ChromeWindow]:
        raw_windows: list[tuple[int, str]] = []

        @self._enum_proc_type
        def callback(hwnd: int, _lparam: int) -> bool:
            if not self.user32.IsWindowVisible(hwnd):
                return True

            title = self._get_window_text(hwnd).strip()
            if not title:
                return True

            class_name = self._get_class_name(hwnd)
            if not class_name.startswith(CHROME_WINDOW_CLASS_PREFIX):
                return True

            if self.user32.GetWindow(hwnd, 4):  # GW_OWNER; exclude owned utility windows.
                return True

            raw_windows.append((int(hwnd), title))
            return True

        if not self.user32.EnumWindows(callback, 0):
            raise ctypes.WinError(ctypes.get_last_error())

        raw_windows.sort(key=lambda item: item[1].casefold())
        labels = build_display_names([title for _, title in raw_windows])
        return [
            ChromeWindow(hwnd=hwnd, title=title, display_name=label)
            for (hwnd, title), label in zip(raw_windows, labels, strict=True)
        ]

    def inspect(self, hwnd: int) -> ChromeWindow | None:
        if not self.user32.IsWindow(wintypes.HWND(hwnd)):
            return None
        if not self.user32.IsWindowVisible(wintypes.HWND(hwnd)):
            return None

        class_name = self._get_class_name(hwnd)
        if not class_name.startswith(CHROME_WINDOW_CLASS_PREFIX):
            return None

        title = self._get_window_text(hwnd).strip()
        if not title:
            return None
        return ChromeWindow(hwnd=hwnd, title=title, display_name=title)

    def _get_window_text(self, hwnd: int) -> str:
        length = self.user32.GetWindowTextLengthW(wintypes.HWND(hwnd))
        buffer = ctypes.create_unicode_buffer(max(1, length + 1))
        self.user32.GetWindowTextW(wintypes.HWND(hwnd), buffer, len(buffer))
        return buffer.value

    def _get_class_name(self, hwnd: int) -> str:
        buffer = ctypes.create_unicode_buffer(256)
        self.user32.GetClassNameW(wintypes.HWND(hwnd), buffer, len(buffer))
        return buffer.value

    def _configure_signatures(self) -> None:
        self.user32.EnumWindows.argtypes = [self._enum_proc_type, wintypes.LPARAM]
        self.user32.EnumWindows.restype = wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [wintypes.HWND]
        self.user32.IsWindowVisible.restype = wintypes.BOOL
        self.user32.IsWindow.argtypes = [wintypes.HWND]
        self.user32.IsWindow.restype = wintypes.BOOL
        self.user32.GetWindowTextLengthW.argtypes = [wintypes.HWND]
        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.GetClassNameW.argtypes = [wintypes.HWND, wintypes.LPWSTR, ctypes.c_int]
        self.user32.GetClassNameW.restype = ctypes.c_int
        self.user32.GetWindow.argtypes = [wintypes.HWND, wintypes.UINT]
        self.user32.GetWindow.restype = wintypes.HWND
