from __future__ import annotations

import string
from dataclasses import asdict, dataclass


class ConfigError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class RunConfig:
    min_delay_seconds: int = 10
    max_delay_seconds: int = 20
    duration_minutes: int = 0
    enable_move: bool = True
    enable_click: bool = True
    enable_wheel: bool = True
    enable_keyboard: bool = True
    shortcut_modifiers: tuple[str, ...] = ()
    shortcut_key: str = ""

    MIN_DELAY = 1
    MAX_DELAY = 3600
    MIN_DURATION = 0
    MAX_DURATION = 1440
    MODIFIERS = ("CTRL", "SHIFT", "ALT", "WIN")
    SHORTCUT_KEYS = tuple(string.ascii_uppercase + string.digits)

    @classmethod
    def from_values(
        cls,
        *,
        min_delay: str,
        max_delay: str,
        duration_minutes: str,
        enable_move: bool,
        enable_click: bool,
        enable_wheel: bool,
        enable_keyboard: bool,
        shortcut_ctrl: bool = False,
        shortcut_shift: bool = False,
        shortcut_alt: bool = False,
        shortcut_win: bool = False,
        shortcut_key: str = "",
    ) -> "RunConfig":
        minimum = cls._parse_int("最小间隔", min_delay)
        maximum = cls._parse_int("最大间隔", max_delay)
        duration = cls._parse_int("运行分钟数", duration_minutes)

        if not cls.MIN_DELAY <= minimum <= cls.MAX_DELAY:
            raise ConfigError(f"最小间隔必须在 {cls.MIN_DELAY}-{cls.MAX_DELAY} 秒之间。")
        if not cls.MIN_DELAY <= maximum <= cls.MAX_DELAY:
            raise ConfigError(f"最大间隔必须在 {cls.MIN_DELAY}-{cls.MAX_DELAY} 秒之间。")
        if minimum > maximum:
            minimum, maximum = maximum, minimum
        if not cls.MIN_DURATION <= duration <= cls.MAX_DURATION:
            raise ConfigError(
                f"运行分钟数必须在 {cls.MIN_DURATION}-{cls.MAX_DURATION} 分钟之间。"
            )

        enabled = (enable_move, enable_click, enable_wheel, enable_keyboard)
        if not any(enabled):
            raise ConfigError("至少需要启用一种测试动作。")

        modifiers: tuple[str, ...] = ()
        key = ""
        if enable_keyboard:
            raw_key = shortcut_key
            if not isinstance(raw_key, str):
                raise ConfigError("快捷键主键必须是文本。")
            key = raw_key.strip().upper()
            if key and key not in cls.SHORTCUT_KEYS:
                raise ConfigError("快捷键主键必须为空，或选择 A-Z、0-9 中的一个按键。")
            modifier_values = (
                ("CTRL", shortcut_ctrl),
                ("SHIFT", shortcut_shift),
                ("ALT", shortcut_alt),
                ("WIN", shortcut_win),
            )
            modifiers = tuple(name for name, selected in modifier_values if selected)
            if key and not modifiers:
                raise ConfigError("配置快捷键时，至少需要选择 Ctrl、Shift、Alt 或 Win。")
            if modifiers and not key:
                raise ConfigError("选择修饰键后，还需要选择一个 A-Z 或 0-9 主键。")

        return cls(
            min_delay_seconds=minimum,
            max_delay_seconds=maximum,
            duration_minutes=duration,
            enable_move=bool(enable_move),
            enable_click=bool(enable_click),
            enable_wheel=bool(enable_wheel),
            enable_keyboard=bool(enable_keyboard),
            shortcut_modifiers=modifiers,
            shortcut_key=key,
        )

    @staticmethod
    def _parse_int(name: str, raw: str) -> int:
        try:
            return int(raw.strip())
        except (AttributeError, TypeError, ValueError) as exc:
            raise ConfigError(f"{name}必须是整数。") from exc

    @property
    def shortcut_text(self) -> str:
        if not self.shortcut_key:
            return ""
        return "+".join((*self.shortcut_modifiers, self.shortcut_key))

    def enabled_actions(self) -> tuple[str, ...]:
        actions: list[str] = []
        if self.enable_move:
            actions.append("move")
        if self.enable_click:
            actions.append("click")
        if self.enable_wheel:
            actions.append("wheel")
        if self.enable_keyboard:
            actions.append("keyboard")
        return tuple(actions)

    def to_log_dict(self) -> dict[str, object]:
        data = asdict(self)
        data["shortcut_text"] = self.shortcut_text
        return data
