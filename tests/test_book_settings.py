"""Tests for book_settings.py: saving and loading each book's settings. No GUI needed."""
import json

import book_settings
from book_settings import BOOK_FILE, clean, load_book, save_book

VOICES = ["am_michael", "bm_george", "af_heart"]


def test_round_trip(tmp_path):
    cover = tmp_path / "cover.jpg"
    cover.write_bytes(b"jpg")
    settings = {"engine": "Kokoro", "voice_a": "bm_george", "voice_b": "af_heart", "clip": None, "speed": 0.9,
                "exaggeration": 0.5, "cfg_weight": 0.3, "temperature": 0.6, "paragraph_pause": 0.8,
                "title_pause": 1.5, "title": "The Night Watch", "author": "A. Writer", "cover": str(cover), "check": False}
    save_book(tmp_path, settings)
    assert load_book(tmp_path, VOICES) == (settings, [])


def test_never_saved_book_is_empty(tmp_path):
    assert load_book(tmp_path, VOICES) == ({}, [])


def test_broken_file_is_ignored(tmp_path):
    (tmp_path / BOOK_FILE).write_text("{not json")
    assert load_book(tmp_path, VOICES) == ({}, [])
    (tmp_path / BOOK_FILE).write_text("[1, 2]")
    assert load_book(tmp_path, VOICES) == ({}, [])


def test_unknown_values_are_dropped():
    settings, _ = clean({"engine": "Siri", "voice_a": "zz_nobody", "speed": "fast", "title": 5}, VOICES)
    assert "engine" not in settings and "voice_a" not in settings and "speed" not in settings
    assert "title" not in settings


def test_numbers_are_clamped_and_rounded():
    settings, _ = clean({"speed": 9, "temperature": 0.0, "paragraph_pause": 0.6000000001}, VOICES)
    assert settings["speed"] == 2.0 and settings["temperature"] == 0.3 and settings["paragraph_pause"] == 0.6


def test_blend_voice_must_differ_from_main_voice():
    assert clean({"voice_a": "am_michael", "voice_b": "am_michael"}, VOICES)[0]["voice_b"] is None
    assert clean({"voice_a": "am_michael", "voice_b": "zz_nobody"}, VOICES)[0]["voice_b"] is None


def test_missing_files_are_reported(tmp_path):
    settings, problems = clean({"clip": str(tmp_path / "gone.wav"), "cover": str(tmp_path / "gone.jpg")}, VOICES)
    assert settings["clip"] is None and settings["cover"] is None
    assert len(problems) == 2 and "gone.wav" in problems[0]


def test_saved_file_is_readable_json(tmp_path):
    save_book(tmp_path, {"title": "Café"})
    assert json.loads((tmp_path / BOOK_FILE).read_text(encoding="utf-8")) == {"title": "Café"}
    assert not list(tmp_path.glob("*.part"))


def test_last_folder(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert book_settings.last_folder() is None
    book = tmp_path / "book"
    book.mkdir()
    book_settings.remember_folder(book)
    assert book_settings.last_folder() == str(book)
    book.rmdir()
    assert book_settings.last_folder() is None  # a folder that was moved or deleted is skipped


def test_cast_is_validated():
    data = {"cast": {"enabled": True, "dialogue": "zz_nobody", "voices": {"Mara": "bf_emma", "Kai": "af_heart"}}}
    settings, _ = clean(data, VOICES)
    assert settings["cast"] == {"enabled": True, "dialogue": None, "voices": {"Kai": "af_heart"}}


def test_gentle_mode_is_on_until_turned_off(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert book_settings.gentle()
    book_settings.remember_gentle(False)
    book = tmp_path / "book"
    book.mkdir()
    book_settings.remember_folder(book)  # remembering a folder keeps the gentle setting
    assert not book_settings.gentle()
    assert book_settings.last_folder() == str(book)
    book_settings.remember_gentle(True)
    assert book_settings.gentle() and book_settings.last_folder() == str(book)


def make_chapters(folder, *names):
    for name in names:
        (folder / name).write_text(f"# {name}\n\nText.\n", encoding="utf-8")


def test_all_chapters_by_default(tmp_path):
    make_chapters(tmp_path, "02-b.md", "01-a.md")
    assert [f.name for f in book_settings.chapter_files(tmp_path)] == ["01-a.md", "02-b.md"]


def test_only_chosen_chapters_are_read(tmp_path):
    make_chapters(tmp_path, "01-a.md", "02-b.md", "03-c.md")
    book_settings.choose_chapters(tmp_path, ["01-a.md", "03-c.md"])
    assert [f.name for f in book_settings.chapter_files(tmp_path)] == ["01-a.md", "03-c.md"]
    make_chapters(tmp_path, "04-d.md")  # added later: read, since only left-out files are remembered
    assert [f.name for f in book_settings.chapter_files(tmp_path)] == ["01-a.md", "03-c.md", "04-d.md"]
    book_settings.choose_chapters(tmp_path, ["01-a.md", "02-b.md", "03-c.md", "04-d.md"])
    assert len(book_settings.chapter_files(tmp_path)) == 4
    assert "skip" not in json.loads((tmp_path / BOOK_FILE).read_text())


def test_saving_settings_keeps_the_chosen_chapters(tmp_path):
    make_chapters(tmp_path, "01-a.md", "02-b.md")
    save_book(tmp_path, {"title": "Old"})
    book_settings.choose_chapters(tmp_path, ["02-b.md"])
    save_book(tmp_path, {"title": "New"})
    data = json.loads((tmp_path / BOOK_FILE).read_text())
    assert data == {"title": "New", "skip": ["01-a.md"]}
    assert [f.name for f in book_settings.chapter_files(tmp_path)] == ["02-b.md"]


def test_choosing_all_writes_no_file(tmp_path):
    make_chapters(tmp_path, "01-a.md")
    book_settings.choose_chapters(tmp_path, ["01-a.md"])
    assert not (tmp_path / BOOK_FILE).exists()


def test_state_changes_keep_the_other_keys(tmp_path, monkeypatch):
    monkeypatch.setattr(book_settings, "APP_STATE", tmp_path / "app_state.json")
    book_settings.update_state(gentle=False)
    book_settings.update_state(last_folder="x")
    assert book_settings.app_state() == {"gentle": False, "last_folder": "x"}


def test_txt_files_are_chapters_but_pronunciations_is_not(tmp_path):
    for name in ("01.md", "02.txt", "03.TXT", "pronunciations.txt", ".hidden.md", "notes.docx"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    assert [f.name for f in book_settings.chapter_files(tmp_path)] == ["01.md", "02.txt", "03.TXT"]


def test_choosing_txt_chapters_skips_the_others(tmp_path):
    for name in ("01.txt", "02.txt", "03.md"):
        (tmp_path / name).write_text("x", encoding="utf-8")
    book_settings.choose_chapters(tmp_path, ["02.txt"])
    assert [f.name for f in book_settings.chapter_files(tmp_path)] == ["02.txt"]


def test_chapter_text_in_any_common_encoding(tmp_path):
    text = "# Chapter One\n\n“Café,” she said — naïve.\n"
    files = {"bom.md": b"\xef\xbb\xbf" + text.encode("utf-8"), "cp1252.md": text.encode("cp1252"),
             "utf16.md": text.encode("utf-16"), "crlf.md": text.replace("\n", "\r\n").encode("utf-8")}
    for name, data in files.items():
        (tmp_path / name).write_bytes(data)
        assert book_settings.read_text(tmp_path / name) == text, name
