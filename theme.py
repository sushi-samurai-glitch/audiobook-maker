"""Colors, fonts and small widget helpers shared by the main window and the recording dialog."""
import functools
import sys

import customtkinter as ctk

# Dark theme from the redesign (see the "Colors, type, spacing and buttons" board on the design canvas).
BG = "#121317"          # window and fields
PANE = "#16181D"        # library pane, top and bottom bars
FOOTER = PANE
CARD = "#1C1F25"        # cards and lists
RAISED = "#23272E"      # selected row, secondary button
HOVER = "#1F2329"       # row under the pointer
LINE = "#262A31"        # dividers
CARD_LINE = "#2A2E36"   # card borders
FIELD = BG
FIELD_LINE = "#343943"  # field and button borders
TEXT = "#ECEDEF"
TEXT2 = "#A9AEB8"
TEXT3 = "#8C929D"
LABEL = "#D5D8DE"
DISABLED = "#6B717C"
AMBER = "#F2A93B"
AMBER_HOVER = "#F7B857"
AMBER_DARK = "#1B1303"  # text on amber
AMBER_SOFT = "#2A2620"  # selected fill, notices
AMBER_LINE = "#4A3A1E"
BLUE = "#7BA7FF"
BLUE_DARK = "#0D1A33"
BLUE_SOFT = "#1D2433"
GREEN = "#5FD39A"
RED = "#FF6B5E"
RED_SOFT = "#2A1B1A"
RED_TEXT = "#FF8A7A"
BADGE = RAISED
TRACK = "#2E333C"       # slider and switch track
KNOB = "#F4F1EA"        # slider and switch knob
KNOB_HOVER = "#FFFFFF"

MONO = "Menlo" if sys.platform == "darwin" else "Consolas" if sys.platform == "win32" else "DejaVu Sans Mono"
SERIF = "Georgia"

BUTTONS = {
    "primary": dict(fg_color=AMBER, hover_color=AMBER_HOVER, text_color=AMBER_DARK, border_width=0),
    "secondary": dict(fg_color=RAISED, hover_color="#2B3038", text_color=TEXT, border_width=1, border_color=FIELD_LINE),
    "ghost": dict(fg_color="transparent", hover_color=HOVER, text_color=TEXT, border_width=1, border_color=FIELD_LINE),
    "danger": dict(fg_color=RED, hover_color="#FF8277", text_color="#2A0A07", border_width=0),
}
SEGMENTS = dict(fg_color=CARD, selected_color=TRACK, selected_hover_color="#363C46", unselected_color=CARD,
                unselected_hover_color=HOVER, text_color=TEXT, corner_radius=9)


@functools.cache
def F(size, weight="normal", family=None):
    """A font; call only after the Tk root exists."""
    return ctk.CTkFont(family=family, size=size, weight=weight)


def label(parent, text, size=13, color=TEXT, weight="normal", family=None, **kw):
    return ctk.CTkLabel(parent, text=text, text_color=color, font=F(size, weight, family), **kw)


def button(parent, text, command, kind="secondary", **kw):
    options = dict(height=40, corner_radius=10, font=F(13, "bold"), **BUTTONS[kind])
    options.update(kw)
    return ctk.CTkButton(parent, text=text, command=command, **options)


def card(parent, **kw):
    return ctk.CTkFrame(parent, fg_color=CARD, border_color=CARD_LINE, border_width=1, corner_radius=14, **kw)


def entry(parent, **kw):
    options = dict(fg_color=FIELD, border_color=FIELD_LINE, text_color=TEXT, border_width=1, height=40,
                   corner_radius=10, font=F(14))
    options.update(kw)
    return ctk.CTkEntry(parent, **options)


def on_click(widget, command):
    """Make a frame and everything inside it clickable."""
    widget.bind("<Button-1>", lambda event: command())
    for child in widget.winfo_children():
        on_click(child, command)
