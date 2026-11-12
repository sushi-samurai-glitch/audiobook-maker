"""Play audio inside the app: ffmpeg decodes the file and sounddevice plays it.

Works for .m4b, MP3 and WAV on macOS and Windows, and changes speed without changing the pitch (ffmpeg's atempo).
Seeking, pausing and changing speed stop ffmpeg and start it again at the new position, which takes a moment."""
import json
import subprocess
import threading

try:
    import sounddevice as sd
except OSError:  # PortAudio missing: the app still opens, and playing says why it can't
    sd = None

import tools

RATE = 44100
CHUNK = 2048  # frames handed to the sound card at a time (about 46 ms)
SPEEDS = (0.75, 1.0, 1.25, 1.5, 2.0)  # atempo accepts 0.5 to 2.0


def probe(path):
    """(duration in seconds, chapters as a list of (start, title)) read with ffprobe."""
    try:
        result = tools.run(["ffprobe", "-v", "error", "-show_format", "-show_chapters", "-of", "json", str(path)],
                           capture_output=True, text=True)
    except OSError:  # ffprobe missing: playing then says FFmpeg is needed
        return 0.0, []
    try:
        info = json.loads(result.stdout or "{}")
    except ValueError:
        info = {}
    duration = float(info.get("format", {}).get("duration") or 0)
    chapters = [(float(c["start_time"]), (c.get("tags") or {}).get("title") or f"Chapter {i}")
                for i, c in enumerate(info.get("chapters", []), 1)]
    return duration, chapters


def chapter_at(chapters, seconds):
    """Index of the chapter playing at this time, or -1 before the first (or when there are none)."""
    index = -1
    for i, (start, _) in enumerate(chapters):
        if start <= seconds + 0.05:
            index = i
    return index


class Player:
    def __init__(self):
        self.path = None
        self.duration, self.chapters = 0.0, []
        self.speed = 1.0
        self.playing = False
        self.error = None  # set by the playing thread if the sound card or ffmpeg fails
        self._start = 0.0  # file position where the current play began
        self._frames = 0  # frames played since then
        self._stop = threading.Event()
        self._thread = None
        self._proc = None

    def load(self, path, position=0.0):
        self.pause()
        self.path = str(path)
        self.duration, self.chapters = probe(path)
        self.error = None
        self._start = self._clamp(position)

    @property
    def position(self):
        if self.playing:
            return min(self._start + self._frames / RATE * self.speed, self.duration)
        return self._start

    def play(self):
        if self.playing or not self.path:
            return
        if self._start >= self.duration - 0.5:
            self._start = 0.0  # at the end: start over
        self._frames = 0
        self._stop = threading.Event()
        self.playing = True
        self._thread = threading.Thread(target=self._run, args=(self._stop, self._start, self.speed), daemon=True)
        self._thread.start()

    def pause(self):
        if not self.playing:
            return
        position = self.position
        self._stop.set()
        if self._proc:
            self._proc.kill()
        self._thread.join(timeout=2)
        self.playing = False
        self._start = position

    def seek(self, seconds):
        was_playing = self.playing
        self.pause()
        self._start = self._clamp(seconds)
        if was_playing:
            self.play()

    def set_speed(self, speed):
        was_playing = self.playing
        self.pause()
        self.speed = speed
        if was_playing:
            self.play()

    def _clamp(self, seconds):
        return max(0.0, min(float(seconds), self.duration))

    def _run(self, stop, start, speed):
        if sd is None:
            self.error = "No audio output: the PortAudio library is missing"
            self.playing = False
            return
        if not tools.find("ffmpeg"):
            self.error = tools.MISSING_FFMPEG
            self.playing = False
            return
        proc = tools.popen(["ffmpeg", "-v", "error", "-ss", f"{start:.3f}", "-i", self.path, "-vn",
                            "-af", f"atempo={speed}", "-f", "s16le", "-ac", "2", "-ar", str(RATE), "-"],
                           stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
        self._proc = proc
        try:
            with sd.RawOutputStream(samplerate=RATE, channels=2, dtype="int16") as stream:
                while not stop.is_set():
                    data = proc.stdout.read(CHUNK * 4)  # 2 channels x 2 bytes
                    if not data:
                        break
                    stream.write(data)
                    self._frames += len(data) // 4
                if stop.is_set():
                    stream.abort()  # drop what's queued so pausing is instant
        except Exception as e:  # no sound device, ffmpeg missing, unreadable file
            self.error = str(e)
        finally:
            proc.kill()
            proc.wait()
            if not stop.is_set():  # reached the end (or failed): stay paused there
                self._start = self.duration if self.error is None else self.position
                self.playing = False
