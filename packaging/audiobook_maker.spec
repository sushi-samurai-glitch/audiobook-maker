# PyInstaller recipe for the Mac app. Run through packaging/build_mac.sh, which installs what it needs first.
# -*- mode: python -*-
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_all, copy_metadata

ROOT = Path(SPECPATH).parent  # noqa: F821  (SPECPATH is set by PyInstaller)
VERSION = re.search(r'^VERSION = "([^"]+)"', (ROOT / "version.py").read_text(), re.M).group(1)
BUNDLE_ID = "io.github.sushi-samurai.audiobook-maker"

# THIRD-PARTY-LICENSES.txt is made by build_mac.sh just before this runs.
datas = [(str(ROOT / name), ".") for name in ("help.md", "LICENSE", "THIRD-PARTY-NOTICES.md",
                                               "THIRD-PARTY-LICENSES.txt")]
binaries = [(str(ROOT / "packaging" / "bin" / name), ".") for name in ("ffmpeg", "ffprobe")]
hiddenimports = ["selfcheck", "downloads"]

# Packages that load data files, native libraries or submodules PyInstaller can't see by reading imports.
for package in ("kokoro", "misaki", "espeakng_loader", "en_core_web_sm", "phonemizer", "language_tags", "segments",
                "csvw", "chatterbox", "perth", "s3tokenizer", "conformer", "faster_whisper", "ctranslate2",
                "customtkinter", "num2words", "spacy", "thinc", "spacy_legacy", "spacy_loggers", "librosa"):
    d, b, h = collect_all(package)
    datas, binaries, hiddenimports = datas + d, binaries + b, hiddenimports + h

# Packages that read their own version (or another's) with importlib.metadata at import time.
for dist in ("en_core_web_sm", "spacy", "thinc", "kokoro", "misaki", "chatterbox-tts", "resemble-perth", "torch",
             "torchaudio", "transformers", "tokenizers", "huggingface_hub", "hf_xet", "safetensors", "tqdm", "regex",
             "filelock", "numpy", "packaging", "requests", "pyyaml", "diffusers", "librosa", "faster-whisper",
             "ctranslate2", "customtkinter", "soundfile", "sounddevice", "num2words", "setuptools"):
    datas += copy_metadata(dist)

a = Analysis(  # noqa: F821
    [str(ROOT / "gui.py")],
    pathex=[str(ROOT)],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    # Installed alongside Chatterbox for its demo web page, which the app never uses.
    excludes=["gradio", "gradio_client", "fastapi", "uvicorn", "starlette", "pytest", "pre_commit", "virtualenv",
              "IPython", "matplotlib", "notebook"],
    noarchive=False,
)
pyz = PYZ(a.pure)  # noqa: F821
exe = EXE(  # noqa: F821
    pyz, a.scripts, [],
    exclude_binaries=True,
    name="Audiobook Maker",
    console=False,
    target_arch="arm64",
    codesign_identity=None,  # unsigned: ad-hoc signed only (see README: the first launch needs Open Anyway)
)
coll = COLLECT(exe, a.binaries, a.datas, name="Audiobook Maker")  # noqa: F821
app = BUNDLE(  # noqa: F821
    coll,
    name="Audiobook Maker.app",
    icon=str(ROOT / "packaging" / "icon.png"),
    bundle_identifier=BUNDLE_ID,
    version=VERSION,
    info_plist={
        "CFBundleDisplayName": "Audiobook Maker",
        "CFBundleShortVersionString": VERSION,
        "CFBundleVersion": VERSION,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": "Audiobook Maker records a short voice clip for Chatterbox to copy.",
        "NSHumanReadableCopyright": "Free software under the GNU GPL, version 3.",
    },
)
