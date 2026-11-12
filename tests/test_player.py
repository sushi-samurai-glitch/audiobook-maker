"""Tests for player.py with a silent fake sound card; needs ffmpeg, like the rest of the app."""
import subprocess
import time
from types import SimpleNamespace

import pytest

import player


class FakeStream:
    """Stands in for sounddevice.RawOutputStream: takes audio as fast as real playback would at 20x speed."""
    def __init__(self, **kw):
        self.aborted = False

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def write(self, data):
        time.sleep(len(data) / 4 / player.RATE / 20)

    def abort(self):
        self.aborted = True


@pytest.fixture
def book(tmp_path, monkeypatch):
    """A 6-second .m4b with chapters at 0, 2 and 4 seconds."""
    monkeypatch.setattr(player, "sd", SimpleNamespace(RawOutputStream=FakeStream))
    meta = tmp_path / "meta.txt"
    meta.write_text(";FFMETADATA1\n" + "".join(
        f"[CHAPTER]\nTIMEBASE=1/1000\nSTART={s * 1000}\nEND={(s + 2) * 1000}\ntitle=Part {i}\n" for i, s in enumerate((0, 2, 4), 1)))
    path = tmp_path / "book.m4b"
    subprocess.run(["ffmpeg", "-v", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=6", "-i", str(meta),
                    "-map_metadata", "1", "-c:a", "aac", str(path)], check=True)
    return path


def wait_until(condition, timeout=5):
    end = time.monotonic() + timeout
    while time.monotonic() < end and not condition():
        time.sleep(0.02)
    return condition()


def test_probe_reads_duration_and_chapters(book):
    duration, chapters = player.probe(book)
    assert duration == pytest.approx(6, abs=0.1)
    assert [title for _, title in chapters] == ["Part 1", "Part 2", "Part 3"]
    assert player.chapter_at(chapters, 3.0) == 1 and player.chapter_at(chapters, 0) == 0


def test_plays_to_the_end_and_stops(book):
    p = player.Player()
    p.load(book)
    p.play()
    assert wait_until(lambda: not p.playing)
    assert p.error is None and p.position == pytest.approx(p.duration)


def test_pause_seek_and_resume_position(book):
    p = player.Player()
    p.load(book, position=4.0)
    assert p.position == 4.0
    p.play()
    assert wait_until(lambda: p.position > 4.5)
    p.pause()
    paused = p.position
    time.sleep(0.1)
    assert not p.playing and p.position == paused
    p.seek(1.0)
    assert p.position == 1.0 and not p.playing  # seeking while paused stays paused


def test_speed_moves_position_faster(book):
    p = player.Player()
    p.load(book)
    p.set_speed(2.0)
    p.play()
    assert wait_until(lambda: not p.playing)
    assert p.position == pytest.approx(p.duration)
