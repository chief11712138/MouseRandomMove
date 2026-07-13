from __future__ import annotations

import sys
import tkinter as tk

from mouse_random_move.app import MouseRandomMoveApp
from mouse_random_move.win32.dpi import enable_per_monitor_dpi_awareness


def main() -> None:
    if sys.platform != "win32":
        raise SystemExit("This application requires Windows 11.")

    enable_per_monitor_dpi_awareness()
    root = tk.Tk()
    MouseRandomMoveApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()

