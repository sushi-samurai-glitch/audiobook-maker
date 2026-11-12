"""The Sound step: speed, pauses, Chatterbox settings and character voices.

A part of the main window (gui.App); self is the App."""
from pathlib import Path
from tkinter import Canvas

import customtkinter as ctk

from cast_window import CastWindow
from gui_common import KOKORO, KOKORO_VOICES, RECOMMENDED, voice_info
from theme import AMBER, DISABLED, FIELD, FIELD_LINE, LABEL, TEXT, TEXT2, TEXT3, F, button, card, label


class SoundStep:
    def build_sound(self, page):
        main = ctk.CTkFrame(page, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        main.grid_columnconfigure(0, weight=1)
        head = ctk.CTkFrame(main, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 18))
        head.grid_columnconfigure(0, weight=1)
        self.page_heading(head, "How should it sound?", "The recommended settings suit most books.").grid(row=0, column=0, sticky="w")
        button(head, "Reset to recommended", self.reset_settings, "ghost", height=34).grid(row=0, column=1, sticky="se")

        pacing = card(main)
        pacing.grid(row=1, column=0, sticky="ew")
        pacing.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(pacing, fg_color="transparent", height=6).grid(row=0, column=0)
        # Only the settings for the selected engine are shown; see set_engine.
        self.kokoro_sliders = ctk.CTkFrame(pacing, fg_color="transparent")
        row, self.speed = self.slider(self.kokoro_sliders, "Speed", "How fast the voice reads. 1.00 is natural.", 0.5, 2.0,
                                      RECOMMENDED["speed"])
        row.pack(fill="x", pady=(10, 10))
        self.chatterbox_sliders = ctk.CTkFrame(pacing, fg_color="transparent")
        row, self.exaggeration = self.slider(self.chatterbox_sliders, "Exaggeration", "Flat to dramatic.", 0.25, 2.0, RECOMMENDED["exaggeration"])
        row.pack(fill="x", pady=(10, 10))
        row, self.cfg_weight = self.slider(self.chatterbox_sliders, "Pacing", "Lower reads slower.", 0.0, 1.0, RECOMMENDED["cfg_weight"])
        row.pack(fill="x", pady=(0, 10))
        row, self.temperature = self.slider(self.chatterbox_sliders, "Temperature", "Higher varies more.", 0.3, 1.5, RECOMMENDED["temperature"])
        row.pack(fill="x", pady=(0, 10))

        pauses = ctk.CTkFrame(pacing, fg_color="transparent")
        pauses.grid(row=2, column=0, sticky="ew", padx=20)
        row, self.paragraph_pause = self.slider(pauses, "Paragraph pause (s)", "Silence after each paragraph.", 0.0, 2.0, RECOMMENDED["paragraph_pause"])
        row.pack(fill="x", pady=(0, 10))
        row, self.title_pause = self.slider(pauses, "Heading pause (s)", "Silence after a chapter heading.", 0.0, 3.0, RECOMMENDED["title_pause"])
        row.pack(fill="x", pady=(0, 10))

        rhythm = ctk.CTkFrame(pacing, fg_color=FIELD, border_color=FIELD_LINE, border_width=1, corner_radius=12)
        rhythm.grid(row=3, column=0, sticky="ew", padx=20, pady=(0, 20))
        top = ctk.CTkFrame(rhythm, fg_color="transparent")
        top.pack(fill="x", padx=14, pady=(12, 6))
        label(top, "Rhythm", 12, LABEL, "bold").pack(side="left")
        label(top, "Paragraph", 11, TEXT3).pack(side="right")
        ctk.CTkLabel(top, text="■", width=12, text_color=DISABLED, font=F(11)).pack(side="right", padx=(10, 2))
        label(top, "Heading", 11, TEXT3).pack(side="right")
        ctk.CTkLabel(top, text="■", width=12, text_color=AMBER, font=F(11)).pack(side="right", padx=(0, 2))
        self.rhythm = Canvas(rhythm, height=24, bg=FIELD, highlightthickness=0)
        self.rhythm.pack(fill="x", padx=14, pady=(0, 14))
        self.rhythm.bind("<Configure>", lambda event: self.draw_rhythm())

        aside = ctk.CTkFrame(page, fg_color="transparent", width=300)
        aside.grid(row=0, column=1, sticky="ns")
        aside.grid_propagate(False)
        aside.grid_columnconfigure(0, weight=1)
        aside.grid_rowconfigure(4, weight=1)
        label(aside, "Voice extras · optional", 12, TEXT3, "bold").grid(row=0, column=0, sticky="w", pady=(0, 10))
        blend = card(aside)
        blend.grid(row=1, column=0, sticky="ew")
        self.extra_cards.append(blend)
        label(blend, "Blend with a second voice", 14, TEXT, "bold").pack(anchor="w", padx=18, pady=(16, 3))
        self.blend_text = label(blend, "", 13, TEXT2, justify="left", wraplength=260)
        self.blend_text.pack(anchor="w", padx=18)
        blend_buttons = ctk.CTkFrame(blend, fg_color="transparent")
        blend_buttons.pack(anchor="w", padx=18, pady=(10, 16))
        self.blend_btn = button(blend_buttons, "Choose a voice…", self.choose_blend, "secondary", height=34)
        self.blend_btn.pack(side="left")
        self.blend_remove = button(blend_buttons, "Remove", self.remove_b, "ghost", height=34, width=80)
        cast = card(aside)
        cast.grid(row=2, column=0, sticky="ew", pady=(12, 0))
        self.extra_cards.append(cast)
        label(cast, "Character voices", 14, TEXT, "bold").pack(anchor="w", padx=18, pady=(16, 3))
        self.cast_status = label(cast, "", 13, TEXT2, justify="left", wraplength=260)
        self.cast_status.pack(anchor="w", padx=18)
        button(cast, "Set up cast…", self.open_cast, "secondary", height=34).pack(anchor="w", padx=18, pady=(10, 16))
        self.extras_note = label(aside, "Blending and character voices work with Kokoro voices. Switch to Kokoro on "
                                 "the Voice step to use them.", 13, TEXT2, justify="left", anchor="w", wraplength=280)
        self.build_preview(aside).grid(row=5, column=0, sticky="ew")

    def choose_blend(self):
        self.show_step("voice")
        self.pick_slot("b")

    def refresh_blend(self):
        if self.voice_b:
            self.blend_text.configure(text=f"{voice_info(self.voice_a)[0]} is blended with {voice_info(self.voice_b)[0]}.")
            self.blend_btn.configure(text="Change…")
            self.blend_remove.pack(side="left", padx=(8, 0))
        else:
            self.blend_text.configure(text=f"Mix {voice_info(self.voice_a)[0]} with another voice to make a narrator "
                                           "no one else has.")
            self.blend_btn.configure(text="Choose a voice…")
            self.blend_remove.pack_forget()

    def draw_rhythm(self):
        """Heading, paragraph, paragraph with the pauses between them, so the sliders' effect is visible."""
        canvas = self.rhythm
        canvas.delete("all")
        width = canvas.winfo_width()
        if width < 20:
            return
        speed = self.speed.get() if self.engine == KOKORO else 1.0
        parts = [("h", 1.6 / speed), ("g", self.title_pause.get()), ("p", 3 / speed), ("g", self.paragraph_pause.get()),
                 ("p", 3 / speed)]
        scale = width / sum(size for _, size in parts)
        x = 0
        for kind, size in parts:
            end = x + size * scale
            if kind == "h":
                canvas.create_rectangle(x, 2, end, 22, fill=AMBER, outline="")
            elif kind == "p":
                canvas.create_rectangle(x, 6, end, 18, fill="#6B717C", outline="")
            else:
                canvas.create_line(x, 12, end, 12, fill="#343943", width=2)
            x = end

    def reset_settings(self):
        for name, value in RECOMMENDED.items():
            slider = getattr(self, name)
            slider.set(value)
            self.value_labels[slider].configure(text=f"{value:.2f}")  # set() doesn't fire the slider's command
        self.draw_rhythm()
        self._append("Speed and pauses reset to the recommended values.")

    def refresh_cast(self):
        if not self.cast.get("enabled"):
            text = "Off. Give characters their own voices for dialogue."
        else:
            count = len(self.cast.get("voices", {}))
            text = f"On. {count} character{'s' if count != 1 else ''} with their own voice."
        self.cast_status.configure(text=text)
        if hasattr(self, "step"):
            self.refresh_summary()

    def open_cast(self):
        if not self.folder or not Path(self.folder).is_dir():
            self.notify("Choose a chapters folder first.")
            return
        if self.cast_window and self.cast_window.winfo_exists():
            self.cast_window.lift()
            return
        self.cast_window = CastWindow(self, sorted(KOKORO_VOICES), self.narrator_voice())
        self.cast_window.lift()
        self.cast_window.focus()
