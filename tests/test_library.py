"""Tests for library.py: the list of books in the library pane. No GUI needed."""
import json
import shutil
from pathlib import Path

import pytest

import book_settings
import library


@pytest.fixture(autouse=True)
def state(tmp_path, monkeypatch):
    monkeypatch.setattr(book_settings, "APP_STATE", tmp_path / "app_state.json")
    return tmp_path / "app_state.json"


def make_book(tmp_path, name, title=None, chapters=2):
    folder = tmp_path / name
    folder.mkdir()
    for i in range(chapters):
        (folder / f"{i:02d}.md").write_text("# Hi\n\nText.")
    if title:
        (folder / book_settings.BOOK_FILE).write_text(json.dumps({"title": title}))
    return folder


def test_add_folder_keeps_other_state_and_one_entry(tmp_path, state):
    state.write_text(json.dumps({"gentle": False}))
    folder = make_book(tmp_path, "wagon")
    library.add_folder(folder, now=lambda: 1)
    library.add_folder(folder, now=lambda: 2)
    books = library.load()
    assert len(books) == 1 and books[0]["opened"] == 2
    assert json.loads(state.read_text())["gentle"] is False


def test_title_status_and_output(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    folder = make_book(tmp_path, "lantern", title="The Lantern", chapters=3)
    library.add_folder(folder)
    book = library.load()[0]
    assert library.display_name(book) == "The Lantern"
    assert library.status(book, out) == "Draft · 3 chapters"
    (out / "The Lantern.m4b").write_bytes(b"m4b")
    assert library.status(book, out) == "Finished · 3 chapters"
    library.update(library.key(book), name="Wagon (Kokoro)")
    assert library.display_name(library.load()[0]) == "Wagon (Kokoro)"


def test_missing_folder_says_so(tmp_path):
    folder = make_book(tmp_path, "gone")
    library.add_folder(folder)
    for f in folder.iterdir():
        f.unlink()
    folder.rmdir()
    assert library.status(library.load()[0]) == "Folder not found"


def test_discover_adds_only_unknown_m4bs_and_forgets_deleted_ones(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    library.add_folder(make_book(tmp_path, "wagon"))
    (out / "wagon.m4b").write_bytes(b"made by the wagon folder")
    (out / "Old Book.m4b").write_bytes(b"made before the library")
    library.discover(out)
    found = [b for b in library.load() if b["m4b"]]
    assert [library.display_name(b) for b in found] == ["Old Book"]
    (out / "Old Book.m4b").unlink()
    library.discover(out)
    assert [b for b in library.load() if b["m4b"]] == []


def test_sections_order(tmp_path):
    for i, name in enumerate(["a", "b", "c", "d"]):
        library.add_folder(make_book(tmp_path, name), now=lambda i=i: i)
    keys = {library.display_name(b): library.key(b) for b in library.load()}
    library.update(keys["a"], pinned=True)
    library.update(keys["b"], archived=True)
    pinned, recent, archived = library.sections(library.load())
    names = lambda books: [library.display_name(b) for b in books]
    assert (names(pinned), names(recent), names(archived)) == (["a"], ["d", "c"], ["b"])


def test_bad_entries_are_ignored(state):
    state.write_text(json.dumps({"books": [5, {"name": "no path"}, {"folder": "/x", "pinned": "yes"}]}))
    assert library.load() == [{"folder": "/x", "m4b": None, "name": None, "pinned": False, "archived": False, "opened": 0}]


def test_positions_and_speed_are_remembered(tmp_path):
    book = tmp_path / "b.m4b"
    assert library.position(book) == 0.0 and library.play_speed() == 1.0
    library.remember_position(book, 123.456)
    library.remember_play_speed(1.5)
    assert library.position(book) == 123.5 and library.play_speed() == 1.5


def test_delete_moves_audio_and_optionally_chapters(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # build/ is relative to the project folder
    out = tmp_path / "out"
    out.mkdir()
    folder = make_book(tmp_path, "wagon", title="Wagon")
    library.add_folder(folder)
    m4b = out / "Wagon.m4b"
    m4b.write_bytes(b"m4b")
    (out / "Wagon (MP3)").mkdir()
    (out / "Wagon - check report.txt").write_text("ok")
    build = library.audiobook.book_folder(folder)
    build.mkdir(parents=True)
    (out / "Other.m4b").write_bytes(b"someone else's")
    library.remember_position(m4b, 10)
    trashed = []

    def trash(path):  # stands in for the Trash: remember, then remove
        trashed.append(path)
        shutil.rmtree(path) if Path(path).is_dir() else Path(path).unlink()

    moved = library.delete(str(folder.resolve()), out=out, trash=trash)
    assert sorted(Path(p).name for p in trashed) == sorted(["Wagon.m4b", "Wagon (MP3)", "Wagon - check report.txt", build.name])
    assert len(moved) == 4 and library.load() == [] and library.position(m4b) == 0.0
    assert folder.exists() and (out / "Other.m4b").exists()

    library.add_folder(folder)
    trashed.clear()
    library.delete(str(folder.resolve()), chapters_too=True, out=out, trash=trash)
    assert [Path(p).name for p in trashed] == ["wagon"] and not folder.exists()


def test_delete_found_m4b(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    (out / "Old.m4b").write_bytes(b"m4b")
    library.discover(out)
    trashed = []
    library.delete(library.key(library.load()[0]), chapters_too=True, out=out, trash=trashed.append)
    assert [Path(p).name for p in trashed] == ["Old.m4b"] and library.load() == []


def test_books_with_the_same_title_get_their_own_audiobook(tmp_path):
    out = tmp_path / "out"
    out.mkdir()
    first, second = make_book(tmp_path, "a", title="Book"), make_book(tmp_path, "b", title="Book")
    library.add_folder(first)
    library.add_folder(second)
    assert library.claim_output(first, "Book", out) == "Book"
    assert library.claim_output(second, "Book", out) == "Book (2)"
    assert library.claim_output(first, "Book", out) == "Book"  # claiming again keeps the name
    (out / "Book.m4b").write_bytes(b"one")
    (out / "Book (2).m4b").write_bytes(b"two")
    books = {Path(b["folder"]).name: b for b in library.load()}
    assert library.output(books["a"], out).name == "Book.m4b"
    assert library.output(books["b"], out).name == "Book (2).m4b"
    # Deleting one book leaves the other's audiobook alone.
    trashed = library.delete(library.key(books["b"]), out=out, trash=lambda p: Path(p).unlink() if Path(p).is_file() else None)
    assert [Path(p).name for p in trashed] == ["Book (2).m4b"]
    assert (out / "Book.m4b").read_bytes() == b"one"


def test_a_new_title_claims_a_new_name_and_settings_keep_it(tmp_path):
    folder = make_book(tmp_path, "wagon", title="Wagon")
    library.add_folder(folder)
    assert library.claim_output(folder, "AC/DC: Live?", tmp_path / "out") == "ACDC Live"
    book_settings.save_book(folder, {"title": "AC/DC: Live?"})  # what the app saves doesn't drop the claimed name
    assert library.output(library.load()[0], tmp_path / "out").name == "ACDC Live.m4b"
