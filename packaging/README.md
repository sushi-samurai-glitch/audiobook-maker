# Building the Mac app

`packaging/build_mac.sh` makes `dist-build/Audiobook-Maker-<version>-mac-arm64.dmg` on an Apple silicon Mac with
[uv](https://docs.astral.sh/uv/):

1. It makes its own Python 3.11 environment in `dist-build/venv` from `requirements.txt` and
   `requirements-build.txt` (PyInstaller, and spaCy's small English model, which Kokoro needs).
2. It downloads static FFmpeg and ffprobe 6.0 builds for Apple silicon into `packaging/bin/` (from
   [eugeneware/ffmpeg-static](https://github.com/eugeneware/ffmpeg-static), GPL) and puts them inside the app.
3. PyInstaller builds `Audiobook Maker.app` from `audiobook_maker.spec`.
4. The built app checks itself (`--self-check --narrate`): every library loads, FFmpeg is found inside the app,
   and Kokoro narrates a two-line book offline. `SKIP_NARRATE=1` skips the narration part.
5. `hdiutil` makes the .dmg: the app, a link to Applications and a note on opening an unsigned app.

The app is not signed with an Apple Developer ID, so the first launch needs System Settings → Privacy & Security →
Open Anyway (see `first-launch.txt`).

GitHub Actions (`.github/workflows/release.yml`) runs the same script on a version tag and drafts a release.
