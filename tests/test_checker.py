"""Tests for checker.py: spotting skipped words, retrying and the book-wide report. Whisper is faked."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import audiobook
import checker
from checker import compare, words

TEXT = "The train pulled into the station just after midnight, and Mara stepped onto the cold platform."


def test_words_normalizes_case_punctuation_and_numbers():
    assert words("It's 1999 — Dr. Kai-Lee!") == ["it's", "nineteen", "ninety", "nine", "dr", "kai", "lee"]
    assert words("42 and 3000") == ["forty", "two", "and", "three", "thousand"]


def test_a_year_read_aloud_or_written_as_digits_passes():
    text = "It was 1999 when Mara left the old farm."
    assert compare(text, "It was nineteen ninety-nine when Mara left the old farm.")[0] is None
    assert compare(text, "It was 1999 when Mara left the old farm.")[0] is None


def test_a_faithful_take_passes():
    assert compare(TEXT, "The train pulled into the station just after midnight and Mara stepped onto the cold platform")[0] is None


def test_small_mishearings_pass():
    # A name heard differently, and a respelled pronunciation, are not skips.
    assert compare("Kai met Seer-sha at the gate.", "Kye met Sirsha at the gate.")[0] is None


def test_a_skipped_phrase_is_caught():
    problem, missing, _ = compare(TEXT, "The train pulled into the station and Mara stepped onto the cold platform")
    assert problem and missing == ["just", "after", "midnight"]


def test_a_skipped_ending_is_caught():
    assert compare(TEXT, "The train pulled into the station just after midnight")[0]


def test_scattered_missing_words_are_caught():
    assert compare("one two three four five six seven eight nine ten", "one three five seven nine ten")[0]


def test_garbled_extra_speech_is_caught():
    problem, _, extra = compare("She opened the door.", "She opened the uh the the door door the the")
    assert problem and "extra" in problem


def test_empty_text_passes():
    assert compare("", "anything")[0] is None


def make_voice(takes):
    """A fake synth/transcribe pair: each synth call returns the next take, and transcribe returns what it 'says'."""
    heard = []

    def synth(text):
        heard.append(takes[min(len(heard), len(takes) - 1)](text))
        return np.full(240, len(heard) - 1, dtype=np.float32)

    def transcribe(audio, sr):
        return heard[int(audio[0])]

    return synth, transcribe, heard


def test_checked_retries_until_a_good_take():
    synth, transcribe, heard = make_voice([lambda t: "the train", lambda t: t])
    problems = []
    audio = checker.checked(synth, 24000, transcribe, log=lambda m: None, problems=problems)(TEXT)
    assert len(heard) == 2 and int(audio[0]) == 1 and problems == []


def test_checked_keeps_the_best_take_and_reports_it():
    takes = [lambda t: "the train", lambda t: "the train pulled into the station", lambda t: "nothing"]
    synth, transcribe, heard = make_voice(takes)
    problems = []
    audio = checker.checked(synth, 24000, transcribe, retries=2, log=lambda m: None, problems=problems,
                            where=lambda: "Chapter 2: ")(TEXT)
    assert len(heard) == 3 and int(audio[0]) == 1
    assert problems[0]["where"] == "Chapter 2" and problems[0]["heard"] == "the train pulled into the station"


def run_book(tmp_path, monkeypatch, chapters, take, **overrides):
    """Run Chatterbox with checking on, with a fake voice whose takes come from take(text, attempt)."""
    folder = tmp_path / "book"
    folder.mkdir(exist_ok=True)
    for name in list(folder.glob("*.md")):
        name.unlink()
    for name, md in chapters.items():
        (folder / name).write_text(md, encoding="utf-8")
    log, heard, attempts = [], [], {}

    def synth(text):
        attempts[text] = attempts.get(text, 0) + 1
        heard.append(take(text, attempts[text]))
        return np.full(240, len(heard) - 1, dtype=np.float32)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audiobook, "load_engine", lambda args: (24000, synth))
    monkeypatch.setattr(audiobook, "build_m4b", lambda chapters, wavs, args, progress=None: Path("out/Book.m4b"))
    monkeypatch.setattr(checker, "available", lambda: True)
    args = SimpleNamespace(chapters=str(folder), engine="chatterbox", voice="Chatterbox", ref=None,
                           exaggeration=0.5, cfg_weight=0.3, temperature=0.6, paragraph_pause=0.6, title_pause=1.2,
                           sample=False, title="Book", author="Me", cover=None, check=True,
                           transcribe=lambda audio, sr: heard[int(audio[0])])
    for name, value in overrides.items():
        setattr(args, name, value)
    audiobook.run(args, log=log.append)
    return log, attempts


REPORT = Path("out") / "Book - check report.txt"


def test_report_lists_paragraphs_that_stay_wrong(tmp_path, monkeypatch):
    always_skips = lambda text, n: "" if text.startswith("Skipped") else text
    log, attempts = run_book(tmp_path, monkeypatch, {"01.md": "Fine sentence here.\n\nSkipped every single time."}, always_skips)
    assert attempts["Skipped every single time."] == 3
    report = (tmp_path / REPORT).read_text(encoding="utf-8")
    assert "Chapter 1" in report and "Skipped every single time." in report


def test_report_survives_runs_that_skip_the_chapter(tmp_path, monkeypatch):
    always_skips = lambda text, n: "" if text.startswith("Skipped") else text
    chapters = {"01.md": "Skipped every single time.", "02.md": "Good."}
    run_book(tmp_path, monkeypatch, chapters, always_skips)
    run_book(tmp_path, monkeypatch, {**chapters, "02.md": "Good, edited."}, always_skips)
    assert "Skipped every single time." in (tmp_path / REPORT).read_text(encoding="utf-8")


def test_report_is_removed_once_fixed(tmp_path, monkeypatch):
    chapters = {"01.md": "Skipped the first time only."}
    run_book(tmp_path, monkeypatch, chapters, lambda text, n: "")
    assert (tmp_path / REPORT).exists()
    run_book(tmp_path, monkeypatch, chapters, lambda text, n: text, redo={1})
    assert not (tmp_path / REPORT).exists()


def test_no_check_without_faster_whisper(tmp_path, monkeypatch):
    log, attempts = run_book(tmp_path, monkeypatch, {"01.md": "Hello there friend."}, lambda text, n: "")
    monkeypatch.setattr(checker, "available", lambda: False)
    folder = tmp_path / "book"
    (folder / "01.md").write_text("A new paragraph to narrate.")
    args_log = []
    monkeypatch.setattr(audiobook, "load_engine", lambda args: (24000, lambda t: np.zeros(240, dtype=np.float32)))
    args = SimpleNamespace(chapters=str(folder), engine="chatterbox", voice="Chatterbox", ref=None, exaggeration=0.5,
                           cfg_weight=0.3, temperature=0.6, paragraph_pause=0.6, title_pause=1.2, sample=False,
                           title="Book", author="Me", cover=None, check=True)
    audiobook.run(args, log=args_log.append)
    assert any("install faster-whisper" in line for line in args_log)


def test_kokoro_is_never_checked(tmp_path, monkeypatch):
    log, attempts = run_book(tmp_path, monkeypatch, {"01.md": "Hello."}, lambda text, n: "", engine="kokoro",
                             voice="am_michael", speed=1.0)
    assert attempts == {"Hello.": 1}


def test_whisper_failure_does_not_stop_narration():
    logged = []

    def transcribe(audio, sr):
        raise OSError("no internet")

    synth_checked = checker.checked(lambda t: np.zeros(10, dtype=np.float32), 24000, transcribe, log=logged.append)
    assert len(synth_checked("One.")) == 10 and len(synth_checked("Two.")) == 10
    assert len(logged) == 1 and "no internet" in logged[0]
