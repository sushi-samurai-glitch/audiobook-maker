"""Settings window: options for this computer rather than one book. Opened from the library pane or with ⌘, (Ctrl+, on Windows).

Sections: Narrating (Gentle mode), Voices and storage (download every voice ahead of time, see what the voices and
the narration cache take, and delete them), and About (version, Copy details, Show log)."""
import queue
import shutil
import threading
import webbrowser
from pathlib import Path
from tkinter import messagebox

import customtkinter as ctk

import book_settings
import desktop
import downloads
import paths
import updates
import version
from theme import (
    AMBER,
    BG,
    CARD,
    CARD_LINE,
    DISABLED,
    GREEN,
    KNOB,
    KNOB_HOVER,
    LINE,
    TEXT,
    TEXT2,
    TEXT3,
    TRACK,
    F,
    button,
    label,
)

NARRATION_CACHE = Path("build")  # in the working folder: every narrated paragraph and chapter, for quick rebuilds


def folder_size(folder):
    folder = Path(folder)
    if not folder.is_dir():
        return 0
    return sum(f.stat().st_size for f in folder.rglob("*") if f.is_file() and not f.is_symlink())


class SettingsWindow(ctk.CTkToplevel):
    def __init__(self, master, on_change=None):
        super().__init__(master)
        self.app = master
        self.on_change = on_change  # lets the main window update its Gentle mode note right away
        self.title("Settings")
        self.geometry("600x660")
        self.minsize(600, 420)
        self.configure(fg_color=BG)
        self.transient(master)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(self, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", padx=28, pady=(26, 8))
        label(head, "Settings", 24, TEXT, "bold").pack(anchor="w", pady=(0, 4))
        label(head, "These apply to every book on this computer.", 13, TEXT2).pack(anchor="w")

        self.body = body = ctk.CTkScrollableFrame(self, fg_color="transparent", scrollbar_button_color=TRACK)
        body.grid(row=1, column=0, sticky="nsew", padx=(16, 8))
        body.grid_columnconfigure(0, weight=1)
        self.build_narrating(body)
        self.build_display(body)
        self.build_voices(body)
        self.build_about(body)

        button(self, "Done", self.close, "primary", width=90).grid(row=2, column=0, sticky="e", padx=28, pady=20)
        self.bind("<Escape>", lambda e: self.close())
        self.protocol("WM_DELETE_WINDOW", self.close)

        self.cancel = threading.Event()
        self.messages = queue.Queue()  # from the download thread: ("progress", done, total, name) or ("end", error)
        self.downloading = False
        self.refresh_voices()
        self.after(200, self.poll)

    # ----- sections

    def section(self, parent, row, title):
        label(parent, title, 11, TEXT3, "bold").grid(row=row, column=0, sticky="w", padx=12, pady=(18, 8))
        box = ctk.CTkFrame(parent, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=14)
        box.grid(row=row + 1, column=0, sticky="ew", padx=12)
        box.grid_columnconfigure(0, weight=1)
        return box

    def build_narrating(self, parent):
        box = self.section(parent, 0, "NARRATING")
        label(box, "Gentle mode", 14, TEXT, "bold").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 2))
        label(box, "Keeps your computer cool and responsive while a book narrates,\nso you can keep using other apps.",
              13, TEXT2, justify="left").grid(row=1, column=0, sticky="w", padx=18)
        self.gentle = ctk.CTkSwitch(box, text="", width=46, progress_color=AMBER, button_color=KNOB,
                                    button_hover_color=KNOB_HOVER, fg_color=TRACK, command=self.changed)
        self.gentle.select() if book_settings.gentle() else self.gentle.deselect()
        self.gentle.grid(row=0, column=1, rowspan=2, padx=(8, 12))
        ctk.CTkFrame(box, fg_color=LINE, height=1).grid(row=2, column=0, columnspan=2, sticky="ew", padx=18, pady=12)
        label(box, "Uses half the processor and rests for 1 minute after every 5 minutes of narrating.\n"
                   "Kokoro takes about a third longer. Turn it off for the fastest render, for example\n"
                   "overnight. A change applies from the next preview or audiobook.",
              12, TEXT3, justify="left").grid(row=3, column=0, columnspan=2, sticky="w", padx=18, pady=(0, 16))

    def build_display(self, parent):
        box = self.section(parent, 2, "DISPLAY")
        label(box, "Larger text", 14, TEXT, "bold").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 2))
        label(box, "Draws everything a little bigger, and the window grows to fit. Best on a\n"
                   f"screen larger than a 13-inch laptop's. Keyboard shortcuts: Help ({desktop.MOD}/).", 13, TEXT2, justify="left").grid(
            row=1, column=0, sticky="w", padx=18, pady=(0, 16))
        self.larger = ctk.CTkSwitch(box, text="", width=46, progress_color=AMBER, button_color=KNOB,
                                    button_hover_color=KNOB_HOVER, fg_color=TRACK, command=self.larger_changed)
        self.larger.select() if book_settings.larger_text() else self.larger.deselect()
        self.larger.grid(row=0, column=1, rowspan=2, padx=(8, 12), pady=(0, 0))

    def larger_changed(self):
        on = bool(self.larger.get())
        book_settings.remember_larger_text(on)
        ctk.set_widget_scaling(book_settings.LARGER_TEXT if on else 1.0)
        self.app.fit_min_size()

    def build_voices(self, parent):
        box = self.section(parent, 4, "VOICES AND STORAGE")
        label(box, "Voices download the first time you use them. Download them all now to use any voice\n"
                   "offline later. They are kept in Hugging Face's folder, which stays if you remove the app.",
              12, TEXT3, justify="left").grid(row=0, column=0, columnspan=2, sticky="w", padx=18, pady=(16, 4))
        self.rows = {}
        row = 1
        for key in ("kokoro", "chatterbox", "whisper", "cache"):
            if row > 1:
                ctk.CTkFrame(box, fg_color=LINE, height=1).grid(row=row, column=0, columnspan=2, sticky="ew", padx=18)
                row += 1
            frame = ctk.CTkFrame(box, fg_color="transparent")
            frame.grid(row=row, column=0, columnspan=2, sticky="ew", padx=18, pady=10)
            frame.grid_columnconfigure(0, weight=1)
            if key == "cache":
                name, purpose = "Narration cache", "Every narrated paragraph, so changing a book doesn't narrate it again."
            else:
                name, purpose = downloads.PACKS[key].name, downloads.PACKS[key].purpose
            label(frame, name, 13, TEXT, "bold").grid(row=0, column=0, sticky="w")
            label(frame, purpose, 12, TEXT3).grid(row=1, column=0, sticky="w")
            status = label(frame, "", 12, TEXT2)
            status.grid(row=2, column=0, sticky="w", pady=(2, 0))
            delete = button(frame, "Delete", lambda k=key: self.delete(k), "ghost", width=76, height=28, font=F(12, "bold"),
                            text_color_disabled=DISABLED)
            delete.grid(row=0, column=1, rowspan=3, padx=(8, 0))
            self.rows[key] = (status, delete)
            row += 1

        bar = ctk.CTkFrame(box, fg_color="transparent")
        bar.grid(row=row, column=0, columnspan=2, sticky="ew", padx=18, pady=(8, 16))
        bar.grid_columnconfigure(1, weight=1)
        self.download_btn = button(bar, "Download all voices", self.download_all, "primary", width=170, height=34)
        self.download_btn.grid(row=0, column=0, sticky="w")
        self.progress = ctk.CTkProgressBar(bar, height=8, progress_color=AMBER, fg_color=TRACK)
        self.progress.set(0)
        self.progress_text = label(bar, "", 12, TEXT2)
        self.progress_text.grid(row=1, column=0, columnspan=2, sticky="w", pady=(8, 0))

    def build_about(self, parent):
        box = self.section(parent, 6, "ABOUT")
        label(box, f"Audiobook Maker {version.VERSION}", 14, TEXT, "bold").grid(row=0, column=0, sticky="w",
                                                                              padx=18, pady=(16, 2))
        label(box, f"{version.COPYRIGHT}.\n{version.LICENSE_NOTE}", 12, TEXT3, justify="left").grid(
            row=1, column=0, columnspan=2, sticky="w", padx=18)
        label(box, "No account and no tracking. The app fetches voices from\nHugging Face and, once a day, "
                   "checks GitHub for a new\nversion. Your books never leave this computer.",
              12, TEXT3, justify="left").grid(row=2, column=0, sticky="w", padx=18, pady=(8, 0))
        label(box, "Reporting a problem? Copy details pastes the version and\nyour system into your message.",
              13, TEXT2, justify="left").grid(row=3, column=0, sticky="w", padx=18, pady=(10, 16))
        buttons = ctk.CTkFrame(box, fg_color="transparent")
        buttons.grid(row=2, column=1, rowspan=2, padx=(8, 14), pady=(8, 16))
        self.copy_btn = button(buttons, "Copy details", self.copy_details, "secondary", width=110, height=30)
        self.copy_btn.pack(pady=(0, 6))
        button(buttons, "Show log", self.show_log, "ghost", width=110, height=30).pack(pady=(0, 6))
        button(buttons, "Licences", self.show_licences, "ghost", width=110, height=30).pack()

        ctk.CTkFrame(box, fg_color=LINE, height=1).grid(row=4, column=0, columnspan=2, sticky="ew", padx=18)
        label(box, "Check for updates", 14, TEXT, "bold").grid(row=5, column=0, sticky="w", padx=18, pady=(12, 2))
        self.update_status = label(box, "", 12, TEXT3, justify="left")
        self.update_status.grid(row=6, column=0, sticky="w", padx=18)
        self.update_switch = ctk.CTkSwitch(box, text="", width=46, progress_color=AMBER, button_color=KNOB,
                                           button_hover_color=KNOB_HOVER, fg_color=TRACK, command=self.updates_changed)
        self.update_switch.select() if updates.enabled() else self.update_switch.deselect()
        self.update_switch.grid(row=5, column=1, rowspan=2, padx=(8, 12), pady=(12, 0))
        update_buttons = ctk.CTkFrame(box, fg_color="transparent")
        update_buttons.grid(row=7, column=0, columnspan=2, sticky="w", padx=18, pady=(8, 16))
        button(update_buttons, "Check now", self.check_now, "secondary", width=110, height=30).pack(side="left")
        self.get_update_btn = button(update_buttons, "Get the new version", self.open_update, "primary", width=170,
                                     height=30)
        self.show_update(updates.known())

    # ----- voices and storage

    def refresh_voices(self):
        """Say what each voice pack and the narration cache take, and whether anything is left to download."""
        try:
            sizes = {key: downloads.size_on_disk(pack) for key, pack in downloads.PACKS.items()}
            missing = {key: downloads.missing(pack) for key, pack in downloads.PACKS.items()}
        except ImportError:  # the voice libraries aren't installed (a test machine)
            sizes = missing = None
        busy = self.downloading or getattr(self.app, "running", False)
        for key, (status, delete) in self.rows.items():
            if key == "cache":
                size = folder_size(NARRATION_CACHE)
                status.configure(text=f"{downloads.human(size)} in {NARRATION_CACHE.resolve()}" if size else "Empty",
                                 text_color=TEXT2)
            elif sizes is None:
                size = 0
                status.configure(text="Can't check: the voice libraries aren't installed", text_color=TEXT3)
            else:
                pack, size, left = downloads.PACKS[key], sizes[key], missing[key]
                if not left:
                    status.configure(text=f"✓  Downloaded · {downloads.human(size)}", text_color=GREEN)
                elif key == "kokoro" and len(left) < len(pack.files):
                    voices = sum(1 for f in pack.files if f.startswith("voices/"))
                    have = voices - sum(1 for f in left if f.startswith("voices/"))
                    status.configure(text=f"{have} of {voices} voices downloaded · {downloads.human(size)}",
                                     text_color=TEXT2)
                else:
                    status.configure(text=f"Not downloaded · {pack.approx}", text_color=TEXT2)
            delete.configure(state="normal" if size and not busy else "disabled")
        nothing_left = missing is not None and not any(missing.values())
        if not self.downloading:
            self.download_btn.configure(text="Download all voices", command=self.download_all,
                                        state="disabled" if nothing_left or missing is None else "normal")
            if nothing_left:
                self.progress_text.configure(text="Every voice is on this computer, so all of them work offline.")

    def download_all(self):
        self.downloading = True
        self.cancel.clear()
        self.download_btn.configure(text="Cancel", command=self.cancel.set)
        self.progress.set(0)
        self.progress.grid(row=0, column=1, sticky="ew", padx=(14, 0))
        self.progress_text.configure(text="Starting…", text_color=TEXT2)
        self.refresh_voices()

        def work():
            try:
                downloads.fetch(list(downloads.PACKS), lambda *p: self.messages.put(("progress", *p)), self.cancel)
                self.messages.put(("end", None))
            except downloads.Cancelled:
                self.messages.put(("end", "Stopped. What finished downloading is kept."))
            except Exception as e:  # offline, or Hugging Face is down
                print(f"Voice download failed: {e!r}")
                self.messages.put(("end", "Couldn't download the voices. Check the internet connection and try again."))

        threading.Thread(target=work, daemon=True).start()

    def poll(self):
        if not self.winfo_exists():
            return
        latest = None
        while not self.messages.empty():
            message = self.messages.get()
            if message[0] == "progress":
                latest = message
            else:
                self.finish_download(message[1])
        if latest and self.downloading:
            _, done, total, name = latest
            self.progress.set(done / total if total else 0)
            if total > 1000:  # bytes; a small total means sizes weren't known and files are counted
                self.progress_text.configure(text=f"{name} · {downloads.human(done)} of {downloads.human(total)}")
            else:
                self.progress_text.configure(text=f"{name} · file {min(done + 1, total)} of {total}")
        self.after(200, self.poll)

    def finish_download(self, error):
        self.downloading = False
        self.progress.grid_remove()
        self.progress_text.configure(text=error or "Done.", text_color=TEXT2)
        self.refresh_voices()

    def delete(self, key):
        if key == "cache":
            what, after = "the narration cache", ("Finished audiobooks are kept, but changing one (a new cover, a "
                                                  "redone chapter) narrates the whole book again.")
        else:
            what, after = downloads.PACKS[key].name, "They download again the next time you use them."
        if not messagebox.askyesno(f"Delete {what}?", after, icon="warning", default="no", parent=self):
            return
        if getattr(self.app, "running", False):
            return  # a run started while the question was open
        if key == "cache":
            shutil.rmtree(NARRATION_CACHE, ignore_errors=True)
        else:
            downloads.delete(downloads.PACKS[key])
        self.refresh_voices()

    # ----- about

    def copy_details(self):
        self.clipboard_clear()
        self.clipboard_append(version.details())
        self.copy_btn.configure(text="Copied ✓")
        self.after(2000, lambda: self.copy_btn.winfo_exists() and self.copy_btn.configure(text="Copy details"))

    def show_log(self):
        log = paths.log_file()
        desktop.reveal(log if log.exists() else log.parent if log.parent.exists() else log.parent.parent)

    def show_licences(self):
        """The licences of the app and everything it includes, in the text editor."""
        found = next((p for p in version.NOTICES if p.is_file()), None)
        if found:
            desktop.open_text(found)

    # ----- updates

    def show_update(self, found):
        """found: (version, url) of a newer release, or None."""
        self.update_url = found[1] if found else None
        if found:
            self.update_status.configure(text=f"Version {found[0]} is out. It's free, like this one: download it and\n"
                                              "drag it into Applications to replace this version.", text_color=AMBER)
            self.get_update_btn.pack(side="left", padx=(8, 0))
        elif updates.failed():
            self.update_status.configure(text="Couldn't reach GitHub just now. The app tries again tomorrow.",
                                         text_color=TEXT3)
            self.get_update_btn.pack_forget()
        else:
            checked = updates.last_checked()
            when = f" Last checked {checked}." if checked else ""
            self.update_status.configure(text=f"Once a day, the app asks GitHub whether a new version is out.{when}"
                                         if updates.enabled() else "Off. Check now still works.", text_color=TEXT3)
            self.get_update_btn.pack_forget()

    def check_now(self):
        self.update_status.configure(text="Checking…", text_color=TEXT3)
        self.app.check_for_updates(force=True)  # the answer comes back through the app's show_update

    def open_update(self):
        if self.update_url:
            webbrowser.open(self.update_url)

    def updates_changed(self):
        updates.remember_enabled(self.update_switch.get())
        self.show_update(updates.known())

    def changed(self):
        book_settings.remember_gentle(self.gentle.get())
        if self.on_change:
            self.on_change()

    def close(self):
        self.cancel.set()  # a download in progress stops at its next chunk; finished files are kept
        self.destroy()
