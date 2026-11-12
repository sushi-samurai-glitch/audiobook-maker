"""Cast window: turn character voices on or off and pick a voice for the dialogue and for each character."""
from pathlib import Path

import customtkinter as ctk

import audiobook
import desktop
from theme import (AMBER, AMBER_SOFT, BG, CARD, CARD_LINE, KNOB, KNOB_HOVER, RAISED, TEXT, TEXT2, TEXT3, TRACK,
                   F, button, label)

NARRATOR = "Narrator's voice"
DIALOGUE = "Other dialogue voice"
MENU = dict(fg_color=RAISED, button_color=RAISED, button_hover_color="#2B3038", text_color=TEXT, corner_radius=9,
            dropdown_fg_color=CARD, dropdown_text_color=TEXT, dropdown_hover_color="#2B3038", width=170, height=32)


class CastWindow(ctk.CTkToplevel):
    """Edits app.cast in place: {"enabled": bool, "dialogue": voice or None, "voices": {name: voice}}."""

    def __init__(self, app, voices, voice_name):
        super().__init__(app)
        self.app, self.voices, self.voice_name = app, voices, voice_name
        self.title("Character voices")
        self.geometry("600x660")
        self.configure(fg_color=BG)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(3, weight=1)
        cast = app.cast

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 6))
        head.grid_columnconfigure(0, weight=1)
        label(head, "Character voices", 24, TEXT, "bold").grid(row=0, column=0, sticky="w")
        self.switch = ctk.CTkSwitch(head, text="", width=46, progress_color=AMBER, button_color=KNOB,
                                    button_hover_color=KNOB_HOVER, fg_color=TRACK, command=self.changed)
        self.switch.grid(row=0, column=1, sticky="e")
        if cast.get("enabled"):
            self.switch.select()
        label(self, "Give characters their own voice for dialogue. The narrator reads everything else. "
                    "Kokoro voices only.", 13, TEXT2, justify="left", wraplength=520).grid(row=1, column=0, sticky="w", padx=28)

        fixed = ctk.CTkFrame(self, fg_color="transparent")
        fixed.grid(row=2, column=0, sticky="ew", padx=28, pady=(16, 12))
        fixed.grid_columnconfigure((0, 1), weight=1, uniform="fixed")
        narrator = ctk.CTkFrame(fixed, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12)
        narrator.grid(row=0, column=0, sticky="nsew", padx=(0, 6))
        label(narrator, "NARRATOR", 11, TEXT3, "bold").pack(anchor="w", padx=16, pady=(12, 2))
        name = " + ".join(v.strip()[3:].title() for v in app.narrator_voice().split(","))  # am_michael -> Michael
        label(narrator, name, 14, AMBER, "bold").pack(anchor="w", padx=16)
        label(narrator, "Everything outside quotes. Change it on the Voice step.", 12, TEXT3, justify="left",
              wraplength=220).pack(anchor="w", padx=16, pady=(2, 12))
        other = ctk.CTkFrame(fixed, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12)
        other.grid(row=0, column=1, sticky="nsew", padx=(6, 0))
        label(other, "OTHER DIALOGUE", 11, TEXT3, "bold").pack(anchor="w", padx=16, pady=(12, 4))
        self.dialogue = ctk.CTkOptionMenu(other, values=[NARRATOR] + voices, command=lambda v: self.changed(), **MENU)
        self.dialogue.set(cast.get("dialogue") or NARRATOR)
        self.dialogue.pack(anchor="w", padx=16)
        label(other, "Characters without their own voice, and unknown speakers.", 12, TEXT3, justify="left",
              wraplength=220).pack(anchor="w", padx=16, pady=(4, 12))

        self.list = ctk.CTkScrollableFrame(self, fg_color=CARD, border_color=CARD_LINE, border_width=1,
                                           corner_radius=14, label_text="Found in the book", label_anchor="w",
                                           label_font=F(12, "bold"), label_fg_color=CARD, label_text_color=TEXT3)
        self.list.grid(row=3, column=0, sticky="nsew", padx=28)
        self.list.grid_columnconfigure(0, weight=1)

        foot = ctk.CTkFrame(self, fg_color="transparent")
        foot.grid(row=4, column=0, sticky="ew", padx=28, pady=18)
        foot.grid_columnconfigure(0, weight=1)
        self.unknown = label(foot, "", 12, TEXT2, justify="left", wraplength=240)
        self.unknown.grid(row=0, column=0, sticky="w")
        button(foot, "Who said what", self.show_report, "secondary", width=130, height=36).grid(row=0, column=1, padx=(8, 8))
        button(foot, "Done", self.close, "primary", width=90, height=36).grid(row=0, column=2)
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.menus = {}
        self.scan()

    def scan(self):
        """Read the chapters again and list the characters, so edits and new {Name} tags show up."""
        for row in self.list.winfo_children():
            row.destroy()
        self.characters, unknown, self.report = audiobook.scan_cast(self.app.folder, self.app.cast)
        self.menus = {}
        if not self.characters:
            label(self.list, "No named speakers found. Dialogue will use the Other dialogue voice.\n"
                             "Tip: put {Name} before a quote to give it to a character.", 12, TEXT2,
                  justify="left").grid(row=0, column=0, sticky="w", padx=10, pady=10)
        for i, (name, count) in enumerate(self.characters):
            row = ctk.CTkFrame(self.list, fg_color="transparent")
            row.grid(row=i, column=0, sticky="ew", pady=3)
            row.grid_columnconfigure(1, weight=1)
            ctk.CTkLabel(row, text=name[:1].upper(), width=30, height=30, corner_radius=15, fg_color=AMBER_SOFT,
                         text_color=AMBER, font=F(13, "bold")).grid(row=0, column=0, rowspan=2, padx=(8, 10))
            label(row, name, 13, TEXT, "bold").grid(row=0, column=1, sticky="sw")
            label(row, f"{count} line{'s' if count != 1 else ''}", 12, TEXT3).grid(row=1, column=1, sticky="nw")
            menu = ctk.CTkOptionMenu(row, values=[DIALOGUE] + self.voices, command=lambda v: self.changed(), **MENU)
            menu.set(self.app.cast.get("voices", {}).get(name) or DIALOGUE)
            menu.grid(row=0, column=2, rowspan=2, padx=(4, 6))
            self.menus[name] = menu
        self.unknown.configure(text=f"{unknown} line{'s' if unknown != 1 else ''} with no known speaker. "
                                    "Wrong speaker? Put {Name} before the quote in the chapter.")

    def changed(self):
        voices = {name: menu.get() for name, menu in self.menus.items() if menu.get() != DIALOGUE}
        # Keep voices for characters not in the list right now (renamed or removed for a moment).
        for name, voice in self.app.cast.get("voices", {}).items():
            if name not in self.menus:
                voices[name] = voice
        self.app.cast = {"enabled": bool(self.switch.get()),
                         "dialogue": None if self.dialogue.get() == NARRATOR else self.dialogue.get(),
                         "voices": voices}
        self.app.refresh_cast()

    def show_report(self):
        path = Path(self.app.folder) / "who said what.txt"
        path.write_text(self.report, encoding="utf-8")
        desktop.open_text(path)

    def close(self):
        self.changed()
        self.app.save_book()
        self.destroy()
