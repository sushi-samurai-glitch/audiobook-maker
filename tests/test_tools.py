"""Tests for tools.py, version.py and awake.py: finding FFmpeg, bug-report details and keeping the computer awake."""
import subprocess
import sys
from pathlib import Path

import awake
import paths
import tools
import version


def test_missing_lists_what_cannot_be_found(monkeypatch):
    monkeypatch.setattr(tools.shutil, "which", lambda name: None if name == "ffprobe" else f"/usr/bin/{name}")
    assert tools.missing() == ["ffprobe"]


def test_a_bundled_copy_wins(monkeypatch, tmp_path):
    exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    (tmp_path / exe).write_text("")
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    monkeypatch.setattr(sys, "executable", str(tmp_path / "Audiobook Maker"))
    monkeypatch.setattr(tools.shutil, "which", lambda name: "/usr/bin/ffmpeg")
    assert tools.find("ffmpeg") == str(tmp_path / exe)
    assert tools.cmd(["ffmpeg", "-version"]) == [str(tmp_path / exe), "-version"]


def test_run_hides_the_console_window_on_windows(monkeypatch):
    seen = {}
    monkeypatch.setattr(tools.subprocess, "run", lambda args, **kw: seen.update(kw))
    monkeypatch.setattr(tools, "NO_WINDOW", {"creationflags": 0x08000000})
    tools.run(["ffmpeg", "-version"], check=True)
    assert seen == {"creationflags": 0x08000000, "check": True}


def test_details_name_the_version_and_hide_the_home_folder(monkeypatch):
    monkeypatch.setattr(paths, "log_file", lambda: Path.home() / "Logs" / "app.log")
    text = version.details()
    assert text.startswith(f"Audiobook Maker {version.VERSION}\n")
    assert "FFmpeg:" in text and str(Path.home()) not in text and "~/Logs/app.log" in text.replace("\\", "/")


def test_keep_awake_on_a_mac_runs_caffeinate_until_stopped(monkeypatch):
    started = []

    class FakeProc:
        def __init__(self, args, **kw):
            started.append(args)
            self.stopped = False

        def terminate(self):
            self.stopped = True

    monkeypatch.setattr(awake.sys, "platform", "darwin")
    monkeypatch.setattr(awake.subprocess, "Popen", FakeProc)
    keep = awake.KeepAwake()
    keep.start()
    keep.start()  # a second start does nothing
    assert len(started) == 1 and started[0][:2] == ["caffeinate", "-i"]
    proc = keep._proc
    keep.stop()
    assert proc.stopped and not keep.active


def test_keep_awake_without_caffeinate_carries_on(monkeypatch):
    def fail(*a, **kw):
        raise FileNotFoundError("caffeinate")

    monkeypatch.setattr(awake.sys, "platform", "darwin")
    monkeypatch.setattr(awake.subprocess, "Popen", fail)
    keep = awake.KeepAwake()
    keep.start()
    assert not keep.active
    keep.stop()


def test_ffmpeg_runs_through_tools():
    assert tools.run(["ffmpeg", "-version"], capture_output=True, check=True).returncode == 0
    with tools.popen(["ffprobe", "-version"], stdout=subprocess.DEVNULL) as proc:
        assert proc.wait() == 0
