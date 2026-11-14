#!/bin/bash
# Build Audiobook Maker.app and a .dmg for Apple silicon Macs.
#   packaging/build_mac.sh            build, check, and make the .dmg in dist-build/
#   SKIP_NARRATE=1 packaging/build_mac.sh      skip the Kokoro narration check
# Needs: an Apple silicon Mac, uv (https://docs.astral.sh/uv/), curl and the internet. Nothing is installed
# outside dist-build/ and packaging/bin/.
set -euo pipefail
cd "$(dirname "$0")/.."
ROOT="$PWD"
OUT="${OUT:-$ROOT/dist-build}"
VERSION="$(sed -n 's/^VERSION = "\(.*\)".*/\1/p' version.py)"
# Static FFmpeg 6.0 builds for Apple silicon (GPL); see packaging/README.md.
FFMPEG_BASE="https://github.com/eugeneware/ffmpeg-static/releases/download/b6.0"
FFMPEG_SHA256="a90e3db6a3fd35f6074b013f948b1aa45b31c6375489d39e572bea3f18336584"
FFPROBE_SHA256="bb2db6f5d8cef919da12fbf592119a987202a8c060a886f3cab091f9cab90b64"

echo "== Audiobook Maker $VERSION"
[ "$(uname -m)" = "arm64" ] || { echo "Build on an Apple silicon Mac."; exit 1; }

echo "== Python environment ($OUT/venv)"
uv venv --python 3.11 --allow-existing "$OUT/venv"
PY="$OUT/venv/bin/python"
uv pip install --python "$PY" -r requirements.txt -r packaging/requirements-build.txt

echo "== FFmpeg"
mkdir -p packaging/bin
for tool in ffmpeg ffprobe; do
    if [ ! -x "packaging/bin/$tool" ]; then
        curl -fsSL "$FFMPEG_BASE/$tool-darwin-arm64.gz" | gunzip > "packaging/bin/$tool"
        chmod +x "packaging/bin/$tool"
    fi
    want="$FFMPEG_SHA256"; [ "$tool" = ffprobe ] && want="$FFPROBE_SHA256"
    echo "$want  packaging/bin/$tool" | shasum -a 256 -c - || { rm -f "packaging/bin/$tool"; exit 1; }
done

echo "== Licences"
# Every bundled Python package's licence text, for Settings → Licences (see THIRD-PARTY-NOTICES.md).
{
    echo "Audiobook Maker $VERSION: licences of the software it includes"
    echo "A summary is in THIRD-PARTY-NOTICES.md. FFmpeg (bundled, GPL-3.0) has the same licence as the app, below."
    echo
    echo "==== Audiobook Maker and FFmpeg: GNU General Public License, version 3 ===="
    cat LICENSE
    echo
    echo "==== Python packages ===="
    uv tool run --from pip-licenses==5.5.5 pip-licenses --python "$PY" --from=mixed --with-urls \
        --with-license-file --no-license-path --format=plain-vertical
} > THIRD-PARTY-LICENSES.txt

echo "== Icon"
"$PY" packaging/make_icon.py packaging/icon.png

echo "== PyInstaller"
"$PY" -m PyInstaller --noconfirm --clean --distpath "$OUT/dist" --workpath "$OUT/work" packaging/audiobook_maker.spec
APP="$OUT/dist/Audiobook Maker.app"

echo "== Self-check of the built app"
CHECK=(--self-check)
if [ -z "${SKIP_NARRATE:-}" ]; then
    CHECK+=(--narrate)
    # The narration check runs offline, so fetch Kokoro's model and one voice first if they aren't here yet.
    "$PY" -c "import downloads; downloads.fetch(['kokoro'], files={'kokoro': downloads.kokoro_files(['am_michael'])})"
fi
"$APP/Contents/MacOS/Audiobook Maker" "${CHECK[@]}"

echo "== Disk image"
STAGE="$OUT/dmg"
rm -rf "$STAGE" && mkdir -p "$STAGE"
cp -R "$APP" "$STAGE/"
ln -s /Applications "$STAGE/Applications"
cp packaging/first-launch.txt "$STAGE/If it won't open.txt"
cp LICENSE "$STAGE/LICENSE.txt"
cp THIRD-PARTY-NOTICES.md "$STAGE/THIRD-PARTY-NOTICES.md"
DMG="$OUT/Audiobook-Maker-$VERSION-mac-arm64.dmg"
rm -f "$DMG"
hdiutil create -volname "Audiobook Maker" -srcfolder "$STAGE" -fs HFS+ -format UDZO -ov "$DMG"
du -h "$APP" | tail -1
ls -lh "$DMG"
echo "== Done: $DMG"
