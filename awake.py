"""Keep the computer from going to sleep while a book is being made.

Only idle sleep is stopped: the screen may still turn off, and closing a laptop's lid still puts it to sleep.
start() and stop() are called from the main thread (Windows ties the request to the thread that makes it)."""
import ctypes
import os
import subprocess
import sys

_ES_CONTINUOUS = 0x80000000
_ES_SYSTEM_REQUIRED = 0x00000001


class KeepAwake:
    def __init__(self):
        self._proc = None
        self.active = False

    def start(self):
        """Stop idle sleep until stop() is called or the app quits. Does nothing if it is already on."""
        if self.active:
            return
        try:
            if sys.platform == "darwin":
                # caffeinate -i holds off idle sleep; -w ends it when this app exits, even after a crash.
                self._proc = subprocess.Popen(["caffeinate", "-i", "-w", str(os.getpid())],
                                              stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            elif sys.platform == "win32":
                ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS | _ES_SYSTEM_REQUIRED)
            else:
                return  # Linux: not supported; the computer may sleep as usual
        except OSError as e:
            print(f"Couldn't keep the computer awake: {e}", file=sys.stderr)
            return
        self.active = True

    def stop(self):
        """Let the computer sleep as usual again."""
        if not self.active:
            return
        self.active = False
        if self._proc:
            self._proc.terminate()
            self._proc = None
        elif sys.platform == "win32":
            ctypes.windll.kernel32.SetThreadExecutionState(_ES_CONTINUOUS)
