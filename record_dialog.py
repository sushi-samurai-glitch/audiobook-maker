"""Dialog that records a short voice clip for Chatterbox and saves it in the voices folder."""
import math
import re
import time
from pathlib import Path

import customtkinter as ctk
import numpy as np
import soundfile as sf

from theme import AMBER, AMBER_DARK, AMBER_HOVER, BG, CARD, CARD_LINE, GREEN, RED, TEXT, TEXT2, TEXT3, TRACK, button, entry, label

RECORD_SR = 44100
RECORD_SECONDS = 12  # Chatterbox only uses the first 10 seconds of a voice clip
READ_ALOUD = ("The evening light came slowly across the valley, and for a moment everything was still. "
              "Then the wind picked up, carrying the smell of rain, and somewhere far off a door closed.")


class RecordDialog(ctk.CTkToplevel):
    """Record, trim the silence, then ask for a name. `result` is the saved path, or None."""

    def __init__(self, master):
        super().__init__(master)
        self.title("Record a voice")
        self.geometry("520x620")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.result = None
        self.captured = False  # a recording was made but not saved
        self.stream = None
        self.audio = None
        self.level = 0.0
        self.confirm_name = None  # name the user has been asked to confirm replacing
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(5, weight=1)  # spare height sits above the buttons

        label(self, "Record a voice", 24, TEXT, "bold").grid(row=0, column=0, sticky="w", padx=32, pady=(28, 6))
        label(self, "Read the passage below in the voice and pace you want for the book. "
                    "Chatterbox copies the first 10 seconds. Record only your own voice, or someone who has agreed to it.", 14, TEXT2, justify="left",
              wraplength=450).grid(row=1, column=0, sticky="w", padx=32)

        passage = ctk.CTkFrame(self, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=14)
        passage.grid(row=2, column=0, sticky="ew", padx=32, pady=(18, 14))
        label(passage, READ_ALOUD, 17, TEXT, justify="left", wraplength=416).pack(anchor="w", padx=18, pady=16)

        meter = ctk.CTkFrame(self, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=14)
        meter.grid(row=3, column=0, sticky="ew", padx=32)
        self.timer = label(meter, self.clock(RECORD_SECONDS), 40, TEXT, family="Menlo")
        self.timer.pack(pady=(18, 10))
        self.meter_bar = ctk.CTkProgressBar(meter, height=10, progress_color=AMBER, fg_color=TRACK)
        self.meter_bar.set(0)
        self.meter_bar.pack(fill="x", padx=24, pady=(0, 20))

        self.message = label(self, "Start speaking right away, in your narrator voice.", 13, TEXT3, justify="left",
                             wraplength=450)
        self.message.grid(row=4, column=0, sticky="w", padx=32, pady=(14, 0))

        self.naming = ctk.CTkFrame(self, fg_color="transparent")
        label(self.naming, "Name this voice", 13, TEXT2, "bold").pack(anchor="w")
        self.name = entry(self.naming, placeholder_text="for example narrator")
        self.name.pack(fill="x", pady=(6, 0))
        self.name.bind("<KeyRelease>", self.name_changed)

        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.grid(row=6, column=0, sticky="ew", padx=32, pady=(18, 28))
        actions.grid_columnconfigure(0, weight=1)
        button(actions, "Cancel", self.close, "ghost", width=96, height=46).grid(row=0, column=0, sticky="w")
        self.action = button(actions, "Start recording", self.start_recording, "danger", width=170, height=46)
        self.action.grid(row=0, column=1)

        self.transient(master)
        self.protocol("WM_DELETE_WINDOW", self.close)
        self.after(150, self.focus_dialog)

    def focus_dialog(self):
        if self.winfo_exists():
            self.grab_set()
            self.focus()

    @staticmethod
    def clock(seconds):
        return f"0:{max(0, math.ceil(seconds)):02d}"

    def say(self, text, color=TEXT3):
        self.message.configure(text=text, text_color=color)

    def start_recording(self):
        import sounddevice as sd

        self.chunks = []
        self.level = 0.0

        def collect(data, frames, t, status):
            self.chunks.append(data.copy())
            self.level = float(np.abs(data).max())

        try:
            self.stream = sd.InputStream(samplerate=RECORD_SR, channels=1, dtype="float32", callback=collect)
            self.stream.start()
        except Exception as e:
            self.stream = None
            self.say(f"Couldn't start recording: {e}", RED)
            return
        self.started = time.time()
        self.say("Recording… keep reading until the timer reaches zero, or click Stop.")
        self.action.configure(text="Stop", command=self.finish_recording)
        self.tick()

    def tick(self):
        if not self.stream:
            return
        left = RECORD_SECONDS - (time.time() - self.started)
        if left <= 0:
            self.finish_recording()
            return
        self.timer.configure(text=self.clock(left))
        self.meter_bar.set(min(1.0, self.level * 3))
        self.after(100, self.tick)

    def finish_recording(self):
        if not self.stream:
            return
        self.stream.stop()
        self.stream.close()
        self.stream = None
        self.meter_bar.set(0)
        self.timer.configure(text=self.clock(RECORD_SECONDS))
        self.action.configure(text="Start recording", command=self.start_recording)
        audio = np.concatenate(self.chunks)[:, 0] if self.chunks else np.zeros(0, dtype=np.float32)

        # Trim the silence around the speech so the 10 seconds Chatterbox uses are all voice.
        loud = np.flatnonzero(np.abs(audio) > 0.02)
        if len(loud) == 0 or (loud[-1] - loud[0]) / RECORD_SR < 5:
            self.say("Didn't catch 5 seconds of speech. Speak closer to the microphone and try again. If it stays "
                     "silent, allow Audiobook Maker in System Settings → Privacy & Security → Microphone.", RED)
            return
        self.audio = audio[max(0, loud[0] - RECORD_SR // 10):loud[-1] + RECORD_SR // 4]
        self.captured = True
        self.say(f"Got {len(self.audio) / RECORD_SR:.0f} seconds of speech. Name it to save it, or record again.", GREEN)
        self.naming.grid(row=5, column=0, sticky="new", padx=32, pady=(14, 0))
        self.action.configure(text="Save voice", command=self.save, fg_color=AMBER, hover_color=AMBER_HOVER,
                              text_color=AMBER_DARK)
        self.name.focus()

    def name_changed(self, event=None):
        if self.confirm_name is not None:
            self.confirm_name = None
            self.action.configure(text="Save voice")
            self.say("Name it to save it, or record again.", GREEN)

    def save(self):
        name = re.sub(r"[^\w-]+", "-", self.name.get().strip()).strip("-")
        if not name:
            self.say("The name needs at least one letter or number.", RED)
            return
        path = Path("voices") / f"{name}.wav"
        if path.exists() and self.confirm_name != name:
            self.confirm_name = name
            self.action.configure(text="Replace voice")
            self.say(f'A voice named "{name}" already exists. Click Replace voice to overwrite it, or type another name.',
                     RED)
            return
        try:
            path.parent.mkdir(exist_ok=True)
            sf.write(path, self.audio, RECORD_SR)
        except Exception as e:
            self.say(f"Couldn't save the voice: {e}", RED)
            return
        self.result = path
        self.seconds = len(self.audio) / RECORD_SR
        self.captured = False
        self.close()

    def close(self):
        if self.stream:
            self.stream.stop()
            self.stream.close()
            self.stream = None
        self.destroy()
