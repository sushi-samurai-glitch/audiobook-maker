"""Text colours stay readable: WCAG AA (4.5:1) against every background they're drawn on."""
import pytest

import theme

BACKGROUNDS = ["BG", "PANE", "CARD", "RAISED", "HOVER", "AMBER_SOFT", "RED_SOFT"]
TEXT_COLOURS = ["TEXT", "TEXT2", "TEXT3", "LABEL", "AMBER", "BLUE", "GREEN", "RED", "RED_TEXT"]


def luminance(colour):
    channels = [int(colour[i:i + 2], 16) / 255 for i in (1, 3, 5)]
    r, g, b = (c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4 for c in channels)
    return 0.2126 * r + 0.7152 * g + 0.0722 * b


def contrast(a, b):
    light, dark = sorted((luminance(a), luminance(b)), reverse=True)
    return (light + 0.05) / (dark + 0.05)


@pytest.mark.parametrize("text", TEXT_COLOURS)
@pytest.mark.parametrize("background", BACKGROUNDS)
def test_text_is_readable(text, background):
    assert contrast(getattr(theme, text), getattr(theme, background)) >= 4.5


def test_buttons_are_readable():
    for style in theme.BUTTONS.values():
        background = style["fg_color"] if style["fg_color"] != "transparent" else theme.BG
        assert contrast(style["text_color"], background) >= 4.5
