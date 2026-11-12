"""What the library pane and the player bar ask the window to do: open, delete and play books and previews.

A part of the main window (gui.App); self is the App."""
from pathlib import Path

import book_settings
import library
from delete_windows import DeleteDialog, preview_files, preview_name
from library_pane import CONTENT_MIN_WIDTH
from library_pane import WIDTH as LIBRARY_WIDTH


class LibraryActions:
    def new_book(self):
        if self.running:
            self.notify("Wait for the narration to finish, or cancel it, before starting another book.")
            return
        self.save_book()
        self.show_view("welcome")  # its Choose a book… button

    def choose_files(self):
        if self.pick_files():
            self.show_view("setup")
            self.show_step("book")

    def open_book(self, key):
        if self.running:
            self.notify("Wait for the narration to finish, or cancel it, before switching books.")
            return
        book = library.find(library.load(), key)
        if not book:
            return
        if book["folder"]:
            if not Path(book["folder"]).is_dir():
                self.notify(f"This book's chapters folder is gone: {book['folder']}")
                return
            if key != self.current_book:  # reopening the same folder would drop unsaved edits
                self.set_folder(book["folder"])
            out = library.output(book)
            if out.is_file():
                # A finished book opens where it can be played; Edit book goes to its settings.
                count = len(book_settings.chapter_files(book["folder"]))
                self.show_finished(out, f"{count} chapter{'s' if count != 1 else ''}. Click Play to listen, or Edit book "
                                   "to change the voice or settings.", library.book_title(book),
                                   self.author.get().strip() or "Unknown", self.cover_path)
            else:
                self.step = "create" if self.book_has_settings else "book"
                self.show_view("setup")
        elif Path(book["m4b"]).is_file():
            # An audiobook found in out/: there are no chapters to edit, so show it as finished.
            self.save_book()
            self.current_book = key
            self.show_finished(Path(book["m4b"]), "Found in your audiobooks folder.", Path(book["m4b"]).stem, "Unknown", None,
                               chapters=False)
            self.library.refresh()

    def delete_book(self, key):
        if self.running:
            self.notify("Wait for the narration to finish, or cancel it, before deleting a book.")
            return
        book = library.find(library.load(), key)
        if book:
            DeleteDialog(self, book, lambda chapters_too: self.finish_delete(key, chapters_too))

    def finish_delete(self, key, chapters_too):
        book = library.find(library.load(), key)
        if not book:
            return
        playing = self.player_bar.player.path
        if playing and Path(playing).resolve() == library.output(book).resolve():
            self.player_bar.close()
        try:
            moved = library.delete(key, chapters_too)
        except OSError as e:
            self.notify(f"Couldn't move everything to the Trash: {e}")
            self.library.refresh()
            return
        self._append(f"Deleted {library.display_name(book)}: moved {len(moved)} item{'s' if len(moved) != 1 else ''} to the Trash.")
        if key == self.current_book:
            if book["folder"]:
                self.folder = ""  # nothing of it to save or go back to
            pinned, recent, _ = library.sections(library.load())
            following = (pinned + recent)[:1]
            self.current_book = None
            if following:
                self.open_book(library.key(following[0]))
            else:
                self.clear_book()
        self.library.refresh()

    def clear_book(self):
        """No book open: the window as it is on a first launch."""
        self.folder, self.current_book = "", None
        self.folder_name.configure(text="No book chosen")
        self.folder_parent.configure(text="")
        for row in self.chapter_list.winfo_children():
            row.destroy()
        self.redo_buttons, self.redo_key = [], None
        self.chapter_status.configure(text="")
        book_settings.forget_folder()
        self.step = "book"
        self.show_view("setup")

    def play_preview_file(self, path):
        self.player_bar.open(path, preview_name(path), resume=False)

    def delete_previews(self, paths):
        """Move voice previews to the Trash (the library lists them under Voice previews)."""
        from send2trash import send2trash
        try:
            for path in paths:
                self.forget_preview(path)  # stops it first if it's playing
                send2trash(str(path))
        except OSError as e:
            self.notify(f"Couldn't move a preview to the Trash: {e}")
        self.library.refresh()

    def delete_all_previews(self):
        self.delete_previews(preview_files())

    def forget_preview(self, path):
        """Called before a preview is deleted: stop it if it's playing, and drop it from the preview box."""
        playing = self.player_bar.player.path
        if playing and Path(playing).resolve() == Path(path).resolve():
            self.player_bar.close()
        if self.sample_path and Path(self.sample_path).resolve() == Path(path).resolve():
            self.sample_path = None
            self.set_preview("idle")

    def back_to_setup(self):
        if self.folder and Path(self.folder).is_dir():
            self.current_book = str(Path(self.folder).resolve())
            self.library.refresh()
        self.step = "create"
        self.show_view("setup")

    def reveal_book(self, key):
        book = library.find(library.load(), key)
        if book:
            path = library.output(book)
            library.reveal(path if path.is_file() else book["folder"])

    def library_resized(self):
        """The library pane was opened or closed. A window too narrow for the open pane is widened to fit it."""
        if not self.library.collapsed:
            width = self._reverse_window_scaling(self.winfo_width())
            needed = round((CONTENT_MIN_WIDTH + LIBRARY_WIDTH) * self.text_scale())
            if width > 1 and width < needed:
                self.geometry(f"{needed}x{self._reverse_window_scaling(self.winfo_height())}")

    def fit_library(self, event):
        """Close the library pane when the window gets too narrow for it, and open it again once there is room,
        so the window fits small screens (a 1366 × 768 laptop, or a 1080p screen at 150%)."""
        if event.widget is not self:
            return
        wide = self._reverse_window_scaling(event.width) >= (CONTENT_MIN_WIDTH + LIBRARY_WIDTH) * self.text_scale()
        if not wide and not self.library.collapsed:
            self.library.toggle(auto=True)
        elif wide and self.library.collapsed and self.library.auto_collapsed:
            self.library.toggle(auto=True)

    def show_player(self):
        self.player_bar.grid(row=2, column=1, sticky="ew", padx=36, pady=(0, 10))

    def hide_player(self):
        self.player_bar.grid_remove()

    def play_output(self):
        book = library.find(library.load(), self.current_book)
        title = library.display_name(book) if book and library.output(book) == Path(self.output) else Path(self.output).stem
        self.player_bar.open(self.output, title)

    def play_preview(self):
        if self.sample_path and Path(self.sample_path).is_file():
            self.play_preview_file(self.sample_path)
