"""Where the app keeps its files.

The app works in one folder (the working directory) that holds build/, samples/, voices/ and app_state.json, and
saves finished audiobooks in OUT. A copy run from its project folder that already has those files keeps using it,
as it always has. A fresh copy (and a packaged app, which can't write inside itself) uses the usual places instead:
the app data folder for its own files and Music/Audiobook Maker for the audiobooks.

Until configure() runs (in tests and on the command line), everything is relative to the current folder."""
import os
from pathlib import Path

APP_NAME = "Audiobook Maker"
OUT = Path("out")  # finished audiobooks, MP3 folders and check reports


def configure(project):
    """Choose the working folder and OUT for the app, and change into the working folder. Returns the working folder."""
    global OUT
    project = Path(project).resolve()
    if any((project / name).exists() for name in ("app_state.json", "out", "build")):
        work, OUT = project, Path("out")
    else:
        import platformdirs

        work = Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))
        OUT = Path(platformdirs.user_music_dir()) / APP_NAME
    work.mkdir(parents=True, exist_ok=True)
    os.chdir(work)
    return work


def log_file():
    """Where the app writes its log (app.log): the system's usual place for logs, which a packaged app can write to.
    ~/Library/Logs/Audiobook Maker on a Mac (Console can open it), the app's Logs folder in AppData on Windows."""
    import platformdirs

    return Path(platformdirs.user_log_dir(APP_NAME, appauthor=False)) / "app.log"


LOG_LIMIT = 5_000_000  # bytes; a bigger log is moved to app.log.1 at launch, replacing the one before


def rotate_log(log=None):
    """Keep the log from growing without limit: past LOG_LIMIT, start a fresh one and keep one old copy."""
    log = Path(log or log_file())
    try:
        if log.stat().st_size > LOG_LIMIT:
            log.replace(log.with_name(log.name + ".1"))
    except OSError:  # no log yet
        pass


def out_label():
    """Where audiobooks are saved, in words for the window."""
    folder = OUT.resolve()
    home = Path.home()
    return f"~/{folder.relative_to(home)}" if folder.is_relative_to(home) else str(folder)
