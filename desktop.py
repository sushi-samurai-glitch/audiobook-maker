"""What differs between macOS, Windows and Linux: opening files, showing them in the file manager, and their names."""
import os
import subprocess
import sys
from pathlib import Path

IS_MAC = sys.platform == "darwin"
IS_WINDOWS = sys.platform == "win32"
MOD_KEY = "Command" if IS_MAC else "Control"  # for Tk key bindings, e.g. <Command-Return>
MOD = "⌘" if IS_MAC else "Ctrl+"  # in words, e.g. ⌘F
SELECT_ALL = "⌘A" if IS_MAC else "Ctrl+A"
FILE_MANAGER = "Finder" if IS_MAC else "Explorer" if IS_WINDOWS else "the file manager"
TEXT_EDITOR = "TextEdit" if IS_MAC else "Notepad" if IS_WINDOWS else "your text editor"
VENV_PYTHON = r".venv\Scripts\python.exe" if IS_WINDOWS else ".venv/bin/python"


def open_text(path):
    """Open a text file in the default text editor."""
    path = str(path)
    if IS_MAC:
        subprocess.run(["open", "-t", path], check=False)
    elif IS_WINDOWS:
        os.startfile(path)  # noqa: S606  (the file's default app; Notepad for .txt)
    else:
        subprocess.run(["xdg-open", path], check=False)


def reveal(path):
    """Show the file or folder in Finder (or Explorer, or the file manager)."""
    path = Path(path)
    if IS_MAC:
        subprocess.run(["open", "-R", str(path)], check=False)
    elif IS_WINDOWS:
        subprocess.run(["explorer", f"/select,{path}"], check=False)
    else:
        subprocess.run(["xdg-open", str(path.parent)], check=False)


def install_hint(package):
    """How to install an optional package, in words for the log."""
    shell = "PowerShell" if IS_WINDOWS else "Terminal"
    return f"In {shell}, in the project folder, run: uv pip install --python {VENV_PYTHON} {package}"
