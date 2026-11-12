"""The outside programs the app runs: FFmpeg and ffprobe.

Every call goes through here so that one place decides which copy is used (a copy bundled next to the app wins over
one installed on the computer) and so that, on Windows, no black console window flashes up for each call."""
import shutil
import subprocess
import sys
from pathlib import Path

# On Windows a program started from a windowless app opens its own console window unless told not to.
NO_WINDOW = {"creationflags": subprocess.CREATE_NO_WINDOW} if sys.platform == "win32" else {}

MISSING_FFMPEG = ("FFmpeg isn't installed, and Audiobook Maker needs it to put the audiobook together. "
                  + ("Install it with Homebrew (brew install ffmpeg) and open the app again."
                     if sys.platform == "darwin" else
                     "Install it (winget install Gyan.FFmpeg) and open the app again." if sys.platform == "win32" else
                     "Install it with your package manager and open the app again."))


def _bundled_dirs():
    """Folders a packaged app keeps its own FFmpeg in: next to the executable, or in PyInstaller's unpack folder."""
    dirs = []
    if getattr(sys, "frozen", False):
        dirs.append(Path(sys.executable).parent)
        if hasattr(sys, "_MEIPASS"):
            dirs.append(Path(sys._MEIPASS))
    return dirs


def find(name):
    """The full path of an outside program (ffmpeg or ffprobe), or None if it can't be found."""
    exe = f"{name}.exe" if sys.platform == "win32" else name
    for folder in _bundled_dirs():
        if (folder / exe).is_file():
            return str(folder / exe)
    return shutil.which(name)


def missing():
    """The names of the programs the app needs but can't find, e.g. ["ffmpeg", "ffprobe"]; empty when all is well."""
    return [name for name in ("ffmpeg", "ffprobe") if not find(name)]


def cmd(args):
    """args with its first item (a program name) replaced by the full path to use, if one is found."""
    return [find(args[0]) or args[0], *args[1:]]


def run(args, **kwargs):
    """subprocess.run for FFmpeg or ffprobe, without a console window on Windows."""
    return subprocess.run(cmd(args), **NO_WINDOW, **kwargs)


def popen(args, **kwargs):
    """subprocess.Popen for FFmpeg or ffprobe, without a console window on Windows."""
    return subprocess.Popen(cmd(args), **NO_WINDOW, **kwargs)
