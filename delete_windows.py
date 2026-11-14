"""The Delete dialogs for a book and for a recorded voice clip, and naming the voice previews shown in the library."""
from pathlib import Path

import customtkinter as ctk
import soundfile as sf

import library
from theme import BG, CARD, CARD_LINE, FIELD_LINE, RED, TEXT, TEXT2, TEXT3, F, button, label

SAMPLES = Path("samples")


class DeleteDialog(ctk.CTkToplevel):
    """Ask before deleting a book; `chapters_too` is the checkbox. Calls on_delete(chapters_too) on confirm."""

    def __init__(self, master, book, on_delete):
        super().__init__(master)
        self.title("Delete book")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.on_delete = on_delete
        name = library.display_name(book)
        label(self, f"Delete “{name}”?", 22, TEXT, "bold", wraplength=420, justify="left").pack(anchor="w", padx=28, pady=(26, 8))
        files = library.audio_files(book)
        what = "The audiobook, its MP3s and its saved narration go" if book["folder"] else "The audiobook file goes"
        label(self, f"{what} to the Trash, so you can get them back. The book leaves your library.", 14, TEXT2,
              wraplength=420, justify="left").pack(anchor="w", padx=28)
        if not files:
            label(self, "There's no audio for it yet, so only the library entry goes.", 12, TEXT3, wraplength=420,
                  justify="left").pack(anchor="w", padx=28, pady=(6, 0))
        self.chapters_too = ctk.BooleanVar(value=False)
        if book["folder"] and Path(book["folder"]).is_dir():
            box = ctk.CTkFrame(self, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12)
            box.pack(fill="x", padx=28, pady=(18, 0))
            ctk.CTkCheckBox(box, text=f"Also move the chapter files (“{Path(book['folder']).name}”) to the Trash",
                            variable=self.chapters_too, font=F(13, "bold"), text_color=TEXT, fg_color=RED,
                            hover_color="#FF8277", border_color=FIELD_LINE).pack(anchor="w", padx=16, pady=(14, 2))
            label(box, "Leave this off to keep them and narrate the book again later.", 12, TEXT3).pack(
                anchor="w", padx=(46, 16), pady=(0, 14))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=28, pady=(22, 24))
        button(buttons, "Move to Trash", self.confirm, "danger", width=150, font=F(14, "bold")).pack(side="right")
        button(buttons, "Cancel", self.destroy, "ghost", width=100).pack(side="right", padx=(0, 10))
        self.bind("<Escape>", lambda e: self.destroy())
        self.transient(master)
        self.after(50, self.grab_and_focus)

    def grab_and_focus(self):
        self.lift()
        self.focus()
        self.grab_set()

    def confirm(self):
        chapters_too = self.chapters_too.get()
        self.destroy()
        self.on_delete(chapters_too)


class DeleteClipDialog(ctk.CTkToplevel):
    """Ask before deleting a recorded voice clip, saying what uses it. Calls on_delete() only on Move to Trash.

    Cancel has the focus, so Return or Escape keeps the clip: only a deliberate click on Move to Trash deletes it."""

    def __init__(self, master, path, uses, on_delete):
        super().__init__(master)
        self.title("Delete voice clip")
        self.resizable(False, False)
        self.configure(fg_color=BG)
        self.on_delete = on_delete
        label(self, f"Delete “{Path(path).stem}”?", 22, TEXT, "bold", wraplength=420, justify="left").pack(
            anchor="w", padx=28, pady=(26, 8))
        label(self, f"The recording ({Path(path).name}) goes to the Trash, so you can put it back from there if you "
                    "change your mind.", 14, TEXT2, wraplength=420, justify="left").pack(anchor="w", padx=28)
        if uses:
            box = ctk.CTkFrame(self, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12)
            box.pack(fill="x", padx=28, pady=(18, 0))
            label(box, "IT'S IN USE", 11, TEXT3, "bold").pack(anchor="w", padx=16, pady=(12, 4))
            for i, use in enumerate(uses):
                label(box, f"•  {use}", 13, TEXT, wraplength=380, justify="left").pack(
                    anchor="w", padx=16, pady=(0, 12 if i == len(uses) - 1 else 4))
        buttons = ctk.CTkFrame(self, fg_color="transparent")
        buttons.pack(fill="x", padx=28, pady=(22, 24))
        button(buttons, "Move to Trash", self.confirm, "danger", width=150, font=F(14, "bold")).pack(side="right")
        self.cancel = button(buttons, "Cancel", self.destroy, "ghost", width=100)
        self.cancel.pack(side="right", padx=(0, 10))
        self.bind("<Escape>", lambda e: self.destroy())
        self.bind("<Return>", lambda e: self.destroy())  # Return is the safe choice, never the delete
        self.transient(master)
        self.after(50, self.grab_and_focus)

    def grab_and_focus(self):
        self.lift()
        self.cancel.focus_set()
        self.grab_set()

    def confirm(self):
        self.destroy()
        self.on_delete()


def preview_name(path):
    """'Kokoro · Michael' or 'Kokoro · Lewis + Michael' for a file in samples/ (or 'Chatterbox · narrator' for a
    preview an earlier version made)."""
    engine, _, voice = Path(path).stem.partition("-")
    if engine == "kokoro":
        return "Kokoro · " + " + ".join(v.strip()[3:].title() for v in voice.split(","))
    if engine == "chatterbox":
        return "Chatterbox · " + ("built-in voice" if voice == "default" else voice)
    return Path(path).stem


def length(path):
    try:
        seconds = round(sf.info(str(path)).duration)
        return f"{seconds // 60}:{seconds % 60:02d}"
    except Exception:
        return ""


def preview_files():
    return sorted(SAMPLES.glob("*.wav")) if SAMPLES.is_dir() else []
