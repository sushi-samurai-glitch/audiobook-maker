"""The app's version, and the details a bug report needs."""
import platform
import sys
from importlib import metadata
from pathlib import Path

import paths
import tools

VERSION = "0.9.0"  # 0.x while the app is in beta; also set in Audiobook Maker.app/Contents/Info.plist
COPYRIGHT = "Copyright © 2026 sushi_samurai"
LICENSE_NOTE = "Free software under the GNU GPL, version 3. It comes with no warranty."
# The full licences of everything bundled: made by the build (packaging/build_mac.sh); from source, the summary.
NOTICES = [Path(__file__).with_name("THIRD-PARTY-LICENSES.txt"), Path(__file__).with_name("THIRD-PARTY-NOTICES.md")]


def _package(name):
    try:
        return metadata.version(name)
    except metadata.PackageNotFoundError:
        return "not installed"


def _ffmpeg():
    if not tools.find("ffmpeg"):
        return "not found"
    try:
        first = tools.run(["ffmpeg", "-version"], capture_output=True, text=True, timeout=10).stdout.splitlines()[0]
    except Exception:  # an ffmpeg that won't run or prints nothing
        return "found, version unknown"
    return first.removeprefix("ffmpeg version ").split(" Copyright")[0]


def _home_hidden(text):
    """text with the home folder written as ~, so a pasted report doesn't show the user's name."""
    home = str(Path.home())
    return text.replace(home, "~") if home and home != "/" else text


def details():
    """Plain text to paste into a bug report: the app's version, the computer and the parts it uses."""
    system = platform.system()
    os_name = {"Darwin": f"macOS {platform.mac_ver()[0]}", "Windows": f"Windows {platform.release()} "
               f"({platform.version()})"}.get(system, f"{system} {platform.release()}")
    lines = [
        f"Audiobook Maker {VERSION}",
        f"System: {os_name}, {platform.machine()}",
        f"Python: {sys.version.split()[0]}",
        f"FFmpeg: {_ffmpeg()}",
        f"Kokoro: {_package('kokoro')}",
        f"PyTorch: {_package('torch')}",
        f"Log file: {paths.log_file()}",
    ]
    return _home_hidden("\n".join(lines))
