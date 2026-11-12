"""Constants and small helpers shared by the main window's parts (gui.py and the step modules)."""
import queue
import re
import threading
import tkinter
import tkinter.font

import soundfile as sf

import audiobook
import desktop
from run_settings import CHATTERBOX, KOKORO  # noqa: F401  (the step modules import them from here too)

KOKORO_VOICES = [
    "am_michael", "am_adam", "am_echo", "am_eric", "am_fenrir", "am_liam", "am_onyx", "am_puck",
    "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore", "af_nicole", "af_nova",
    "af_river", "af_sarah", "af_sky",
    "bm_daniel", "bm_fable", "bm_george", "bm_lewis",
    "bf_alice", "bf_emma", "bf_isabella", "bf_lily",
]
# Narration-friendly starting values; the Reset button restores them.
RECOMMENDED = {
    "speed": 0.95,
    "exaggeration": 0.5,
    "cfg_weight": 0.3,
    "temperature": 0.6,
    "paragraph_pause": audiobook.PARAGRAPH_PAUSE,
    "title_pause": audiobook.TITLE_PAUSE,
}
ENGINE_LABELS = {KOKORO: "Kokoro · fast", CHATTERBOX: "Chatterbox · expressive, slower"}
ACCENT_CHOICES = {"Any accent": None, "American": "US", "British": "UK"}
GENDER_CHOICES = {"Any voice": None, "Female": "Female", "Male": "Male"}
PRONUNCIATIONS_TEMPLATE = """\
# Pronunciations for this book, one per line:
#   word = how to say it
#
# Examples (remove the # to use one):
#   Saoirse = Seer-sha
#   Hermione = Her-my-oh-nee
#   St. = Saint
#
# Capitalization doesn't matter, and only whole words are replaced.
# Save this file, then click Create audiobook. Only the chapters that use a changed word are rendered again.

"""
PREVIEW_HINT = "Hear the opening of chapter 1 with these choices."
COVER_HINT = "Optional. 1400 × 1400 or larger looks sharp in Books."
COVER_BG = "#2B2418"  # the generated cover, when the book has none
STEPS = [("book", "Book"), ("voice", "Voice"), ("sound", "Sound"), ("create", "Create")]
STEP_KEYS = [key for key, _ in STEPS]
SUMMARY_ROWS = [("Book", "book"), ("Chapters", "book"), ("Narrator", "voice"), ("Sound", "sound"), ("Characters", "sound")]
ACCENTS = {"US": "American", "UK": "British"}
GENTLE_ON = "Gentle mode is on. It rests a minute after every 5 minutes of narrating."
REVEAL_LABEL = f"Show in {desktop.FILE_MANAGER}"
# Error text that means a voice model couldn't be downloaded (audiobook.ModelNotDownloaded covers the usual case).
OFFLINE = re.compile(r"huggingface|ConnectionError|Max retries|Failed to resolve|offline|Temporary failure in name "
                     r"resolution|nodename nor servname", re.I)
HOW_IT_WORKS = [("1", "Add a book", "Chapters are found for you."), ("2", "Pick a voice", "Press play to hear each one."),
                ("3", "Create and listen", "Play it here or in Books.")]

# Tk isn't thread-safe. Garbage collection can run on the worker thread (it does while the TTS libraries
# import) and finalize leftover Tk variables, images or fonts there, which crashes Tcl with a bus error.
# Finalizers that land on another thread are queued instead, and App.poll runs them on the main thread.
TK_FINALIZERS = queue.SimpleQueue()


def main_thread_finalizer(finalize):
    def wrapper(self):
        if threading.current_thread() is threading.main_thread():
            finalize(self)
        else:
            TK_FINALIZERS.put((finalize, self))
    return wrapper


for tk_class in (tkinter.Variable, tkinter.Image, tkinter.font.Font):
    tk_class.__del__ = main_thread_finalizer(tk_class.__del__)


def voice_info(voice):
    """('Michael', 'US', 'Male') for am_michael: first letter is the accent, second the gender."""
    return voice[3:].title(), "US" if voice[0] == "a" else "UK", "Female" if voice[1] == "f" else "Male"


def shorten(text, limit):
    return text if len(text) <= limit else text[:limit - 1] + "…"


def clip_length(path):
    try:
        seconds = round(sf.info(path).duration)
        return f"{seconds // 60}:{seconds % 60:02d}"
    except Exception:
        return ""
