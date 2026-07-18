from __future__ import annotations

import sys

import ttkbootstrap as ttk

from mouse_random_move.click_through_app import ClickThroughApp
from mouse_random_move.win32.dpi import enable_per_monitor_dpi_awareness


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("This application requires Windows 11.")

    enable_per_monitor_dpi_awareness()
    root = ttk.Window(themename="flatly")
    ClickThroughApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
