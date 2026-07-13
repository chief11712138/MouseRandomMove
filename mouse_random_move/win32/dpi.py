from __future__ import annotations

import ctypes
import sys


def enable_per_monitor_dpi_awareness() -> None:
    if sys.platform != "win32":
        return

    user32 = ctypes.WinDLL("user32", use_last_error=True)
    try:
        # DPI_AWARENESS_CONTEXT_PER_MONITOR_AWARE_V2
        user32.SetProcessDpiAwarenessContext(ctypes.c_void_p(-4))
    except (AttributeError, OSError):
        try:
            user32.SetProcessDPIAware()
        except (AttributeError, OSError):
            pass
