"""What a preview or an audiobook is narrated with, worked out from the window's choices. No Tk needed, so it is tested."""
from argparse import Namespace
from pathlib import Path

CHATTERBOX = "Chatterbox"
KOKORO = "Kokoro"
SLIDERS = ("speed", "exaggeration", "cfg_weight", "temperature", "paragraph_pause", "title_pause")


def render_args(choices, sample=False, redo=None, mp3=False, voice=None):
    """The arguments audiobook.run takes, from the window's choices.

    choices: folder, engine (KOKORO or CHATTERBOX), voice_a, voice_b, clip, the SLIDERS values, title, author, cover,
    check, gentle and cast. voice: a Kokoro voice to preview instead of the chosen one (a voice card's play button)."""
    engine = KOKORO if voice else choices["engine"]
    if not voice:
        voice = choices["voice_a"]
        if choices["voice_b"] and choices["voice_b"] != voice:
            voice = f"{voice},{choices['voice_b']}"  # Kokoro averages comma-separated voices
    if engine == CHATTERBOX:
        voice = CHATTERBOX
    # Sliders return values like 0.6000000001; round so settings hash the same between runs.
    values = {name: round(choices[name], 2) for name in SLIDERS}
    return Namespace(
        chapters=choices["folder"],
        engine="chatterbox" if engine == CHATTERBOX else "kokoro",
        voice=voice,
        ref=choices["clip"] if engine == CHATTERBOX else None,
        **values,
        sample=sample,
        title=choices["title"].strip() or Path(choices["folder"]).name,
        author=choices["author"].strip() or "Unknown",
        cover=choices["cover"],
        redo=redo or set(),
        check=bool(choices["check"]),
        gentle=choices["gentle"],
        mp3=mp3,
        cast=choices["cast"] if engine == KOKORO else None,
    )


def preview_key(args):
    """What decides how a preview sounds, so a card's play button can replay one that still matches."""
    return repr({k: v for k, v in vars(args).items() if k not in ("title", "author", "cover", "gentle", "redo", "mp3")})


def chapters_key(args):
    """What decides whether a chapter already made can be reused (for the Redo buttons)."""
    return repr({k: v for k, v in vars(args).items() if k not in ("title", "author", "cover", "gentle", "check")})
