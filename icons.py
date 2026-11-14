"""Small line icons drawn with Pillow, so they look the same on every Mac and PC (text symbols like ⚙ don't).

Icons follow the usual desktop sizing: a 20 point glyph in a button at least 40 points tall.
Each is drawn on a 24 unit grid at 8× and scaled down, so the edges stay smooth on Retina screens.
"""
import functools
import math

import customtkinter as ctk
from PIL import Image, ImageDraw

ICON = 20       # points: the glyph
HIT = 40        # points: the smallest button an icon sits in
_GRID = 24      # the drawing grid, like most icon sets
_OVER = 8       # supersampling: units drawn per grid unit
_STROKE = 1.75  # grid units


def _canvas():
    side = _GRID * _OVER
    return Image.new("RGBA", (side, side), (0, 0, 0, 0)), side


def _u(value):
    return value * _OVER


def _finish(image, size):
    """Scale the 8× drawing down to 2× the point size (crisp on Retina, fine elsewhere)."""
    return image.resize((size * 2, size * 2), Image.LANCZOS)


def _gear(color, size):
    image, _ = _canvas()
    draw = ImageDraw.Draw(image)
    c, w = _GRID / 2, round(_u(_STROKE))
    teeth, outer, inner = 8, 10.0, 7.4
    points = []
    steps = teeth * 16
    for i in range(steps):
        angle = 2 * math.pi * i / steps
        phase = (i % 16) / 16  # where in one tooth's cycle we are
        # flat-topped teeth with sloped sides: up 0-.12, top .12-.38, down .38-.5, valley .5-1
        if phase < 0.12:
            r = inner + (outer - inner) * phase / 0.12
        elif phase < 0.38:
            r = outer
        elif phase < 0.5:
            r = outer - (outer - inner) * (phase - 0.38) / 0.12
        else:
            r = inner
        points.append((_u(c + r * math.cos(angle)), _u(c + r * math.sin(angle))))
    draw.line(points + points[:2], fill=color, width=w, joint="curve")
    hole = 3.2
    draw.ellipse([_u(c - hole), _u(c - hole), _u(c + hole), _u(c + hole)], outline=color, width=w)
    return _finish(image, size)


def _help(color, size):
    image, _ = _canvas()
    draw = ImageDraw.Draw(image)
    c, w = _GRID / 2, round(_u(_STROKE))
    r = 10.0
    draw.ellipse([_u(c - r), _u(c - r), _u(c + r), _u(c + r)], outline=color, width=w)
    # the question mark: a hook, a short stem and a dot
    hook = 3.3
    hx, hy = c, 9.3
    draw.arc([_u(hx - hook), _u(hy - hook), _u(hx + hook), _u(hy + hook)], 180, 405, fill=color, width=w)
    end = (hx + hook * math.cos(math.radians(45)), hy + hook * math.sin(math.radians(45)))
    draw.line([(_u(end[0]), _u(end[1])), (_u(c), _u(13.6)), (_u(c), _u(14.4))], fill=color, width=w, joint="curve")
    for x, y in (end, (c, 13.6)):  # round the joins
        draw.ellipse([_u(x) - w / 2, _u(y) - w / 2, _u(x) + w / 2, _u(y) + w / 2], fill=color)
    dot = 1.25
    draw.ellipse([_u(c - dot), _u(17.4 - dot), _u(c + dot), _u(17.4 + dot)], fill=color)
    return _finish(image, size)


_DRAW = {"settings": _gear, "help": _help}


@functools.cache
def icon(name, color, size=ICON):
    """A CTkImage of the named icon ("settings" or "help") in color, size points square."""
    image = _DRAW[name](color, size)
    return ctk.CTkImage(light_image=image, dark_image=image, size=(size, size))
