from __future__ import annotations

import random
import tkinter as tk
from datetime import datetime, timedelta
from math import ceil
from tkinter import messagebox

import ttkbootstrap as ttk

from .chrome_launcher import ChromeNotFoundError, open_test_page
from .config import ConfigError, RunConfig
from .controller import ExecutionReceipt, SingleWindowController
from .event_log import EventLogger
from .paths import frontend_root
from .web.server import TestPageServer
from .win32.chrome_windows import ChromeWindow, ChromeWindowService
from .win32.input_sender import TargetWindowError, WindowInputSender


def countdown_seconds(deadline: datetime, now: datetime | None = None) -> int:
    """Return a non-negative whole-second countdown for display."""
    current = now or datetime.now()
    return max(0, ceil((deadline - current).total_seconds()))


class MouseRandomMoveApp:
    STATUS_POLL_MS = 500
    COUNTDOWN_POLL_MS = 200
    CONFIRMATION_DELAY_MS = 850
    COMMAND_HISTORY_LIMIT = 500

    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Nethard Music")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = max(1000, min(1240, screen_width - 80))
        window_height = max(640, min(720, screen_height - 100))
        window_x = max(0, (screen_width - window_width) // 2)
        window_y = max(0, (screen_height - window_height) // 2)
        self.root.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
        self.root.minsize(min(960, window_width), min(600, window_height))
        self._full_window_size = (window_width, window_height)
        self._simple_window_size = (min(540, window_width), min(390, window_height))

        self.rng = random.Random()
        self.window_service = ChromeWindowService()
        self.server = TestPageServer(frontend_root())
        self.server.start()
        self.server.store.set_active(False)
        self.sender = WindowInputSender(self.window_service, self.rng)
        self.controller = SingleWindowController(self.sender, self.server.store, self.rng)
        self.logger = EventLogger()

        self.windows_by_display_name: dict[str, ChromeWindow] = {}
        self.running = False
        self.run_ends_at: datetime | None = None
        self.next_action_at: datetime | None = None
        self._schedule_job: str | None = None
        self._status_poll_job: str | None = None
        self._countdown_job: str | None = None
        self._command_count = 0

        self.selected_window_name = tk.StringVar(value="")
        self.min_delay = tk.StringVar(value="10")
        self.max_delay = tk.StringVar(value="20")
        self.duration_minutes = tk.StringVar(value="0")
        self.enable_move = tk.BooleanVar(value=True)
        self.enable_click = tk.BooleanVar(value=True)
        self.enable_wheel = tk.BooleanVar(value=True)
        self.enable_keyboard = tk.BooleanVar(value=True)
        self.shortcut_ctrl = tk.BooleanVar(value=False)
        self.shortcut_shift = tk.BooleanVar(value=False)
        self.shortcut_alt = tk.BooleanVar(value=False)
        self.shortcut_win = tk.BooleanVar(value=False)
        self.shortcut_key = tk.StringVar(value="")
        self.ui_mode = tk.StringVar(value="simple")
        self.always_on_top = tk.BooleanVar(value=True)
        self.window_opacity = tk.DoubleVar(value=95.0)
        self.opacity_text = tk.StringVar(value="透明度 95%")
        self.start_button_text = tk.StringVar(value="开始")

        self.status_text = tk.StringVar(value="状态：已停止")
        self.next_action_text = tk.StringVar(value="下一次操作：无")
        self.last_action_text = tk.StringVar(value="上一次操作：无")
        self.browser_status_text = tk.StringVar(value="测试页面事件：尚未连接")
        self.selected_status_text = tk.StringVar(value="目标：未选择")

        self._build_ui()
        self.refresh_windows()
        self._poll_browser_status()
        self._update_countdown()
        self.root.protocol("WM_DELETE_WINDOW", self.close)
        self.root.after(250, self.open_test_page)

    def _build_ui(self) -> None:
        self.root.configure(background="#111827")

        self.shell = ttk.Frame(self.root, padding=12, bootstyle="dark")
        self.shell.pack(fill=tk.BOTH, expand=True)

        self._build_header()

        self.view_host = ttk.Frame(self.shell, bootstyle="dark")
        self.view_host.pack(fill=tk.BOTH, expand=True, pady=(10, 0))

        self.full_view = ttk.Frame(self.view_host, bootstyle="dark")
        self.simple_view = ttk.Frame(self.view_host, bootstyle="dark")
        self._build_full_view()
        self._build_simple_view()
        self._sync_keyboard_controls()

        self._set_always_on_top()
        self._set_opacity(str(self.window_opacity.get()))
        self._update_run_visual(False)
        self._set_ui_mode(self.ui_mode.get())

    def _build_header(self) -> None:
        self.header = ttk.Frame(self.shell, bootstyle="dark")
        self.header.pack(fill=tk.X)
        header = self.header

        brand = ttk.Frame(header, bootstyle="dark")
        brand.pack(side=tk.LEFT)
        ttk.Label(
            brand,
            text="NETHARD MUSIC",
            font=("Segoe UI Semibold", 15),
            bootstyle="info",
        ).pack(anchor=tk.W)
        ttk.Label(
            brand,
            text="单窗口输入自动化 · 后台状态监视器",
            font=("Segoe UI", 9),
            bootstyle="secondary",
        ).pack(anchor=tk.W)

        mode_bar = ttk.Frame(header, bootstyle="dark")
        mode_bar.pack(side=tk.RIGHT)
        ttk.Button(
            mode_bar,
            text="说明",
            command=self._show_help,
            bootstyle="secondary-outline",
            width=6,
        ).pack(side=tk.RIGHT, padx=(6, 0))
        self.full_mode_button = ttk.Button(
            mode_bar,
            text="全量模式",
            command=lambda: self._set_ui_mode("full"),
            width=9,
        )
        self.full_mode_button.pack(side=tk.RIGHT, padx=(6, 0))
        self.simple_mode_button = ttk.Button(
            mode_bar,
            text="简易模式",
            command=lambda: self._set_ui_mode("simple"),
            width=9,
        )
        self.simple_mode_button.pack(side=tk.RIGHT)

    def _build_full_view(self) -> None:
        self.full_view.columnconfigure(0, weight=3)
        self.full_view.columnconfigure(1, weight=2)
        self.full_view.rowconfigure(1, weight=1)

        summary = ttk.Labelframe(
            self.full_view,
            text="实时状态",
            padding=10,
            bootstyle="info",
        )
        summary.grid(row=0, column=0, columnspan=2, sticky=tk.EW, pady=(0, 10))
        summary.columnconfigure(0, weight=1)
        summary.columnconfigure(1, weight=1)
        self.full_status_label = ttk.Label(
            summary,
            textvariable=self.status_text,
            font=("Segoe UI Semibold", 11),
            bootstyle="secondary",
        )
        self.full_status_label.grid(row=0, column=0, sticky=tk.W)
        ttk.Label(
            summary,
            textvariable=self.next_action_text,
            font=("Segoe UI Semibold", 11),
            bootstyle="warning",
        ).grid(row=0, column=1, sticky=tk.E)
        ttk.Label(
            summary,
            textvariable=self.selected_status_text,
            wraplength=900,
            bootstyle="light",
        ).grid(row=1, column=0, columnspan=2, sticky=tk.W, pady=(6, 0))

        left = ttk.Frame(self.full_view, bootstyle="dark")
        left.grid(row=1, column=0, sticky=tk.NSEW, padx=(0, 6))
        left.columnconfigure(0, weight=1)

        target = ttk.Labelframe(left, text="目标窗口", padding=10, bootstyle="primary")
        target.grid(row=0, column=0, sticky=tk.EW)
        target.columnconfigure(0, weight=1)
        self.window_combo = ttk.Combobox(
            target,
            textvariable=self.selected_window_name,
            state="readonly",
        )
        self.window_combo.grid(row=0, column=0, sticky=tk.EW)
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)
        self.refresh_button = ttk.Button(
            target,
            text="刷新",
            command=self.refresh_windows,
            bootstyle="primary-outline",
            width=7,
        )
        self.refresh_button.grid(row=0, column=1, padx=(8, 0))
        ttk.Button(
            target,
            text="测试页",
            command=self.open_test_page,
            bootstyle="info-outline",
            width=8,
        ).grid(row=0, column=2, padx=(8, 0))
        ttk.Label(
            target,
            text="输入会真实作用于所选 Chrome 页面，请避开重要数据窗口。",
            bootstyle="danger",
            font=("Segoe UI", 8),
        ).grid(row=1, column=0, columnspan=3, sticky=tk.W, pady=(6, 0))

        settings = ttk.Labelframe(left, text="运行参数", padding=10, bootstyle="secondary")
        settings.grid(row=1, column=0, sticky=tk.EW, pady=(8, 0))
        for column in (1, 3, 5):
            settings.columnconfigure(column, weight=1)

        ttk.Label(settings, text="最小间隔/秒").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.min_delay, width=7).grid(
            row=0, column=1, padx=(6, 12), sticky=tk.EW
        )
        ttk.Label(settings, text="最大间隔/秒").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.max_delay, width=7).grid(
            row=0, column=3, padx=(6, 12), sticky=tk.EW
        )
        ttk.Label(settings, text="运行分钟").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.duration_minutes, width=7).grid(
            row=0, column=5, padx=(6, 0), sticky=tk.EW
        )

        ttk.Label(settings, text="动作").grid(row=1, column=0, sticky=tk.W, pady=(10, 0))
        ttk.Checkbutton(
            settings,
            text="移动",
            variable=self.enable_move,
            bootstyle="info",
        ).grid(row=1, column=1, sticky=tk.W, pady=(10, 0))
        ttk.Checkbutton(
            settings,
            text="单击",
            variable=self.enable_click,
            bootstyle="info",
        ).grid(row=1, column=2, sticky=tk.W, pady=(10, 0))
        ttk.Checkbutton(
            settings,
            text="滚轮",
            variable=self.enable_wheel,
            bootstyle="info",
        ).grid(row=1, column=3, sticky=tk.W, pady=(10, 0))
        ttk.Checkbutton(
            settings,
            text="键盘",
            variable=self.enable_keyboard,
            command=self._sync_keyboard_controls,
            bootstyle="info",
        ).grid(row=1, column=4, sticky=tk.W, pady=(10, 0))

        ttk.Label(settings, text="运行快捷键").grid(
            row=2, column=0, sticky=tk.W, pady=(10, 0)
        )
        shortcut = ttk.Frame(settings)
        shortcut.grid(
            row=2,
            column=1,
            columnspan=5,
            sticky=tk.W,
            pady=(10, 0),
        )
        self.full_modifier_controls = []
        for text, variable in self._modifier_options():
            control = ttk.Checkbutton(
                shortcut,
                text=text,
                variable=variable,
                command=self._sync_keyboard_controls,
            )
            control.pack(side=tk.LEFT, padx=(0, 8))
            self.full_modifier_controls.append(control)
        self.full_shortcut_key_combo = ttk.Combobox(
            shortcut,
            textvariable=self.shortcut_key,
            values=("", *RunConfig.SHORTCUT_KEYS),
            state="readonly",
            width=6,
        )
        self.full_shortcut_key_combo.pack(side=tk.LEFT)
        ttk.Label(
            shortcut,
            text="组合键留空时随机输入；0 分钟表示持续运行。",
            bootstyle="secondary",
        ).pack(side=tk.LEFT, padx=(10, 0))

        action_bar = ttk.Labelframe(left, text="控制", padding=10, bootstyle="success")
        action_bar.grid(row=2, column=0, sticky=tk.EW, pady=(8, 0))
        self.start_button = ttk.Button(
            action_bar,
            textvariable=self.start_button_text,
            command=self.start,
            bootstyle="success",
            width=9,
        )
        self.start_button.pack(side=tk.LEFT)
        ttk.Button(
            action_bar,
            text="停止",
            command=self.stop,
            bootstyle="danger-outline",
            width=9,
        ).pack(side=tk.LEFT, padx=(8, 0))
        self.send_once_button = ttk.Button(
            action_bar,
            text="发送一次",
            command=self.send_once,
            bootstyle="primary-outline",
            width=10,
        )
        self.send_once_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            action_bar,
            text="清空检测",
            command=self._reset_browser_events,
            bootstyle="secondary-outline",
            width=10,
        ).pack(side=tk.LEFT, padx=(8, 0))

        preferences = ttk.Labelframe(
            left,
            text="窗口显示",
            padding=10,
            bootstyle="secondary",
        )
        preferences.grid(row=3, column=0, sticky=tk.EW, pady=(8, 0))
        preferences.columnconfigure(1, weight=1)
        ttk.Label(preferences, textvariable=self.opacity_text).grid(
            row=0, column=0, sticky=tk.W
        )
        ttk.Scale(
            preferences,
            from_=40,
            to=100,
            variable=self.window_opacity,
            command=self._set_opacity,
            bootstyle="info",
        ).grid(row=0, column=1, padx=10, sticky=tk.EW)
        ttk.Checkbutton(
            preferences,
            text="始终置顶",
            variable=self.always_on_top,
            command=self._set_always_on_top,
            bootstyle="success",
        ).grid(row=0, column=2, sticky=tk.E)

        right = ttk.Frame(self.full_view, bootstyle="dark")
        right.grid(row=1, column=1, sticky=tk.NSEW, padx=(6, 0))
        right.columnconfigure(0, weight=1)
        right.rowconfigure(1, weight=1)

        details = ttk.Labelframe(right, text="状态详情", padding=10, bootstyle="warning")
        details.grid(row=0, column=0, sticky=tk.EW)
        ttk.Label(
            details,
            textvariable=self.last_action_text,
            wraplength=400,
            bootstyle="light",
        ).pack(anchor=tk.W)
        ttk.Separator(details).pack(fill=tk.X, pady=8)
        ttk.Label(
            details,
            textvariable=self.browser_status_text,
            wraplength=400,
            bootstyle="secondary",
        ).pack(anchor=tk.W)

        command_frame = ttk.Labelframe(
            right,
            text="已发送命令",
            padding=8,
            bootstyle="secondary",
        )
        command_frame.grid(row=1, column=0, sticky=tk.NSEW, pady=(8, 0))
        command_frame.columnconfigure(0, weight=1)
        command_frame.rowconfigure(0, weight=1)
        self.command_log = tk.Text(
            command_frame,
            height=12,
            width=40,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Cascadia Mono", 9),
            background="#101820",
            foreground="#d8e2ef",
            insertbackground="#ffffff",
            relief=tk.FLAT,
            padx=8,
            pady=8,
        )
        command_scrollbar = ttk.Scrollbar(
            command_frame,
            orient=tk.VERTICAL,
            command=self.command_log.yview,
            bootstyle="round",
        )
        self.command_log.configure(yscrollcommand=command_scrollbar.set)
        self.command_log.grid(row=0, column=0, sticky=tk.NSEW)
        command_scrollbar.grid(row=0, column=1, sticky=tk.NS)

    def _build_simple_view(self) -> None:
        self.simple_view.columnconfigure(0, weight=1)
        self.simple_view.rowconfigure(0, weight=1)

        card = ttk.Frame(self.simple_view, padding=16, bootstyle="secondary")
        card.grid(row=0, column=0, sticky=tk.NSEW)
        card.columnconfigure(0, weight=1)

        top = ttk.Frame(card, bootstyle="secondary")
        top.grid(row=0, column=0, sticky=tk.EW)
        ttk.Label(
            top,
            text="后台状态",
            font=("Segoe UI Semibold", 10),
            bootstyle="info",
        ).pack(side=tk.LEFT)
        ttk.Button(
            top,
            text="全量",
            command=lambda: self._set_ui_mode("full"),
            bootstyle="info-outline",
            width=7,
        ).pack(side=tk.RIGHT, padx=(8, 0))
        ttk.Checkbutton(
            top,
            text="置顶",
            variable=self.always_on_top,
            command=self._set_always_on_top,
            bootstyle="success",
        ).pack(side=tk.RIGHT)

        self.simple_status_label = ttk.Label(
            card,
            textvariable=self.status_text,
            font=("Segoe UI Semibold", 13),
            bootstyle="secondary",
        )
        self.simple_status_label.grid(row=1, column=0, sticky=tk.W, pady=(12, 0))
        ttk.Label(
            card,
            textvariable=self.next_action_text,
            font=("Segoe UI Semibold", 20),
            bootstyle="warning",
        ).grid(row=2, column=0, sticky=tk.W, pady=(4, 0))

        ttk.Separator(card).grid(row=3, column=0, sticky=tk.EW, pady=10)
        ttk.Label(
            card,
            textvariable=self.selected_status_text,
            wraplength=440,
            bootstyle="light",
        ).grid(row=4, column=0, sticky=tk.W)
        ttk.Label(
            card,
            textvariable=self.last_action_text,
            wraplength=440,
            bootstyle="info",
        ).grid(row=5, column=0, sticky=tk.W, pady=(6, 0))
        ttk.Label(
            card,
            textvariable=self.browser_status_text,
            wraplength=440,
            bootstyle="secondary",
            font=("Segoe UI", 8),
        ).grid(row=6, column=0, sticky=tk.W, pady=(4, 0))

        footer = ttk.Frame(card, bootstyle="secondary")
        footer.grid(row=7, column=0, sticky=tk.EW, pady=(12, 0))
        self.simple_start_button = ttk.Button(
            footer,
            textvariable=self.start_button_text,
            command=self.start,
            bootstyle="success",
            width=9,
        )
        self.simple_start_button.pack(side=tk.LEFT)
        ttk.Button(
            footer,
            text="停止",
            command=self.stop,
            bootstyle="danger-outline",
            width=9,
        ).pack(side=tk.LEFT, padx=(8, 0))
        ttk.Label(footer, textvariable=self.opacity_text, bootstyle="secondary").pack(
            side=tk.RIGHT
        )
        ttk.Scale(
            footer,
            from_=40,
            to=100,
            variable=self.window_opacity,
            command=self._set_opacity,
            length=90,
            bootstyle="info",
        ).pack(side=tk.RIGHT, padx=(8, 8))

    def _modifier_options(self):
        return (
            ("Ctrl", self.shortcut_ctrl),
            ("Shift", self.shortcut_shift),
            ("Alt", self.shortcut_alt),
            ("Win", self.shortcut_win),
        )

    def _sync_keyboard_controls(self) -> None:
        enabled = bool(self.enable_keyboard.get())
        check_state = tk.NORMAL if enabled else tk.DISABLED
        combo_state = "readonly" if enabled else "disabled"
        for control in getattr(self, "simple_modifier_controls", []):
            control.configure(state=check_state)
        for control in getattr(self, "full_modifier_controls", []):
            control.configure(state=check_state)
        if hasattr(self, "simple_shortcut_key_combo"):
            self.simple_shortcut_key_combo.configure(state=combo_state)
        if hasattr(self, "full_shortcut_key_combo"):
            self.full_shortcut_key_combo.configure(state=combo_state)

    def _show_help(self) -> None:
        messagebox.showinfo(
            "使用说明",
            "全量模式：配置目标、间隔、动作和组合键，并查看完整日志。\n"
            "简易模式：只保留实时状态、倒计时、目标、最近动作和开始/停止按钮。\n\n"
            "模式切换只改变界面，不会重建控制器、取消后台计时器或改变已锁定目标。\n"
            "简易模式默认位于屏幕右上角并保持置顶；状态刷新不会抢占 Chrome 焦点。\n"
            "透明度可在 40%–100% 之间调整。\n\n"
            f"本地测试页面：{self.server.url}\n"
            f"日志目录：{self.logger.log_dir}",
            parent=self.root,
        )

    def _set_always_on_top(self) -> None:
        self.root.attributes("-topmost", bool(self.always_on_top.get()))

    def _set_opacity(self, raw_value: str) -> None:
        try:
            percent = round(float(raw_value))
        except (TypeError, ValueError):
            percent = 100
        percent = max(40, min(100, percent))
        self.opacity_text.set(f"透明度 {percent}%")
        self.root.attributes("-alpha", percent / 100)

    def _set_ui_mode(self, mode: str) -> None:
        if mode not in {"full", "simple"}:
            raise ValueError(f"Unknown UI mode: {mode}")

        # Only swap visible frames. Scheduled jobs, controller state and target lock stay intact.
        self.ui_mode.set(mode)
        self.full_view.pack_forget()
        self.simple_view.pack_forget()

        if mode == "simple":
            self.header.pack_forget()
            self.simple_view.pack(fill=tk.BOTH, expand=True)
            self.simple_mode_button.configure(bootstyle="info")
            self.full_mode_button.configure(bootstyle="secondary-outline")
            self.always_on_top.set(True)
            self._set_always_on_top()
            size = self._simple_window_size
        else:
            if not self.header.winfo_manager():
                self.header.pack(fill=tk.X, before=self.view_host)
            self.full_view.pack(fill=tk.BOTH, expand=True)
            self.full_mode_button.configure(bootstyle="info")
            self.simple_mode_button.configure(bootstyle="secondary-outline")
            size = self._full_window_size

        self._resize_window(size, anchor_right=mode == "simple")

    def _resize_window(self, size: tuple[int, int], *, anchor_right: bool) -> None:
        width, height = size
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        if anchor_right:
            x = max(0, screen_width - width - 24)
            y = min(48, max(0, screen_height - height))
            self.root.minsize(min(500, width), min(350, height))
        else:
            x = max(0, min(self.root.winfo_x(), screen_width - width))
            y = max(0, min(self.root.winfo_y(), screen_height - height))
            self.root.minsize(min(960, width), min(600, height))
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    def _update_run_visual(self, running: bool) -> None:
        bootstyle = "success" if running else "secondary"
        self.full_status_label.configure(bootstyle=bootstyle)
        self.simple_status_label.configure(bootstyle=bootstyle)

    def refresh_windows(self, *, prefer_test_page: bool = False) -> None:
        previous_hwnd = self._selected_window().hwnd if self._selected_window() else None
        try:
            windows = self.window_service.list_windows()
        except OSError as exc:
            messagebox.showerror("窗口枚举失败", str(exc), parent=self.root)
            return

        self.windows_by_display_name = {window.display_name: window for window in windows}
        names = list(self.windows_by_display_name)
        self.window_combo["values"] = names

        selected_name = ""
        if previous_hwnd is not None and not prefer_test_page:
            for name, window in self.windows_by_display_name.items():
                if window.hwnd == previous_hwnd:
                    selected_name = name
                    break
        if not selected_name:
            test_names = [
                name
                for name, window in self.windows_by_display_name.items()
                if window.is_test_page
            ]
            selected_name = (
                test_names[0] if prefer_test_page and test_names else (names[0] if names else "")
            )

        self.selected_window_name.set(selected_name)
        self._on_window_selected()

    def open_test_page(self) -> None:
        try:
            open_test_page(self.server.url)
        except ChromeNotFoundError as exc:
            messagebox.showerror("无法启动 Chrome", str(exc), parent=self.root)
            return
        self.root.after(1400, lambda: self.refresh_windows(prefer_test_page=True))

    def start(self) -> None:
        if self.running:
            return
        config = self._read_config_or_show_error()
        target = self._validate_selected_target()
        if config is None or target is None:
            return

        try:
            self.sender.focus(target.hwnd)
        except (OSError, TargetWindowError) as exc:
            self.last_action_text.set(f"无法自动聚焦目标窗口：{exc}")
            self.logger.write(
                "focus_error",
                {"target_title": target.title, "error": str(exc)},
            )
            messagebox.showerror("自动聚焦失败", str(exc), parent=self.root)
            return

        self.controller.lock_target(target.hwnd)
        self.server.store.set_active(True)
        self.running = True
        self.run_ends_at = (
            datetime.now() + timedelta(minutes=config.duration_minutes)
            if config.duration_minutes > 0
            else None
        )
        self._set_target_controls_enabled(False)
        self.start_button_text.set("运行中")
        self._update_run_visual(True)
        self.status_text.set(f"状态：运行中；已自动聚焦：{target.title}")
        self.logger.write(
            "start",
            {
                "target_title": target.title,
                "single_window": True,
                "auto_focused": True,
                **config.to_log_dict(),
            },
        )
        self._schedule_next(config)

    def stop(self, reason: str = "manual") -> None:
        if self._schedule_job is not None:
            try:
                self.root.after_cancel(self._schedule_job)
            except tk.TclError:
                pass
            self._schedule_job = None

        was_running = self.running
        self.running = False
        self.run_ends_at = None
        self.next_action_at = None
        self.server.store.set_active(False)
        self.controller.unlock_target()
        self._set_target_controls_enabled(True)
        self.start_button_text.set("开始")
        self._update_run_visual(False)
        self.status_text.set("状态：已停止")
        self.next_action_text.set("下一次操作：无")
        if was_running:
            self.logger.write("stop", {"reason": reason})

    def send_once(self) -> None:
        if self.running:
            messagebox.showinfo("当前正在运行", "请先停止连续运行，再执行单次发送。", parent=self.root)
            return
        config = self._read_config_or_show_error()
        target = self._validate_selected_target()
        if config is None or target is None:
            return

        self.controller.lock_target(target.hwnd)
        self.server.store.set_active(True)
        try:
            self._execute_action(config, stop_on_error=False)
        finally:
            self.root.after(self.CONFIRMATION_DELAY_MS + 350, lambda: self.server.store.set_active(False))
            self.controller.unlock_target()

    def _schedule_next(self, config: RunConfig) -> None:
        if not self.running:
            return
        remaining = self._remaining_seconds()
        if remaining is not None and remaining <= 0:
            self.stop(reason="duration_complete")
            self.last_action_text.set("上一次操作：达到设定运行时长")
            return

        delay = self.rng.randint(config.min_delay_seconds, config.max_delay_seconds)
        if remaining is not None:
            delay = min(delay, max(1, remaining))
        self.next_action_at = datetime.now() + timedelta(seconds=delay)
        self._refresh_countdown_text()
        self._schedule_job = self.root.after(delay * 1000, self._on_action_due)

    def _on_action_due(self) -> None:
        self._schedule_job = None
        self.next_action_at = None
        if not self.running:
            return
        self.next_action_text.set("下一次操作：正在执行")
        config = self._read_config_or_show_error()
        if config is None:
            self.stop(reason="invalid_config")
            return
        if not self._execute_action(config, stop_on_error=True):
            return
        self._schedule_next(config)

    def _execute_action(self, config: RunConfig, *, stop_on_error: bool) -> bool:
        try:
            receipt = self.controller.execute_once(config)
        except (OSError, RuntimeError, TargetWindowError, ValueError) as exc:
            self.last_action_text.set(f"操作失败：{exc}")
            self.logger.write("action_error", {"error": str(exc)})
            if stop_on_error:
                self.stop(reason="target_error")
            else:
                messagebox.showerror("发送失败", str(exc), parent=self.root)
            return False

        result = receipt.result
        if result.browser_confirmation_supported:
            self.last_action_text.set(f"已发送：{result.description}；等待页面确认")
        else:
            self.last_action_text.set(f"已发送到目标 Chrome 窗口：{result.description}")
        self.logger.write("action_sent", result.to_log_dict())
        self._append_command(result.action, result.description)
        if result.browser_confirmation_supported:
            self.root.after(
                self.CONFIRMATION_DELAY_MS,
                lambda current=receipt: self._verify_receipt(current),
            )
        return True

    def _verify_receipt(self, receipt: ExecutionReceipt) -> None:
        confirmed = self.controller.is_confirmed(receipt)
        if confirmed is None:
            self.last_action_text.set(f"已发送到目标 Chrome 窗口：{receipt.result.description}")
        elif confirmed:
            self.last_action_text.set(f"页面已确认：{receipt.result.description}")
        else:
            self.last_action_text.set(
                f"未收到对应页面事件：{receipt.result.description}。"
                "请确认选中的窗口位于前台且测试区域可见。"
            )
        self.logger.write(
            "action_confirmation",
            {
                "action": receipt.result.action,
                "expected_event": receipt.result.expected_browser_event,
                "confirmed": confirmed,
            },
        )

    def _validate_selected_target(self) -> ChromeWindow | None:
        target = self._selected_window()
        if target is None:
            messagebox.showerror("未选择窗口", "请先刷新并选择一个 Chrome 窗口。", parent=self.root)
            return None
        current = self.window_service.inspect(target.hwnd)
        if current is None:
            messagebox.showerror("窗口不可用", "目标窗口已经关闭，请刷新列表。", parent=self.root)
            return None
        return current

    def _selected_window(self) -> ChromeWindow | None:
        return self.windows_by_display_name.get(self.selected_window_name.get())

    def _on_window_selected(self, _event: object | None = None) -> None:
        target = self._selected_window()
        if target is None:
            self.selected_status_text.set("目标：未检测到可见 Chrome 窗口")
        elif target.is_test_page:
            self.selected_status_text.set(f"目标：{target.title}；支持页面事件确认")
        else:
            self.selected_status_text.set(
                f"目标：{target.title}；可接收输入（普通页面不提供事件确认）"
            )

    def _read_config_or_show_error(self) -> RunConfig | None:
        try:
            config = RunConfig.from_values(
                min_delay=self.min_delay.get(),
                max_delay=self.max_delay.get(),
                duration_minutes=self.duration_minutes.get(),
                enable_move=self.enable_move.get(),
                enable_click=self.enable_click.get(),
                enable_wheel=self.enable_wheel.get(),
                enable_keyboard=self.enable_keyboard.get(),
                shortcut_ctrl=self.shortcut_ctrl.get(),
                shortcut_shift=self.shortcut_shift.get(),
                shortcut_alt=self.shortcut_alt.get(),
                shortcut_win=self.shortcut_win.get(),
                shortcut_key=self.shortcut_key.get(),
            )
        except ConfigError as exc:
            messagebox.showerror("设置错误", str(exc), parent=self.root)
            return None

        self.min_delay.set(str(config.min_delay_seconds))
        self.max_delay.set(str(config.max_delay_seconds))
        self.duration_minutes.set(str(config.duration_minutes))
        return config

    def _remaining_seconds(self) -> int | None:
        if self.run_ends_at is None:
            return None
        return max(0, int((self.run_ends_at - datetime.now()).total_seconds() + 0.999))

    def _append_command(self, action: str, description: str) -> None:
        timestamp = datetime.now().strftime("%H:%M:%S")
        line = f"[{timestamp}] {action.upper():<8} {description}\n"
        self.command_log.configure(state=tk.NORMAL)
        self.command_log.insert(tk.END, line)
        self._command_count += 1
        if self._command_count > self.COMMAND_HISTORY_LIMIT:
            self.command_log.delete("1.0", "2.0")
            self._command_count -= 1
        self.command_log.configure(state=tk.DISABLED)
        self.command_log.see(tk.END)

    def _refresh_countdown_text(self) -> None:
        if not self.running or self.next_action_at is None:
            return
        remaining = countdown_seconds(self.next_action_at)
        if remaining > 0:
            self.next_action_text.set(f"下一次操作：{remaining} 秒后")
        else:
            self.next_action_text.set("下一次操作：即将执行")

    def _update_countdown(self) -> None:
        self._refresh_countdown_text()
        self._countdown_job = self.root.after(
            self.COUNTDOWN_POLL_MS,
            self._update_countdown,
        )

    def _set_target_controls_enabled(self, enabled: bool) -> None:
        target_state = tk.NORMAL if enabled else tk.DISABLED
        self.window_combo.configure(state="readonly" if enabled else "disabled")
        self.refresh_button.configure(state=target_state)
        self.send_once_button.configure(state=target_state)
        self.start_button.configure(state=target_state)
        self.simple_start_button.configure(state=target_state)

    def _poll_browser_status(self) -> None:
        snapshot = self.server.store.snapshot()
        last = snapshot.get("last_event")
        if last is None:
            self.browser_status_text.set("测试页面事件：尚未连接")
        else:
            counts = snapshot.get("counts", {})
            summary = ", ".join(f"{name}={count}" for name, count in sorted(counts.items()))
            self.browser_status_text.set(
                f"测试页面事件：最后为 {last['event_type']}；总序号 {snapshot['sequence']}；{summary}"
            )
        self._status_poll_job = self.root.after(self.STATUS_POLL_MS, self._poll_browser_status)

    def _reset_browser_events(self) -> None:
        self.server.store.reset()
        self.browser_status_text.set("测试页面事件：记录已清空")

    def close(self) -> None:
        self.stop(reason="application_close")
        if self._countdown_job is not None:
            try:
                self.root.after_cancel(self._countdown_job)
            except tk.TclError:
                pass
            self._countdown_job = None

        if self._status_poll_job is not None:
            try:
                self.root.after_cancel(self._status_poll_job)
            except tk.TclError:
                pass
            self._status_poll_job = None
        self.server.stop()
        self.root.destroy()
