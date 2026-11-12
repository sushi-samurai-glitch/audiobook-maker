# Third-party notices

Audiobook Maker is Copyright © 2026 sushi_samurai and is free software under the GNU General Public License,
version 3 (see `LICENSE`). It is built on the open-source software below. The Mac app includes all of it, and
its full licence texts are in `THIRD-PARTY-LICENSES.txt` inside the app (Settings → Licences), made when the app
is built.

The source code of every released version of Audiobook Maker is on GitHub under that version's tag.

## Licences that require sharing source

| Software | Licence | Used for |
|---|---|---|
| [FFmpeg](https://ffmpeg.org) 6.0, static build from [eugeneware/ffmpeg-static](https://github.com/eugeneware/ffmpeg-static) | GPL-3.0 (built with GPL parts) | Levelling, joining and playing audio |
| [espeak-ng](https://github.com/espeak-ng/espeak-ng), through espeakng-loader | GPL-3.0 | Kokoro's pronunciation of unknown words |
| [phonemizer-fork](https://github.com/thewh1teagle/phonemizer-fork) | GPL-3.0 | Kokoro's text to sounds |
| [pykakasi](https://codeberg.org/miurahr/pykakasi) | GPL-3.0 | Installed with Kokoro's text reader (Japanese; not used for English) |
| [libsndfile](https://libsndfile.github.io/libsndfile/), through soundfile | LGPL-2.1 | Reading and writing audio files |
| [num2words](https://github.com/savoirfairelinux/num2words) | LGPL-2.1 | Spoken numbers in the skipped-word check |
| [python-soxr](https://github.com/dofuuz/python-soxr) / libsoxr | LGPL-2.1 | Resampling in the skipped-word check |

FFmpeg's source for the bundled 6.0 build is at <https://ffmpeg.org/releases/ffmpeg-6.0.tar.xz>, and the build
scripts at <https://github.com/eugeneware/ffmpeg-static>.

## Permissive licences

| Software | Licence |
|---|---|
| [Kokoro](https://github.com/hexgrad/kokoro) and [misaki](https://github.com/hexgrad/misaki) | Apache-2.0 |
| [Chatterbox](https://github.com/resemble-ai/chatterbox) and [Perth](https://github.com/resemble-ai/Perth) watermarker | MIT |
| [faster-whisper](https://github.com/SYSTRAN/faster-whisper) and CTranslate2 | MIT |
| [PyTorch](https://pytorch.org) and torchaudio | BSD-3-Clause, BSD-2-Clause |
| [Transformers](https://github.com/huggingface/transformers), [Diffusers](https://github.com/huggingface/diffusers), [huggingface_hub](https://github.com/huggingface/huggingface_hub) | Apache-2.0 |
| [spaCy](https://spacy.io) and en_core_web_sm | MIT |
| [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) | MIT |
| [NumPy](https://numpy.org), [SciPy](https://scipy.org), [soundfile](https://github.com/bastibe/python-soundfile) | BSD-3-Clause |
| [sounddevice](https://github.com/spatialaudio/python-sounddevice) and PortAudio | MIT |
| [librosa](https://librosa.org) | ISC |
| [Pillow](https://python-pillow.org) | MIT-CMU |
| [pypdf](https://github.com/py-pdf/pypdf), [Send2Trash](https://github.com/arsenetar/send2trash) | BSD-3-Clause |
| [platformdirs](https://github.com/tox-dev/platformdirs) | MIT |
| [Python](https://python.org) and Tcl/Tk | PSF-2.0, Tcl/Tk licence |

## Voice models

The models download from Hugging Face the first time they're used; they aren't part of the app.

| Model | Licence |
|---|---|
| [Kokoro-82M](https://huggingface.co/hexgrad/Kokoro-82M) | Apache-2.0 |
| [Chatterbox](https://huggingface.co/ResembleAI/chatterbox) | MIT. Audio it makes carries Resemble AI's inaudible Perth watermark. |
| [Whisper small.en](https://huggingface.co/Systran/faster-whisper-small.en) | MIT |
