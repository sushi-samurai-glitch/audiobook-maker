# Contributing

Thank you for helping. Bug reports are the most useful thing: use the issue form, and paste the **Copy details**
text from Settings → About so the version and macOS are known.

## Changing the code

Set up as in **Run from source** in the README, then install the test tools:

```bash
uv pip install --python .venv/bin/python -r requirements-dev.txt
.venv/bin/ruff check .
.venv/bin/pytest
```

The tests don't download voice models or narrate, so they run in a few seconds. If you change narration, also make
a short audiobook from `test_chapters/` with Kokoro and listen to it.

- Keep pull requests to one change, and say in the description what it fixes and how you checked it.
- Text in the app talks to people who aren't technical: plain words, full sentences, no jargon.
- Python packages are pinned in `requirements.txt` on purpose. Change a version only after a test narration.

Contributions are under the project's licence, GPL-3.0 (see `LICENSE`).

## Building the Mac app

See `packaging/README.md`.
