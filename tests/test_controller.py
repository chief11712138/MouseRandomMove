import random
import unittest
from unittest.mock import Mock

from mouse_random_move.config import RunConfig
from mouse_random_move.controller import ExecutionReceipt, SingleWindowController
from mouse_random_move.web.server import BrowserEventStore
from mouse_random_move.win32.input_sender import ActionResult


class ControllerConfirmationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.store = BrowserEventStore()
        self.controller = SingleWindowController(
            sender=object(),  # type: ignore[arg-type]
            browser_events=self.store,
            rng=random.Random(1),
        )

    def test_regular_page_does_not_report_confirmation_failure(self) -> None:
        receipt = ExecutionReceipt(
            result=ActionResult(
                action="move",
                description="move",
                expected_browser_event="mousemove",
                browser_confirmation_supported=False,
            ),
            browser_sequence_before=0,
        )
        self.assertIsNone(self.controller.is_confirmed(receipt))

    def test_test_page_event_can_be_confirmed(self) -> None:
        self.store.set_active(True)
        receipt = ExecutionReceipt(
            result=ActionResult(
                action="click",
                description="click",
                expected_browser_event="click",
                browser_confirmation_supported=True,
            ),
            browser_sequence_before=0,
        )
        self.store.add("click", {})
        self.assertTrue(self.controller.is_confirmed(receipt))


class ControllerShortcutTests(unittest.TestCase):
    def test_keyboard_action_forwards_modifier_shortcut(self) -> None:
        sender = Mock()
        sender.send.return_value = ActionResult(
            action="keyboard",
            description="Ctrl+Shift+M",
            expected_browser_event="keydown",
        )
        rng = Mock()
        rng.choice.return_value = "keyboard"
        controller = SingleWindowController(
            sender=sender,
            browser_events=BrowserEventStore(),
            rng=rng,
        )
        controller.lock_target(123)
        config = RunConfig(
            enable_move=False,
            enable_click=False,
            enable_wheel=False,
            enable_keyboard=True,
            shortcut_modifiers=("CTRL", "SHIFT"),
            shortcut_key="M",
        )

        controller.execute_once(config)

        sender.send.assert_called_once_with(
            123,
            "keyboard",
            shortcut="CTRL+SHIFT+M",
        )


if __name__ == "__main__":
    unittest.main()
