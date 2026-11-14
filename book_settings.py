"""Remember each book's voice, settings, title, author and cover in its chapters folder, and the last book opened."""
import json
import threading
from pathlib import Path

BOOK_FILE = "audiobook-settings.json"  # saved in the chapters folder, next to the chapter files
PRONUNCIATIONS_FILE = "pronunciations.txt"  # word = how to say it, in the chapters folder; never read as a chapter
WHO_SAID_WHAT = "who said what.txt"  # the Cast window's list of who says each line; never read as a chapter
NOT_CHAPTERS = {PRONUNCIATIONS_FILE, WHO_SAID_WHAT}  # the app's own .txt files in a chapters folder
CHAPTER_TYPES = (".md", ".txt")
APP_STATE = Path("app_state.json")  # in the project folder: which book to open at launch

# Allowed range of each slider; values outside are clamped, so a hand-edited file can't break the app.
RANGES = {
    "speed": (0.5, 2.0),
    "paragraph_pause": (0.0, 2.0),
    "title_pause": (0.0, 3.0),
}
# What earlier versions saved for Chatterbox, the second engine, which was taken out. It's ignored, but kept in the
# file when the book is saved again, so nothing is lost if a book is opened in an older copy of the app.
CHATTERBOX_KEYS = ("engine", "clip", "clip_cast", "check", "exaggeration", "cfg_weight", "temperature")


def read_json(path):
    """The file's JSON object, or {} if it is missing, unreadable or not an object."""
    try:
        data = json.loads(Path(path).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_json(path, data):
    path = Path(path)
    tmp = path.with_name(path.name + ".part")
    tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    tmp.replace(path)


def clean(data, voices):
    """Keep only valid settings: known voices, numbers in range, a cover that still exists.

    Returns (settings, problems), where problems lists what was dropped, in words for the log."""
    settings, problems = {}, []
    voice_a, voice_b = data.get("voice_a"), data.get("voice_b")
    if voice_a in voices:
        settings["voice_a"] = voice_a
        settings["voice_b"] = voice_b if voice_b in voices and voice_b != voice_a else None
    for name, (low, high) in RANGES.items():
        value = data.get(name)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            settings[name] = round(min(max(float(value), low), high), 2)
    if isinstance(data.get("cast"), dict):
        c = data["cast"]
        settings["cast"] = {"enabled": c.get("enabled") is True,
                            "dialogue": c.get("dialogue") if c.get("dialogue") in voices else None,
                            "voices": {str(name): voice for name, voice in (c.get("voices") or {}).items()
                                       if voice in voices} if isinstance(c.get("voices"), dict) else {}}
    for name in ("title", "author"):
        if isinstance(data.get(name), str):
            settings[name] = data[name]
    path = data.get("cover")
    if isinstance(path, str) and path and not Path(path).is_file():
        problems.append(f"The saved cover image is missing: {path}")
    settings["cover"] = path if isinstance(path, str) and path and Path(path).is_file() else None
    return settings, problems


def load_book(folder, voices):
    """(settings, problems) for the book in folder; settings is {} if it was never saved."""
    data = read_json(Path(folder) / BOOK_FILE)
    return clean(data, voices) if data else ({}, [])


def save_book(folder, settings):
    if Path(folder).is_dir():
        # Kept as they are: the chapters left out in Browse, the file name claimed by library.claim_output, and
        # any Chatterbox settings an earlier version saved.
        saved = read_json(Path(folder) / BOOK_FILE)
        kept = {name: saved[name] for name in ("skip", "output") if saved.get(name)}
        kept.update({name: saved[name] for name in CHATTERBOX_KEYS if name in saved})
        write_json(Path(folder) / BOOK_FILE, {**settings, **kept})


def is_chapter(path):
    """True for a file that can be a chapter: .md or .txt, but not pronunciations.txt or a hidden file."""
    path = Path(path)
    return (path.suffix.lower() in CHAPTER_TYPES and path.name.lower() not in NOT_CHAPTERS
            and not path.name.startswith("."))


def all_chapter_files(folder):
    """Every chapter file in folder, sorted by name, including any left out when the chapters were chosen."""
    folder = Path(folder)
    return sorted((f for f in folder.iterdir() if f.is_file() and is_chapter(f)), key=lambda f: f.name) \
        if folder.is_dir() else []


def chapter_files(folder):
    """The book's chapters in reading order: the chapter files in folder, minus any left out when they were chosen."""
    folder = Path(folder)
    skip = read_json(folder / BOOK_FILE).get("skip")
    skip = {name for name in skip if isinstance(name, str)} if isinstance(skip, list) else set()
    return [f for f in all_chapter_files(folder) if f.name not in skip]


def read_text(path):
    """A chapter or pronunciations file as text, whatever it was saved as.

    UTF-8 is tried first (a byte order mark, which Windows Notepad adds, is dropped), then UTF-16 when the file
    starts with its mark, and anything else is read as Windows-1252, the usual encoding of older Windows files."""
    data = Path(path).read_bytes()
    if data.startswith((b"\xff\xfe", b"\xfe\xff")):
        text = data.decode("utf-16")
    else:
        try:
            text = data.decode("utf-8-sig")
        except UnicodeDecodeError:
            text = data.decode("cp1252", errors="replace")
    return text.replace("\r\n", "\n").replace("\r", "\n")


def choose_chapters(folder, names):
    """Narrate only the chapter files named; the folder's other chapter files are skipped. Choosing all clears it.
    Files added to the folder later are read too, since only the left-out ones are remembered."""
    folder = Path(folder)
    names = set(names)
    skip = [f.name for f in all_chapter_files(folder) if f.name not in names]
    data = read_json(folder / BOOK_FILE)
    data.pop("skip", None)
    if skip:
        data["skip"] = skip
    if data or (folder / BOOK_FILE).exists():
        write_json(folder / BOOK_FILE, data)


_state_lock = threading.Lock()


def app_state():
    """Everything in app_state.json, as a dict ({} when it is missing or unreadable)."""
    return read_json(APP_STATE)


def update_state(**changes):
    """Change some keys of app_state.json and keep the rest. All writes to it go through here, one at a time,
    so two changes made close together never undo each other."""
    with _state_lock:
        write_json(APP_STATE, {**read_json(APP_STATE), **changes})


def last_folder():
    folder = app_state().get("last_folder")
    return folder if isinstance(folder, str) and Path(folder).is_dir() else None


def remember_folder(folder):
    update_state(last_folder=str(folder))


def forget_folder():
    update_state(last_folder=None)


def gentle():
    """Whether gentle mode is on; a setting for this Mac rather than for one book, and on unless turned off."""
    return app_state().get("gentle") is not False


def remember_gentle(on):
    update_state(gentle=bool(on))


LARGER_TEXT = 1.15  # how much bigger Larger text makes everything


def larger_text():
    """Whether the window is drawn larger, for easier reading; off unless turned on in Settings."""
    return app_state().get("larger_text") is True


def remember_larger_text(on):
    update_state(larger_text=bool(on))
