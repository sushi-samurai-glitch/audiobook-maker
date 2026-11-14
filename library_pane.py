"""The left pane listing the books, like the sidebar of a chat app: hover a book for its ⋯ menu."""
import tkinter
import webbrowser

import customtkinter as ctk

import library
from icons import HIT, icon
from gui_common import REVEAL_LABEL
from delete_windows import length, preview_files, preview_name
from theme import (AMBER, AMBER_LINE, AMBER_SOFT, CARD, FIELD_LINE, FOOTER, LINE, TEXT, TEXT2, TEXT3, F, button, entry,
                   label, on_click)

WIDTH = 250
NARROW = 56  # collapsed: just the open and new-book buttons
CONTENT_MIN_WIDTH = 1000  # the narrowest the steps beside the pane can be
MIN_HEIGHT = 680  # fits a 1280 × 800 Mac with the Dock showing
SELECTED = "#23272E"
HOVER = "#1F2329"


def shorten(text, limit):
    return text if len(text) <= limit else text[:limit - 1] + "…"


class LibraryPane(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=FOOTER, corner_radius=0, width=WIDTH, border_width=0)
        self.app = app
        self.grid_propagate(False)
        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)
        self.show_archived = False
        self.show_previews = False
        self.collapsed = False
        self.auto_collapsed = False  # closed because the window got narrow, not by the user
        self.renaming = None  # key of the book whose name is being edited

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.grid(row=0, column=0, sticky="ew", padx=12, pady=(18, 8))
        top.grid_columnconfigure(0, weight=1)
        self.title = label(top, "Library", 15, TEXT, "bold")
        self.title.grid(row=0, column=0, sticky="w", padx=4)
        self.toggle_btn = button(top, "‹", self.toggle, "ghost", width=32, height=32, border_width=0, font=F(18))
        self.toggle_btn.grid(row=0, column=1)
        self.new_btn = button(self, "＋  New book", app.new_book, "secondary", height=38, anchor="w")
        self.new_btn.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        self.list = ctk.CTkScrollableFrame(self, fg_color="transparent", corner_radius=0,
                                           scrollbar_button_color=LINE, scrollbar_button_hover_color=FIELD_LINE)
        self.list.grid(row=2, column=0, sticky="nsew", padx=(6, 2), pady=(0, 6))

        # Settings and Help live at the bottom of the pane, like the Claude desktop app, not in the bottom bar.
        bottom = ctk.CTkFrame(self, fg_color="transparent")
        bottom.grid(row=3, column=0, sticky="ew", padx=8, pady=(0, 12))
        bottom.grid_columnconfigure(0, weight=1)
        ctk.CTkFrame(bottom, fg_color=LINE, height=1).grid(row=0, column=0, sticky="ew", padx=4, pady=(0, 6))
        # "Version 1.0 is out": shown only when a newer version is found (see updates.py).
        self.update_btn = ctk.CTkButton(bottom, text="", command=self.open_update, anchor="w", height=34,
                                        corner_radius=8, fg_color=AMBER_SOFT, hover_color=AMBER_LINE,
                                        text_color=AMBER, font=F(13, "bold"))
        self.update_url = None
        self.settings_btn = self.pane_button(bottom, "Settings", "settings", app.show_settings)
        self.settings_btn.grid(row=1, column=0, sticky="ew")
        self.help_btn = self.pane_button(bottom, "Help", "help", app.show_help)
        self.help_btn.grid(row=2, column=0, sticky="ew")

    def show_update(self, found):
        """found: (version, url) of a newer release, or None to hide the button."""
        if not found:
            self.update_btn.grid_remove()
            return
        self.update_version, self.update_url = found
        self.update_btn.configure(text="↑" if self.collapsed else f"Version {self.update_version} is out")
        self.update_btn.grid(row=3, column=0, sticky="ew", pady=(4, 0))

    def open_update(self):
        if self.update_url:
            webbrowser.open(self.update_url)

    def pane_button(self, parent, text, icon_name, command):
        """A Settings or Help row: a 20 point icon and its name, 40 points tall so it's easy to hit."""
        return ctk.CTkButton(parent, text=text, image=icon(icon_name, TEXT2), compound="left", command=command,
                             anchor="w", height=HIT, width=HIT, corner_radius=8, fg_color="transparent",
                             hover_color=HOVER, text_color=TEXT2, font=F(13, "bold"))

    def toggle(self, auto=False):
        """Open or close the pane. auto: the window's width did it, so widening the window opens it again."""
        self.collapsed = not self.collapsed
        self.auto_collapsed = auto and self.collapsed
        if self.collapsed:
            self.configure(width=NARROW)
            self.title.grid_remove()
            self.list.grid_remove()
            self.toggle_btn.configure(text="›")
            self.new_btn.configure(text="＋", anchor="center")
            self.settings_btn.configure(text="", anchor="center")
            self.help_btn.configure(text="", anchor="center")
            self.update_btn.configure(text="↑", anchor="center")
        else:
            self.configure(width=WIDTH)
            self.title.grid()
            self.list.grid()
            self.toggle_btn.configure(text="‹")
            self.new_btn.configure(text="＋  New book", anchor="w")
            self.settings_btn.configure(text="Settings", anchor="w")
            self.help_btn.configure(text="Help", anchor="w")
            if self.update_url:
                self.update_btn.configure(text=f"Version {self.update_version} is out", anchor="w")
        if not auto:
            self.app.library_resized()

    def refresh(self):
        for widget in self.list.winfo_children():
            widget.destroy()
        pinned, recent, archived = library.sections(library.load())
        if pinned:
            self.heading("PINNED")
            for book in pinned:
                self.row(book)
        if recent:
            self.heading("BOOKS" if pinned else "RECENT")
            for book in recent:
                self.row(book)
        if not pinned and not recent:
            label(self.list, "Books you open or create\nshow up here.", 12, TEXT3, justify="left").pack(anchor="w", padx=8, pady=8)
        previews = preview_files()
        if previews:
            self.fold(f"Voice previews ({len(previews)})", self.show_previews, self.toggle_previews)
            if self.show_previews:
                for path in previews:
                    self.preview_row(path)
                ctk.CTkButton(self.list, text="Delete all previews", command=self.app.delete_all_previews,
                              fg_color="transparent", hover_color=HOVER, text_color=TEXT3, font=F(12), height=26,
                              anchor="w").pack(fill="x", padx=4, pady=(2, 0))
        if archived:
            self.fold(f"Archived ({len(archived)})", self.show_archived, self.toggle_archived)
            if self.show_archived:
                for book in archived:
                    self.row(book)

    def fold(self, text, open_, command):
        """A section heading that shows or hides the rows under it."""
        button(self.list, f"{'▾' if open_ else '▸'}  {text}", command, "ghost", border_width=0, height=30, anchor="w",
               text_color=TEXT3, font=F(12, "bold")).pack(fill="x", pady=(14, 2))

    def toggle_archived(self):
        self.show_archived = not self.show_archived
        self.refresh()

    def toggle_previews(self):
        self.show_previews = not self.show_previews
        self.refresh()

    def preview_row(self, path):
        """One voice preview: click to play it, hover for the trash button."""
        frame = ctk.CTkFrame(self.list, fg_color="transparent", corner_radius=8)
        frame.pack(fill="x", pady=1)
        frame.grid_columnconfigure(0, weight=1)
        name = label(frame, "▶  " + shorten(preview_name(path), 24), 13, TEXT, anchor="w")
        name.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=6)
        time = label(frame, length(path), 11, TEXT3, family="Menlo")
        time.grid(row=0, column=1, padx=(0, 4))
        trash = ctk.CTkButton(frame, text="🗑", width=30, height=28, corner_radius=8, fg_color="transparent",
                              hover_color=CARD, text_color=TEXT2, command=lambda: self.app.delete_previews([path]))
        trash.grid(row=0, column=2, padx=(0, 6))
        trash.grid_remove()
        for widget in (frame, name, time):
            on_click(widget, lambda: self.app.play_preview_file(path))
        self.hover(frame, trash, "transparent")

    def hover(self, frame, reveal, base, keep=False):
        """Tint the row and show `reveal` while the pointer is over it (always shown if keep)."""
        def enter(event):
            reveal.grid()
            if not keep:
                frame.configure(fg_color=HOVER)

        def leave(event):
            # Leave also fires when the pointer moves onto a widget inside the row; only react when it really left.
            inside = frame.winfo_containing(*frame.winfo_pointerxy())
            if inside is not None and str(inside).startswith(str(frame)):
                return
            frame.configure(fg_color=base)
            if not keep:
                reveal.grid_remove()

        for widget in [frame, *frame.winfo_children()]:
            widget.bind("<Enter>", enter, add="+")
            widget.bind("<Leave>", leave, add="+")

    def heading(self, text):
        label(self.list, text, 11, TEXT3, "bold").pack(anchor="w", padx=8, pady=(10, 2))

    def row(self, book):
        key = library.key(book)
        current = key == self.app.current_book
        base = SELECTED if current else "transparent"
        frame = ctk.CTkFrame(self.list, fg_color=base, corner_radius=8)
        frame.pack(fill="x", pady=1)
        frame.grid_columnconfigure(0, weight=1)
        if self.renaming == key:
            name = entry(frame, height=30, font=F(13))
            name.insert(0, library.display_name(book))
            name.grid(row=0, column=0, sticky="ew", padx=(6, 6), pady=(6, 0))
            name.bind("<Return>", lambda e: self.finish_rename(key, name.get()))
            name.bind("<Escape>", lambda e: self.finish_rename(key, None))
            name.bind("<FocusOut>", lambda e: self.finish_rename(key, name.get()))
            name.after(10, lambda: (name.focus_set(), name.select_range(0, "end")))
        else:
            name = label(frame, shorten(library.display_name(book), 26), 13, TEXT, "bold" if current else "normal", anchor="w")
            name.grid(row=0, column=0, sticky="ew", padx=(10, 4), pady=(7, 0))
        pin = "📌 " if book["pinned"] and book["archived"] else ""
        status = label(frame, pin + library.status(book), 11, TEXT3, anchor="w")
        status.grid(row=1, column=0, sticky="ew", padx=(10, 4), pady=(0, 7))
        dots = ctk.CTkButton(frame, text="⋯", width=30, height=30, corner_radius=8, fg_color="transparent",
                             hover_color=CARD, text_color=TEXT2, font=F(16, "bold"))
        dots.configure(command=lambda: self.menu(book, dots))
        dots.grid(row=0, column=1, rowspan=2, padx=(0, 6))
        if not current:
            dots.grid_remove()
        if self.renaming != key:
            for widget in (name, status):
                on_click(widget, lambda: self.app.open_book(key))
            frame.bind("<Button-1>", lambda e: self.app.open_book(key))

        self.hover(frame, dots, base, keep=current)

    def menu(self, book, anchor):
        key = library.key(book)
        menu = tkinter.Menu(self, tearoff=0)
        menu.add_command(label=REVEAL_LABEL, command=lambda: self.app.reveal_book(key))
        menu.add_command(label="Rename", command=lambda: self.start_rename(key))
        menu.add_command(label="Unpin" if book["pinned"] else "Pin", command=lambda: self.change(key, pinned=not book["pinned"]))
        menu.add_command(label="Unarchive" if book["archived"] else "Archive",
                         command=lambda: self.change(key, archived=not book["archived"]))
        menu.add_separator()
        menu.add_command(label="Delete…", command=lambda: self.app.delete_book(key))
        menu.tk_popup(anchor.winfo_rootx(), anchor.winfo_rooty() + anchor.winfo_height())

    def change(self, key, **changes):
        library.update(key, **changes)
        self.refresh()

    def start_rename(self, key):
        self.renaming = key
        self.refresh()

    def finish_rename(self, key, name):
        if self.renaming != key:
            return  # Return already saved it; the FocusOut that follows does nothing
        self.renaming = None
        if name is not None:
            library.update(key, name=name.strip() or None)  # an empty name goes back to the book's title
        self.after(0, self.refresh)  # not while the entry's own key or focus event is still running
