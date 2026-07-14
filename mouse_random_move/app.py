from __future__ import annotations

import random
import tkinter as tk
from datetime import datetime, timedelta
from math import ceil
from tkinter import messagebox, ttk

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
        self.root.title("Mouse Random Move")
        screen_width = self.root.winfo_screenwidth()
        screen_height = self.root.winfo_screenheight()
        window_width = min(1000, max(820, screen_width - 80))
        window_height = min(900, max(700, screen_height - 100))
        window_x = max(0, (screen_width - window_width) // 2)
        window_y = max(0, (screen_height - window_height) // 2)
        self.root.geometry(f"{window_width}x{window_height}+{window_x}+{window_y}")
        self.root.minsize(min(900, window_width), min(760, window_height))

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
        outer = ttk.Frame(self.root, padding=16)
        outer.pack(fill=tk.BOTH, expand=True)

        ttk.Label(
            outer,
            text="Mouse Random Move",
            font=("Segoe UI", 16, "bold"),
        ).pack(anchor=tk.W)
        ttk.Label(
            outer,
            text="单窗口模式：每次动作只发送到当前选中的一个 Chrome 窗口",
        ).pack(anchor=tk.W, pady=(2, 12))

        target_frame = ttk.LabelFrame(outer, text="Chrome 目标窗口", padding=12)
        target_frame.pack(fill=tk.X)
        target_frame.columnconfigure(1, weight=1)

        ttk.Label(target_frame, text="窗口名称").grid(row=0, column=0, sticky=tk.W)
        self.window_combo = ttk.Combobox(
            target_frame,
            textvariable=self.selected_window_name,
            state="readonly",
            width=78,
        )
        self.window_combo.grid(row=0, column=1, padx=(8, 8), sticky=tk.EW)
        self.window_combo.bind("<<ComboboxSelected>>", self._on_window_selected)

        self.refresh_button = ttk.Button(
            target_frame,
            text="刷新列表",
            command=self.refresh_windows,
        )
        self.refresh_button.grid(row=0, column=2, padx=(0, 8))

        ttk.Button(
            target_frame,
            text="打开配套测试页",
            command=self.open_test_page,
        ).grid(row=0, column=3)

        ttk.Label(
            target_frame,
            textvariable=self.selected_status_text,
            wraplength=820,
        ).grid(row=1, column=0, columnspan=4, pady=(10, 0), sticky=tk.W)
        ttk.Label(
            target_frame,
            text="注意：输入会真实作用于选中的 Chrome 页面，请避免选择含有重要数据的窗口。",
            foreground="#8b0000",
        ).grid(row=2, column=0, columnspan=4, pady=(6, 0), sticky=tk.W)

        settings = ttk.LabelFrame(outer, text="运行设置", padding=12)
        settings.pack(fill=tk.X, pady=(12, 0))

        ttk.Label(settings, text="最小间隔（秒）").grid(row=0, column=0, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.min_delay, width=10).grid(
            row=0, column=1, padx=(8, 24), sticky=tk.W
        )
        ttk.Label(settings, text="最大间隔（秒）").grid(row=0, column=2, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.max_delay, width=10).grid(
            row=0, column=3, padx=(8, 24), sticky=tk.W
        )
        ttk.Label(settings, text="运行分钟数").grid(row=0, column=4, sticky=tk.W)
        ttk.Entry(settings, textvariable=self.duration_minutes, width=10).grid(
            row=0, column=5, padx=(8, 0), sticky=tk.W
        )

        ttk.Label(settings, text="动作类型").grid(row=1, column=0, pady=(12, 0), sticky=tk.W)
        ttk.Checkbutton(settings, text="移动", variable=self.enable_move).grid(
            row=1, column=1, pady=(12, 0), sticky=tk.W
        )
        ttk.Checkbutton(settings, text="单击", variable=self.enable_click).grid(
            row=1, column=2, pady=(12, 0), sticky=tk.W
        )
        ttk.Checkbutton(settings, text="滚轮", variable=self.enable_wheel).grid(
            row=1, column=3, pady=(12, 0), sticky=tk.W
        )
        ttk.Checkbutton(settings, text="键盘", variable=self.enable_keyboard).grid(
            row=1, column=4, pady=(12, 0), sticky=tk.W
        )
        ttk.Label(settings, text="0 分钟表示持续运行").grid(
            row=1, column=5, pady=(12, 0), sticky=tk.W
        )

        controls = ttk.Frame(outer)
        controls.pack(fill=tk.X, pady=12)
        self.start_button = ttk.Button(controls, text="开始", command=self.start)
        self.start_button.pack(side=tk.LEFT)
        ttk.Button(controls, text="停止", command=self.stop).pack(side=tk.LEFT, padx=(8, 0))
        self.send_once_button = ttk.Button(
            controls,
            text="发送一次",
            command=self.send_once,
        )
        self.send_once_button.pack(side=tk.LEFT, padx=(8, 0))
        ttk.Button(
            controls,
            text="清空页面检测记录",
            command=self._reset_browser_events,
        ).pack(side=tk.LEFT, padx=(8, 0))

        status = ttk.LabelFrame(outer, text="运行状态", padding=12)
        status.pack(fill=tk.X)
        ttk.Label(status, textvariable=self.status_text).pack(anchor=tk.W)
        ttk.Label(status, textvariable=self.next_action_text).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(
            status,
            textvariable=self.last_action_text,
            wraplength=930,
        ).pack(anchor=tk.W, pady=(4, 0))
        ttk.Label(
            status,
            textvariable=self.browser_status_text,
            wraplength=930,
        ).pack(anchor=tk.W, pady=(4, 0))

        command_frame = ttk.LabelFrame(outer, text="已发送命令", padding=8)
        command_frame.pack(fill=tk.X, pady=(12, 0))
        command_frame.columnconfigure(0, weight=1)
        command_frame.rowconfigure(0, weight=1)
        self.command_log = tk.Text(
            command_frame,
            height=8,
            wrap=tk.WORD,
            state=tk.DISABLED,
            font=("Consolas", 10),
        )
        command_scrollbar = ttk.Scrollbar(
            command_frame,
            orient=tk.VERTICAL,
            command=self.command_log.yview,
        )
        self.command_log.configure(yscrollcommand=command_scrollbar.set)
        self.command_log.grid(row=0, column=0, sticky=tk.NSEW)
        command_scrollbar.grid(row=0, column=1, sticky=tk.NS)

        explanation = ttk.LabelFrame(outer, text="工作方式", padding=12)
        explanation.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        text = tk.Text(explanation, height=10, wrap=tk.WORD, state=tk.NORMAL)
        text.pack(fill=tk.BOTH, expand=True)
        text.insert(
            "1.0",
            "1. 程序启动后会自动打开并选中配套测试页。\n"
            "2. 在测试页点击“发送一次”，确认所选动作和事件回传正常。\n"
            "3. 验证后关闭测试页，点击“刷新列表”并选择需要操作的 Chrome 窗口。\n"
            "4. 配置动作与间隔后点击“开始”；普通页面会显示动作已发送。\n"
            "5. 每次仅锁定并操作一个窗口；运行中无法切换目标。\n"
            "6. 勾选“键盘”后，程序会随机输入 3-6 个小写字母或数字。\n"
            "7. 若目标窗口关闭或不再是 Chrome 窗口，任务会停止。\n\n"
            f"本地测试页面：{self.server.url}\n"
            f"日志目录：{self.logger.log_dir}",
        )
        text.configure(state=tk.DISABLED)

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

        self.controller.lock_target(target.hwnd)
        self.server.store.set_active(True)
        self.running = True
        self.run_ends_at = (
            datetime.now() + timedelta(minutes=config.duration_minutes)
            if config.duration_minutes > 0
            else None
        )
        self._set_target_controls_enabled(False)
        self.start_button.configure(text="运行中")
        self.status_text.set(f"状态：运行中；单一目标：{target.title}")
        self.logger.write(
            "start",
            {"target_title": target.title, "single_window": True, **config.to_log_dict()},
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
        self.start_button.configure(text="开始")
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
        self.window_combo.configure(state="readonly" if enabled else "disabled")
        self.refresh_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)
        self.send_once_button.configure(state=tk.NORMAL if enabled else tk.DISABLED)

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


