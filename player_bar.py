"""The player bar along the bottom of the window; it appears when something is played."""
from pathlib import Path

import customtkinter as ctk

import library
from player import SPEEDS, Player, chapter_at
from theme import AMBER, CARD, CARD_LINE, FIELD_LINE, HOVER, KNOB, KNOB_HOVER, RAISED, TEXT, TEXT2, TEXT3, F, button, label

SAVE_EVERY = 40  # ticks (10 s) between saving the position while playing


def clock(seconds):
    seconds = int(seconds)
    h, m, s = seconds // 3600, seconds // 60 % 60, seconds % 60
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"


def speed_text(speed):
    return f"{speed:g}×"


class PlayerBar(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color=CARD, corner_radius=14, border_width=1, border_color=CARD_LINE, height=76)
        self.app = app
        self.player = Player()
        self.player.speed = library.play_speed()
        self.resume = False  # remember the position of this file (books yes, voice previews no)
        self.dragging = False
        self.ticks = 0
        self.grid_columnconfigure(2, weight=1)

        info = ctk.CTkFrame(self, fg_color="transparent", width=230)
        info.grid(row=0, column=0, sticky="w", padx=(18, 8), pady=10)
        info.grid_propagate(False)
        info.configure(height=56)
        self.title = label(info, "", 14, TEXT, "bold", anchor="w")
        self.title.place(x=0, y=0)
        self.chapter_menu = ctk.CTkOptionMenu(info, values=[""], command=self.pick_chapter, width=226, height=26,
                                              dynamic_resizing=False, fg_color=CARD, button_color=CARD,
                                              button_hover_color=RAISED, text_color=TEXT2, font=F(12),
                                              dropdown_font=F(12), dropdown_fg_color=CARD, dropdown_hover_color=RAISED,
                                              dropdown_text_color=TEXT)
        self.chapter_text = label(info, "", 12, TEXT3, anchor="w")

        controls = ctk.CTkFrame(self, fg_color="transparent")
        controls.grid(row=0, column=1, padx=8)
        small = dict(kind="ghost", width=36, height=36, border_width=0, font=F(15))
        self.prev_btn = button(controls, "⏮", self.prev_chapter, **small)
        self.prev_btn.pack(side="left")
        button(controls, "−15", lambda: self.skip(-15), **{**small, "width": 44, "font": F(13, "bold")}).pack(side="left")
        self.play_btn = button(controls, "▶", self.toggle, "primary", width=46, height=46, corner_radius=23, font=F(17))
        self.play_btn.pack(side="left", padx=6)
        button(controls, "+30", lambda: self.skip(30), **{**small, "width": 44, "font": F(13, "bold")}).pack(side="left")
        self.next_btn = button(controls, "⏭", self.next_chapter, **small)
        self.next_btn.pack(side="left")

        track = ctk.CTkFrame(self, fg_color="transparent")
        track.grid(row=0, column=2, sticky="ew", padx=8)
        track.grid_columnconfigure(1, weight=1)
        self.now = label(track, "0:00", 12, TEXT2, family="Menlo", width=56, anchor="e")
        self.now.grid(row=0, column=0)
        self.slider = ctk.CTkSlider(track, from_=0, to=1, height=16, progress_color=AMBER, button_color=KNOB,
                                    button_hover_color=KNOB_HOVER, fg_color=FIELD_LINE)
        self.slider.grid(row=0, column=1, sticky="ew", padx=8)
        self.slider.bind("<ButtonPress-1>", lambda e: setattr(self, "dragging", True), add="+")
        self.slider.bind("<ButtonRelease-1>", self.drop, add="+")
        self.total = label(track, "0:00", 12, TEXT2, family="Menlo", width=56, anchor="w")
        self.total.grid(row=0, column=2)

        # One button that steps through the speeds, as in the design.
        self.speed = button(self, speed_text(self.player.speed), self.next_speed, "ghost", width=58, height=32,
                            corner_radius=8, font=F(12, "bold"))
        self.speed.grid(row=0, column=3, padx=8)
        ctk.CTkButton(self, text="×", command=self.close, width=32, height=32, fg_color="transparent", hover_color=HOVER,
                      text_color=TEXT2, font=F(18)).grid(row=0, column=4, padx=(0, 14))

    # ---- opening and closing

    def open(self, path, title, resume=True):
        """Play the file from where it was left (resume) or from the start."""
        self.save_position()
        self.player.load(path, library.position(path) if resume else 0.0)
        self.resume = resume
        self.title.configure(text=title if len(title) <= 26 else title[:25] + "…")
        titles = [f"{i}. {t}" for i, (_, t) in enumerate(self.player.chapters, 1)]
        if titles:
            self.chapter_text.place_forget()
            self.chapter_menu.configure(values=titles)
            self.chapter_menu.place(x=0, y=27)
        else:
            self.chapter_menu.place_forget()
            self.chapter_text.configure(text=Path(path).name)
            self.chapter_text.place(x=0, y=29)
        for btn in (self.prev_btn, self.next_btn):
            btn.configure(state="normal" if titles else "disabled")
        self.slider.configure(to=max(self.player.duration, 1))
        self.total.configure(text=clock(self.player.duration))
        self.app.show_player()
        self.player.play()
        self.update_view()
        if self.ticks == 0:
            self.tick()

    def close(self):
        self.player.pause()
        self.save_position()
        self.app.hide_player()

    def save_position(self):
        if self.resume and self.player.path:
            try:
                library.remember_position(self.player.path, self.player.position)
            except OSError:
                pass

    # ---- controls

    def toggle(self):
        if self.player.playing:
            self.player.pause()
            self.save_position()
        else:
            self.player.play()
        self.update_view()

    def skip(self, seconds):
        self.player.seek(self.player.position + seconds)
        self.update_view()

    def prev_chapter(self):
        chapters, now = self.player.chapters, self.player.position
        i = chapter_at(chapters, now)
        if i < 0:
            return
        # Like a CD player: back to the start of this chapter, or to the previous one if already near its start.
        target = chapters[i - 1][0] if now - chapters[i][0] < 3 and i > 0 else chapters[i][0]
        self.player.seek(target)
        self.update_view()

    def next_chapter(self):
        i = chapter_at(self.player.chapters, self.player.position)
        if i + 1 < len(self.player.chapters):
            self.player.seek(self.player.chapters[i + 1][0])
            self.update_view()

    def pick_chapter(self, choice):
        index = int(choice.split(".", 1)[0]) - 1
        self.player.seek(self.player.chapters[index][0])
        if not self.player.playing:
            self.player.play()
        self.update_view()

    def next_speed(self):
        speeds = list(SPEEDS)
        current = min(speeds, key=lambda s: abs(s - self.player.speed))
        speed = speeds[(speeds.index(current) + 1) % len(speeds)]
        self.player.set_speed(speed)
        self.speed.configure(text=speed_text(speed))
        library.remember_play_speed(speed)

    def drop(self, event):
        self.dragging = False
        self.player.seek(self.slider.get())
        self.update_view()

    # ---- keeping the bar up to date

    def update_view(self):
        p = self.player
        self.play_btn.configure(text="⏸" if p.playing else "▶")
        if not self.dragging:
            self.slider.set(p.position)
        self.now.configure(text=clock(self.slider.get() if self.dragging else p.position))
        i = chapter_at(p.chapters, p.position)
        if i >= 0 and self.chapter_menu.get() != self.chapter_menu.cget("values")[i]:
            self.chapter_menu.set(self.chapter_menu.cget("values")[i])

    def tick(self):
        self.ticks += 1
        if self.winfo_ismapped():
            self.update_view()
            if self.player.error:
                self.app.notify(f"Couldn't play the audio: {self.player.error}")
                self.player.error = None
            if self.player.playing and self.ticks % SAVE_EVERY == 0:
                self.save_position()
        self.after(250, self.tick)
