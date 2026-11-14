"""A check that a built app has everything it needs: `Audiobook Maker --self-check` (or python gui.py --self-check).

Imports every part the app loads only when narrating (Kokoro and its English data), finds the
bundled FFmpeg, and, with --narrate and Kokoro's model already downloaded, makes a short audiobook offline.
Prints one line per check and exits with 1 if any failed. The build script runs it on every build."""
import importlib
import sys
import tempfile
import traceback
from pathlib import Path


def check(name, fn, results):
    try:
        detail = fn()
        results.append(True)
        print(f"ok    {name}{f': {detail}' if detail else ''}", flush=True)
    except Exception as e:
        results.append(False)
        print(f"FAIL  {name}: {e!r}", flush=True)
        traceback.print_exc()


def ffmpeg():
    import tools

    missing = tools.missing()
    if missing:
        raise RuntimeError(f"not found: {', '.join(missing)}")
    out = tools.run(["ffmpeg", "-version"], capture_output=True, text=True, check=True).stdout.splitlines()[0]
    return f"{tools.find('ffmpeg')} ({out[:40]})"


def english_data():
    from misaki import en

    g2p = en.G2P(trf=False, british=False, fallback=None)
    phonemes, _ = g2p("Hello world, this is a test.")
    if not phonemes:
        raise RuntimeError("no phonemes")
    return phonemes


def espeak():
    import espeakng_loader

    lib = Path(espeakng_loader.get_library_path())
    if not lib.is_file():
        raise RuntimeError(f"missing {lib}")
    return lib.name


def narrate():
    """A two-paragraph book narrated with Kokoro from the model already on this computer, offline."""
    import os

    os.environ["HF_HUB_OFFLINE"] = "1"
    import audiobook
    import run_settings

    with tempfile.TemporaryDirectory() as tmp:
        tmp = Path(tmp)
        book = tmp / "Check"
        book.mkdir()
        (book / "01.md").write_text("# Chapter One\n\nThe app works.\n\nIt really does.\n", encoding="utf-8")
        cwd = Path.cwd()
        os.chdir(tmp)
        try:
            choices = dict(folder=str(book), voice_a="am_michael", voice_b=None, title="Check", author="Check",
                           cover=None, gentle=False, cast={"enabled": False}, speed=1.0, paragraph_pause=0.6,
                           title_pause=1.2)
            out = audiobook.run(run_settings.render_args(choices), log=lambda m: None)
            size = Path(out).stat().st_size
        finally:
            os.chdir(cwd)
    if size < 10_000:
        raise RuntimeError(f"audiobook is only {size} bytes")
    return f"{size // 1000} KB .m4b"


def main(argv):
    results = []
    print(f"Python {sys.version.split()[0]}, frozen={getattr(sys, 'frozen', False)}", flush=True)
    import version

    print(f"Audiobook Maker {version.VERSION}", flush=True)
    check("FFmpeg and ffprobe", ffmpeg, results)
    for module in ("customtkinter", "sounddevice", "soundfile", "PIL", "send2trash", "pypdf", "platformdirs",
                   "huggingface_hub", "torch", "kokoro"):
        check(f"import {module}", lambda m=module: getattr(importlib.import_module(m), "__version__", ""), results)
    check("espeak-ng", espeak, results)
    check("Kokoro's English data (spaCy)", english_data, results)
    if "--narrate" in argv:
        check("narrate a short book with Kokoro", narrate, results)
    print("ALL OK" if all(results) else f"{results.count(False)} FAILED", flush=True)
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
