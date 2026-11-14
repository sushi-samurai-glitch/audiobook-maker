"""Turn a folder of Markdown chapters into an .m4b audiobook with open-source TTS."""
import argparse
import ctypes
import hashlib
import json
import re
import subprocess
import sys
import time
from pathlib import Path

import numpy as np
import soundfile as sf

import book_settings
import cast
import paths
import tools

PARAGRAPH_PAUSE = 0.6
TITLE_PAUSE = 1.2
SCENE_PAUSE = 2.0  # silence at a scene break (---, *** or * * * on its own line)
DEFAULT_TAG_PAUSE = 1.0  # [pause] without a number
SAMPLE_CHARS = 1500
PRONUNCIATIONS_FILE = book_settings.PRONUNCIATIONS_FILE
SAMPLE_RATE = 24000  # Kokoro narrates at 24 kHz

# Loudness of each chapter in the finished files, within what audiobook stores (ACX) accept:
# about -20 dB average (they allow -23 to -18) with peaks no higher than -3 dB.
LOUDNESS = -20.0
TRUE_PEAK = -3.0
OUT_RATE = 44100
MP3_BITRATE = "192k"
ROOM_TONE = (0.75, 2.0)  # seconds of silence at the start and end of each MP3, as ACX asks

# Gentle mode, for a Mac without a fan. Measured on an M4 MacBook Air: Kokoro on 2 threads instead of all 4
# fast cores is about 15% slower but uses 40% less CPU.
GENTLE_THREADS = 2
WORK_STRETCH = 300  # seconds of narrating before gentle mode rests
REST = 60  # seconds of rest, so the chip cools down instead of throttling itself
QOS_CLASS_UTILITY = 0x11  # macOS: long-running work the person isn't waiting on; apps they're using come first

# [pause], [pause 2], [pause 2s], [pause 1.5 s]: extra silence at that spot.
PAUSE_TAG = re.compile(r"\[pause(?:\s+(\d+(?:\.\d+)?)\s*s?)?\]", re.I)
SCENE_BREAK = "\x00scene\x00"
ENGINE = "kokoro"  # the start of render and preview names (build/<book>/kokoro-am_michael, samples/kokoro-am_michael.wav)


def md_to_paragraphs(md, paragraph_pause=PARAGRAPH_PAUSE, title_pause=TITLE_PAUSE, scene_pause=SCENE_PAUSE):
    """Return [(text, pause_after_seconds), ...] with Markdown syntax removed.

    A scene break makes the pause before it at least scene_pause long; a [pause N] tag adds N seconds of
    silence where it appears, splitting the paragraph there. Text can be empty when silence comes first."""
    md = re.sub(r"```.*?```", "", md, flags=re.S)
    md = re.sub(r"<!--.*?-->", "", md, flags=re.S)
    md = re.sub(r"<[^>]+>", "", md)
    md = re.sub(r"!\[[^\]]*\]\([^)]*\)", "", md)
    md = re.sub(r"\[([^\]]+)\]\([^)]*\)", r"\1", md)
    md = re.sub(r"`([^`]*)`", r"\1", md)
    md = re.sub(r"^[ \t]{0,3}([-*_][ \t]*){3,}$", f"\n{SCENE_BREAK}\n", md, flags=re.M)
    md = re.sub(r"^[ \t]*>[ \t]?", "", md, flags=re.M)
    md = re.sub(r"^[ \t]*([-*+]|\d+\.)[ \t]+", "", md, flags=re.M)
    md = re.sub(r"(\*\*|__|~~)(\S.*?)\1", r"\2", md)
    md = re.sub(r"(?<!\w)([*_])(\S.*?)\1(?!\w)", r"\2", md)

    paragraphs = []

    def add_silence(seconds, at_least=False):
        if not paragraphs:
            paragraphs.append(("", seconds))
            return
        text, pause = paragraphs[-1]
        paragraphs[-1] = (text, max(pause, seconds) if at_least else pause + seconds)

    for block in re.split(r"\n\s*\n", md):
        text = " ".join(line.strip() for line in block.splitlines() if line.strip())
        if not text:
            continue
        if text == SCENE_BREAK:
            add_silence(scene_pause, at_least=True)
            continue
        heading = text.startswith("#")
        if heading:
            text = text.lstrip("#").strip()
        own_pause = title_pause if heading else paragraph_pause
        # Odd items of the split are the tags' numbers, even items the text between them.
        parts = PAUSE_TAG.split(text)
        spoken = [i for i in range(0, len(parts), 2) if parts[i].strip()]
        for i, part in enumerate(parts):
            if i % 2:
                add_silence(float(part) if part else DEFAULT_TAG_PAUSE)
                continue
            part = part.strip()
            if not part:
                continue
            if heading and i == spoken[-1] and not part.endswith((".", "!", "?")):
                part += "."
            paragraphs.append((part, own_pause if i == len(parts) - 1 else 0.0))
        if spoken and spoken[-1] != len(parts) - 1:
            # The block's text ended with a tag: its own pause still follows the tag's silence.
            add_silence(own_pause)
    return paragraphs


def load_pronunciations(folder):
    """Read word = how to say it rules from pronunciations.txt in the chapters folder.

    Returns [(word, replacement), ...]; lines without '=' and lines starting with # are ignored."""
    path = Path(folder) / PRONUNCIATIONS_FILE
    if not path.is_file():
        return []
    rules = []
    for line in book_settings.read_text(path).splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        word, say = (part.strip() for part in line.split("=", 1))
        if word and say:
            rules.append((word, say))
    return rules


def apply_pronunciations(paragraphs, rules):
    """Replace each rule's word (whole word, any capitalization) with how it should be said."""
    if not rules:
        return paragraphs
    # Longest words first, so "New York" wins over "York".
    say = {word.lower(): replacement for word, replacement in rules}
    pattern = re.compile("|".join(rf"(?<!\w){re.escape(w)}(?!\w)" for w in sorted(say, key=len, reverse=True)), re.I)
    return [(pattern.sub(lambda m: say[m.group(0).lower()], item[0]),) + tuple(item[1:]) for item in paragraphs]


def chapter_title(md, path):
    m = re.search(r"^#+\s+(.+)$", md, flags=re.M)
    return m.group(1).strip() if m else path.stem


def sentence_chunks(text, limit=300):
    chunks, current = [], ""
    for sentence in re.split(r"(?<=[.!?…])\s+", text):
        if current and len(current) + len(sentence) + 1 > limit:
            chunks.append(current)
            current = sentence
        else:
            current = f"{current} {sentence}".strip()
    if current:
        chunks.append(current)
    return chunks


_full_threads = []  # PyTorch's own thread count, remembered so turning gentle mode off restores it


def limit_threads(gentle):
    import torch

    if not _full_threads:
        _full_threads.append(torch.get_num_threads())
    torch.set_num_threads(min(GENTLE_THREADS, _full_threads[0]) if gentle else _full_threads[0])


def lower_priority():
    """Mark the calling thread as background-ish work, so macOS gives the apps in use the CPU first."""
    if sys.platform == "darwin":
        ctypes.CDLL(None).pthread_set_qos_class_self_np(QOS_CLASS_UTILITY, 0)


def with_rests(synth, log=print, cancel=None, work=WORK_STRETCH, rest=REST, clock=time.monotonic, wait=None,
               resting=None):
    """Wrap synth so that after `work` seconds of narrating it rests for `rest` seconds before the next paragraph.

    Paragraphs reused from the cache don't call synth, so they never cause a rest. Raises Cancelled if
    the cancel event is set during a rest. resting(True) is called as a rest starts and resting(False) as it ends."""
    resting = resting or (lambda now: None)
    if wait is None:
        wait = cancel.wait if cancel is not None else (lambda seconds: time.sleep(seconds))
    started = [clock()]

    def rested(text, voice=None):
        if clock() - started[0] >= work:
            log(f"Gentle mode: resting {rest} s to let your computer cool down…")
            resting(True)
            try:
                if wait(rest):
                    raise Cancelled
            finally:
                resting(False)
            started[0] = clock()
        return synth(text) if voice is None else synth(text, voice)

    return rested


def load_engine(args, log=print):
    """Return (sample_rate, synth) where synth(text) -> float32 numpy array."""
    limit_threads(getattr(args, "gentle", False))
    from kokoro import KPipeline

    pipelines = {args.voice[0]: KPipeline(lang_code=args.voice[0], repo_id="hexgrad/Kokoro-82M")}

    def synth(text, voice=None):
        """voice is a character's voice; None means the narrator's (args.voice)."""
        voice = voice or args.voice
        if voice[0] not in pipelines:  # a British character in an American book, or the other way round
            first = next(iter(pipelines.values()))
            pipelines[voice[0]] = KPipeline(lang_code=voice[0], repo_id="hexgrad/Kokoro-82M", model=first.model)
        parts = [audio.numpy() for _, _, audio in pipelines[voice[0]](text, voice=voice, speed=args.speed)]
        return np.concatenate(parts) if parts else np.zeros(0, dtype=np.float32)

    return 24000, synth


def not_downloaded(error):
    """True if error (or what caused it) means a model file isn't on this Mac and the internet couldn't be reached."""
    while error is not None:
        if type(error).__name__ == "LocalEntryNotFoundError":  # from huggingface_hub, which downloads the models
            return True
        error = error.__cause__ or error.__context__
    return False


# The voice model on Hugging Face, and roughly how much the first use downloads.
MODELS = {"kokoro": ("hexgrad/Kokoro-82M", "about 330 MB")}


def model_downloaded(engine="kokoro", cache=None):
    """Whether the voice model is already on this computer (in the Hugging Face cache)."""
    if cache is None:
        try:
            from huggingface_hub.constants import HF_HUB_CACHE as cache
        except ImportError:
            return True  # can't tell; say nothing rather than something wrong
    snapshots = Path(cache) / f"models--{MODELS[engine][0].replace('/', '--')}" / "snapshots"
    return snapshots.is_dir() and any(snapshots.iterdir())


class LazyVoice:
    """Loads the voice model only when a paragraph actually needs narrating, so rebuilding a finished book
    (new cover, title, MP3 export) doesn't wait for Kokoro to load."""

    def __init__(self, args, log=print, report=None, cancel=None):
        self.args, self.log, self.synth = args, log, None
        self.report = report or (lambda *step: None)
        self.cancel = cancel

    def needed_files(self):
        """{pack key: files} the run needs: Kokoro's model and the voices this book uses."""
        import downloads

        voices = {v.strip() for v in self.args.voice.split(",") if v.strip()}
        cast = cast_voices(self.args) or {}
        voices |= {v for v in [cast.get("dialogue"), *(cast.get("voices") or {}).values()] if v}
        return {"kokoro": list(downloads.kokoro_files(sorted(voices)))}

    def download(self):
        """Fetch what the run needs that isn't here yet, saying how far along it is (in the log every 10%)."""
        import downloads

        needed = self.needed_files()
        key = next(iter(needed))
        try:
            missing = downloads.missing(downloads.PACKS[key], files=needed[key])
        except ImportError:  # no huggingface_hub here: let the engine download as it always has
            return
        if not missing:
            return
        size = "about 330 MB" if "kokoro-v1_0.pth" in missing else "a few MB"
        self.log(f"Downloading what this voice needs ({size}). This happens only once, and can take a while on a "
                 "slow connection…")
        said = [-1]

        def progress(done, total, _name):
            self.report("download", done, total)
            tenth = int(10 * done / total) if total else 0
            if tenth > said[0] and 0 < tenth < 10:
                said[0] = tenth
                self.log(f"Downloading… {tenth * 10}%")

        try:
            downloads.fetch([key], progress, self.cancel, files=needed)
        except downloads.Cancelled:
            raise Cancelled() from None

    def __call__(self, text, voice=None):
        try:
            if self.synth is None:
                self.download()
                sr, self.synth = load_engine(self.args, log=self.log)
                if sr != SAMPLE_RATE:
                    raise RuntimeError(f"Kokoro narrates at {sr} Hz, but the app expects {SAMPLE_RATE} Hz")
            return self.synth(text, voice) if voice else self.synth(text)
        except Exception as e:
            if not not_downloaded(e):
                raise
            # Each Kokoro voice, and the model, downloads the first time it's used.
            if self.synth is None:
                what = "Kokoro's voice model hasn't"
            else:
                what = f"The Kokoro voice {voice or self.args.voice} hasn't"
            raise ModelNotDownloaded(f"{what} been downloaded yet. Connect to the internet and try again; "
                                     "after that it works offline.") from e


class ModelNotDownloaded(Exception):
    """A voice model isn't on this computer yet and the internet couldn't be reached to download it."""


class Cancelled(Exception):
    """Raised when the caller's cancel event is set; chapters already rendered are kept."""


class ParagraphCache:
    """Each paragraph's narration, saved as FLAC under a hash of its text and the voice settings.

    A chapter is put together from these, so an edited paragraph, a changed pause or a redone chapter
    only narrates what is missing, and a cancelled chapter keeps the paragraphs it finished."""

    def __init__(self, folder, settings, sr):
        self.folder, self.settings, self.sr = Path(folder), settings, sr
        self.fresh = set()  # narrated during this run, so a redo doesn't narrate a repeated paragraph twice

    def path(self, text, voice=None):
        # Narrator lines keep the key they had before character voices existed, so nothing is narrated again.
        key = (text, self.settings) if voice is None else (text, self.settings, voice)
        return self.folder / f"{hashlib.sha1(repr(key).encode()).hexdigest()[:16]}.flac"

    def get(self, text, synth, redo=False, voice=None):
        path = self.path(text, voice)
        if path.exists() and (not redo or path in self.fresh):
            audio, _ = sf.read(path, dtype="float32")
            return audio
        audio = synth(text) if voice is None else synth(text, voice)
        if len(audio):
            self.folder.mkdir(parents=True, exist_ok=True)
            tmp = path.with_suffix(".part")
            sf.write(tmp, audio, self.sr, format="FLAC")
            tmp.replace(path)
            self.fresh.add(path)
        return audio


def render(paragraphs, sr, synth, out_path, cancel=None, cache=None, redo=False):
    """Write paragraphs and their pauses to out_path. With a cache, saved paragraphs are reused unless redo.

    Each item is (text, pause) for the narrator's voice, or (text, pause, voice) for a character's line."""
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".part")
    try:
        # Each paragraph is written as soon as it is ready, so a long chapter never has to fit in memory at once.
        with sf.SoundFile(tmp, "w", samplerate=sr, channels=1, format="WAV", subtype="PCM_16") as wav:
            for text, pause, *rest in paragraphs:
                voice = rest[0] if rest else None
                if cancel is not None and cancel.is_set():
                    raise Cancelled
                if text:
                    if cache:
                        wav.write(cache.get(text, synth, redo, voice))
                    else:
                        wav.write(synth(text) if voice is None else synth(text, voice))
                wav.write(np.zeros(int(sr * pause), dtype=np.float32))
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(out_path)


def book_folder(chapters):
    """build/<folder name>-<short hash of its full path>, so two books never share renders."""
    folder = Path(chapters).resolve()
    return Path("build") / f"{folder.name}-{hashlib.sha1(str(folder).encode()).hexdigest()[:6]}"


def clean_up(build, keep):
    """Delete chapter WAVs and saved paragraphs in build that the current book no longer uses.

    Returns (files deleted, bytes freed). Other voices' folders are left alone, so switching back reuses them."""
    count = freed = 0
    candidates = list(build.glob("*.wav")) + list(build.glob("*.part"))
    candidates += list(build.glob("leveled/*.wav")) + list(build.glob("leveled/*.part"))
    if (build / "paragraphs").is_dir():
        candidates += list((build / "paragraphs").iterdir())
    for path in candidates:
        if path.is_file() and path not in keep:
            freed += path.stat().st_size
            path.unlink()
            count += 1
    return count, freed


def ffmeta_escape(value):
    return re.sub(r"([=;#\\\n])", r"\\\1", value)


def measure_loudness(wav):
    """ffmpeg loudnorm's first pass: the chapter's measured loudness values, as a dict of strings."""
    result = tools.run(["ffmpeg", "-hide_banner", "-nostats", "-i", str(wav), "-af",
                        f"loudnorm=I={LOUDNESS}:TP={TRUE_PEAK}:LRA=11:print_format=json", "-f", "null", "-"],
                       capture_output=True, text=True, check=True)
    return json.loads(result.stderr[result.stderr.rindex("{"):result.stderr.rindex("}") + 1])


def level_chapter(wav, out):
    """Write wav at the book's loudness and 44.1 kHz to out (two-pass loudnorm, so the level is even, not pumped).

    Kept in build/.../leveled under the chapter's own name, so it is only redone when the chapter changes."""
    if out.exists():
        return out
    m = measure_loudness(wav)
    if m.get("input_i") in ("-inf", None):  # a silent chapter: nothing to level
        audio_filter = "anull"
    else:
        audio_filter = (f"loudnorm=I={LOUDNESS}:TP={TRUE_PEAK}:LRA=11:measured_I={m['input_i']}:"
                        f"measured_TP={m['input_tp']}:measured_LRA={m['input_lra']}:measured_thresh={m['input_thresh']}:"
                        f"offset={m['target_offset']}:linear=true")
    out.parent.mkdir(parents=True, exist_ok=True)
    tmp = out.with_suffix(".part")
    tools.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af", audio_filter, "-ar", str(OUT_RATE),
               "-ac", "1", "-c:a", "pcm_s16le", "-f", "wav", str(tmp)], check=True)
    tmp.replace(out)
    return out


def safe_name(text):
    return re.sub(r'[\\/:*?"<>|]+', "", text).strip().rstrip(".") or "Chapter"


def out_name(args):
    """The name the book's files in out/ share: the .m4b and the MP3 folder (and the check report earlier versions made).

    The app picks one no other book uses (library.claim_output); without one it is the title, made safe for a file name."""
    return getattr(args, "output_name", None) or safe_name(args.title)


def m4b_path(args):
    return paths.OUT / f"{out_name(args)}.m4b"


def mp3_folder(args):
    return paths.OUT / f"{out_name(args)} (MP3)"


def export_mp3(chapters, wavs, args, progress=None):
    """One MP3 per chapter, numbered in order, in the format audiobook stores ask for: 44.1 kHz mono, 192 kbps
    constant bit rate, with a little silence at the start and end. Returns the folder.

    progress(done, total) is called after each chapter."""
    folder = mp3_folder(args)
    folder.mkdir(parents=True, exist_ok=True)
    for old in folder.glob("*.mp3"):  # chapters may have been renamed or removed since the last export
        old.unlink()
    head, tail = ROOM_TONE
    for i, ((title, _), wav) in enumerate(zip(chapters, wavs, strict=True), 1):
        out = folder / f"{i:02d} - {safe_name(title)}.mp3"
        tools.run(["ffmpeg", "-y", "-loglevel", "error", "-i", str(wav), "-af",
                   f"adelay={round(head * 1000)}:all=1,apad=pad_dur={tail}", "-ar", str(OUT_RATE), "-ac", "1",
                   "-c:a", "libmp3lame", "-b:a", MP3_BITRATE, "-metadata", f"title={title}",
                   "-metadata", f"album={args.title}", "-metadata", f"artist={args.author}",
                   "-metadata", f"track={i}/{len(chapters)}", "-metadata", "genre=Audiobook", str(out)], check=True)
        if progress:
            progress(i, len(chapters))
    return folder


def build_m4b(chapters, wavs, args, progress=None):
    """Join the chapters into one .m4b with chapter markers, metadata and the cover; returns its path.

    progress(done, total) is called as ffmpeg encodes, in milliseconds of audio."""
    out = m4b_path(args)
    out.parent.mkdir(parents=True, exist_ok=True)
    # Written under another name first, so a build that is stopped never leaves a broken .m4b that looks finished.
    tmp = out.with_name(out.name + ".part")
    work = wavs[0].parent

    concat = work / "concat.txt"
    lines = ("file '{}'\n".format(w.resolve().as_posix().replace("'", r"'\''")) for w in wavs)
    concat.write_text("".join(lines), encoding="utf-8")

    meta = [";FFMETADATA1", f"title={ffmeta_escape(args.title)}", f"album={ffmeta_escape(args.title)}",
            f"artist={ffmeta_escape(args.author)}", "genre=Audiobook", ""]
    start = 0
    for (title, _), wav in zip(chapters, wavs, strict=True):
        end = start + round(sf.info(wav).duration * 1000)
        meta += ["[CHAPTER]", "TIMEBASE=1/1000", f"START={start}", f"END={end}", f"title={ffmeta_escape(title)}", ""]
        start = end
    metafile = work / "metadata.txt"
    metafile.write_text("\n".join(meta), encoding="utf-8")

    cmd = ["ffmpeg", "-y", "-loglevel", "error", "-f", "concat", "-safe", "0", "-i", str(concat), "-i", str(metafile)]
    if args.cover:
        cmd += ["-i", args.cover]
    cmd += ["-map", "0:a", "-map_metadata", "1", "-map_chapters", "1"]
    if args.cover:
        cmd += ["-map", "2:v", "-c:v", "copy", "-disposition:v", "attached_pic"]
    cmd += ["-c:a", "aac", "-b:a", "64k", "-ac", "1", "-f", "mp4", str(tmp)]
    try:
        run_ffmpeg(cmd, start, progress)
    except BaseException:
        tmp.unlink(missing_ok=True)
        raise
    tmp.replace(out)
    return out


def run_ffmpeg(cmd, total_ms, progress=None):
    """Run an ffmpeg command, calling progress(done_ms, total_ms) as it works through the audio."""
    if not progress:
        tools.run(cmd, check=True)
        return
    cmd = cmd[:1] + ["-nostats", "-progress", "pipe:1"] + cmd[1:]
    with tools.popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True) as proc:
        for line in proc.stdout:
            key, _, value = line.strip().partition("=")
            # out_time_us is newer; older ffmpeg names the same microseconds out_time_ms.
            if key in ("out_time_us", "out_time_ms") and value.isdigit():
                progress(min(int(value) // 1000, total_ms), total_ms)
        error = proc.stderr.read()
    if proc.returncode:
        raise subprocess.CalledProcessError(proc.returncode, cmd, stderr=error)
    progress(total_ms, total_ms)


def main():
    import os

    os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")  # no usage reports to Hugging Face
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--chapters", default="chapters", help="folder of .md or .txt files, one per chapter, sorted by name")
    p.add_argument("--voice", default="am_michael",
                   help="Kokoro voice, e.g. af_heart, am_michael, bf_emma; blend voices with a comma: am_michael,bm_george")
    p.add_argument("--speed", type=float, default=1.0, help="Kokoro speaking speed")
    p.add_argument("--paragraph-pause", type=float, default=PARAGRAPH_PAUSE, help="seconds of silence after a paragraph")
    p.add_argument("--title-pause", type=float, default=TITLE_PAUSE, help="seconds of silence after a heading")
    p.add_argument("--scene-pause", type=float, default=SCENE_PAUSE, help="seconds of silence at a scene break (---)")
    p.add_argument("--sample", action="store_true", help="render a short sample of chapter 1 only")
    p.add_argument("--redo", type=int, nargs="+", metavar="N", help="narrate these chapter numbers again")
    p.add_argument("--cast", help="character voices as JSON, e.g. '{\"enabled\": true, \"dialogue\": \"af_heart\", "
                                   "\"voices\": {\"Mara\": \"bf_emma\"}}'")
    p.add_argument("--mp3", action="store_true", help="also export one MP3 per chapter (44.1 kHz, 192 kbps) to out/")
    p.add_argument("--gentle", action="store_true",
                   help="fewer threads, lower priority and a short rest every few minutes, for a laptop without a fan")
    p.add_argument("--title", default="Audiobook")
    p.add_argument("--author", default="Unknown")
    p.add_argument("--cover", help="cover image (jpg/png)")
    args = p.parse_args()
    args.cast = json.loads(args.cast) if args.cast else None
    try:
        run(args)
    except ModelNotDownloaded as e:
        raise SystemExit(str(e)) from e


def prepare(args, log=print):
    """Read the chapters and work out what narrating them takes: (chapters, settings, voice_id, voices, build).

    chapters is [(title, paragraphs)] with voices and pronunciations applied; build is the folder for the renders."""
    files = book_settings.chapter_files(args.chapters)
    if not files:
        raise SystemExit(f"No chapter files (.md or .txt) found in {args.chapters}/")
    rules = load_pronunciations(args.chapters)
    if rules:
        log(f"Using {len(rules)} pronunciation{'s' if len(rules) != 1 else ''} from {PRONUNCIATIONS_FILE}")
    scene_pause = getattr(args, "scene_pause", SCENE_PAUSE)
    raw = []
    for f in files:
        md = book_settings.read_text(f)
        raw.append((chapter_title(md, f), md_to_paragraphs(md, args.paragraph_pause, args.title_pause, scene_pause)))
    voices = cast_voices(args)
    if voices:
        log("Reading dialogue in character voices")
    known = book_cast(raw) if voices else ()
    chapters = []
    for title, paragraphs in raw:
        paragraphs = assign_voices(paragraphs, voices, known)
        # Applied before hashing, so editing the list re-renders only the chapters that use a changed word.
        chapters.append((title, apply_pronunciations(paragraphs, rules)))

    voice_id = args.voice
    settings = (args.speed,)
    # Character-voice renders get their own folder, so switching back to one voice reuses the one-voice renders.
    # The "kokoro-" start is from when there was a second engine; it stays so books made then are reused.
    build = book_folder(args.chapters) / f"{ENGINE}-{voice_id}{'-cast' if voices else ''}"
    return chapters, settings, voice_id, voices, build


def chapter_wav(build, i, paragraphs, settings):
    """Where chapter i is rendered. Hashing the text, pauses and voice settings means an edited chapter,
    a different book, or changed settings is re-rendered."""
    digest = hashlib.sha1(repr((paragraphs, settings)).encode()).hexdigest()[:8]
    return build / f"{i:02d}-{digest}.wav"


def legacy_folder(args, voice_id):
    return Path("build") / f"{ENGINE}-{voice_id}"  # where earlier versions kept every book's renders


def made_chapters(args):
    """Numbers of the chapters already rendered with these chapters, voice and settings (for the Redo buttons)."""
    chapters, settings, voice_id, _, build = prepare(args, log=lambda message: None)
    legacy = legacy_folder(args, voice_id)
    made = set()
    for i, (_, paragraphs) in enumerate(chapters, 1):
        wav = chapter_wav(build, i, paragraphs, settings)
        if wav.exists() or (legacy / wav.name).exists():
            made.add(i)
    return made


def run(args, log=print, cancel=None, progress=None):
    """Render a sample or the full audiobook; returns the path of the file written.

    If `cancel` (a threading.Event) is set, stops at the next paragraph and raises Cancelled.
    progress(stage, done, total[, details]) reports a full build: stage "narrate" (chapters narrated of those that need
    it, starting at 0), then "level" (chapters), "build" (milliseconds of audio in the .m4b) and "mp3" (chapters).
    Along the way, "chapter" (chapter number, chapter count, details) says a chapter is ready: details is
    {"kept": True} for one made earlier, else {"audio": minutes of audio, "took": minutes it took}; and in gentle mode
    "rest" (1 or 0, 1) says a rest started or ended."""
    report = progress or (lambda *step: None)
    chapters, settings, voice_id, voices, build = prepare(args, log)
    sr, synth = SAMPLE_RATE, LazyVoice(args, log, report, cancel)
    cache = ParagraphCache(build / "paragraphs", settings, sr)

    gentle = getattr(args, "gentle", False)
    if gentle:
        lower_priority()
        log("Gentle mode: narrating more slowly to keep your computer cool and responsive")

    if gentle:
        synth = with_rests(synth, log, cancel, WORK_STRETCH, REST, resting=lambda now: report("rest", int(now), 1))

    if args.sample:
        paragraphs, total = [], 0
        for para in chapters[0][1]:
            paragraphs.append(para)
            total += len(para[0])
            if total >= SAMPLE_CHARS:
                break
        out = Path("samples") / f"{ENGINE}-{voice_id}.wav"
        # Always a fresh take; the full build then reuses the one you heard.
        render(paragraphs, sr, synth, out, cancel, cache, redo=True)
        log(f"Wrote {out}")
        return out

    redo = set(getattr(args, "redo", None) or ())
    legacy = legacy_folder(args, voice_id)
    wavs = []
    for i, (_, paragraphs) in enumerate(chapters, 1):
        wav = chapter_wav(build, i, paragraphs, settings)
        wavs.append(wav)
        if not wav.exists() and (legacy / wav.name).exists():
            build.mkdir(parents=True, exist_ok=True)
            (legacy / wav.name).replace(wav)
    todo = [i for i, wav in enumerate(wavs, 1) if not wav.exists() or i in redo]
    report("narrate", 0, len(todo))
    for i, ((title, paragraphs), wav) in enumerate(zip(chapters, wavs, strict=True), 1):
        if i not in todo:
            log(f"[{i}/{len(chapters)}] {title}: already rendered, skipping")
            report("chapter", i, len(chapters), {"kept": True})
            continue
        t = time.time()
        render(paragraphs, sr, synth, wav, cancel, cache, redo=i in redo)
        audio, took = sf.info(wav).duration / 60, (time.time() - t) / 60
        log(f"[{i}/{len(chapters)}] {title}: {audio:.1f} min audio in {took:.1f} min")
        report("chapter", i, len(chapters), {"audio": audio, "took": took})
        report("narrate", todo.index(i) + 1, len(todo))
    log("Levelling the volume of each chapter…")
    leveled = []
    for i, wav in enumerate(wavs, 1):
        leveled.append(level_chapter(wav, build / "leveled" / wav.name))
        report("level", i, len(wavs))
    log("Building the audiobook file…")
    out = build_m4b(chapters, leveled, args, progress=lambda done, total: report("build", done, total))
    log(f"Wrote {out}")
    if getattr(args, "mp3", False):
        log("Exporting the MP3s…")
        log(f"Wrote {export_mp3(chapters, leveled, args, progress=lambda done, total: report('mp3', done, total))}")

    keep = set(wavs) | set(leveled) | {cache.path(text, rest[0] if rest else None)
                                       for _, paragraphs in chapters for text, _, *rest in paragraphs if text}
    count, freed = clean_up(build, keep)
    if count:
        log(f"Deleted {count} old render{'s' if count != 1 else ''} ({freed / 1e6:.0f} MB)")
    return out


def cast_voices(args):
    """The book's character voices as {"dialogue": voice or None, "voices": {name: voice}}, or None when the
    book is read in one voice. Voices are Kokoro names like af_heart."""
    config = getattr(args, "cast", None) or {}
    if not config.get("enabled"):
        return None
    narrator = args.voice
    same = lambda voice: None if not voice or voice == narrator else voice  # the narrator's voice means "no change"
    return {"dialogue": same(config.get("dialogue")),
            "voices": {name: same(voice) for name, voice in (config.get("voices") or {}).items() if same(voice)}}


def book_cast(raw):
    """Every character name found by speech tags or {Name} tags, with how many times each was found."""
    counts = {}
    for _, paragraphs in raw:
        for text, *_ in paragraphs:
            for name in cast.find_names(text):
                counts[name] = counts.get(name, 0) + 1
    return counts


def assign_voices(paragraphs, voices, known):
    """Split paragraphs with dialogue into narrator and character lines. Without voices, only {Name} tags are
    removed, so a book read in one voice is unchanged."""
    if not voices:
        return [(cast.strip_tags(t), *rest) if "{" in t else (t, *rest) for t, *rest in paragraphs]
    out = []
    for (text, pause), segments in zip(paragraphs, cast.split_all([text for text, _ in paragraphs], known), strict=True):
        lines = []
        for piece, speaker in segments:
            voice = None
            if speaker is not None:  # dialogue
                voice = voices["voices"].get(speaker) or voices["dialogue"]
            if lines and lines[-1][1] == voice:
                lines[-1] = (f"{lines[-1][0]} {piece}", voice)
            else:
                lines.append((piece, voice))
        if all(voice is None for _, voice in lines):
            out.append((cast.strip_tags(text), pause))  # nothing to voice differently: keep the paragraph whole
            continue
        for j, (piece, voice) in enumerate(lines):
            gap = pause if j == len(lines) - 1 else 0.0
            out.append((piece, gap) if voice is None else (piece, gap, voice))
    return out


def scan_cast(folder, config=None):
    """For the Cast window: (characters with their line counts, most first; unknown-speaker lines; report text).

    The report lists every line of dialogue with the voice it gets, chapter by chapter."""
    config = config or {}
    files = book_settings.chapter_files(folder)
    texts = [(f, book_settings.read_text(f)) for f in files]
    raw = [(chapter_title(md, f), md_to_paragraphs(md)) for f, md in texts]
    known = book_cast(raw)
    lines, unknown = {}, 0
    report = ["Who said what", "", "Each line of dialogue and the character it was given to. "
              "To fix one, put {Name} right before its opening quote mark in the chapter.", ""]
    for i, (title, paragraphs) in enumerate(raw, 1):
        report += [f"Chapter {i}: {title}", ""]
        for segments in cast.split_all([text for text, *_ in paragraphs], known):
            for piece, speaker in segments:
                if speaker is None:
                    continue
                if speaker:
                    lines[speaker] = lines.get(speaker, 0) + 1
                else:
                    unknown += 1
                report.append(f"  {speaker or '(other dialogue)'}: “{piece}”")
        report.append("")
    characters = sorted(lines.items(), key=lambda item: (-item[1], item[0]))
    return characters, unknown, "\n".join(report)



if __name__ == "__main__":
    main()
