"""Tests for volume levelling, MP3 export and not loading the voice when nothing needs narrating. Need ffmpeg."""
import shutil
import subprocess
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

import audiobook

pytestmark = pytest.mark.skipif(not shutil.which("ffmpeg"), reason="needs ffmpeg")


def tone(path, gain, seconds=6.0):
    """A speech-like test signal: a 220 Hz tone that comes and goes, at the given gain."""
    t = np.arange(int(seconds * audiobook.SAMPLE_RATE)) / audiobook.SAMPLE_RATE
    audio = gain * np.sin(2 * np.pi * 220 * t) * (np.sin(2 * np.pi * 0.7 * t) > 0)
    sf.write(path, audio.astype(np.float32), audiobook.SAMPLE_RATE)
    return path


def loudness(path):
    return float(audiobook.measure_loudness(path)["input_i"])


def test_quiet_and_loud_chapters_come_out_at_the_same_level(tmp_path):
    quiet = audiobook.level_chapter(tone(tmp_path / "q.wav", 0.02), tmp_path / "out" / "q.wav")
    loud = audiobook.level_chapter(tone(tmp_path / "l.wav", 0.9), tmp_path / "out" / "l.wav")
    for path in (quiet, loud):
        audio, sr = sf.read(path)
        assert sr == audiobook.OUT_RATE
        assert abs(loudness(path) - audiobook.LOUDNESS) < 1.0
        assert 20 * np.log10(np.abs(audio).max()) <= audiobook.TRUE_PEAK + 0.1


def test_levelled_chapter_is_reused(tmp_path):
    out = audiobook.level_chapter(tone(tmp_path / "a.wav", 0.3), tmp_path / "out" / "a.wav")
    stamp = out.stat().st_mtime_ns
    assert audiobook.level_chapter(tmp_path / "a.wav", out).stat().st_mtime_ns == stamp


def test_silent_chapter_does_not_fail(tmp_path):
    sf.write(tmp_path / "s.wav", np.zeros(24000, dtype=np.float32), 24000)
    assert audiobook.level_chapter(tmp_path / "s.wav", tmp_path / "out" / "s.wav").exists()


def test_mp3_export_matches_store_format(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wavs = [audiobook.level_chapter(tone(tmp_path / f"{i}.wav", 0.3, 3.0), tmp_path / "lv" / f"{i}.wav") for i in (1, 2)]
    args = SimpleNamespace(title="Night: Watch?", author="A. Writer")
    folder = audiobook.export_mp3([("Chapter One: Arrival", []), ("Two", [])], wavs, args)
    files = sorted(folder.glob("*.mp3"))
    assert folder.name == "Night Watch (MP3)"
    assert [f.name for f in files] == ["01 - Chapter One Arrival.mp3", "02 - Two.mp3"]
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "stream=sample_rate,bit_rate,channels:format=duration",
                            "-of", "default=nw=1", str(files[0])], capture_output=True, text=True).stdout
    assert "sample_rate=44100" in probe and "channels=1" in probe and "bit_rate=192000" in probe
    duration = float(probe.split("duration=")[1].split()[0])
    assert abs(duration - (3.0 + sum(audiobook.ROOM_TONE))) < 0.15


def test_mp3_export_replaces_old_files(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wav = audiobook.level_chapter(tone(tmp_path / "1.wav", 0.3, 1.0), tmp_path / "lv" / "1.wav")
    args = SimpleNamespace(title="Book", author="A. Writer")
    audiobook.export_mp3([("Old name", [])], [wav], args)
    folder = audiobook.export_mp3([("New name", [])], [wav], args)
    assert [f.name for f in folder.glob("*.mp3")] == ["01 - New name.mp3"]


def test_finished_book_rebuilds_without_loading_the_voice(tmp_path, monkeypatch):
    folder = tmp_path / "book"
    folder.mkdir()
    (folder / "01.md").write_text("Hello there.")
    loads = []

    def load_engine(args):
        loads.append(1)
        return audiobook.SAMPLE_RATE, lambda text: np.full(2400, 0.1, dtype=np.float32)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audiobook, "load_engine", load_engine)
    monkeypatch.setattr(audiobook, "build_m4b", lambda chapters, wavs, args, progress=None: Path("out/Book.m4b"))
    args = SimpleNamespace(chapters=str(folder), engine="kokoro", voice="am_michael", speed=1.0, ref=None,
                           paragraph_pause=0.6, title_pause=1.2, sample=False, title="Book", author="Me", cover=None)
    audiobook.run(args, log=lambda m: None)
    args.mp3 = True
    audiobook.run(args, log=lambda m: None)
    assert loads == [1]
    assert list((tmp_path / "out" / "Book (MP3)").glob("*.mp3"))


def test_old_levelled_chapters_are_cleaned_up(tmp_path, monkeypatch):
    folder = tmp_path / "book"
    folder.mkdir()
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audiobook, "load_engine",
                        lambda args: (audiobook.SAMPLE_RATE, lambda text: np.full(2400, 0.1, dtype=np.float32)))
    monkeypatch.setattr(audiobook, "build_m4b", lambda chapters, wavs, args, progress=None: Path("out/Book.m4b"))
    args = SimpleNamespace(chapters=str(folder), engine="kokoro", voice="am_michael", speed=1.0, ref=None,
                           paragraph_pause=0.6, title_pause=1.2, sample=False, title="Book", author="Me", cover=None)
    for text in ("First version.", "Second version."):
        (folder / "01.md").write_text(text)
        audiobook.run(args, log=lambda m: None)
    assert len(list(tmp_path.glob("build/*/kokoro-am_michael/leveled/*.wav"))) == 1


def test_m4b_from_levelled_chapters_has_chapters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wavs = [audiobook.level_chapter(tone(tmp_path / f"{i}.wav", 0.3, 2.0), tmp_path / "lv" / f"{i}.wav") for i in (1, 2)]
    args = SimpleNamespace(title="Book", author="A. Writer", cover=None)
    out = audiobook.build_m4b([("One", []), ("Two", [])], wavs, args)
    probe = subprocess.run(["ffprobe", "-v", "error", "-show_chapters", "-of", "csv", str(out)],
                           capture_output=True, text=True).stdout
    assert probe.count("chapter") == 2 and "One" in probe and "Two" in probe


def test_m4b_reports_progress_up_to_the_whole_book(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wavs = [audiobook.level_chapter(tone(tmp_path / f"{i}.wav", 0.3, 2.0), tmp_path / "lv" / f"{i}.wav") for i in (1, 2)]
    steps = []
    out = audiobook.build_m4b([("One", []), ("Two", [])], wavs, SimpleNamespace(title="Book", author="A. Writer", cover=None),
                              progress=lambda done, total: steps.append((done, total)))
    assert out.exists()
    total = steps[-1][1]
    assert 3900 <= total <= 4100 and steps[-1] == (total, total)
    assert all(done <= total for done, _ in steps) and [d for d, _ in steps] == sorted(d for d, _ in steps)


def test_full_build_reports_each_stage_in_order(tmp_path, monkeypatch):
    folder = tmp_path / "book"
    folder.mkdir()
    for n in (1, 2):
        (folder / f"0{n}.md").write_text(f"Chapter {n} text.")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audiobook, "load_engine",
                        lambda args: (audiobook.SAMPLE_RATE, lambda text: np.full(2400, 0.1, dtype=np.float32)))
    args = SimpleNamespace(chapters=str(folder), engine="kokoro", voice="am_michael", speed=1.0, ref=None,
                           paragraph_pause=0.6, title_pause=1.2, sample=False, title="Book", author="Me", cover=None)
    steps = []
    audiobook.run(args, log=lambda m: None, progress=lambda *step: steps.append(step))
    chapters = [step for step in steps if step[0] == "chapter"]
    assert [step[:3] for step in chapters] == [("chapter", 1, 2), ("chapter", 2, 2)]
    assert all(set(step[3]) == {"audio", "took"} for step in chapters)
    steps = [step for step in steps if step[0] != "chapter"]
    stages = [stage for stage, *_ in steps]
    assert steps[:3] == [("narrate", 0, 2), ("narrate", 1, 2), ("narrate", 2, 2)]
    assert stages.index("level") < stages.index("build") and "mp3" not in stages
    assert steps[-1][0] == "build" and steps[-1][1] == steps[-1][2]

    # Run again with MP3s: nothing left to narrate, so the build is the whole job.
    args.mp3 = True
    steps.clear()
    audiobook.run(args, log=lambda m: None, progress=lambda *step: steps.append(step))
    assert steps[0] == ("narrate", 0, 0) and steps[-1] == ("mp3", 2, 2)
    assert ("chapter", 1, 2, {"kept": True}) in steps


def test_m4b_takes_a_safe_name_and_a_stopped_build_leaves_no_file(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    wavs = [audiobook.level_chapter(tone(tmp_path / "1.wav", 0.3, 1.0), tmp_path / "lv" / "1.wav")]
    out = audiobook.build_m4b([("One", [])], wavs, SimpleNamespace(title="AC/DC: Live?", author="A. Writer", cover=None))
    assert out == Path("out") / "ACDC Live.m4b" and out.exists()

    def stopped(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(audiobook, "run_ffmpeg", stopped)
    args = SimpleNamespace(title="Other", author="A. Writer", cover=None, output_name="Other (2)")
    with pytest.raises(KeyboardInterrupt):
        audiobook.build_m4b([("One", [])], wavs, args)
    assert sorted(p.name for p in Path("out").iterdir()) == ["ACDC Live.m4b"]
