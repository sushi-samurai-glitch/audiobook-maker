"""Running a preview or an audiobook on a worker thread, and showing what it reports.

A part of the main window (gui.App); self is the App."""
import threading
import traceback
from contextlib import suppress
from pathlib import Path

import audiobook
import book_settings
import downloads
import library
import run_settings
import tools
from gui_common import OFFLINE, TK_FINALIZERS, shorten, voice_info


class Runner:
    def log(self, message):
        self.messages.put(("log", message))

    def poll(self):
        while not TK_FINALIZERS.empty():
            finalize, obj = TK_FINALIZERS.get()
            with suppress(Exception):  # as in __del__, a failed cleanup is not worth reporting
                finalize(obj)
        while not self.messages.empty():
            kind, *rest = self.messages.get()
            if kind == "progress":
                if self.view == "creating":
                    stage, done, total, *details = rest
                    if stage == "chapter":
                        self.chapter_done(done, details[0] if details else None)
                    elif stage == "rest":
                        self.note_rest(bool(done))
                    else:
                        self.step_progress(stage, done, total)
            elif kind == "imported":
                self.finish_import(*rest)
            elif kind == "update":
                self.update_found(rest[0])
            elif kind == "log":
                self._append(rest[0])
            else:
                self.finish_run(kind, *rest)
        self.polls += 1
        if self.polls % 5 == 0:
            self.refresh_redo()
        self.after(100, self.poll)

    def finish_run(self, kind, *rest):
        self.running = False
        self.keep_awake.stop()
        self.previewing = None
        self.refresh_play_buttons()
        self.redo_key = None  # chapters may have been made, so check the Redo buttons again
        self.set_preview_buttons("normal")
        self.build_btn.configure(state="normal")
        self.library.refresh()  # a book may have just been finished
        if kind == "done":
            args, out = rest
            if args.sample:
                self.fresh_previews[self.pending_preview] = out
                self.set_preview("ready", out)
                self.play_preview()
            else:
                self.show_ring(1)
                self.show_done(args, out, len(self.chapters))
            return
        self.set_preview("idle")
        stopped_in = None
        if self.view == "creating":
            stopped_in = next((i for i, row in enumerate(self.chapters, 1) if row["status"].cget("text") == "Narrating…"), None)
            self.show_view("setup")
        if kind == "cancelled":
            self._append("Cancelled. Finished chapters are kept; click Create audiobook to continue.")
        else:
            self._append(rest[0])
            self.show_problem(rest[0], stopped_in, offline=len(rest) > 1 and rest[1])

    def show_problem(self, message, chapter=None, offline=False, title=None):
        """Explain a failed preview or audiobook in a banner above the step, with the details in the log."""
        if title:
            text = message
        elif offline or OFFLINE.search(message):
            title = "This voice hasn't been downloaded yet"
            text = "Connect to the internet once to download it, then try again. Voices you've used before work offline."
        elif chapter:
            title = f"Narrating stopped in chapter {chapter}"
            text = "Finished chapters are safe. Click Create audiobook to carry on from where it stopped."
        else:
            title = "Something went wrong"
            text = shorten(message.removeprefix("Error: "), 140)
        self.banner_title.configure(text=title)
        self.banner_text.configure(text=text)
        self.banner.grid(row=0, column=0, sticky="ew", pady=(0, 16))

    def report_callback_exception(self, exc, val, tb):
        # Tk calls this when a button handler raises; show it in the log box, not only in app.log.
        traceback.print_exception(exc, val, tb)
        self.notify(f"Unexpected error: {val}")

    def cancel_run(self):
        self.cancel.set()
        self.cancel_btn.configure(state="disabled", text="Cancelling…")

    def render_args(self, sample=False, redo=None, mp3=False, voice=None):
        """The settings audiobook.run narrates with, as chosen in the window (see run_settings.render_args)."""
        choices = dict(folder=self.folder, voice_a=self.voice_a, voice_b=self.voice_b,
                       title=self.book_title.get(), author=self.author.get(), cover=self.cover_path,
                       gentle=book_settings.gentle(), cast=self.cast)
        choices.update({name: getattr(self, name).get() for name in run_settings.SLIDERS})
        return run_settings.render_args(choices, sample, redo, mp3, voice)

    @staticmethod
    def preview_key(args):
        return run_settings.preview_key(args)

    def start(self, sample, redo=None, mp3=False, voice=None):
        if self.running:
            return
        folder = self.folder
        if not folder:
            self.notify("Choose a chapters folder first.")
            return
        if not Path(folder).is_dir():
            self.notify(f"Chapters folder not found: {folder}")
            return
        files = book_settings.chapter_files(folder)
        if not files:
            self.notify(f"No chapter files (.md or .txt) found in {folder}/")
            return
        if self.cover_path and not Path(self.cover_path).is_file():
            self.notify(f"Cover image not found: {self.cover_path}")
            return
        if tools.missing():  # without FFmpeg the book can't be levelled, joined or played, so say so before narrating
            self.notify(tools.MISSING_FFMPEG)
            self.show_problem(tools.MISSING_FFMPEG, title="FFmpeg is needed")
            return
        args = self.render_args(sample, redo, mp3, voice)
        if not sample:
            try:
                args.output_name = library.claim_output(folder, args.title)
            except OSError as e:
                self.notify(f"Couldn't save this book's settings: {e}")
                return
        voice_label = " + ".join(voice_info(v.strip())[0] for v in args.voice.split(","))
        # A quick look at the files on disk: say a download is coming only when one really is.
        self.will_download = downloads.needs_download(audiobook.LazyVoice(args).needed_files())
        self.previewing = voice
        self.pending_preview = self.preview_key(args) if sample else None
        self.save_book()
        self.running = True
        if not sample:  # an audiobook can take hours; a preview is over in a minute
            self.keep_awake.start()
        self.cancel.clear()
        self.cancel_btn.configure(state="normal", text="Cancel")
        self.set_preview_buttons("disabled")
        self.banner.grid_remove()
        self.build_btn.configure(state="disabled")
        if mp3:
            self._append("Exporting one MP3 per chapter…")
        elif redo:
            self._append(f"Narrating chapter {', '.join(map(str, sorted(redo)))} again with {voice_label}…")
        else:
            note = " (first use downloads the model)" if self.will_download else ""
            self._append(f"{'Previewing' if sample else 'Creating audiobook with'} {voice_label}…{note}")
        if sample:
            self.set_preview("busy")
            self.refresh_play_buttons()
        else:
            titles = [audiobook.chapter_title(book_settings.read_text(f), f) for f in files]
            self.begin_creating(args, titles, voice_label)
            self.show_view("creating")
        threading.Thread(target=self.work, args=(args,), daemon=True).start()

    def work(self, args):
        try:
            out = audiobook.run(args, log=self.log, cancel=self.cancel,
                                progress=lambda *step: self.messages.put(("progress", *step)))
            self.messages.put(("done", args, out))
        except audiobook.Cancelled:
            self.messages.put(("cancelled",))
        except audiobook.ModelNotDownloaded as e:
            self.messages.put(("error", f"Error: {e}", True))
        except BaseException as e:  # anything else, including SystemExit for a book with no chapters
            traceback.print_exc()  # full details go to app.log
            self.messages.put(("error", f"Error: {e}"))
