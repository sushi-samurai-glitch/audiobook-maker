"""Desktop app for audiobook.py: pick a chapters folder, a voice and its settings, then preview or build the .m4b."""
import os

os.environ.setdefault("TQDM_DISABLE", "1")  # Chatterbox's progress bars would fill app.log, which no one watches
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")  # no usage reports to Hugging Face: the app doesn't track anyone
import queue
import sys
import threading
import tkinter
from pathlib import Path
from tkinter import Canvas, messagebox

import customtkinter as ctk

import book_settings
from awake import KeepAwake
import desktop
import library
import paths
import updates
from book_step import BookStep
from create_step import CreateStep
from gui_common import HOW_IT_WORKS, KOKORO, STEP_KEYS, STEPS, shorten
from help_window import HelpWindow
from library_actions import LibraryActions
from library_pane import CONTENT_MIN_WIDTH, MIN_HEIGHT, NARROW
from library_pane import WIDTH as LIBRARY_WIDTH
from library_pane import LibraryPane
from player_bar import PlayerBar
from runner import Runner
from settings_window import SettingsWindow
from sound_step import SoundStep
from theme import (
    AMBER,
    AMBER_DARK,
    AMBER_SOFT,
    BG,
    CARD,
    FIELD,
    FIELD_LINE,
    FOOTER,
    LABEL,
    LINE,
    MONO,
    PANE,
    RAISED,
    RED_SOFT,
    RED_TEXT,
    TEXT,
    TEXT2,
    TEXT3,
    TRACK,
    F,
    button,
    label,
    on_click,
)
from voice_step import VoiceStep


class App(BookStep, VoiceStep, SoundStep, CreateStep, LibraryActions, Runner, ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("Audiobook Maker")
        self.geometry(f"{1180 + LIBRARY_WIDTH}x860")  # room for the player bar
        # Small enough for a 1366 × 768 laptop or a 1080p screen at 150%: below CONTENT_MIN_WIDTH + LIBRARY_WIDTH the
        # library pane closes to its narrow strip (see fit_library).
        self.fit_min_size()
        self.configure(fg_color=BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(1, weight=1)  # rows: step bar, body, player bar, log, footer

        self.folder = ""
        self.current_book = None  # library key of the book shown: its chapters folder, or an .m4b found in out/
        self.engine = KOKORO
        self.voice_a, self.voice_b, self.slot = "am_michael", None, "a"  # slot: which one a voice click sets
        self.clip = None  # path of the Chatterbox voice clip; None means the built-in voice
        self.cover_path = None  # cover image embedded in the .m4b; None means no cover
        self.cast = {"enabled": False, "dialogue": None, "voices": {}}  # character voices; see CastWindow
        self.cast_window = None
        self.value_labels = {}
        self.help_window = None
        self.settings_window = None
        self.running = False
        self.book_has_settings = False
        self.sample_path = None  # the last voice preview, for Play again
        self.previewing = None  # the voice whose card play button is making a preview
        self.fresh_previews = {}  # previews made since the app opened, by preview_key, so play can replay them
        self.pending_preview = None
        self.redo_buttons, self.redo_key, self.polls = [], None, 0
        self.redo_pending = (None, 0.0)  # settings that changed, and when: Redo is checked once they stay put
        self.importing = False
        self.view = "setup"
        self.cancel = threading.Event()
        self.keep_awake = KeepAwake()  # on while an audiobook is being made, so the computer doesn't sleep
        # Tk timers created from the worker thread never fire on macOS, so the worker posts
        # messages here and the main thread polls for them.
        self.messages = queue.Queue()

        self.body = ctk.CTkFrame(self, fg_color="transparent")
        self.body.grid(row=1, column=1, sticky="nsew", padx=36, pady=(28, 20))
        self.body.grid_columnconfigure(0, weight=1)
        self.body.grid_rowconfigure(0, weight=1)
        self.build_stepbar()
        self.build_welcome()
        self.build_setup()
        self.build_creating()
        self.build_done()
        self.build_log()
        self.build_footer()
        self.library = LibraryPane(self, self)
        self.library.grid(row=0, column=0, rowspan=5, sticky="ns")
        self.bind("<Configure>", self.fit_library, add="+")
        self.player_bar = PlayerBar(self, self)  # shown by show_player once something plays

        self.refresh_cast()
        self.bind("<FocusIn>", self.refresh_pronunciations, add="+")  # pick up edits saved in the text editor
        self.bind("<FocusIn>", self.refresh_gentle, add="+")  # Settings also calls refresh_gentle as soon as the switch flips
        self.set_engine(KOKORO)
        self.show_view("setup")
        self.refresh_voices()
        # Reopen the last book, with the voice and settings it was saved with.
        start_folder = book_settings.last_folder()
        first_launch = "last_folder" not in book_settings.app_state()  # not after deleting every book
        if not start_folder and first_launch and Path("chapters").is_dir():
            start_folder = str(Path("chapters").resolve())
        if start_folder:
            self.set_folder(start_folder)
        self.step = "create" if self.folder and self.book_has_settings else "book"
        self.show_view("setup")  # the first launch screen when no book is open
        library.discover()
        self.library.refresh()
        self.protocol("WM_DELETE_WINDOW", self.quit_app)
        self.createcommand("::tk::mac::Quit", self.quit_app)  # ⌘Q and Quit in the menu
        if sys.platform == "darwin":
            self.createcommand("::tk::mac::ShowPreferences", self.show_settings)  # ⌘, and Settings… in the app menu
        else:
            self.bind_all("<Control-comma>", lambda e: self.show_settings())
        self.bind_shortcuts()
        self.poll()
        self.after(3000, self.check_for_updates)

    def text_scale(self):
        """1.0, or more with Larger text on (Settings)."""
        return ctk.ScalingTracker.get_widget_scaling(self)

    def fit_min_size(self):
        """Keep the window big enough for its content, which Larger text makes bigger."""
        scale = self.text_scale()
        width, height = round((CONTENT_MIN_WIDTH + NARROW) * scale), round(MIN_HEIGHT * scale)
        self.minsize(width, height)
        self.update_idletasks()
        now_w = self._reverse_window_scaling(self.winfo_width())
        now_h = self._reverse_window_scaling(self.winfo_height())
        if now_w > 1 and (now_w < width or now_h < height):
            self.geometry(f"{max(now_w, width)}x{max(now_h, height)}")

    def bind_shortcuts(self):
        """Keyboard shortcuts for the main things, so the app works without a mouse (listed in Help, Keyboard)."""
        mod = desktop.MOD_KEY

        def setup_only(action):
            def run(event):
                if self.view == "setup" and self.in_main_window(event):
                    action()
                return "break"
            return run

        self.bind_all(f"<{mod}-Return>", setup_only(
            lambda: self.build_btn.cget("state") != "disabled" and self.next_step()))
        self.bind_all(f"<{mod}-bracketleft>", setup_only(self.previous_step))
        for number, key in enumerate(STEP_KEYS, 1):
            self.bind_all(f"<{mod}-Key-{number}>", setup_only(lambda key=key: self.show_step(key)))
        self.bind_all(f"<{mod}-f>", setup_only(self.find_voice))
        self.bind_all(f"<{mod}-n>", lambda e: (self.new_book(), "break")[1])
        self.bind_all(f"<{mod}-l>", lambda e: (self.library.toggle(), "break")[1])
        self.bind_all(f"<{mod}-slash>", lambda e: (self.show_help(), "break")[1])
        self.bind_all("<space>", self.space_pressed, add="+")

    def in_main_window(self, event):
        """Whether a key was pressed in this window, not in Settings, Help or another window of the app."""
        try:
            return event.widget.winfo_toplevel() is self
        except (AttributeError, KeyError, tkinter.TclError):  # a menu, or a widget that has just been destroyed
            return False

    def find_voice(self):
        self.show_step("voice")
        self.search.focus_set()

    def space_pressed(self, event):
        """Space plays and pauses the player, unless the cursor is in a text field or on a button."""
        if isinstance(event.widget, (tkinter.Entry, tkinter.Text, tkinter.Button)) or not self.player_bar.player.path:
            return None
        if not self.in_main_window(event):
            return None
        self.player_bar.toggle()
        return "break"

    def check_for_updates(self, force=False):
        """Show a newer version found earlier, and ask GitHub again if a day has passed (or force)."""
        self.library.show_update(updates.known())
        if force or updates.due():
            threading.Thread(target=lambda: self.messages.put(("update", updates.check())), daemon=True).start()

    def update_found(self, found):
        self.library.show_update(found)
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.show_update(found)

    def show_settings(self):
        if self.settings_window and self.settings_window.winfo_exists():
            self.settings_window.lift()
        else:
            self.settings_window = SettingsWindow(self, on_change=self.refresh_gentle)
        self.settings_window.focus()

    def show_help(self, topic=None):
        if self.help_window and self.help_window.winfo_exists():
            if topic:
                self.help_window.show(topic)
        else:
            self.help_window = HelpWindow(self, topic)
        self.help_window.lift()
        self.help_window.focus()

    def slider(self, parent, text, hint, low, high, default):
        row = ctk.CTkFrame(parent, fg_color="transparent")
        row.grid_columnconfigure(0, weight=1)
        names = ctk.CTkFrame(row, fg_color="transparent")
        names.grid(row=0, column=0, sticky="w")
        label(names, text, 13, LABEL, "bold").pack(anchor="w")
        label(names, hint, 12, TEXT3).pack(anchor="w")
        value = ctk.CTkLabel(row, text=f"{default:.2f}", width=54, height=26, corner_radius=7, fg_color=FIELD,
                             text_color=AMBER, font=F(12, family=MONO))
        value.grid(row=0, column=1, sticky="ne")
        slider = ctk.CTkSlider(row, from_=low, to=high, number_of_steps=round((high - low) / 0.05), height=18,
                               progress_color=AMBER, button_color="#F4F1EA", button_hover_color="#FFFFFF",
                               fg_color=TRACK, command=lambda v: self.slider_moved(slider, v))
        slider.set(default)
        slider.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(8, 0))
        self.value_labels[slider] = value
        return row, slider

    def slider_moved(self, slider, v):
        self.value_labels[slider].configure(text=f"{v:.2f}")
        self.draw_rhythm()

    def build_stepbar(self):
        """The bar above the steps: the book's title, then the four steps. Any step can be clicked."""
        bar = ctk.CTkFrame(self, fg_color=PANE, corner_radius=0, height=64)
        bar.grid_propagate(False)
        bar.grid_rowconfigure(0, weight=1)
        bar.grid_columnconfigure(len(STEPS) + 1, weight=1)
        self.stepbar = bar
        self.step_title = label(bar, "", 15, TEXT, "bold")
        self.step_title.grid(row=0, column=0, padx=(36, 28))
        self.step_items = {}
        self.eyebrow = label(bar, "CREATING YOUR AUDIOBOOK", 12, AMBER, "bold")  # in place of the steps while creating
        for i, (key, name) in enumerate(STEPS):
            item = ctk.CTkFrame(bar, fg_color="transparent")
            item.grid(row=0, column=i + 1, padx=(0, 12))
            dot = Canvas(item, width=22, height=22, bg=PANE, highlightthickness=0)
            dot.create_oval(0, 0, 21, 21, outline="", tags="circle")
            dot.create_text(11, 11, text=str(i + 1), font=F(11, "bold"), tags="mark")
            dot.pack(side="left")
            text = label(item, name, 13, TEXT3, "bold")
            text.pack(side="left", padx=(8, 0))
            if i < len(STEPS) - 1:
                ctk.CTkFrame(item, fg_color=FIELD_LINE, width=28, height=1, corner_radius=0).pack(side="left", padx=(12, 0))
            on_click(item, lambda k=key: self.show_step(k))
            self.step_items[key] = (dot, text)
        ctk.CTkFrame(bar, fg_color=LINE, height=1, corner_radius=0).place(relx=0, rely=1.0, anchor="sw", relwidth=1.0)

    def page_heading(self, parent, title, text):
        box = ctk.CTkFrame(parent, fg_color="transparent")
        label(box, title, 26, TEXT, "bold").pack(anchor="w")
        label(box, text, 14, TEXT2).pack(anchor="w", pady=(6, 0))
        return box

    def build_welcome(self):
        """The first launch screen, shown while no book is open."""
        self.welcome = ctk.CTkFrame(self.body, fg_color="transparent")
        self.welcome.grid_columnconfigure(0, weight=1)
        self.welcome.grid_rowconfigure((0, 2), weight=1)
        inner = ctk.CTkFrame(self.welcome, fg_color="transparent", width=620)
        inner.grid(row=1, column=0)
        icon = ctk.CTkLabel(inner, text="♫", width=72, height=72, corner_radius=18, fg_color=AMBER_SOFT,
                            text_color=AMBER, font=F(34))
        icon.pack(pady=(0, 24))
        label(inner, "Turn your book into an audiobook", 32, TEXT, "bold").pack()
        label(inner, "Natural voices, chapter markers and cover art. Everything runs on this computer, free.", 15,
              TEXT2).pack(pady=(10, 26))
        choose = ctk.CTkFrame(inner, fg_color=CARD, border_color="#4A505C", border_width=2, corner_radius=16)
        choose.pack(fill="x")
        button(choose, "Choose a book…", self.choose_files, "primary", height=46, width=190,
               font=F(15, "bold")).pack(pady=(26, 8))
        label(choose, f"Select chapter .md or .txt files ({desktop.SELECT_ALL} for all), or an EPUB, Word or PDF book", 13, TEXT2).pack(pady=(0, 24))
        steps = ctk.CTkFrame(inner, fg_color="transparent")
        steps.pack(fill="x", pady=(26, 0))
        steps.grid_columnconfigure((0, 1, 2), weight=1, uniform="how")
        for i, (number, title, text) in enumerate(HOW_IT_WORKS):
            box = ctk.CTkFrame(steps, fg_color=PANE, border_color=LINE, border_width=1, corner_radius=12)
            box.grid(row=0, column=i, sticky="nsew", padx=(0 if i == 0 else 6, 0 if i == 2 else 6))
            label(box, number, 13, AMBER, "bold").pack(anchor="w", padx=14, pady=(12, 0))
            label(box, title, 13, TEXT, "bold").pack(anchor="w", padx=14)
            label(box, text, 13, TEXT3).pack(anchor="w", padx=14, pady=(0, 12))
        label(inner, "Voices download once, the first time you use them. After that, no internet is needed.", 12,
              TEXT3).pack(pady=(24, 0))

    def build_banner(self):
        """A problem with the last preview or audiobook, shown above the step instead of in a pop-up."""
        self.banner = ctk.CTkFrame(self.setup, fg_color=RED_SOFT, border_color="#5A2C28", border_width=1,
                                   corner_radius=14)
        self.banner.grid_columnconfigure(1, weight=1)
        label(self.banner, "!", 16, RED_TEXT, "bold", width=24).grid(row=0, column=0, rowspan=2, padx=(16, 8), sticky="n",
                                                                    pady=14)
        self.banner_title = label(self.banner, "", 14, TEXT, "bold")
        self.banner_title.grid(row=0, column=1, sticky="w", pady=(14, 2))
        self.banner_text = label(self.banner, "", 13, "#D9B5B0", justify="left", wraplength=700)
        self.banner_text.grid(row=1, column=1, sticky="w", pady=(0, 14))
        actions = ctk.CTkFrame(self.banner, fg_color="transparent")
        actions.grid(row=0, column=2, rowspan=2, padx=14)
        ctk.CTkButton(actions, text="Show details", command=self.toggle_log, width=110, height=32, corner_radius=8,
                      fg_color="transparent", hover_color="#3A2321", border_width=1, border_color="#5A2C28",
                      text_color=TEXT, font=F(12, "bold")).pack(side="left")
        ctk.CTkButton(actions, text="×", command=self.banner.grid_remove, width=32, height=32, fg_color="transparent",
                      hover_color="#3A2321", text_color=TEXT2, font=F(18)).pack(side="left", padx=(6, 0))

    def build_setup(self):
        self.setup = ctk.CTkFrame(self.body, fg_color="transparent")
        self.setup.grid_columnconfigure(0, weight=1)
        self.setup.grid_rowconfigure(1, weight=1)
        self.build_banner()
        self.previews = []  # the preview boxes on the Voice and Sound steps; set_preview updates both
        self.extra_cards = []  # blending and character voices, shown only for Kokoro
        self.pages = {}
        for key, build in (("book", self.build_book), ("voice", self.build_voice), ("sound", self.build_sound),
                           ("create", self.build_create)):
            page = ctk.CTkFrame(self.setup, fg_color="transparent")
            page.grid_columnconfigure(0, weight=1)
            page.grid_rowconfigure(0, weight=1)
            build(page)
            self.pages[key] = page
        self.step = "book"

    def show_step(self, key):
        if key != "voice" and self.slot == "b":
            self.pick_slot("a")  # choosing a blend voice ends when the Voice step is left
        self.step = key
        index = STEP_KEYS.index(key)
        for name, page in self.pages.items():
            page.grid(row=1, column=0, sticky="nsew") if name == key else page.grid_remove()
        for i, name in enumerate(STEP_KEYS):
            dot, text = self.step_items[name]
            dot.itemconfigure("circle", fill=AMBER if i <= index else RAISED)
            dot.itemconfigure("mark", text="✓" if i < index else str(i + 1), fill=AMBER_DARK if i <= index else TEXT2)
            text.configure(text_color=TEXT if i <= index else TEXT3)
        last = index == len(STEPS) - 1
        self.build_btn.configure(text="Create audiobook" if last else f"Next: {STEPS[index + 1][1]}")
        if self.view == "setup":
            self.back_btn.grid(row=0, column=2, padx=(0, 12)) if index else self.back_btn.grid_remove()
        self.refresh_summary()
        if key == "sound":
            self.after(50, self.draw_rhythm)

    def next_step(self):
        index = STEP_KEYS.index(self.step)
        if index == len(STEPS) - 1:
            self.start(sample=False)
        else:
            self.show_step(STEP_KEYS[index + 1])

    def previous_step(self):
        index = STEP_KEYS.index(self.step)
        if index:
            self.show_step(STEP_KEYS[index - 1])

    def build_log(self):
        # Its own row between the player bar and the footer, shown by toggle_log. It used to float over the window,
        # which covered the player bar, and on macOS left a stale picture of itself behind when hidden.
        self.log_open = False
        self.log_frame = ctk.CTkFrame(self, fg_color="transparent", height=180)
        self.log_frame.pack_propagate(False)
        self.log_box = ctk.CTkTextbox(self.log_frame, fg_color="#0D0E11", text_color=LABEL, font=F(12, family=MONO),
                                      state="disabled", corner_radius=12, border_width=1, border_color=FIELD_LINE)
        self.log_box.pack(fill="both", expand=True, padx=36, pady=(0, 10))
        self.log_line = "Ready"

    def build_footer(self):
        footer = ctk.CTkFrame(self, fg_color=FOOTER, corner_radius=0, height=80)
        footer.grid(row=4, column=1, sticky="ew")
        footer.grid_propagate(False)
        footer.grid_columnconfigure(0, weight=1)
        footer.grid_rowconfigure(0, weight=1)
        self.log_btn = ctk.CTkButton(footer, text="›  Ready", anchor="w", fg_color=FIELD, hover_color=CARD, border_width=1,
                                     border_color=FIELD_LINE, text_color=TEXT2, font=F(12, family=MONO), height=44,
                                     corner_radius=10, command=self.toggle_log)
        self.log_btn.grid(row=0, column=0, sticky="ew", padx=(36, 16))
        # Gentle mode is a setting for this computer, so it lives in the Settings window; Help is in the library pane.
        # In the set up view: Back, and Next (Create audiobook on the last step).
        self.back_btn = button(footer, "Back", self.previous_step, "ghost", width=90, height=46, font=F(14, "bold"))
        self.build_btn = button(footer, "Next: Voice", self.next_step, "primary", width=190, height=50,
                                corner_radius=12, font=F(16, "bold"))
        self.cancel_btn = button(footer, "Cancel", self.cancel_run, "ghost", width=120, height=54, corner_radius=14,
                                 font=F(15, "bold"))
        self.again_btn = button(footer, "Edit book", self.back_to_setup, "ghost", width=150, height=54,
                                corner_radius=14, font=F(15, "bold"))

    def toggle_log(self, show=None):
        """Open or close the log; show=True or False sets it instead of flipping it."""
        self.log_open = (not self.log_open) if show is None else show
        if self.log_open:
            self.log_frame.grid(row=3, column=1, sticky="ew")
        else:
            self.log_frame.grid_remove()
        self.log_btn.configure(text=("⌄  " if self.log_open else "›  ") + self.log_line)

    def show_view(self, view):
        if view == "setup" and not (self.folder and Path(self.folder).is_dir()):
            view = "welcome"  # no book yet: the first launch screen
        self.view = view
        for name, frame, action in (("welcome", self.welcome, None), ("setup", self.setup, self.build_btn),
                                    ("creating", self.creating, self.cancel_btn), ("done", self.done, self.again_btn)):
            if name == view:
                frame.grid(row=0, column=0, sticky="nsew")
                if action:
                    action.grid(row=0, column=3, padx=(0, 36))
            else:
                frame.grid_remove()
                if action:
                    action.grid_remove()
        for dot, text in self.step_items.values():
            dot.master.grid() if view == "setup" else dot.master.grid_remove()
        if view == "creating":
            self.eyebrow.grid(row=0, column=len(STEPS) + 2, padx=(0, 36), sticky="e")
        else:
            self.eyebrow.grid_remove()
        if view in ("done", "welcome"):
            self.stepbar.grid_remove()
        else:
            self.stepbar.grid(row=0, column=1, sticky="ew")
        if view == "done" and self.log_open:
            self.toggle_log(False)  # fold the progress log away so the finished book and its player have the room
        if view == "setup":
            self.show_step(self.step)  # places Back and refreshes the summary
        else:
            self.back_btn.grid_remove()

    def _append(self, message, show=False):
        self.log_box.configure(state="normal")
        self.log_box.insert("end", message + "\n")
        self.log_box.see("end")
        self.log_box.configure(state="disabled")
        self.log_line = shorten(message.splitlines()[0], 110)
        self.log_btn.configure(text=("⌄  " if self.log_open else "›  ") + self.log_line)
        if show and not self.log_open:
            self.toggle_log(True)

    def notify(self, message):
        """Log a problem and open the log, since it is hidden by default."""
        self._append(message, show=True)

    def quit_app(self):
        if self.running and not messagebox.askyesno(
                "Quit Audiobook Maker?", "Narration is still running. If you quit now, it stops; the chapters and "
                "paragraphs already narrated are kept, so Create audiobook carries on from there next time.",
                icon="warning", default="no", parent=self):
            return
        self.cancel.set()
        self.keep_awake.stop()
        self.player_bar.close()
        self.save_book()
        self.destroy()


if __name__ == "__main__":
    import multiprocessing

    multiprocessing.freeze_support()  # a packaged app: helper processes start this file again
    if "--self-check" in sys.argv:  # used by the build script to test a built app
        import selfcheck

        sys.exit(selfcheck.main(sys.argv[1:]))
    # A packaged app (or pythonw on Windows) has no console to write to: keep the details in app.log
    if getattr(sys, "frozen", False) or sys.stdout is None or sys.stderr is None:
        log = paths.log_file()
        log.parent.mkdir(parents=True, exist_ok=True)
        paths.rotate_log(log)
        sys.stdout = sys.stderr = open(log, "a", encoding="utf-8", buffering=1)  # noqa: SIM115
        import time

        import version

        print(f"--- Audiobook Maker {version.VERSION} started {time.strftime('%Y-%m-%d %H:%M')}")
    paths.configure(Path(__file__).parent)  # where build/, samples/, voices/ and the audiobooks are kept
    ctk.set_appearance_mode("dark")
    if book_settings.larger_text():
        ctk.set_widget_scaling(book_settings.LARGER_TEXT)
    App().mainloop()
