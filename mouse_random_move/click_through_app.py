from __future__ import annotations

import ctypes
import sys
import tkinter as tk
from ctypes import wintypes
from tkinter import messagebox

import ttkbootstrap as ttk

from .light_product import NethardLightApp


GWL_EXSTYLE = -20
GWLP_WNDPROC = -4
WS_EX_TRANSPARENT = 0x00000020
WS_EX_LAYERED = 0x00080000
WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_NOREPEAT = 0x4000
HOTKEY_ID = 0x4E48
RESTORE_KEY = "Ctrl + Shift + Alt + X"
SWP_REFRESH_FRAME = 0x0037


def click_through_style(current_style: int, enabled: bool) -> int:
    if enabled:
        return current_style | WS_EX_TRANSPARENT | WS_EX_LAYERED
    return current_style & ~WS_EX_TRANSPARENT


if sys.platform == "win32":
    LRESULT = ctypes.c_ssize_t
    WNDPROC = ctypes.WINFUNCTYPE(
        LRESULT,
        wintypes.HWND,
        wintypes.UINT,
        wintypes.WPARAM,
        wintypes.LPARAM,
    )


class ClickThroughApp(NethardLightApp):
    """Add reversible Windows mouse click-through to the light console."""

    RESTORE_POLL_MS = 40

    def _build_ui(self) -> None:
        self._restore_requested = False
        self._restore_poll_job: str | None = None
        self.click_through = tk.BooleanVar(value=False)
        self.click_through_hint = tk.StringVar(value=f"穿透恢复：{RESTORE_KEY}")
        self._hotkey_registered = False
        self._hotkey_hwnd = 0
        self._previous_wndproc = 0
        self._wndproc_callback = None
        super()._build_ui()
        self._poll_restore_request()

    def _poll_restore_request(self) -> None:
        if self._restore_requested:
            self._restore_requested = False
            self._restore_click_through()
        self._restore_poll_job = self.root.after(
            self.RESTORE_POLL_MS,
            self._poll_restore_request,
        )

    def _build_simple_view(self) -> None:
        super()._build_simple_view()
        topmost = self._find_widget_by_text(self.simple_view, "置顶")
        if topmost is not None:
            toolbar = topmost.master
            self.simple_click_through_control = ttk.Checkbutton(
                toolbar,
                text="穿透点击",
                variable=self.click_through,
                command=self._set_click_through,
                bootstyle="warning-round-toggle",
            )
            self.simple_click_through_control.pack(
                side=tk.RIGHT,
                padx=(8, 0),
                before=topmost,
            )

        opacity_label = self._find_label_by_variable(
            self.simple_view,
            str(self.opacity_text),
        )
        if opacity_label is not None:
            ttk.Label(
                opacity_label.master,
                textvariable=self.click_through_hint,
                style="Console.Footer.TLabel",
            ).grid(row=0, column=2, sticky=tk.E, padx=(16, 0))

    def _build_full_view(self) -> None:
        super()._build_full_view()
        preferences = self._find_labelframe(self.full_view, "窗口显示")
        if preferences is None:
            return
        self.full_click_through_control = ttk.Checkbutton(
            preferences,
            text="穿透点击",
            variable=self.click_through,
            command=self._set_click_through,
            bootstyle="warning-round-toggle",
        )
        self.full_click_through_control.grid(row=1, column=0, sticky=tk.W, pady=(8, 0))
        ttk.Label(
            preferences,
            textvariable=self.click_through_hint,
        ).grid(row=1, column=1, columnspan=2, sticky=tk.W, padx=(10, 0), pady=(8, 0))

    @staticmethod
    def _find_widget_by_text(parent: tk.Misc, text: str):
        for widget in parent.winfo_children():
            try:
                if widget.cget("text") == text:
                    return widget
            except tk.TclError:
                pass
            nested = ClickThroughApp._find_widget_by_text(widget, text)
            if nested is not None:
                return nested
        return None

    @staticmethod
    def _find_label_by_variable(parent: tk.Misc, variable_name: str):
        for widget in parent.winfo_children():
            if isinstance(widget, ttk.Label) and str(widget.cget("textvariable")) == variable_name:
                return widget
            nested = ClickThroughApp._find_label_by_variable(widget, variable_name)
            if nested is not None:
                return nested
        return None

    def _outer_hwnd(self) -> int:
        self.root.update_idletasks()
        user32 = ctypes.windll.user32
        return int(
            user32.GetAncestor(self.root.winfo_id(), 2)
            or user32.GetParent(self.root.winfo_id())
            or self.root.winfo_id()
        )

    def _set_click_through(self) -> None:
        enabled = bool(self.click_through.get())
        if enabled and not self._register_restore_hotkey():
            self.click_through.set(False)
            messagebox.showerror(
                "无法启用穿透点击",
                f"恢复快捷键 {RESTORE_KEY} 已被其他程序占用。",
                parent=self.root,
            )
            return
        if not enabled:
            self._unregister_restore_hotkey()
        self._apply_click_through(enabled)

    def _restore_click_through(self) -> None:
        if not self.click_through.get():
            return
        self.click_through.set(False)
        self._unregister_restore_hotkey()
        self._apply_click_through(False)

    def _apply_click_through(self, enabled: bool) -> None:
        if sys.platform != "win32":
            return
        user32 = ctypes.windll.user32
        hwnd = self._outer_hwnd()
        current = int(user32.GetWindowLongPtrW(hwnd, GWL_EXSTYLE))
        updated = click_through_style(current, enabled)
        user32.SetWindowLongPtrW(hwnd, GWL_EXSTYLE, updated)
        user32.SetWindowPos(hwnd, 0, 0, 0, 0, 0, SWP_REFRESH_FRAME)

    def _register_restore_hotkey(self) -> bool:
        if sys.platform != "win32":
            return False
        if self._hotkey_registered:
            return True
        if not self._install_window_proc():
            return False
        modifiers = MOD_CONTROL | MOD_SHIFT | MOD_ALT | MOD_NOREPEAT
        registered = bool(
            ctypes.windll.user32.RegisterHotKey(
                self._hotkey_hwnd,
                HOTKEY_ID,
                modifiers,
                ord("X"),
            )
        )
        self._hotkey_registered = registered
        return registered

    def _unregister_restore_hotkey(self) -> None:
        if self._hotkey_registered and self._hotkey_hwnd:
            ctypes.windll.user32.UnregisterHotKey(self._hotkey_hwnd, HOTKEY_ID)
        self._hotkey_registered = False

    def _install_window_proc(self) -> bool:
        if self._previous_wndproc:
            return True
        user32 = ctypes.windll.user32
        hwnd = self._outer_hwnd()
        user32.GetWindowLongPtrW.argtypes = [wintypes.HWND, ctypes.c_int]
        user32.GetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.SetWindowLongPtrW.argtypes = [
            wintypes.HWND,
            ctypes.c_int,
            ctypes.c_ssize_t,
        ]
        user32.SetWindowLongPtrW.restype = ctypes.c_ssize_t
        user32.CallWindowProcW.argtypes = [
            ctypes.c_void_p,
            wintypes.HWND,
            wintypes.UINT,
            wintypes.WPARAM,
            wintypes.LPARAM,
        ]
        user32.CallWindowProcW.restype = ctypes.c_ssize_t

        @WNDPROC
        def window_proc(
            callback_hwnd: int,
            message: int,
            wparam: int,
            lparam: int,
        ) -> int:
            if message == WM_HOTKEY and int(wparam) == HOTKEY_ID:
                self._restore_requested = True
                return 0
            return int(
                user32.CallWindowProcW(
                    ctypes.c_void_p(self._previous_wndproc),
                    callback_hwnd,
                    message,
                    wparam,
                    lparam,
                )
            )

        callback_address = ctypes.cast(window_proc, ctypes.c_void_p).value
        if callback_address is None:
            return False
        previous = int(
            user32.SetWindowLongPtrW(
                hwnd,
                GWLP_WNDPROC,
                callback_address,
            )
        )
        if not previous:
            return False
        self._hotkey_hwnd = hwnd
        self._previous_wndproc = previous
        self._wndproc_callback = window_proc
        return True

    def _uninstall_window_proc(self) -> None:
        if self._previous_wndproc and self._hotkey_hwnd:
            ctypes.windll.user32.SetWindowLongPtrW(
                self._hotkey_hwnd,
                GWLP_WNDPROC,
                self._previous_wndproc,
            )
        self._previous_wndproc = 0
        self._hotkey_hwnd = 0
        self._wndproc_callback = None

    def close(self) -> None:
        if self._restore_poll_job is not None:
            try:
                self.root.after_cancel(self._restore_poll_job)
            except tk.TclError:
                pass
            self._restore_poll_job = None
        if self.click_through.get():
            self.click_through.set(False)
            self._apply_click_through(False)
        self._unregister_restore_hotkey()
        self._uninstall_window_proc()
        super().close()
