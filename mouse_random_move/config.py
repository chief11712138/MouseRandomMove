from __future__ import annotations

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

    MIN_DELAY = 1
    MAX_DELAY = 3600
    MIN_DURATION = 0
    MAX_DURATION = 1440

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

        return cls(
            min_delay_seconds=minimum,
            max_delay_seconds=maximum,
            duration_minutes=duration,
            enable_move=bool(enable_move),
            enable_click=bool(enable_click),
            enable_wheel=bool(enable_wheel),
            enable_keyboard=bool(enable_keyboard),
        )

    @staticmethod
    def _parse_int(name: str, raw: str) -> int:
        try:
            return int(raw.strip())
        except (AttributeError, TypeError, ValueError) as exc:
            raise ConfigError(f"{name}必须是整数。") from exc

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
        return asdict(self)
