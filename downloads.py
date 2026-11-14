"""The voice models the app downloads from Hugging Face: what they are, whether they're here, and fetching them.

Kokoro's model and voices download on first use into Hugging Face's cache folder. This module lets the app fetch
them all ahead of time with a progress bar, say how much room they take, and delete them (and the models earlier
versions downloaded, which are no longer used). Nothing here is imported until it's needed, so the app opens without huggingface_hub loaded."""
import os
import shutil
import threading
from dataclasses import dataclass
from pathlib import Path

from gui_common import KOKORO_VOICES


@dataclass(frozen=True)
class Pack:
    key: str
    name: str  # in words, for the window
    repo: str  # on Hugging Face
    files: tuple  # what the app needs from the repo
    approx: str  # rough download size, shown before the real size is known
    purpose: str


def kokoro_files(voices=KOKORO_VOICES):
    return ("config.json", "kokoro-v1_0.pth", *(f"voices/{v}.pt" for v in voices))


PACKS = {
    "kokoro": Pack("kokoro", "Kokoro voices", "hexgrad/Kokoro-82M", kokoro_files(), "about 330 MB",
                   f"All {len(KOKORO_VOICES)} Kokoro voices, so each one works offline."),
}

# Models earlier versions downloaded and this one no longer uses. Settings lists one only while it is still on disk,
# so its room can be freed; nothing downloads them.
LEFT_OVER = {
    "chatterbox": Pack("chatterbox", "Chatterbox (no longer used)", "ResembleAI/chatterbox", (), "about 3 GB",
                       "The slower voice from an earlier version. Delete it to free the room."),
    "whisper": Pack("whisper", "Skipped-word check (no longer used)", "Systran/faster-whisper-small.en", (),
                    "about 480 MB", "Whisper, which listened back to Chatterbox. Delete it to free the room."),
}


def left_over(cache=None):
    """{key: pack} of the LEFT_OVER models still in the cache."""
    return {key: pack for key, pack in LEFT_OVER.items() if repo_folder(pack, cache or hub_cache()).is_dir()}


def hub_cache():
    """Hugging Face's cache folder, worked out the way huggingface_hub does, without importing it (so it's instant)."""
    for name in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE"):
        if os.environ.get(name):
            return Path(os.environ[name]).expanduser()
    if os.environ.get("HF_HOME"):
        return Path(os.environ["HF_HOME"]).expanduser() / "hub"
    base = os.environ.get("XDG_CACHE_HOME") or Path.home() / ".cache"
    return Path(base).expanduser() / "huggingface" / "hub"


def on_disk(pack, files=None, cache=None):
    """Whether every one of the pack's files (or `files`) is already in the cache. Only looks at files on disk:
    nothing is loaded, nothing goes online, and huggingface_hub isn't imported, so it takes milliseconds."""
    snapshots = repo_folder(pack, cache or hub_cache()) / "snapshots"
    try:
        revisions = [d for d in snapshots.iterdir() if d.is_dir()]
    except OSError:
        return False
    wanted = files or pack.files
    # A snapshot links each file to its blob; a broken link (a deleted blob) doesn't count as there.
    return any(all((revision / f).is_file() for f in wanted) for revision in revisions)


def scan(cache=None):
    """{pack key: on disk?} for each pack (just Kokoro now). Kokoro counts as there with its model; each of its
    voices is a small file that downloads the first time that voice is used."""
    kokoro = PACKS["kokoro"].files[:2]  # config.json and the model
    return {key: on_disk(pack, kokoro if key == "kokoro" else None, cache) for key, pack in PACKS.items()}


def needs_download(needed, cache=None):
    """Whether any of {pack key: files} (what a run needs, see audiobook.LazyVoice.needed_files) is missing."""
    try:
        return any(not on_disk(PACKS[key], files, cache) for key, files in needed.items())
    except Exception:  # can't tell: say it may download rather than say nothing
        return True


class Cancelled(Exception):
    """Downloading was stopped with the cancel event; files already finished are kept."""


def cache_dir():
    from huggingface_hub.constants import HF_HUB_CACHE

    return Path(HF_HUB_CACHE)


def repo_folder(pack, cache=None):
    return Path(cache or cache_dir()) / f"models--{pack.repo.replace('/', '--')}"


def is_cached(pack, filename, cache=None):
    from huggingface_hub import try_to_load_from_cache

    found = try_to_load_from_cache(pack.repo, filename, cache_dir=cache)
    return isinstance(found, str) and Path(found).is_file()


def missing(pack, cache=None, files=None):
    """The pack's files that aren't on this computer yet. Works offline."""
    return [f for f in (files or pack.files) if not is_cached(pack, f, cache)]


def size_on_disk(pack, cache=None):
    """Bytes the pack takes in the cache (its blobs folder holds each file once; snapshots only link to them)."""
    blobs = repo_folder(pack, cache) / "blobs"
    if not blobs.is_dir():
        return 0
    return sum(f.stat().st_size for f in blobs.iterdir() if f.is_file())


def delete(pack, cache=None):
    """Delete the pack from the cache. It downloads again the next time it's used."""
    shutil.rmtree(repo_folder(pack, cache), ignore_errors=True)


def human(size):
    """A size in bytes in words: 340 MB, 3.1 GB."""
    if size >= 1e9:
        return f"{size / 1e9:.1f} GB"
    if size >= 1e6:
        return f"{size / 1e6:.0f} MB"
    return f"{max(1, round(size / 1e3))} KB" if size > 0 else "0 KB"


def _sizes(pack, files):
    """{filename: bytes} for files, asked of Hugging Face; {} when it can't be reached (the bar then counts files)."""
    from huggingface_hub import hf_hub_download

    sizes = {}
    try:
        for f in files:
            sizes[f] = hf_hub_download(pack.repo, f, dry_run=True).file_size or 0
    except Exception:  # offline, or an older huggingface_hub without dry_run: the download itself says what's wrong
        return {}
    return sizes


def fetch(keys, progress=None, cancel=None, files=None):
    """Download what's missing from the packs named in keys (e.g. ["kokoro"]).

    progress(done_bytes, total_bytes, pack_name) is called as it goes, possibly from huggingface_hub's own threads,
    so it must only hand the numbers on (to a queue), never touch the window. The bytes reported never go down.
    files, if given, is {key: [filenames]} to fetch only those (a run needs only the voices it uses).
    Raises Cancelled soon after cancel (a threading.Event) is set; the file being fetched then finishes quietly in
    the background unless the app quits first (a cut-off file downloads again next time). The download errors of huggingface_hub otherwise pass through."""
    from huggingface_hub import hf_hub_download
    from tqdm.std import tqdm as _tqdm

    cancel = cancel or threading.Event()
    progress = progress or (lambda done, total, name: None)
    todo = [(PACKS[k], f) for k in keys for f in missing(PACKS[k], files=(files or {}).get(k))]
    if not todo:
        return
    sizes = {}
    for pack in {p for p, _ in todo}:
        sizes.update({(pack.key, f): s for f, s in _sizes(pack, [f for p, f in todo if p is pack]).items()})
    known = len(sizes) == len(todo)
    total = sum(sizes.values()) if known else len(todo)
    lock = threading.Lock()
    # done: bytes (or files) finished; bars: this file's progress bars (Xet downloads open two per file, one for
    # fetching and one for putting the file together, each counting up to the file's size); sent: last reported.
    # Bars report from huggingface_hub's own threads too, hence the lock.
    state = {"done": 0, "file": None, "name": "", "bars": [], "sent": 0}

    def report(value):
        with lock:
            value = max(value, state["sent"])
            state["sent"] = value
        progress(value, total, state["name"])

    class Bar(_tqdm):
        """huggingface_hub reports each file's bytes to this; tqdm itself stays silent."""

        def __init__(self, *args, **kwargs):
            kwargs["disable"] = True
            self.sofar = kwargs.get("initial", 0) or 0
            with lock:
                self.file = state["file"]
                state["bars"].append(self)
            super().__init__(*args, **kwargs)

        def update(self, n=1):
            if cancel.is_set():  # the waiting thread raises Cancelled; raising here only prints tracebacks
                return
            with lock:
                self.sofar += n or 0
                if not known or self.file != state["file"]:
                    return
                # The file is as far along as its furthest bar: a Xet download's second bar starts from 0 only
                # once the first has fetched the bytes. report() keeps the total from going back.
                here = max(bar.sofar for bar in state["bars"] if bar.file == self.file)
                value = state["done"] + min(here, sizes[self.file])
            report(value)

    for pack, filename in todo:
        if cancel.is_set():
            raise Cancelled()
        with lock:
            state.update(file=(pack.key, filename), name=pack.name, bars=[])
        report(state["done"])
        outcome = {}

        def work(repo=pack.repo, filename=filename, outcome=outcome):
            try:
                hf_hub_download(repo, filename, tqdm_class=Bar)
            except BaseException as e:  # handed to the waiting thread below
                outcome["error"] = e

        worker = threading.Thread(target=work, daemon=True)
        worker.start()
        while worker.is_alive():
            worker.join(0.2)
            if cancel.is_set():
                raise Cancelled()
        if "error" in outcome:
            raise outcome["error"]
        with lock:
            state["done"] += sizes[state["file"]] if known else 1
        report(state["done"])
    report(total)
