"""The Voice step: Kokoro voice cards and blending, Chatterbox clips, and voice previews.

A part of the main window (gui.App); self is the App."""
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk

from gui_common import (
    ACCENT_CHOICES,
    ACCENTS,
    COVER_BG,
    ENGINE_LABELS,
    GENDER_CHOICES,
    KOKORO,
    KOKORO_VOICES,
    PREVIEW_HINT,
    clip_length,
    shorten,
    voice_info,
)
from record_dialog import RecordDialog
from theme import (
    AMBER,
    AMBER_DARK,
    AMBER_HOVER,
    AMBER_LINE,
    AMBER_SOFT,
    CARD,
    CARD_LINE,
    FIELD,
    FIELD_LINE,
    KNOB,
    KNOB_HOVER,
    LABEL,
    LINE,
    MONO,
    RAISED,
    SEGMENTS,
    TEXT,
    TEXT2,
    TEXT3,
    TRACK,
    F,
    button,
    card,
    entry,
    label,
    on_click,
)


class VoiceStep:
    def build_voice(self, page):
        main = ctk.CTkFrame(page, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(2, weight=1)
        self.page_heading(main, "Who should read your book?", "Press play on any voice to hear it read your first "
                          "chapter. Click a voice to choose it.").grid(row=0, column=0, sticky="ew", pady=(0, 16))
        engines = ctk.CTkFrame(main, fg_color="transparent")
        engines.grid(row=1, column=0, sticky="ew", pady=(0, 12))
        engine_of = {text: engine for engine, text in ENGINE_LABELS.items()}
        self.engine_toggle = ctk.CTkSegmentedButton(engines, values=list(ENGINE_LABELS.values()), height=38,
                                                    command=lambda text: self.set_engine(engine_of[text]),
                                                    font=F(13, "bold"), **SEGMENTS)
        self.engine_toggle.pack(side="left")

        panels = ctk.CTkFrame(main, fg_color="transparent")
        panels.grid(row=2, column=0, sticky="nsew")
        panels.grid_columnconfigure(0, weight=1)
        panels.grid_rowconfigure(0, weight=1)
        self.build_kokoro_panel(panels)
        self.build_chatterbox_panel(panels)

        aside = ctk.CTkFrame(page, fg_color="transparent", width=280)
        aside.grid(row=0, column=1, sticky="ns")
        aside.grid_propagate(False)
        aside.grid_columnconfigure(0, weight=1)
        aside.grid_rowconfigure(4, weight=1)
        summary = card(aside)
        summary.grid(row=0, column=0, sticky="ew")
        summary.grid_columnconfigure(0, weight=1)
        label(summary, "Your audiobook", 12, TEXT3, "bold").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 10))
        book = ctk.CTkFrame(summary, fg_color="transparent")
        book.grid(row=1, column=0, sticky="ew", padx=18)
        self.voice_cover = ctk.CTkLabel(book, text="", width=56, height=56, corner_radius=6, fg_color=COVER_BG)
        self.voice_cover.pack(side="left")
        names = ctk.CTkFrame(book, fg_color="transparent")
        names.pack(side="left", padx=(12, 0))
        self.voice_book = label(names, "", 13, TEXT, "bold")
        self.voice_book.pack(anchor="w")
        self.voice_book_sub = label(names, "", 12, TEXT2)
        self.voice_book_sub.pack(anchor="w")
        ctk.CTkFrame(summary, fg_color=LINE, height=1, corner_radius=0).grid(row=2, column=0, sticky="ew", padx=18, pady=12)
        facts = ctk.CTkFrame(summary, fg_color="transparent")
        facts.grid(row=3, column=0, sticky="ew", padx=18, pady=(0, 16))
        facts.grid_columnconfigure(1, weight=1)
        self.voice_facts = {}
        for i, name in enumerate(("Narrator", "Speed", "Characters")):
            label(facts, name, 13, TEXT2).grid(row=i, column=0, sticky="w", pady=3)
            self.voice_facts[name] = label(facts, "", 13, TEXT, "bold")
            self.voice_facts[name].grid(row=i, column=1, sticky="e", pady=3)

        self.build_preview(aside).grid(row=2, column=0, sticky="ew", pady=(14, 0))
        extras = card(aside)
        extras.grid(row=3, column=0, sticky="ew", pady=(14, 0))
        self.extra_cards.append(extras)
        label(extras, "Make it yours", 13, TEXT, "bold").pack(anchor="w", padx=18, pady=(16, 4))
        label(extras, "Blend two voices into one, or give characters their own voices.", 13, TEXT2, justify="left",
              wraplength=240).pack(anchor="w", padx=18)
        button(extras, "Voice extras", lambda: self.show_step("sound"), "secondary", height=34).pack(anchor="w", padx=18,
                                                                                                   pady=(10, 16))

    def build_kokoro_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        self.kokoro_panel = panel
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(2, weight=1)

        # Shown while the blend voice is being chosen (from the Sound step's Blend with a second voice).
        self.blend_notice = ctk.CTkFrame(panel, fg_color=AMBER_SOFT, border_color=AMBER_LINE, border_width=1,
                                         corner_radius=12)
        self.blend_notice.grid_columnconfigure(0, weight=1)
        self.blend_notice_text = label(self.blend_notice, "", 13, TEXT, "bold")
        self.blend_notice_text.grid(row=0, column=0, sticky="w", padx=16, pady=10)
        button(self.blend_notice, "Cancel", lambda: self.pick_slot("a"), "ghost", width=80, height=30,
               font=F(12, "bold")).grid(row=0, column=1, padx=(0, 12))

        filters = ctk.CTkFrame(panel, fg_color="transparent")
        filters.grid(row=1, column=0, sticky="ew")
        filters.grid_columnconfigure(0, weight=1)
        self.search = entry(filters, placeholder_text=f"Search {len(KOKORO_VOICES)} voices", height=38)
        self.search.grid(row=0, column=0, sticky="ew")
        self.search.bind("<KeyRelease>", lambda event: self.refresh_voices())
        menu = dict(height=38, width=132, corner_radius=10, fg_color=CARD, button_color=CARD, button_hover_color=RAISED,
                    text_color=TEXT, font=F(13, "bold"), dropdown_font=F(13), dropdown_fg_color=CARD,
                    dropdown_hover_color=RAISED, dropdown_text_color=TEXT, command=lambda v: self.refresh_voices())
        self.accent = ctk.CTkOptionMenu(filters, values=list(ACCENT_CHOICES), **menu)
        self.accent.grid(row=0, column=1, padx=(10, 0))
        self.gender = ctk.CTkOptionMenu(filters, values=list(GENDER_CHOICES), **menu)
        self.gender.grid(row=0, column=2, padx=(10, 0))
        self.voice_count = label(filters, "", 12, TEXT3)
        self.voice_count.grid(row=1, column=0, columnspan=3, sticky="w", pady=(8, 0))

        self.voice_grid = ctk.CTkScrollableFrame(panel, fg_color="transparent", height=120)
        self.voice_grid.grid(row=2, column=0, sticky="nsew", pady=(6, 0))
        self.voice_grid.grid_columnconfigure((0, 1, 2), weight=1, uniform="voice")
        self.no_match = label(self.voice_grid, "No voices match. Try another name or clear a filter.", 13, TEXT2)
        self.voice_cards = {voice: self.make_voice_card(voice) for voice in sorted(KOKORO_VOICES)}

    def make_voice_card(self, voice):
        name, accent, gender = voice_info(voice)
        frame = ctk.CTkFrame(self.voice_grid, height=64, corner_radius=12, border_width=1, border_color=CARD_LINE,
                             fg_color=CARD)
        frame.grid_propagate(False)
        frame.grid_columnconfigure(1, weight=1)
        frame.grid_rowconfigure(0, weight=1)
        texts = ctk.CTkFrame(frame, fg_color="transparent")
        texts.grid(row=0, column=1, sticky="w", padx=(12, 4), pady=4)
        label(texts, name, 14, TEXT, "bold").pack(anchor="w")
        label(texts, f"{ACCENTS.get(accent, accent)} · {gender}", 12, TEXT3).pack(anchor="w")
        badge = label(frame, "", 11, AMBER, "bold")
        badge.grid(row=0, column=2, padx=(0, 12), pady=4)
        on_click(frame, lambda: self.pick_voice(voice))
        # Added after on_click, so pressing play previews the voice without choosing it.
        play = ctk.CTkButton(frame, text="▶", width=36, height=36, corner_radius=18, fg_color=TRACK,
                             hover_color="#3A404B", text_color=TEXT, font=F(13), command=lambda: self.play_voice(voice))
        play.grid(row=0, column=0, padx=(12, 0))
        return dict(frame=frame, badge=badge, play=play)

    def build_chatterbox_panel(self, parent):
        panel = ctk.CTkFrame(parent, fg_color="transparent")
        self.chatterbox_panel = panel
        panel.grid_columnconfigure(0, weight=1)
        panel.grid_rowconfigure(1, weight=1)
        head = ctk.CTkFrame(panel, fg_color="transparent")
        head.grid(row=0, column=0, sticky="w")
        label(head, "Voice clip", 13, LABEL, "bold").pack(anchor="w")
        label(head, "Optional. Without a clip, Chatterbox uses its built-in voice. Only copy your own voice, or the "
              "voice of someone who has agreed to it.", 12, TEXT3, justify="left", wraplength=520).pack(anchor="w", pady=(2, 0))
        self.clip_list = ctk.CTkScrollableFrame(panel, fg_color="transparent", height=120)
        self.clip_list.grid(row=1, column=0, sticky="nsew", pady=(10, 10))
        self.clip_list.grid_columnconfigure(0, weight=1)
        buttons = ctk.CTkFrame(panel, fg_color="transparent")
        buttons.grid(row=2, column=0, sticky="ew")
        buttons.grid_columnconfigure((0, 1), weight=1, uniform="clip")
        button(buttons, "Browse…", self.pick_ref, "secondary", height=44, font=F(14, "bold")).grid(row=0, column=0, sticky="ew", padx=(0, 5))
        button(buttons, "Record…", self.record, "secondary", height=44, font=F(14, "bold")).grid(row=0, column=1, sticky="ew", padx=(5, 0))
        check = ctk.CTkFrame(panel, fg_color="transparent")
        check.grid(row=3, column=0, sticky="ew", pady=(12, 0))
        check.grid_columnconfigure(0, weight=1)
        texts = ctk.CTkFrame(check, fg_color="transparent")
        texts.grid(row=0, column=0, sticky="w")
        label(texts, "Check for skipped words", 13, LABEL, "bold").pack(anchor="w")
        label(texts, "Retries a paragraph if Whisper hears words missing.", 12, TEXT3).pack(anchor="w")
        self.check_switch = ctk.CTkSwitch(check, text="", width=46, progress_color=AMBER, button_color=KNOB,
                                          button_hover_color=KNOB_HOVER, fg_color=TRACK)
        self.check_switch.select()
        self.check_switch.grid(row=0, column=1, sticky="e")

    def build_preview(self, parent):
        """A preview box; there is one on the Voice step and one on the Sound step."""
        panel = card(parent)
        panel.grid_columnconfigure(1, weight=1)
        btn = button(panel, "▶  Preview", lambda: self.start(sample=True), "primary", width=110, height=40)
        btn.grid(row=0, column=0, padx=(14, 12), pady=14, sticky="n")
        text = label(panel, PREVIEW_HINT, 12, TEXT2, justify="left", anchor="w", wraplength=130)
        text.grid(row=0, column=1, sticky="w", padx=(0, 12), pady=10)
        again = button(panel, "Play again", self.play_preview, "ghost", width=110, height=30, font=F(12, "bold"))
        bar = ctk.CTkProgressBar(panel, mode="indeterminate", height=4, progress_color=AMBER, fg_color=TRACK)
        self.previews.append(dict(btn=btn, text=text, again=again, bar=bar))
        return panel

    def set_engine(self, engine):
        self.engine = engine
        self.engine_toggle.set(ENGINE_LABELS[engine])
        kokoro = engine == KOKORO
        for frame, shown in ((self.kokoro_panel, kokoro), (self.chatterbox_panel, not kokoro)):
            frame.grid(row=0, column=0, sticky="nsew") if shown else frame.grid_remove()
        for frame, shown in ((self.kokoro_sliders, kokoro), (self.chatterbox_sliders, not kokoro)):
            frame.grid(row=1, column=0, sticky="ew", padx=20) if shown else frame.grid_remove()
        self.refresh_clips()
        self.set_preview("idle")
        self.draw_rhythm()
        if hasattr(self, "step"):
            self.refresh_summary()

    def narrator_voice(self):
        return f"{self.voice_a}, {self.voice_b}" if self.voice_b else self.voice_a

    def pick_slot(self, slot):
        self.slot = slot
        self.refresh_voices()

    def remove_b(self):
        self.voice_b = None
        self.slot = "a"
        self.refresh_voices()

    def pick_voice(self, voice):
        a, b = self.voice_a, self.voice_b
        if self.slot == "a":
            if voice == b:
                b = a  # picking the blend voice as the main one swaps them
            a = voice
        else:
            if voice == a and b is None:
                return
            if voice == a:
                a = b
            b = voice
        self.voice_a, self.voice_b = a, b
        self.slot = "a"  # a blend voice is picked once, then clicks choose the narrator again
        self.refresh_voices()
        self.set_preview("idle")

    def refresh_voices(self):
        if self.slot == "b":
            self.blend_notice_text.configure(text=f"Choose a voice to blend with {voice_info(self.voice_a)[0]}.")
            self.blend_notice.grid(row=0, column=0, sticky="ew", pady=(0, 12))
        else:
            self.blend_notice.grid_remove()

        query = self.search.get().strip().lower()
        shown = []
        for voice in sorted(KOKORO_VOICES):
            name, accent, gender = voice_info(voice)
            if (ACCENT_CHOICES[self.accent.get()] in (None, accent) and GENDER_CHOICES[self.gender.get()] in (None, gender)
                    and (not query or query in name.lower() or query in voice)):
                shown.append(voice)
        total = len(KOKORO_VOICES)
        self.voice_count.configure(text=f"{total} voices" if len(shown) == total else f"{len(shown)} of {total}")
        self.no_match.grid_forget()
        for voice, card_ in self.voice_cards.items():
            card_["frame"].grid_forget()
            chosen = voice == self.voice_a or voice == self.voice_b
            card_["frame"].configure(fg_color=AMBER_SOFT if chosen else CARD, border_width=2 if chosen else 1,
                                     border_color=AMBER if chosen else CARD_LINE)
            card_["badge"].configure(text="Narrator" if voice == self.voice_a else "Blend" if voice == self.voice_b else "")
            self.style_play(voice, chosen)
        for i, voice in enumerate(shown):
            self.voice_cards[voice]["frame"].grid(row=i // 3, column=i % 3, sticky="ew", padx=4, pady=4)
        if not shown:
            self.no_match.grid(row=0, column=0, columnspan=3, sticky="w", padx=4, pady=14)
        if hasattr(self, "step"):
            self.refresh_summary()

    def refresh_clips(self):
        for row in self.clip_list.winfo_children():
            row.destroy()
        saved = sorted(Path("voices").glob("*.wav"), key=lambda p: p.stat().st_mtime, reverse=True) if Path("voices").is_dir() else []
        paths = [str(p.resolve()) for p in saved]
        if self.clip and self.clip not in paths:
            paths.insert(0, self.clip)  # a clip chosen with Browse… from elsewhere
        rows = [(None, "Built-in voice", "Default · no clip needed")]
        rows += [(p, Path(p).name, f"Reference clip · {clip_length(p)}") for p in paths]
        for i, (path, name, meta) in enumerate(rows):
            selected = path == self.clip
            frame = ctk.CTkFrame(self.clip_list, height=58, corner_radius=12, border_width=1, fg_color=AMBER_SOFT if selected else FIELD,
                                 border_color=AMBER if selected else FIELD_LINE)
            frame.grid(row=i, column=0, sticky="ew", padx=2, pady=3)
            frame.grid_propagate(False)
            frame.grid_columnconfigure(0, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            texts = ctk.CTkFrame(frame, fg_color="transparent")
            texts.grid(row=0, column=0, sticky="w", padx=(14, 4), pady=4)
            label(texts, shorten(name, 40), 13, TEXT, "bold", family=MONO if path else None).pack(anchor="w")
            label(texts, meta, 12, TEXT3).pack(anchor="w")
            label(frame, "✓" if selected else "", 16, AMBER, "bold", width=24).grid(row=0, column=1, padx=(0, 12), pady=4)
            on_click(frame, lambda p=path: self.choose_clip(p))
            if path:  # hear the clip itself; added after on_click so it doesn't also choose it
                button(frame, "▶", lambda p=path, n=name: self.player_bar.open(p, n, resume=False), "secondary",
                       width=34, height=34, corner_radius=17, border_width=0, font=F(12)).grid(row=0, column=2, padx=(0, 10))

    def choose_clip(self, path):
        self.clip = path
        self.refresh_clips()
        self.set_preview("idle")
        self.refresh_summary()

    def pick_ref(self):
        clip = filedialog.askopenfilename(title="Voice clip to copy (about 10 seconds of clean speech)",
                                          filetypes=[("Audio", "*.wav *.mp3 *.flac *.m4a"), ("All files", "*")])
        if clip:
            self.choose_clip(clip)

    def record(self):
        dialog = RecordDialog(self)
        self.wait_window(dialog)
        if dialog.result:
            self.choose_clip(str(dialog.result.resolve()))
            self._append(f"Saved {dialog.result} ({dialog.seconds:.0f}s). Click Preview to hear Chatterbox read with it.")
        elif dialog.captured:
            self._append("Recording discarded.")

    def set_preview(self, state, path=None):
        if state == "ready":
            self.sample_path = str(path)
        for preview in self.previews:
            preview["bar"].stop()
            preview["bar"].grid_remove()
            preview["again"].grid_remove()
            if state == "busy":
                preview["text"].configure(text="Making a sample… the first time, the voice has to download.")
                preview["bar"].grid(row=1, column=0, columnspan=2, sticky="ew", padx=14, pady=(0, 14))
                preview["bar"].start()
            elif state == "ready":
                preview["text"].configure(text="Playing in the bar below.")
                preview["again"].grid(row=1, column=0, padx=(14, 12), pady=(0, 14))
            else:
                preview["text"].configure(text=PREVIEW_HINT)

    def set_preview_buttons(self, state):
        for preview in self.previews:
            preview["btn"].configure(state=state)

    def play_voice(self, voice):
        """A voice card's play button: replay this voice's preview if one matches, otherwise make one."""
        if self.running:
            return
        if not self.folder or not Path(self.folder).is_dir():
            self.notify("Choose a book first, so the voice has something to read.")
            return
        path = self.fresh_previews.get(self.preview_key(self.render_args(sample=True, voice=voice)))
        if path and Path(path).is_file():
            self.set_preview("ready", path)
            self.play_preview()
        else:
            self.start(sample=True, voice=voice)

    def refresh_play_buttons(self):
        for voice in self.voice_cards:
            self.style_play(voice, voice in (self.voice_a, self.voice_b))

    def style_play(self, voice, chosen):
        busy = self.running and self.previewing == voice
        lit = chosen or busy
        self.voice_cards[voice]["play"].configure(
            text="…" if busy else "▶", fg_color=AMBER if lit else TRACK, hover_color=AMBER_HOVER if lit else "#3A404B",
            text_color=AMBER_DARK if lit else TEXT, state="disabled" if self.running and not busy else "normal")
