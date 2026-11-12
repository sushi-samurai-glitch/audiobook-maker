"""The books in the library pane: chapters folders the app has opened, and finished .m4b files found in out/.

Kept in app_state.json as a list of entries:
  folder    the chapters folder (None for an .m4b found in out/ whose folder isn't known)
  m4b       the .m4b file, only for those found-in-out/ books
  name      a name given with Rename; None shows the book's title
  pinned, archived, opened (when it was last opened, for the order)"""
import re
import time
from pathlib import Path

import audiobook
import book_settings
import desktop
import paths



def load():
    books = book_settings.app_state().get("books")
    if not isinstance(books, list):
        return []
    clean = []
    for b in books:
        if not isinstance(b, dict) or not (isinstance(b.get("folder"), str) or isinstance(b.get("m4b"), str)):
            continue
        clean.append({"folder": b.get("folder") if isinstance(b.get("folder"), str) else None,
                      "m4b": b.get("m4b") if isinstance(b.get("m4b"), str) else None,
                      "name": b.get("name") if isinstance(b.get("name"), str) and b.get("name").strip() else None,
                      "pinned": b.get("pinned") is True, "archived": b.get("archived") is True,
                      "opened": b.get("opened") if isinstance(b.get("opened"), (int, float)) else 0})
    return clean


def save(books):
    book_settings.update_state(books=books)


def key(book):
    return book["folder"] or book["m4b"]


def find(books, book_key):
    return next((b for b in books if key(b) == book_key), None)


def add_folder(folder, now=time.time):
    """Put the chapters folder in the library (or mark it opened now); returns its key."""
    folder = str(Path(folder).resolve())
    books = load()
    book = find(books, folder)
    if not book:
        book = {"folder": folder, "m4b": None, "name": None, "pinned": False, "archived": False, "opened": 0}
        books.append(book)
    book["opened"] = now()
    save(books)
    return folder


def update(book_key, **changes):
    books = load()
    book = find(books, book_key)
    if book:
        book.update(changes)
        save(books)


def book_title(book):
    """The title the .m4b is named after: the one typed in the Book card, else the folder name (as in gui.render_args)."""
    if book["folder"]:
        title = book_settings.read_json(Path(book["folder"]) / book_settings.BOOK_FILE).get("title")
        return title.strip() if isinstance(title, str) and title.strip() else Path(book["folder"]).name
    return Path(book["m4b"]).stem


def display_name(book):
    return book["name"] or book_title(book)


def output_name(book):
    """The name the book's files in out/ share (see audiobook.out_name): the one claimed when it was last created,
    else its title made safe for a file name."""
    if book["m4b"]:
        return Path(book["m4b"]).stem
    name = book_settings.read_json(Path(book["folder"]) / book_settings.BOOK_FILE).get("output")
    return name if isinstance(name, str) and name and name == audiobook.safe_name(name) else audiobook.safe_name(book_title(book))


def output(book, out=None):
    """The book's finished .m4b, whether or not it exists yet."""
    out = paths.OUT if out is None else Path(out)
    return Path(book["m4b"]) if book["m4b"] else Path(out) / f"{output_name(book)}.m4b"


def claim_output(folder, title, out=None):
    """Choose the name the book in folder creates its files under, one that no other book in the library uses, and
    remember it in the book's settings. Two books with the same title get "Title" and "Title (2)", so creating one
    never overwrites the other's audiobook, and deleting one never takes the other's with it."""
    out = paths.OUT if out is None else Path(out)
    folder = str(Path(folder).resolve())
    base = audiobook.safe_name(title)
    settings_file = Path(folder) / book_settings.BOOK_FILE
    data = book_settings.read_json(settings_file)
    current = data.get("output")
    mine = f"{current if isinstance(current, str) and current else base}.m4b".lower()
    taken = set()
    for b in load():
        if key(b) == folder:
            continue
        name = output(b, out).name.lower()
        claimed = b["m4b"] or isinstance(book_settings.read_json(Path(b["folder"]) / book_settings.BOOK_FILE).get("output"), str)
        # A book that never claimed a name only holds one once its audiobook exists. Books made before names were
        # claimed may share a file: the first to be created again keeps it, and the other moves to "Title (2)".
        if claimed or (output(b, out).is_file() and name != mine):
            taken.add(name)
    # Keep the name already claimed while it still belongs to this title and no other book has taken it.
    if isinstance(current, str) and re.fullmatch(re.escape(base) + r"( \(\d+\))?", current) \
            and f"{current}.m4b".lower() not in taken:
        return current
    name, n = base, 2
    while f"{name}.m4b".lower() in taken:
        name, n = f"{base} ({n})", n + 1
    if name != current:
        book_settings.write_json(settings_file, {**data, "output": name})
    return name


def status(book, out=None):
    """One short line under the book's name."""
    out = paths.OUT if out is None else Path(out)
    if book["folder"] and not Path(book["folder"]).is_dir():
        return "Folder not found"
    count = len(book_settings.chapter_files(book["folder"])) if book["folder"] else 0
    chapters = f" · {count} chapter{'s' if count != 1 else ''}" if count else ""
    if output(book, out).is_file():
        return "Finished" + chapters
    return "Draft" + chapters


def discover(out=None):
    """Add finished .m4b files in out/ that no book in the library made, and drop those whose file is gone."""
    out = paths.OUT if out is None else Path(out)
    books = load()
    made = {output(b, out).resolve() for b in books if b["folder"]}
    books = [b for b in books if b["folder"] or (Path(b["m4b"]).is_file() and Path(b["m4b"]).resolve() not in made)]
    known = {Path(b["m4b"]).resolve() for b in books if b["m4b"]}
    for m4b in sorted(Path(out).glob("*.m4b")) if Path(out).is_dir() else []:
        path = m4b.resolve()
        if path not in made and path not in known:
            books.append({"folder": None, "m4b": str(path), "name": None, "pinned": False, "archived": False,
                          "opened": m4b.stat().st_mtime})
    save(books)


def sections(books):
    """(pinned, recent, archived), each with the most recently opened first."""
    books = sorted(books, key=lambda b: b["opened"], reverse=True)
    return ([b for b in books if b["pinned"] and not b["archived"]],
            [b for b in books if not b["pinned"] and not b["archived"]],
            [b for b in books if b["archived"]])


def audio_files(book, out=None):
    """What Delete always moves to the Trash: the .m4b, its MP3 folder and check report, and the book's saved narration."""
    out = paths.OUT if out is None else Path(out)
    name = output(book, out).stem
    found = [output(book, out), Path(out) / f"{name} (MP3)", Path(out) / f"{name} - check report.txt"]
    if book["folder"]:
        found.append(audiobook.book_folder(book["folder"]))
    return [p for p in found if p.exists()]


def delete(book_key, chapters_too=False, out=None, trash=None):
    """Move the book's audio (and its chapters folder, if asked) to the Trash and drop it from the library.

    Returns the paths moved. Stops at the first one that can't be moved, leaving the book in the library."""
    out = paths.OUT if out is None else Path(out)
    if trash is None:
        from send2trash import send2trash as trash
    books = load()
    book = find(books, book_key)
    if not book:
        return []
    found = audio_files(book, out)
    if chapters_too and book["folder"] and Path(book["folder"]).is_dir():
        found.append(Path(book["folder"]))
    for path in found:
        trash(str(path))
    remember = book_settings.app_state()
    positions = remember.get("positions") if isinstance(remember.get("positions"), dict) else {}
    positions.pop(str(output(book, out).resolve()), None)
    save([b for b in books if key(b) != book_key])
    book_settings.update_state(positions=positions)
    return found


reveal = desktop.reveal  # Show in Finder (or Explorer)


def position(path):
    """Where playback of this file stopped last time, in seconds (0 if never played)."""
    seconds = book_settings.app_state().get("positions", {}).get(str(Path(path).resolve()))
    return float(seconds) if isinstance(seconds, (int, float)) else 0.0


def remember_position(path, seconds):
    state = book_settings.app_state()
    positions = state.get("positions") if isinstance(state.get("positions"), dict) else {}
    positions[str(Path(path).resolve())] = round(seconds, 1)
    book_settings.update_state(positions=positions)


def play_speed():
    speed = book_settings.app_state().get("play_speed")
    return speed if isinstance(speed, (int, float)) and 0.5 <= speed <= 2.0 else 1.0


def remember_play_speed(speed):
    book_settings.update_state(play_speed=speed)
