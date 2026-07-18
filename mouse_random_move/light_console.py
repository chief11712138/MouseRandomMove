from __future__ import annotations

import ctypes
import sys
import tkinter as tk
import ttkbootstrap as ttk

from .app import MouseRandomMoveApp
from .config import RunConfig


BG = "#f2f5f9"
SURFACE = "#ffffff"
PANEL = "#ffffff"
BORDER = "#b8c5d3"
TEXT = "#111827"
MUTED = "#4b5563"
ACCENT = "#075ea8"
SUCCESS = "#087f5b"
STOPPED = "#5b6472"


def colorref(hex_color: str) -> int:
    value = hex_color.lstrip("#")
    red, green, blue = (int(value[index : index + 2], 16) for index in (0, 2, 4))
    return red | (green << 8) | (blue << 16)


class LightControlConsoleApp(MouseRandomMoveApp):
    """Light, high-contrast console with editable regular-key shortcuts."""

    SIMPLE_SIZE = (760, 500)

    def _build_ui(self) -> None:
        self.run_state_text = tk.StringVar(value="已停止")
        self.window_opacity.set(100.0)
        self.opacity_text.set("透明度 100%")
        self._configure_styles()
        self._set_window_icon()
        super()._build_ui()
        self.root.configure(background=BG)
        self.command_log.configure(
            background="#ffffff",
            foreground=TEXT,
            insertbackground=TEXT,
            selectbackground="#b9dcff",
            selectforeground=TEXT,
        )

    def _configure_styles(self) -> None:
        style = ttk.Style()
        style.theme_use("flatly")
        style.configure("TLabel", foreground=TEXT, font=("Microsoft YaHei UI", 10))
        style.configure("TButton", font=("Microsoft YaHei UI", 9))
        style.configure("TCheckbutton", foreground=TEXT, font=("Microsoft YaHei UI", 9))
        style.configure("TLabelframe.Label", foreground=TEXT, font=("Microsoft YaHei UI", 9, "bold"))
        style.configure("dark.TFrame", background=BG)
        style.configure("secondary.TFrame", background=BG)
        style.configure("light.TLabel", background=BG, foreground=TEXT)
        style.configure("secondary.TLabel", background=BG, foreground=MUTED)

        style.configure("Console.Surface.TFrame", background=SURFACE)
        style.configure("Console.Panel.TFrame", background=PANEL)
        style.configure("Console.Border.TFrame", background=BORDER)
        style.configure("Console.Toolbar.TFrame", background=SURFACE)
        style.configure(
            "Console.Title.TLabel",
            background=SURFACE,
            foreground=TEXT,
            font=("Microsoft YaHei UI", 15, "bold"),
        )
        style.configure(
            "Console.Section.TLabel",
            background=PANEL,
            foreground=TEXT,
            font=("Microsoft YaHei UI", 10, "bold"),
        )
        style.configure(
            "Console.Field.TLabel",
            background=PANEL,
            foreground=TEXT,
            font=("Microsoft YaHei UI", 9, "bold"),
        )
        style.configure(
            "Console.Text.TLabel",
            background=PANEL,
            foreground=TEXT,
            font=("Microsoft YaHei UI", 9),
        )
        style.configure(
            "Console.Hint.TLabel",
            background=PANEL,
            foreground=MUTED,
            font=("Microsoft YaHei UI", 8),
        )
        style.configure(
            "Console.Footer.TLabel",
            background=SURFACE,
            foreground=TEXT,
            font=("Microsoft YaHei UI", 8),
        )
        style.configure(
            "Console.Stopped.TLabel",
            background="#e5e7eb",
            foreground=STOPPED,
            font=("Microsoft YaHei UI", 11, "bold"),
            padding=(12, 7),
        )
        style.configure(
            "Console.Running.TLabel",
            background="#c7f3df",
            foreground="#045d41",
            font=("Microsoft YaHei UI", 11, "bold"),
            padding=(12, 7),
        )
        style.configure(
            "Console.TCheckbutton",
            background=PANEL,
            foreground=TEXT,
            font=("Microsoft YaHei UI", 9),
        )
        style.map(
            "Console.TCheckbutton",
            background=[("active", PANEL)],
            foreground=[("disabled", "#8b95a3"), ("active", TEXT)],
        )

    def _set_window_icon(self) -> None:
        icon = tk.PhotoImage(width=32, height=32)
        icon.put("#ffffff", to=(0, 0, 32, 32))
        icon.put(ACCENT, to=(6, 6, 10, 26))
        icon.put(ACCENT, to=(22, 6, 26, 26))
        for x, y in ((10, 6), (12, 9), (14, 12), (16, 15), (18, 18), (20, 21)):
            icon.put(ACCENT, to=(x, y, x + 4, y + 5))
        self._window_icon = icon
        self.root.iconphoto(True, icon)

    @staticmethod
    def _find_labelframe(parent: tk.Misc, text: str) -> ttk.Labelframe | None:
        for widget in parent.winfo_children():
            if isinstance(widget, ttk.Labelframe) and widget.cget("text") == text:
                return widget
            nested = LightControlConsoleApp._find_labelframe(widget, text)
            if nested is not None:
                return nested
        return None

    def _build_simple_view(self) -> None:
        self.simple_view.columnconfigure(0, weight=1)
        self.simple_view.rowconfigure(0, weight=1)
        surface = ttk.Frame(
            self.simple_view,
            padding=(10, 9),
            style="Console.Surface.TFrame",
        )
        surface.grid(row=0, column=0, sticky=tk.NSEW)
        surface.columnconfigure(0, weight=1)

        toolbar = ttk.Frame(surface, style="Console.Toolbar.TFrame")
        toolbar.grid(row=0, column=0, sticky=tk.EW)
        ttk.Label(toolbar, text="运行控制台", style="Console.Title.TLabel").pack(
            side=tk.LEFT
        )
        self.simple_state_badge = ttk.Label(
            toolbar,
            textvariable=self.run_state_text,
            style="Console.Stopped.TLabel",
        )
        self.simple_state_badge.pack(side=tk.LEFT, padx=(12, 0))
        ttk.Button(
            toolbar,
            text="全量模式",
            command=lambda: self._set_ui_mode("full"),
            bootstyle="primary-outline",
            width=9,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Checkbutton(
            toolbar,
            text="置顶",
            variable=self.always_on_top,
            command=self._set_always_on_top,
            bootstyle="success-round-toggle",
        ).pack(side=tk.RIGHT)

        target = self._panel(surface, row=1, pady=(9, 0), padding=(12, 9))
        target.columnconfigure(0, weight=1)
        ttk.Label(target, text="当前目标页面", style="Console.Section.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        self.simple_refresh_button = ttk.Button(
            target,
            text="刷新列表",
            command=self.refresh_windows,
            bootstyle="primary-outline",
            width=9,
        )
        self.simple_refresh_button.grid(row=0, column=1, sticky=tk.E)
        self.simple_window_combo = ttk.Combobox(
            target,
            textvariable=self.selected_window_name,
            state="readonly",
        )
        self.simple_window_combo.grid(
            row=1,
            column=0,
            columnspan=2,
            sticky=tk.EW,
            pady=(6, 0),
        )
        self.simple_window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)

        settings = self._panel(surface, row=2, pady=(8, 0), padding=(12, 9))
        settings.columnconfigure(0, weight=1)
        ttk.Label(settings, text="当前启用功能", style="Console.Section.TLabel").grid(
            row=0, column=0, sticky=tk.W
        )
        actions = ttk.Frame(settings, style="Console.Panel.TFrame")
        actions.grid(row=1, column=0, sticky=tk.EW, pady=(5, 7))
        for column in range(4):
            actions.columnconfigure(column, weight=1)
        for column, (text, variable) in enumerate(
            (
                ("鼠标移动", self.enable_move),
                ("单击", self.enable_click),
                ("滚轮", self.enable_wheel),
                ("键盘", self.enable_keyboard),
            )
        ):
            ttk.Checkbutton(
                actions,
                text=text,
                variable=variable,
                command=self._sync_keyboard_controls if variable is self.enable_keyboard else None,
                style="Console.TCheckbutton",
            ).grid(row=0, column=column, sticky=tk.W)

        ttk.Separator(settings).grid(row=2, column=0, sticky=tk.EW)
        form = ttk.Frame(settings, style="Console.Panel.TFrame")
        form.grid(row=3, column=0, sticky=tk.EW, pady=(6, 0))
        form.columnconfigure(0, minsize=105)
        form.columnconfigure(1, weight=1)

        ttk.Label(form, text="运行快捷键", style="Console.Field.TLabel").grid(
            row=0, column=0, sticky=tk.W, pady=4
        )
        shortcut = ttk.Frame(form, style="Console.Panel.TFrame")
        shortcut.grid(row=0, column=1, sticky=tk.W, pady=4)
        self.simple_modifier_controls = []
        for text, variable in self._modifier_options():
            control = ttk.Checkbutton(
                shortcut,
                text=text,
                variable=variable,
                command=self._sync_keyboard_controls,
                style="Console.TCheckbutton",
            )
            control.pack(side=tk.LEFT, padx=(0, 7))
            self.simple_modifier_controls.append(control)
        ttk.Label(shortcut, text="按键", style="Console.Field.TLabel").pack(
            side=tk.LEFT, padx=(5, 5)
        )
        self.simple_shortcut_key_combo = ttk.Combobox(
            shortcut,
            textvariable=self.shortcut_key,
            values=("", *RunConfig.SHORTCUT_KEYS),
            state="readonly",
            width=6,
        )
        self.simple_shortcut_key_combo.pack(side=tk.LEFT)

        ttk.Label(form, text="操作间隔", style="Console.Field.TLabel").grid(
            row=1, column=0, sticky=tk.W, pady=4
        )
        interval = ttk.Frame(form, style="Console.Panel.TFrame")
        interval.grid(row=1, column=1, sticky=tk.W, pady=4)
        ttk.Entry(interval, textvariable=self.min_delay, width=8).pack(side=tk.LEFT)
        ttk.Label(interval, text="至", style="Console.Text.TLabel").pack(
            side=tk.LEFT, padx=8
        )
        ttk.Entry(interval, textvariable=self.max_delay, width=8).pack(side=tk.LEFT)
        ttk.Label(interval, text="秒", style="Console.Text.TLabel").pack(
            side=tk.LEFT, padx=(7, 0)
        )

        ttk.Label(form, text="运行分钟", style="Console.Field.TLabel").grid(
            row=2, column=0, sticky=tk.W, pady=4
        )
        duration = ttk.Frame(form, style="Console.Panel.TFrame")
        duration.grid(row=2, column=1, sticky=tk.W, pady=4)
        ttk.Entry(duration, textvariable=self.duration_minutes, width=8).pack(side=tk.LEFT)
        ttk.Label(
            duration,
            text="0 表示持续运行；组合键留空时随机输入文本",
            style="Console.Hint.TLabel",
        ).pack(side=tk.LEFT, padx=(9, 0))
        self._sync_keyboard_controls()

        controls = ttk.Frame(surface, style="Console.Toolbar.TFrame")
        controls.grid(row=3, column=0, sticky=tk.EW, pady=(9, 0))
        for column in range(3):
            controls.columnconfigure(column, weight=1)
        self.simple_start_button = ttk.Button(
            controls,
            textvariable=self.start_button_text,
            command=self.start,
            bootstyle="success",
        )
        self.simple_start_button.grid(row=0, column=0, sticky=tk.EW, padx=(0, 4))
        ttk.Button(
            controls,
            text="停止",
            command=self.stop,
            bootstyle="danger-outline",
        ).grid(row=0, column=1, sticky=tk.EW, padx=4)
        self.simple_send_once_button = ttk.Button(
            controls,
            text="发送一次",
            command=self.send_once,
            bootstyle="primary-outline",
        )
        self.simple_send_once_button.grid(row=0, column=2, sticky=tk.EW, padx=(4, 0))

        display = ttk.Frame(surface, style="Console.Toolbar.TFrame")
        display.grid(row=4, column=0, sticky=tk.EW, pady=(8, 0))
        display.columnconfigure(0, weight=1)
        ttk.Scale(
            display,
            from_=40,
            to=100,
            variable=self.window_opacity,
            command=self._set_opacity,
            bootstyle="primary",
        ).grid(row=0, column=0, sticky=tk.EW, padx=(0, 10))
        ttk.Label(
            display,
            textvariable=self.opacity_text,
            style="Console.Footer.TLabel",
        ).grid(row=0, column=1, sticky=tk.E)

    def _panel(
        self,
        parent: ttk.Frame,
        *,
        row: int,
        pady: tuple[int, int],
        padding: tuple[int, int],
    ) -> ttk.Frame:
        border = ttk.Frame(parent, padding=1, style="Console.Border.TFrame")
        border.grid(row=row, column=0, sticky=tk.EW, pady=pady)
        border.columnconfigure(0, weight=1)
        panel = ttk.Frame(border, padding=padding, style="Console.Panel.TFrame")
        panel.grid(row=0, column=0, sticky=tk.EW)
        return panel

    def refresh_windows(self, *, prefer_test_page: bool = False) -> None:
        super().refresh_windows(prefer_test_page=prefer_test_page)
        self.simple_window_combo["values"] = list(self.windows_by_display_name)

    def _set_target_controls_enabled(self, enabled: bool) -> None:
        super()._set_target_controls_enabled(enabled)
        target_state = tk.NORMAL if enabled else tk.DISABLED
        self.simple_window_combo.configure(state="readonly" if enabled else "disabled")
        self.simple_refresh_button.configure(state=target_state)
        self.simple_send_once_button.configure(state=target_state)

    def _set_ui_mode(self, mode: str) -> None:
        self._simple_window_size = self.SIMPLE_SIZE
        super()._set_ui_mode(mode)
        if mode == "simple":
            self.shell.configure(padding=4)
            self.view_host.pack_configure(pady=0)
            self._resize_window(self.SIMPLE_SIZE, anchor_right=True)
        else:
            self.shell.configure(padding=12)
            self.view_host.pack_configure(pady=(10, 0))
        self._sync_keyboard_controls()
        suffix = "运行控制台" if mode == "simple" else "全量控制台"
        self.root.title(f"Nethard Music · {suffix}")
        self._configure_native_titlebar()

    def _update_run_visual(self, running: bool) -> None:
        self.full_status_label.configure(bootstyle="success" if running else "secondary")
        self.run_state_text.set("运行中" if running else "已停止")
        self.simple_state_badge.configure(
            style="Console.Running.TLabel" if running else "Console.Stopped.TLabel"
        )

    def _configure_native_titlebar(self) -> None:
        if sys.platform == "win32":
            self.root.after(120, self._apply_native_titlebar)

    def _apply_native_titlebar(self) -> None:
        try:
            self.root.update_idletasks()
            user32 = ctypes.windll.user32
            dwmapi = ctypes.windll.dwmapi
            hwnd = user32.GetAncestor(self.root.winfo_id(), 2)
            light_mode = ctypes.c_int(0)
            dwmapi.DwmSetWindowAttribute(
                hwnd, 20, ctypes.byref(light_mode), ctypes.sizeof(light_mode)
            )
            for attribute, value in (
                (34, colorref(BORDER)),
                (35, colorref("#f8fafc")),
                (36, colorref(TEXT)),
            ):
                color = ctypes.c_uint(value)
                dwmapi.DwmSetWindowAttribute(
                    hwnd,
                    attribute,
                    ctypes.byref(color),
                    ctypes.sizeof(color),
                )
            user32.RedrawWindow(hwnd, None, None, 0x0501)
        except (AttributeError, OSError, tk.TclError):
            return
