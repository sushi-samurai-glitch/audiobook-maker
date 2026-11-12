"""Tests for run_settings.py: turning the window's choices into what audiobook.run narrates with."""
import run_settings
from run_settings import CHATTERBOX, KOKORO, chapters_key, preview_key, render_args


def choices(**changes):
    base = dict(folder="/books/Wagon", engine=KOKORO, voice_a="am_michael", voice_b=None, clip="/voices/me.wav",
                title="  ", author="", cover=None, check=1, gentle=True, cast={"enabled": True},
                speed=0.9500000001, exaggeration=0.5, cfg_weight=0.3, temperature=0.6, paragraph_pause=0.6,
                title_pause=1.2)
    return {**base, **changes}


def test_kokoro_defaults_and_rounding():
    args = render_args(choices())
    assert args.engine == "kokoro" and args.voice == "am_michael" and args.ref is None
    assert args.speed == 0.95 and args.title == "Wagon" and args.author == "Unknown" and args.check is True
    assert args.cast == {"enabled": True} and args.redo == set()


def test_blend_and_preview_voice():
    assert render_args(choices(voice_b="bf_emma")).voice == "am_michael,bf_emma"
    assert render_args(choices(voice_b="am_michael")).voice == "am_michael"  # the same voice twice isn't a blend
    preview = render_args(choices(engine=CHATTERBOX), sample=True, voice="af_heart")
    assert preview.engine == "kokoro" and preview.voice == "af_heart" and preview.sample


def test_chatterbox_uses_the_clip_and_no_cast():
    args = render_args(choices(engine=CHATTERBOX))
    assert args.engine == "chatterbox" and args.voice == CHATTERBOX and args.ref == "/voices/me.wav" and args.cast is None


def test_keys_ignore_what_doesnt_change_the_sound():
    a, b = render_args(choices()), render_args(choices(title="New title", gentle=False, cover="c.jpg"))
    assert preview_key(a) == preview_key(b) and chapters_key(a) == chapters_key(b)
    c = render_args(choices(speed=1.2))
    assert preview_key(a) != preview_key(c) and chapters_key(a) != chapters_key(c)
    # Checking for skipped words changes a preview (it may be narrated again) but not which chapters are made.
    d = render_args(choices(check=0))
    assert preview_key(a) != preview_key(d) and chapters_key(a) == chapters_key(d)
    assert set(run_settings.SLIDERS) <= set(vars(a))
