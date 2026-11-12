"""The Book step: the chapters, pronunciations, title, author and cover, and saving each book's settings.

A part of the main window (gui.App); self is the App."""
import threading
import time
import traceback
from pathlib import Path
from tkinter import filedialog

import customtkinter as ctk
from PIL import Image, ImageOps

import audiobook
import desktop
import book_settings
import library
import run_settings
from gui_common import COVER_HINT, KOKORO_VOICES, PRONUNCIATIONS_TEMPLATE, RECOMMENDED, shorten
from theme import AMBER, BG, CARD, CARD_LINE, GREEN, LABEL, MONO, RED, TEXT, TEXT2, TEXT3, F, button, card, entry, label


class BookStep:
    def build_book(self, page):
        main = ctk.CTkFrame(page, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=(0, 28))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(3, weight=1)
        self.page_heading(main, "Which book are we narrating?", "Select the chapter files to narrate, or an EPUB, Word or PDF "
                          "book and we'll split it into chapters.").grid(row=0, column=0, sticky="ew", pady=(0, 18))

        box = ctk.CTkFrame(main, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12)
        box.grid(row=1, column=0, sticky="ew")
        box.grid_columnconfigure(0, weight=1)
        names = ctk.CTkFrame(box, fg_color="transparent")
        names.grid(row=0, column=0, sticky="w", padx=16, pady=12)
        self.folder_name = label(names, "No book chosen", 14, TEXT, "bold")
        self.folder_name.pack(anchor="w")
        self.folder_parent = label(names, "", 12, TEXT3)
        self.folder_parent.pack(anchor="w")
        button(box, "Browse…", self.pick_files, "secondary", width=96, height=36).grid(row=0, column=1, padx=(0, 14))

        status = ctk.CTkFrame(main, fg_color="transparent")
        status.grid(row=2, column=0, sticky="ew", pady=(18, 8))
        status.grid_columnconfigure(0, weight=1)
        self.chapter_status = label(status, "", 13, GREEN, "bold")
        self.chapter_status.grid(row=0, column=0, sticky="w")
        label(status, "Read in this order", 12, TEXT3).grid(row=0, column=1, sticky="e")
        self.chapter_list = ctk.CTkScrollableFrame(main, fg_color=CARD, border_color=CARD_LINE, border_width=1,
                                                   corner_radius=12, height=120)
        self.chapter_list.grid(row=3, column=0, sticky="nsew")
        # In place of the chapter list when the folder has no chapter files.
        self.no_chapters = card(main)
        label(self.no_chapters, "No chapter files in this folder", 14, TEXT, "bold").pack(anchor="w", padx=18, pady=(16, 4))
        label(self.no_chapters, "The chapters need to be .md or .txt files directly inside the folder, not in subfolders. "
              "Or choose an EPUB, Word or PDF book instead.", 13, TEXT2, justify="left", wraplength=560).pack(
            anchor="w", padx=18)
        actions = ctk.CTkFrame(self.no_chapters, fg_color="transparent")
        actions.pack(anchor="w", padx=18, pady=(12, 16))
        button(actions, "Browse…", self.pick_files, "primary", height=34).pack(side="left")
        button(actions, "How to prepare chapters", lambda: self.show_help("Preparing chapters"), "ghost",
               height=34).pack(side="left", padx=(10, 0))

        words = ctk.CTkFrame(main, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12)
        words.grid(row=4, column=0, sticky="ew", pady=(12, 0))
        words.grid_columnconfigure(0, weight=1)
        texts = ctk.CTkFrame(words, fg_color="transparent")
        texts.grid(row=0, column=0, sticky="w", padx=16, pady=12)
        label(texts, "Pronunciations", 13, TEXT, "bold").pack(anchor="w")
        label(texts, "Fix how names and words are said in this book.", 13, TEXT2).pack(anchor="w")
        # Opens the book's pronunciations.txt; its label shows how many words it fixes.
        self.pronunciation_btn = button(words, "Edit list…", self.edit_pronunciations, "secondary", height=34)
        self.pronunciation_btn.grid(row=0, column=1, padx=(0, 14))

        details = card(page, width=300)
        details.grid(row=0, column=1, sticky="ns")
        details.grid_propagate(False)
        details.grid_columnconfigure(0, weight=1)
        fields = ctk.CTkFrame(details, fg_color="transparent")
        fields.grid(row=0, column=0, sticky="ew", padx=20, pady=20)
        label(fields, "Book details", 12, TEXT3, "bold").pack(anchor="w", pady=(0, 12))
        label(fields, "Title", 13, LABEL, "bold").pack(anchor="w")
        self.book_title = entry(fields, placeholder_text="Defaults to the folder name")
        self.book_title.pack(fill="x", pady=(6, 14))
        self.book_title.bind("<FocusOut>", lambda e: (self.save_book(), self.library.refresh(), self.refresh_summary()),
                             add="+")  # the library and the step bar show it
        label(fields, "Author", 13, LABEL, "bold").pack(anchor="w")
        self.author = entry(fields, placeholder_text="Optional")
        self.author.pack(fill="x", pady=(6, 14))
        self.author.bind("<FocusOut>", lambda e: self.save_book(), add="+")
        label(fields, "Cover", 13, LABEL, "bold").pack(anchor="w")
        cover_row = ctk.CTkFrame(fields, fg_color="transparent")
        cover_row.pack(fill="x", pady=(8, 8))
        self.cover_thumb = ctk.CTkLabel(cover_row, text="Square\nJPG or PNG", width=110, height=110, corner_radius=8,
                                        fg_color=BG, text_color=TEXT3, font=F(12))
        self.cover_thumb.pack(side="left")
        cover_buttons = ctk.CTkFrame(cover_row, fg_color="transparent")
        cover_buttons.pack(side="left", anchor="s", padx=(14, 0))
        button(cover_buttons, "Choose…", self.pick_cover, "secondary", width=96, height=34).pack(anchor="w")
        self.cover_clear = button(cover_buttons, "Remove", self.clear_cover, "ghost", width=96, height=30,
                                  font=F(12, "bold"))
        self.cover_name = label(fields, COVER_HINT, 12, TEXT3, justify="left", wraplength=250)
        self.cover_name.pack(anchor="w")

    def set_folder(self, folder):
        if self.folder and self.folder != folder:
            self.save_book()  # keep the settings of the book being left
        self.folder = folder
        if Path(folder).is_dir():
            book_settings.remember_folder(folder)
            self.current_book = library.add_folder(folder)
            self.load_book()
            if hasattr(self, "library"):  # not yet built while the last book reopens at launch
                self.library.refresh()
        path = Path(folder)
        self.folder_name.configure(text=shorten(path.name or folder, 60))
        parent = str(path.parent).replace(str(Path.home()), "~")
        self.folder_parent.configure(text=parent if len(parent) <= 70 else "…" + parent[-69:])
        files = book_settings.chapter_files(path) if path.is_dir() else []
        for row in self.chapter_list.winfo_children():
            row.destroy()
        self.redo_buttons, self.redo_key = [], None  # shown by refresh_redo once a chapter has been made
        for i, file in enumerate(files, 1):
            row = ctk.CTkFrame(self.chapter_list, fg_color="transparent")
            row.pack(fill="x")
            label(row, f"{i:02d}", 11, TEXT3, family=MONO, width=24).pack(side="left", padx=(8, 10), pady=7)
            try:
                name = audiobook.chapter_title(book_settings.read_text(file), file)
            except (OSError, UnicodeDecodeError):
                name = file.stem
            label(row, shorten(name, 64), 13, TEXT, "bold").pack(side="left")
            # Narrates just this chapter again (a new take with Chatterbox), then rebuilds the .m4b.
            self.redo_buttons.append(button(row, "Redo", lambda n=i: self.start(sample=False, redo={n}), "ghost",
                                            width=56, height=28, font=F(12, "bold")))
        self.no_chapters.grid_remove()
        self.chapter_list.grid()
        if not path.is_dir():
            self.chapter_status.configure(text="Folder not found", text_color=RED)
        elif not files:
            self.chapter_status.configure(text="No chapters found", text_color=AMBER)
            self.chapter_list.grid_remove()
            self.no_chapters.grid(row=3, column=0, sticky="new")
        else:
            total = len(book_settings.all_chapter_files(path))
            found = f"{len(files)} chapter{'s' if len(files) != 1 else ''}"
            self.chapter_status.configure(text=f"✓  {found} found" if total == len(files) else
                                          f"✓  {found} chosen, {total - len(files)} skipped", text_color=GREEN)
        self.refresh_pronunciations()

    def refresh_redo(self):
        """Show Redo only on chapters already made with the current chapters, voice and settings.

        Called from poll. The chapters are read again only when something that decides it has changed, and only
        once it has stayed the same for a second, so dragging a slider doesn't re-read a long book at every step."""
        if self.running or not self.redo_buttons:
            return
        args = self.render_args()
        folder = Path(args.chapters)
        try:
            files = sorted((p.name, p.stat().st_mtime_ns) for p in folder.iterdir()
                           if book_settings.is_chapter(p) or p.name == audiobook.PRONUNCIATIONS_FILE)
            clip = Path(args.ref).stat().st_mtime_ns if args.ref else None
        except OSError:
            return
        key = (run_settings.chapters_key(args), files, clip)
        if key == self.redo_key:
            return
        if key != self.redo_pending[0]:
            self.redo_pending = (key, time.monotonic())
            return
        if time.monotonic() - self.redo_pending[1] < 1.0:
            return
        self.redo_key = key
        try:
            made = audiobook.made_chapters(args)
        except Exception:  # a half-saved chapter or missing clip: show no Redo rather than an error
            made = set()
        for i, redo in enumerate(self.redo_buttons, 1):
            if i in made:
                redo.pack(side="right", padx=(4, 8))
            else:
                redo.pack_forget()

    def refresh_pronunciations(self, event=None):
        """Show how many words the book's pronunciations.txt fixes; called again when the app regains focus."""
        count = len(audiobook.load_pronunciations(self.folder)) if self.folder and Path(self.folder).is_dir() else 0
        self.pronunciation_btn.configure(text=f"Edit list · {count}" if count else "Edit list…")

    def edit_pronunciations(self):
        if not self.folder or not Path(self.folder).is_dir():
            self.notify("Choose a chapters folder first.")
            return
        path = Path(self.folder) / audiobook.PRONUNCIATIONS_FILE
        if not path.exists():
            path.write_text(PRONUNCIATIONS_TEMPLATE, encoding="utf-8")
        desktop.open_text(path)
        self._append(f"Opened {path.name}. Save it, then create the audiobook.")

    def book_state(self):
        """What is saved for the book: voice, settings (rounded like the render args), title, author and cover."""
        state = {"engine": self.engine, "voice_a": self.voice_a, "voice_b": self.voice_b, "clip": self.clip,
                 "check": bool(self.check_switch.get()), "cast": self.cast}
        state.update({name: round(getattr(self, name).get(), 2) for name in RECOMMENDED})
        state.update(title=self.book_title.get().strip(), author=self.author.get().strip(), cover=self.cover_path)
        return state

    def save_book(self):
        if self.folder and Path(self.folder).is_dir():
            try:
                book_settings.save_book(self.folder, self.book_state())
            except OSError as e:
                self._append(f"Couldn't save this book's settings: {e}")

    def load_book(self):
        """Apply the settings saved with the book. A book without saved settings keeps the current voice and
        settings, but starts with an empty title, author and cover, since those belong to the other book."""
        settings, problems = book_settings.load_book(self.folder, KOKORO_VOICES)
        self.book_has_settings = bool(settings)  # a book set up before opens on the Create step
        for problem in problems:
            self._append(problem)
        if "voice_a" in settings:
            self.voice_a, self.voice_b, self.slot = settings["voice_a"], settings["voice_b"], "a"
        for name in RECOMMENDED:
            if name in settings:
                slider = getattr(self, name)
                slider.set(settings[name])
                self.value_labels[slider].configure(text=f"{settings[name]:.2f}")
        self.clip = settings.get("clip")
        self.cast = settings.get("cast") or {"enabled": False, "dialogue": None, "voices": {}}
        self.refresh_cast()
        if "check" in settings:
            self.check_switch.select() if settings["check"] else self.check_switch.deselect()
        for field in ("title", "author"):
            entry_ = self.book_title if field == "title" else self.author
            entry_.delete(0, "end")
            if settings.get(field):
                entry_.insert(0, settings[field])
        if settings.get("cover"):
            self.set_cover(settings["cover"])
        else:
            self.clear_cover()
        self.set_engine(settings.get("engine", self.engine))  # also refreshes the clip list and the rhythm
        self.refresh_voices()
        if settings:
            self._append(f"Loaded the voice and settings saved with {Path(self.folder).name}.")

    def pick_cover(self):
        path = filedialog.askopenfilename(title="Cover image for the audiobook (square works best in Books)",
                                          filetypes=[("Images", "*.jpg *.jpeg *.png")])
        if path:
            self.set_cover(path)

    def set_cover(self, path):
        try:
            image = ImageOps.fit(Image.open(path).convert("RGB"), (220, 220))
        except Exception as e:
            self.notify(f"Couldn't open that image: {e}")
            return
        self.cover_path = path
        self.cover_thumb.configure(image=ctk.CTkImage(image, size=(110, 110)), text="")
        self.cover_name.configure(text=shorten(Path(path).name, 36), text_color=TEXT2)
        self.cover_clear.pack(anchor="w", pady=(6, 0))
        self.refresh_summary()

    def clear_cover(self):
        self.cover_path = None
        self.cover_thumb.configure(image=None, text="Square\nJPG or PNG")
        self.cover_name.configure(text=COVER_HINT, text_color=TEXT3)
        self.cover_clear.pack_forget()
        self.refresh_summary()

    def import_book(self, path):
        """Turn an EPUB, Word or PDF book into a new folder of chapter .md files next to it, and open that.

        The import runs on another thread so a long PDF doesn't freeze the window; finish_import opens the result."""
        if self.importing or self.running:
            self.notify("Wait for the book being imported, or the narration, to finish first.")
            return False
        self.importing = True
        self._append(f"Importing {Path(path).name}…", show=True)
        self.configure(cursor="watch")

        def work():
            import importer  # only needed here
            try:
                self.messages.put(("imported", path, importer.import_book(path, self.log), None))
            except Exception as e:
                traceback.print_exc()
                self.messages.put(("imported", path, None, e))

        threading.Thread(target=work, daemon=True).start()
        return True

    def finish_import(self, path, result, error):
        self.importing = False
        self.configure(cursor="")
        if error is not None:
            self.notify(f"Couldn't import {Path(path).name}: {error}")
            return
        folder, book = result
        self.set_folder(str(folder))
        for entry_, value in ((self.book_title, book.title), (self.author, book.author)):
            entry_.delete(0, "end")
            entry_.insert(0, value or "")
        cover = next((p for p in (folder / "cover.jpg", folder / "cover.png") if p.exists()), None)
        if cover:
            self.set_cover(str(cover))
        self.save_book()
        self.show_step("book")
        self._append("Check the chapter files before you narrate: open the folder, fix any odd line breaks, "
                     "and delete chapters you don't want read (like a copyright page).", show=True)

    def pick_files(self):
        """One Browse for both: select chapter .md or .txt files to narrate (all of them, or only some), or one book file to
        import into a new folder of chapters. Returns True if a book was opened.
        (A Tk file dialog can't choose a folder, so the chapters are chosen as files: Ctrl+A or ⌘A selects them all.)"""
        start = self.folder if self.folder and Path(self.folder).is_dir() else None
        paths = filedialog.askopenfilenames(
            title=f"Select the chapters to narrate ({desktop.SELECT_ALL} for all), or a book to import", initialdir=start,
            filetypes=[("Chapters or books", "*.md *.txt *.epub *.docx *.pdf"), ("Chapter files", "*.md *.txt"),
                       ("Books to import", "*.epub *.docx *.pdf")])
        paths = [Path(p) for p in (self.tk.splitlist(paths) if isinstance(paths, str) else paths or ())]
        if not paths:
            return False
        chapters = [p for p in paths if book_settings.is_chapter(p)]
        books = [p for p in paths if p.suffix.lower() in (".epub", ".docx", ".pdf")]
        if books:
            if chapters or len(books) > 1:
                self.notify("Select chapter files (.md or .txt), or one EPUB, Word or PDF book, not both.")
                return False
            return self.import_book(str(books[0]))
        if not chapters:
            self.notify("Select chapter files (.md or .txt), or one EPUB, Word or PDF book.")
            return False
        folders = {p.parent for p in chapters}
        if len(folders) > 1:
            self.notify("Select chapters from one folder. Put all of a book's chapters in the same folder first.")
            return False
        folder = folders.pop()
        self.save_book()  # keep the open book's settings before its chapters are reread
        try:
            book_settings.choose_chapters(folder, [p.name for p in chapters])
        except OSError as e:
            self.notify(f"Couldn't save the chosen chapters: {e}")
            return False
        if str(folder) == self.folder:
            self.folder = ""  # same book: list its chapters again
        self.set_folder(str(folder))
        return True
