from __future__ import annotations

import random
from dataclasses import dataclass

from .config import RunConfig
from .web.server import BrowserEventStore
from .win32.input_sender import ActionResult, WindowInputSender


@dataclass(frozen=True, slots=True)
class ExecutionReceipt:
    result: ActionResult
    browser_sequence_before: int


class SingleWindowController:
    """Owns exactly one selected HWND for the current run."""

    def __init__(
        self,
        sender: WindowInputSender,
        browser_events: BrowserEventStore,
        rng: random.Random,
    ) -> None:
        self.sender = sender
        self.browser_events = browser_events
        self.rng = rng
        self._target_hwnd: int | None = None
        self._last_action: str | None = None

    @property
    def target_hwnd(self) -> int | None:
        return self._target_hwnd

    def lock_target(self, hwnd: int) -> None:
        self._target_hwnd = hwnd
        self._last_action = None

    def unlock_target(self) -> None:
        self._target_hwnd = None
        self._last_action = None

    def execute_once(self, config: RunConfig) -> ExecutionReceipt:
        if self._target_hwnd is None:
            raise RuntimeError("No target window is locked.")

        enabled_actions = config.enabled_actions()
        candidates = tuple(action for action in enabled_actions if action != self._last_action)
        action = self.rng.choice(candidates or enabled_actions)
        sequence = int(self.browser_events.snapshot()["sequence"])
        result = self.sender.send(self._target_hwnd, action)
        self._last_action = action
        return ExecutionReceipt(result=result, browser_sequence_before=sequence)

    def is_confirmed(self, receipt: ExecutionReceipt) -> bool | None:
        if not receipt.result.browser_confirmation_supported:
            return None
        return self.browser_events.has_event_after(
            receipt.result.expected_browser_event,
            receipt.browser_sequence_before,
        )
