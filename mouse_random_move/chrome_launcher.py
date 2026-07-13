from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path


class ChromeNotFoundError(RuntimeError):
    pass


def find_chrome_executable() -> Path:
    candidates: list[Path] = []

    for executable_name in ("chrome.exe", "chrome"):
        resolved = shutil.which(executable_name)
        if resolved:
            candidates.append(Path(resolved))

    for environment_name in ("PROGRAMFILES", "PROGRAMFILES(X86)", "LOCALAPPDATA"):
        base = os.environ.get(environment_name)
        if base:
            candidates.append(Path(base) / "Google" / "Chrome" / "Application" / "chrome.exe")

    for candidate in candidates:
        if candidate.is_file():
            return candidate

    raise ChromeNotFoundError("未找到 Google Chrome。请先在 Windows 11 虚拟机中安装 Chrome。")


def open_test_page(url: str) -> None:
    chrome = find_chrome_executable()
    subprocess.Popen(
        [str(chrome), "--new-window", url],
        close_fds=True,
        creationflags=getattr(subprocess, "CREATE_NEW_PROCESS_GROUP", 0),
    )
