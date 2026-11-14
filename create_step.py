"""The Create step, the Creating screen with its progress ring, and the Finished screen.

A part of the main window (gui.App); self is the App."""
import time
from contextlib import suppress
from pathlib import Path
from tkinter import Canvas

import customtkinter as ctk
from PIL import Image, ImageOps, ImageTk

import audiobook
import book_settings
import downloads
import library
import paths
from gui_common import COVER_BG, GENTLE_ON, REVEAL_LABEL, STEPS, SUMMARY_ROWS, shorten, voice_info
from theme import (
    AMBER,
    AMBER_SOFT,
    BG,
    CARD,
    CARD_LINE,
    GREEN,
    HOVER,
    LINE,
    MONO,
    SERIF,
    TEXT,
    TEXT2,
    TEXT3,
    F,
    button,
    card,
    label,
    on_click,
)


class CreateStep:
    def build_create(self, page):
        self.page_heading(page, "Ready to create your audiobook", "Check everything below. Click any row to go back "
                          "and change it.").grid(row=0, column=0, sticky="new", pady=(0, 22))
        page.grid_rowconfigure(0, weight=0)
        page.grid_rowconfigure(3, weight=1)
        top = ctk.CTkFrame(page, fg_color="transparent")
        top.grid(row=1, column=0, sticky="ew")
        top.grid_columnconfigure(1, weight=1)
        self.create_cover = ctk.CTkLabel(top, text="", width=180, height=180, corner_radius=10, fg_color=COVER_BG,
                                         text_color="#F4F1EA", font=F(20, family=SERIF), wraplength=150, justify="left")
        self.create_cover.grid(row=0, column=0, sticky="n", padx=(0, 24))
        rows = card(top)
        rows.grid(row=0, column=1, sticky="new")
        rows.grid_columnconfigure(0, weight=1)
        self.summary_rows = {}
        for i, (name, step) in enumerate(SUMMARY_ROWS):
            if i:
                ctk.CTkFrame(rows, fg_color=LINE, height=1, corner_radius=0).grid(row=2 * i - 1, column=0, sticky="ew", padx=18)
            row = ctk.CTkFrame(rows, fg_color="transparent", corner_radius=10, height=52)
            row.grid(row=2 * i, column=0, sticky="ew", padx=4, pady=2)
            row.grid_propagate(False)
            row.grid_columnconfigure(1, weight=1)
            row.grid_rowconfigure(0, weight=1)
            label(row, name, 13, TEXT3, width=110, anchor="w").grid(row=0, column=0, padx=(18, 8))
            value = label(row, "", 13, TEXT, "bold", anchor="w", justify="left", wraplength=560)
            value.grid(row=0, column=1, sticky="ew")
            label(row, dict(STEPS)[step] + "  ›", 13, TEXT3).grid(row=0, column=2, padx=(8, 18))
            on_click(row, lambda s=step: self.show_step(s))
            row.bind("<Enter>", lambda e, r=row: r.configure(fg_color=HOVER))
            row.bind("<Leave>", lambda e, r=row: r.configure(fg_color="transparent"))
            self.summary_rows[name] = value

        notes = ctk.CTkFrame(page, fg_color="transparent")
        notes.grid(row=2, column=0, sticky="ew", pady=(22, 0))
        notes.grid_columnconfigure((0, 1), weight=1, uniform="note")
        time_box = ctk.CTkFrame(notes, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12, height=60)
        time_box.grid(row=0, column=0, sticky="ew", padx=(0, 7))
        time_box.grid_propagate(False)
        time_box.grid_rowconfigure(0, weight=1)
        self.estimate_text = label(time_box, "", 13, TEXT2, justify="left", anchor="w", wraplength=380)
        self.estimate_text.grid(row=0, column=0, sticky="w", padx=16)
        gentle_box = ctk.CTkFrame(notes, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12, height=60)
        gentle_box.grid(row=0, column=1, sticky="ew", padx=(7, 0))
        gentle_box.grid_propagate(False)
        gentle_box.grid_rowconfigure(0, weight=1)
        gentle_box.grid_columnconfigure(0, weight=1)
        self.gentle_text = label(gentle_box, "", 13, TEXT2, justify="left", anchor="w", wraplength=300)
        self.gentle_text.grid(row=0, column=0, sticky="w", padx=16)
        button(gentle_box, "Settings", self.show_settings, "ghost", width=84, height=30,
               font=F(12, "bold")).grid(row=0, column=1, padx=(0, 14))

    def cover_image(self, size):
        """The book's cover fitted to a square of size points, or None when there is no cover."""
        if not self.cover_path or not Path(self.cover_path).is_file():
            return None
        try:
            image = ImageOps.fit(Image.open(self.cover_path).convert("RGB"), (size * 2, size * 2))
        except Exception:
            return None
        return ctk.CTkImage(image, size=(size, size))

    def refresh_summary(self):
        """Fill the step bar title, the Voice step's Your audiobook card and the Create step's summary."""
        folder = Path(self.folder) if self.folder else None
        has_book = bool(folder and folder.is_dir())
        title = self.book_title.get().strip() or (folder.name if folder else "") or "New book"
        author = self.author.get().strip()
        count = len(book_settings.chapter_files(folder)) if has_book else 0
        chapters = f"{count} chapter{'s' if count != 1 else ''}"
        self.step_title.configure(text=shorten(title, 30))

        narrator = voice_info(self.voice_a)[0]
        if self.voice_b:
            narrator += f" + {voice_info(self.voice_b)[0]}"
        if self.cast.get("enabled"):
            voices = len(self.cast.get("voices", {}))
            characters = f"{voices} character voice{'s' if voices != 1 else ''}"
        else:
            characters = "One voice"
        speed = self.speed.get()
        self.voice_book.configure(text=shorten(title, 22))
        self.voice_book_sub.configure(text=f"{shorten(author, 16) + ' · ' if author else ''}{chapters}")
        image = self.cover_image(56)
        self.voice_cover.configure(image=image)
        self.voice_facts["Narrator"].configure(text=shorten(narrator, 20))
        self.voice_facts["Speed"].configure(text=f"{speed:.2f}")
        self.voice_facts["Characters"].configure(text=characters)
        self.refresh_blend()

        if self.step != "create":
            return
        image = self.cover_image(180)
        self.create_cover.configure(image=image, text="" if image else title)
        made = set()
        if count:
            with suppress(Exception):  # a half-saved chapter: count nothing as made
                made = audiobook.made_chapters(self.render_args())
        if not has_book:
            chapter_text = "No book chosen yet"
        elif made and len(made) >= count:
            chapter_text = f"{chapters}, all narrated already (only the audiobook is rebuilt)"
        elif made:
            chapter_text = f"{chapters}, {len(made)} narrated already"
        else:
            chapter_text = chapters
        sound = f"Speed {speed:.2f}"
        sound += f" · paragraph pause {self.paragraph_pause.get():.2f} s · heading pause {self.title_pause.get():.2f} s"
        values = {
            "Book": title + (f" · {author}" if author else ""),
            "Chapters": chapter_text,
            "Narrator": narrator,
            "Sound": sound,
            "Characters": characters,
        }
        for name, value in values.items():
            self.summary_rows[name].configure(text=shorten(value, 120))
        left = count - len(made) if has_book else 0
        if has_book and not left:
            estimate = "Every chapter is narrated, so this only takes a moment."
        else:
            estimate = "Kokoro takes about a minute per chapter. Finished chapters are kept if you stop."
        self.estimate_text.configure(text=estimate)
        self.refresh_gentle()

    def refresh_gentle(self, event=None):
        if book_settings.gentle():
            text = "Gentle mode is on: your computer stays cool, but narrating takes a bit longer."
        else:
            text = "Gentle mode is off, for the fastest render."
        self.gentle_text.configure(text=text)

    def build_creating(self):
        self.creating = ctk.CTkFrame(self.body, fg_color="transparent")
        self.creating.grid_columnconfigure(0, weight=1)
        self.creating.grid_rowconfigure(0, weight=1)
        main = ctk.CTkFrame(self.creating, fg_color="transparent")
        main.grid(row=0, column=0, sticky="nsew", padx=(0, 32))
        main.grid_columnconfigure(0, weight=1)
        main.grid_rowconfigure(1, weight=1)

        head = ctk.CTkFrame(main, fg_color="transparent")
        head.grid(row=0, column=0, sticky="ew", pady=(0, 24))
        self.ring = Canvas(head, width=128, height=128, bg=BG, highlightthickness=0)
        self.ring.grid(row=0, column=0, rowspan=3, padx=(0, 28))
        self.ring.create_oval(6, 6, 122, 122, outline=LINE, width=10)
        self.ring.create_arc(6, 6, 122, 122, start=90, extent=0, style="arc", outline=AMBER, width=10, tags="arc")
        self.ring.create_text(64, 64, text="0%", fill=TEXT, font=F(26, "bold"), tags="percent")
        self.creating_title = label(head, "", 26, TEXT, "bold")
        self.creating_title.grid(row=0, column=1, sticky="sw")
        self.creating_sub = label(head, "", 14, TEXT2)
        self.creating_sub.grid(row=1, column=1, sticky="nw", pady=(6, 0))
        # Shown while Gentle mode is on; its text changes while it rests (see note_rest).
        self.gentle_notice = ctk.CTkFrame(head, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=10)
        self.gentle_notice.grid_columnconfigure(1, weight=1)
        label(self.gentle_notice, "●", 12, GREEN).grid(row=0, column=0, padx=(12, 8), pady=8)
        self.gentle_notice_text = label(self.gentle_notice, "", 13, TEXT2)
        self.gentle_notice_text.grid(row=0, column=1, sticky="w", pady=8)
        button(self.gentle_notice, "Settings", self.show_settings, "ghost", width=80, height=28,
               font=F(12, "bold")).grid(row=0, column=2, padx=(12, 8), pady=6)

        self.chapter_rows = ctk.CTkScrollableFrame(main, fg_color=CARD, border_color=CARD_LINE, border_width=1,
                                                   corner_radius=14)
        self.chapter_rows.grid(row=1, column=0, sticky="nsew")
        self.chapter_rows.grid_columnconfigure(0, weight=1)

        side = ctk.CTkFrame(self.creating, fg_color="transparent", width=280)
        side.grid(row=0, column=1, sticky="ns")
        side.grid_propagate(False)
        side.grid_columnconfigure(0, weight=1)
        in_use = card(side)
        in_use.grid(row=0, column=0, sticky="ew")
        in_use.grid_columnconfigure(0, weight=1)
        label(in_use, "Settings in use", 12, TEXT3, "bold").grid(row=0, column=0, sticky="w", padx=18, pady=(16, 6))
        self.summary = ctk.CTkFrame(in_use, fg_color="transparent")
        self.summary.grid(row=1, column=0, sticky="ew", padx=18, pady=(0, 14))
        self.summary.grid_columnconfigure(0, weight=1)
        leave = card(side)
        leave.grid(row=1, column=0, sticky="ew", pady=(14, 0))
        label(leave, "You can leave it running", 13, TEXT, "bold").pack(anchor="w", padx=18, pady=(16, 4))
        label(leave, "Finished chapters are kept. If you cancel or quit, Create picks up where it stopped. "
              "You can still play other books.", 13, TEXT2, justify="left", wraplength=240).pack(anchor="w", padx=18,
                                                                                               pady=(0, 16))

    def begin_creating(self, args, titles, voice_label):
        self.creating_title.configure(text=f"Chapter 1 of {len(titles)}")
        self.run_title = args.title
        self.chapters_ready = 0  # chapters finished so far, narrated now or made earlier
        self.chapter_minutes = []  # minutes each newly narrated chapter took, for the time left
        # The ring covers narrating and then building the file, so 100% means the audiobook is ready to play.
        # finish_share is the part of the ring kept for building; it is set once the run says how much it narrates.
        self.finish_share, self.finish_started = None, None
        self.narrate = (0, 0)  # chapters narrated, of those that need narrating
        self.finish_steps = ("level", "build", "mp3") if args.mp3 else ("level", "build")
        for row in self.chapter_rows.winfo_children():
            row.destroy()
        self.chapters = []
        for i, title in enumerate(titles):
            if i:
                ctk.CTkFrame(self.chapter_rows, fg_color=LINE, height=1, corner_radius=0).grid(row=2 * i - 1, column=0,
                                                                                               sticky="ew", padx=12)
            frame = ctk.CTkFrame(self.chapter_rows, fg_color="transparent", height=46, corner_radius=0)
            frame.grid(row=2 * i, column=0, sticky="ew")
            frame.grid_propagate(False)
            frame.grid_columnconfigure(1, weight=1)
            frame.grid_rowconfigure(0, weight=1)
            label(frame, f"{i + 1:02d}", 11, TEXT3, family=MONO, width=24).grid(row=0, column=0, padx=(12, 10))
            label(frame, shorten(title, 60), 13, TEXT, "bold").grid(row=0, column=1, sticky="w")
            status = label(frame, "Waiting", 12, TEXT3)
            status.grid(row=0, column=2, padx=(8, 16))
            self.chapters.append(dict(frame=frame, status=status))
        self.chapter_state(0, "active")
        self.set_progress(0)
        if args.gentle:
            self.gentle_notice_text.configure(text=GENTLE_ON)
            self.gentle_notice.grid(row=2, column=1, sticky="w", pady=(10, 0))
        else:
            self.gentle_notice.grid_remove()

        for row in self.summary.winfo_children():
            row.destroy()
        rows = [("Voice", voice_label), ("Speed", f"{args.speed:.2f}")]
        cast = args.cast or {}
        count = len(cast.get("voices", {})) if cast.get("enabled") else 0
        rows.append(("Characters", f"{count} with their own voice" if count else "One voice"))
        rows += [("Paragraph pause", f"{args.paragraph_pause:.2f} s"), ("Heading pause", f"{args.title_pause:.2f} s")]
        for i, (name, value) in enumerate(rows):
            label(self.summary, name, 13, TEXT2).grid(row=i, column=0, sticky="w", pady=4)
            label(self.summary, shorten(value, 20), 13, TEXT, "bold").grid(row=i, column=1, sticky="e", pady=4)

    def note_rest(self, resting):
        """Gentle mode says when a rest starts and ends; show it in the notice."""
        if not self.gentle_notice.winfo_ismapped():
            return
        self.gentle_notice_text.configure(text="Resting for a minute to keep the computer cool." if resting else GENTLE_ON)

    def chapter_state(self, i, state, details=None):
        row = self.chapters[i]
        if state == "done":
            details = details or {}
            if "took" in details:
                self.chapter_minutes.append(details["took"])
            text = ("Already made" if details.get("kept") else
                    f"Done · {details['audio']:.1f} min of audio" if "audio" in details else "Done")
            row["status"].configure(text=text, text_color=GREEN, font=F(12, "bold"))
            row["frame"].configure(fg_color="transparent")
        else:  # active
            row["status"].configure(text="Narrating…", text_color=AMBER, font=F(12, "bold"))
            row["frame"].configure(fg_color=AMBER_SOFT)

    def show_ring(self, share):
        """Fill the ring to share (0 to 1). It stops at 99% until the audiobook is ready, then the Finished screen shows."""
        share = min(max(share, 0), 1)
        self.ring.itemconfigure("arc", extent=-359.9 * share)
        self.ring.itemconfigure("percent", text=f"{min(int(100 * share), 99) if share < 1 else 100}%")

    def set_progress(self, done):
        """Show that done chapters are finished (narrated now or made earlier)."""
        total = len(self.chapters)
        if done < total:
            self.creating_title.configure(text=f"Chapter {done + 1} of {total}")
            narrated, todo = self.narrate
            if self.chapter_minutes:
                left = sum(self.chapter_minutes) / len(self.chapter_minutes) * max(todo - narrated, 1)
                sub = f"About {round(left)} minute{'s' if round(left) != 1 else ''} left" if left >= 1.5 else "Almost done"
            else:
                sub = "Working out how long it will take…"
            self.creating_sub.configure(text=f"{shorten(self.run_title, 40)} · {sub}")
        elif self.finish_started is None:
            self.creating_title.configure(text="Building the audiobook")
            self.creating_sub.configure(text=f"{shorten(self.run_title, 40)} · All {total} chapters narrated")

    def chapter_done(self, i, details):
        self.chapters_ready = i
        self.chapter_state(i - 1, "done", details)
        if i < len(self.chapters):
            self.chapter_state(i, "active")
        self.set_progress(i)

    def step_progress(self, stage, done, total):
        """audiobook.run reports each stage of a full build; move the ring and say what it is doing."""
        if stage == "download":  # the voice model, before the first paragraph; the ring waits at 0
            if done >= total:  # downloaded: back to the chapter being narrated
                self.set_progress(self.chapters_ready)
                return
            self.creating_title.configure(text="Downloading the voice")
            amount = (f"{downloads.human(done)} of {downloads.human(total)}" if total > 1000 else
                      f"file {min(done + 1, total)} of {total}")
            self.creating_sub.configure(text=f"{shorten(self.run_title, 40)} · {amount} · only the first time")
            return
        if stage == "narrate":
            self.narrate = (done, total)
            if self.finish_share is None:
                # Building the file takes about as long as narrating a chapter or two. With nothing to narrate
                # (an MP3 export, or every chapter already made), building is the whole job.
                self.finish_share = min(max(1 / (total + 1), 0.05), 0.25) if total else 1.0
            self.show_ring((1 - self.finish_share) * (done / total if total else 0))
            return
        if self.finish_share is None or stage not in self.finish_steps:
            return
        if self.finish_started is None:
            self.finish_started = time.monotonic()
        step = self.finish_steps.index(stage)
        finished = (step + (done / total if total else 1)) / len(self.finish_steps)
        # Tidying up after the last step is quick, but only the Finished screen shows 100%.
        self.show_ring(min(1 - self.finish_share + self.finish_share * finished, 0.995))
        if stage == "level":
            title, what = "Levelling the volume", f"Chapter {min(done + 1, total)} of {total}"
        elif stage == "build":
            title, what = "Building the audiobook file", "Joining the chapters and adding chapter markers"
        else:
            title, what = "Exporting the MP3s", f"Chapter {min(done + 1, total)} of {total}"
        self.creating_title.configure(text=title)
        elapsed = time.monotonic() - self.finish_started
        if finished >= 0.05 and elapsed >= 10:
            left = elapsed / finished * (1 - finished) / 60
            what += f" · about {round(left)} minute{'s' if round(left) != 1 else ''} left" if left >= 1.5 else " · almost done"
        self.creating_sub.configure(text=f"{shorten(self.run_title, 40)} · {what}")

    def build_done(self):
        self.done = ctk.CTkFrame(self.body, fg_color="transparent")
        self.done.grid_columnconfigure((0, 3), weight=1)
        self.done.grid_rowconfigure(0, weight=1)
        self.cover = Canvas(self.done, width=260, height=260, bg=BG, highlightthickness=0)
        self.cover.grid(row=0, column=1, padx=(0, 56))
        text = ctk.CTkFrame(self.done, fg_color="transparent", width=440)
        text.grid(row=0, column=2)
        label(text, "✓  FINISHED", 12, GREEN, "bold").pack(anchor="w")
        label(text, "Your audiobook is ready", 34, TEXT, "bold").pack(anchor="w", pady=(12, 10))
        self.done_sub = label(text, "", 15, TEXT2, justify="left", wraplength=440)
        self.done_sub.pack(anchor="w")
        file_box = ctk.CTkFrame(text, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=12)
        file_box.pack(fill="x", pady=(18, 16))
        file_box.grid_columnconfigure(0, weight=1)
        names = ctk.CTkFrame(file_box, fg_color="transparent")
        names.grid(row=0, column=0, sticky="w", padx=16, pady=12)
        self.done_file = label(names, "", 12, TEXT, "bold", family=MONO)
        self.done_file.pack(anchor="w")
        label(names, f"Saved in {shorten(paths.out_label(), 44)} · opens in Books", 12, TEXT3).pack(anchor="w")
        self.reveal_btn = ctk.CTkButton(file_box, text=REVEAL_LABEL, command=lambda: library.reveal(self.output),
                                        width=10, height=30, fg_color="transparent", hover_color=HOVER,
                                        text_color=AMBER, font=F(13, "bold"))
        self.reveal_btn.grid(row=0, column=1, padx=(8, 10))
        actions = ctk.CTkFrame(text, fg_color="transparent")
        actions.pack(anchor="w")
        self.done_play = button(actions, "▶  Play", self.play_output, "primary", height=48, width=120,
                                font=F(15, "bold"))
        self.done_play.pack(side="left", padx=(0, 10))
        # One MP3 per chapter, in the format audiobook stores ask for; reuses the finished chapters, so it's quick.
        self.mp3_btn = button(actions, "Export MP3s", lambda: self.start(sample=False, mp3=True), "secondary", height=48,
                              width=140, font=F(14, "bold"))
        self.mp3_btn.pack(side="left")

    def show_done(self, args, out, count):
        voice = " blended with ".join(voice_info(v.strip())[0] for v in args.voice.split(","))
        chapters = f"{count} chapter{'s' if count != 1 else ''}"
        self.show_finished(out, f"{chapters}, read by {voice}.", args.title, args.author, args.cover)

    def show_finished(self, out, sub, title, author, cover_path, chapters=True):
        """The Finished screen; chapters=False for an .m4b found in out/, which has no chapters to export as MP3s."""
        self.output = out
        self.mp3_btn.pack(side="left", padx=(10, 0)) if chapters else self.mp3_btn.pack_forget()
        self.done_file.configure(text=shorten(Path(out).name, 40))
        self.done_sub.configure(text=sub)
        cover = self.cover
        cover.delete("all")
        if cover_path:
            # Show the cover that was embedded, fitted inside the same 260 x 260 square.
            image = ImageOps.contain(Image.open(cover_path).convert("RGB"), (260, 260))
            self.cover_photo = ImageTk.PhotoImage(image)  # keep a reference or Tk drops the image
            cover.create_image(130, 130, image=self.cover_photo)
            self.show_view("done")
            return
        cover.create_rectangle(0, 0, 260, 260, fill=COVER_BG, outline="")
        cover.create_rectangle(28, 28, 64, 31, fill=AMBER, outline="")
        cover.create_text(28, 56, text=title, anchor="nw", width=204, fill="#F4F1EA", font=(SERIF, 24))
        if author != "Unknown":
            cover.create_text(28, 232, text=author.upper(), anchor="sw", width=204, fill="#C9BBA5", font=F(11))
        self.show_view("done")
