"""Catch sentences Chatterbox skipped or garbled: transcribe each new paragraph with Whisper and compare it with the text."""
import re
from difflib import SequenceMatcher

import numpy as np

WHISPER_MODEL = "small.en"  # about 480 MB, downloaded on first use; good enough for names and quiet endings
WHISPER_RATE = 16000
MISSING_RUN = 3  # this many expected words in a row not heard means a skipped phrase
MISSING_SHARE = 0.2  # or this share of all the words
EXTRA_RUN = 4  # this many heard words in a row that aren't in the text means garbled or repeated speech
EXTRA_SHARE = 0.3  # or at least 3 extra words making up this share of the text
SAME_WORD = 0.7  # spelling similarity at which a misheard word still counts as said (Kye for Kai, Seer-sha)


def words(text):
    """Lowercase words with punctuation removed and digits spelled out, as Whisper and the text may differ."""
    text = text.lower().replace("’", "'")
    try:
        from num2words import num2words

        text = re.sub(r"\d+(?:\.\d+)?", lambda m: " " + spell_number(m.group(), num2words) + " ", text)
    except ImportError:
        pass
    return re.findall(r"[a-z0-9']+", text.replace("-", " "))


def spell_number(digits, num2words):
    """A number as it is read aloud. Four-digit numbers from 1100 to 2099 are read as years ("nineteen ninety-nine"),
    the way narrators say them; Whisper's transcript goes through the same rule, so either spelling matches."""
    if "." in digits:
        return num2words(float(digits))
    if len(digits) == 4 and 1100 <= int(digits) <= 2099:
        return num2words(int(digits), to="year")
    return num2words(int(digits))


def compare(expected, heard):
    """Return (problem, missing, extra): problem is None when the take is fine, else a short description.

    missing and extra are the expected words not heard and the heard words not in the text, for the report."""
    want, got = words(expected), words(heard)
    if not want:
        return None, [], []
    missing, extra, longest_missing, longest_extra = [], [], 0, 0
    for op, a1, a2, b1, b2 in SequenceMatcher(None, want, got, autojunk=False).get_opcodes():
        if op == "equal":
            continue
        lost, added = want[a1:a2], got[b1:b2]
        if op == "replace" and SequenceMatcher(None, " ".join(lost), " ".join(added)).ratio() >= SAME_WORD:
            continue  # a mishearing or respelling of the same words, not a skip
        missing += lost
        extra += added
        longest_missing = max(longest_missing, len(lost))
        longest_extra = max(longest_extra, len(added))
    if longest_missing >= MISSING_RUN or len(missing) > MISSING_SHARE * len(want):
        return f"{len(missing)} of {len(want)} words not heard", missing, extra
    if longest_extra >= EXTRA_RUN or (len(extra) >= 3 and len(extra) > EXTRA_SHARE * len(want)):
        return f"{len(extra)} extra words heard", missing, extra
    return None, missing, extra


def not_downloaded(error):
    """True if error (or what caused it) means a model file isn't on this Mac and the internet couldn't be reached."""
    while error is not None:
        if type(error).__name__ == "LocalEntryNotFoundError":  # from huggingface_hub, which downloads the models
            return True
        error = error.__cause__ or error.__context__
    return False


def available():
    import importlib.util

    return importlib.util.find_spec("faster_whisper") is not None


class Whisper:
    """faster-whisper, loaded (and downloaded the first time) only when a paragraph is first checked."""

    def __init__(self, model=WHISPER_MODEL, log=print, threads=0):
        self.name, self.log, self.threads, self.model = model, log, threads, None

    def transcribe(self, audio, sr):
        if self.model is None:
            from faster_whisper import WhisperModel

            self.log(f"Loading Whisper ({self.name}) to check for skipped words… the first time, it downloads about 480 MB")
            self.model = WhisperModel(self.name, device="cpu", compute_type="int8", cpu_threads=self.threads)
        if sr != WHISPER_RATE:
            import soxr

            audio = soxr.resample(audio, sr, WHISPER_RATE)
        segments, _ = self.model.transcribe(np.asarray(audio, dtype=np.float32), language="en", beam_size=5,
                                            condition_on_previous_text=False, vad_filter=False)
        return " ".join(segment.text.strip() for segment in segments)


def checked(synth, sr, transcribe, retries=2, log=print, problems=None, where=lambda: ""):
    """Wrap synth so each paragraph is transcribed and narrated again (up to `retries` times) if words are missing.

    The take with the fewest missing words is kept. Paragraphs still wrong after the retries are appended to
    `problems` as dicts, so they can be listed in a report."""

    broken = []  # set when Whisper can't run (for example offline on first use); narration then carries on unchecked

    def synth_checked(text):
        if broken:
            return synth(text)
        best = None
        for attempt in range(retries + 1):
            audio = synth(text)
            try:
                heard = transcribe(audio, sr)
            except Exception as e:
                broken.append(e)
                if not_downloaded(e):
                    log("Whisper hasn't been downloaded yet, so this run isn't checked for skipped words. "
                        "Connect to the internet once to download it (about 480 MB); after that it works offline.")
                else:
                    log(f"Couldn't run Whisper, so the rest of this run isn't checked for skipped words: {e}")
                return audio
            problem, missing, extra = compare(text, heard)
            score = len(missing) + len(extra)
            if best is None or score < best[0]:
                best = (score, audio, problem, heard, missing)
            if problem is None:
                if attempt:
                    log(f"{where()}fixed on try {attempt + 1}: “{shorten(text)}”")
                return audio
            if attempt < retries:
                log(f"{where()}{problem}, narrating again: “{shorten(text)}”")
        _, audio, problem, heard, missing = best
        if problem:
            log(f"{where()}still {problem} after {retries + 1} tries; listed in the check report")
            if problems is not None:
                problems.append(dict(where=where().rstrip(": "), problem=problem, text=text, heard=heard,
                                     missing=" ".join(missing)))
        return audio

    return synth_checked


def shorten(text, limit=70):
    return text if len(text) <= limit else text[:limit - 1] + "…"


def write_report(path, title, problems):
    lines = [f"Paragraphs in “{title}” that may have skipped or garbled words", "",
             "Listen to each one. To get a new take, click Redo next to its chapter.", ""]
    for i, p in enumerate(problems, 1):
        lines += [f"{i}. {p['where']}: {p['problem']}", f"   Text:  {p['text']}", f"   Heard: {p['heard']}",
                  f"   Not heard: {p['missing'] or '(none)'}", ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
