"""Help window: topics from help.md in the left pane, the selected topic's guide on the right."""
import re
from pathlib import Path

import customtkinter as ctk

from theme import BG, CARD, CARD_LINE, HOVER, LABEL, LINE, PANE, RAISED, TEXT, TEXT2, TEXT3, F, entry, label

HELP_FILE = Path(__file__).with_name("help.md")


def load_topics():
    """Return {topic name: [non-empty lines]} in the order they appear in help.md."""
    text = re.sub(r"<!--.*?-->", "", HELP_FILE.read_text(encoding="utf-8"), flags=re.S)
    topics = {}
    for section in re.split(r"^## ", text, flags=re.M)[1:]:
        name, _, body = section.partition("\n")
        topics[name.strip()] = [line.strip() for line in body.splitlines() if line.strip()]
    return topics


class HelpWindow(ctk.CTkToplevel):
    def __init__(self, master, topic=None):
        super().__init__(master)
        self.title("Help")
        self.bind("<Escape>", lambda e: self.destroy())
        self.geometry("900x640")
        self.configure(fg_color=BG)
        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)
        self.topics = load_topics()

        sidebar = ctk.CTkFrame(self, corner_radius=0, fg_color=PANE, width=240)
        sidebar.grid(row=0, column=0, sticky="ns")
        sidebar.grid_propagate(False)
        sidebar.grid_columnconfigure(0, weight=1)
        sidebar.grid_rowconfigure(1, weight=1)
        ctk.CTkFrame(sidebar, fg_color=LINE, width=1, corner_radius=0).place(relx=1.0, rely=0, relheight=1.0, anchor="ne")
        self.search = entry(sidebar, placeholder_text="Search help", height=36, fg_color=CARD, border_color=CARD_LINE,
                            font=F(13))
        self.search.grid(row=0, column=0, sticky="ew", padx=12, pady=(18, 10))
        self.search.bind("<KeyRelease>", lambda e: self.filter_topics())
        topics = ctk.CTkScrollableFrame(sidebar, fg_color="transparent")
        topics.grid(row=1, column=0, sticky="nsew", padx=(4, 0), pady=(0, 12))
        topics.grid_columnconfigure(0, weight=1)
        self.no_topics = label(topics, "No topics match.", 13, TEXT3)
        self.topic_buttons = {}
        for name in self.topics:
            self.topic_buttons[name] = ctk.CTkButton(topics, text=name, anchor="w", height=30, corner_radius=7,
                                                     fg_color="transparent", hover_color=HOVER, text_color=TEXT2,
                                                     font=F(13), command=lambda n=name: self.show(n))
        self.filter_topics()

        self.page = None
        self.show(topic if topic in self.topics else next(iter(self.topics)))

    def filter_topics(self):
        """Show the topics whose name or text contains the search words."""
        query = self.search.get().strip().lower()
        shown = 0
        for name, btn in self.topic_buttons.items():
            text = (name + " " + " ".join(self.topics[name])).lower()
            if all(word in text for word in query.split()):
                btn.grid(row=shown, column=0, sticky="ew", padx=4, pady=1)
                shown += 1
            else:
                btn.grid_remove()
        self.no_topics.grid(row=0, column=0, sticky="w", padx=10, pady=8) if not shown else self.no_topics.grid_remove()

    def show(self, name):
        for n, btn in self.topic_buttons.items():
            selected = n == name
            btn.configure(fg_color=RAISED if selected else "transparent", text_color=TEXT if selected else TEXT2,
                          font=F(13, "bold") if selected else F(13))

        # A fresh page per topic also starts it scrolled to the top.
        if self.page:
            self.page.destroy()
        self.page = ctk.CTkScrollableFrame(self, fg_color="transparent")
        self.page.grid(row=0, column=1, sticky="nsew", padx=(28, 12), pady=(14, 8))
        self.page.grid_columnconfigure(0, weight=1)
        self.wrapped = []  # (label, indent) pairs whose wrap width follows the window width
        self.page.bind("<Configure>", self.rewrap)

        self.add_text(name, F(26, "bold"), pady=(10, 8), color=TEXT)
        first = True
        for line in self.topics[name]:
            if line.startswith("### "):
                self.add_text(line[4:], F(15, "bold"), pady=(16, 6), color=TEXT)
            elif step := re.match(r"(\d+)\.\s+(.*)", line):
                self.add_item(f"{step[1]}.", step[2])
            elif line.startswith("- "):
                self.add_item("•", line[2:])
            else:
                self.add_text(line, F(14), color=TEXT2 if first else LABEL)
            first = False

    def add_text(self, text, font=None, pady=(2, 2), color=LABEL):
        lbl = ctk.CTkLabel(self.page, text=text, font=font or F(14), anchor="w", justify="left", text_color=color)
        lbl.grid(column=0, sticky="ew", padx=4, pady=pady)
        self.wrapped.append((lbl, 0))

    def add_item(self, marker, text):
        # Marker and text in separate columns so wrapped lines line up under the text, not the number.
        row = ctk.CTkFrame(self.page, fg_color="transparent")
        row.grid(column=0, sticky="ew", padx=(12, 4), pady=2)
        row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(row, text=marker, width=26, anchor="nw", font=F(14), text_color=TEXT3).grid(row=0, column=0, sticky="n")
        lbl = ctk.CTkLabel(row, text=text, anchor="w", justify="left", font=F(14), text_color=LABEL)
        lbl.grid(row=0, column=1, sticky="ew")
        self.wrapped.append((lbl, 50))

    def rewrap(self, event):
        for lbl, indent in self.wrapped:
            lbl.configure(wraplength=max(200, event.width - indent - 30))
