"""Tests for the quick look at which voice models are on disk (downloads.scan and friends), with a fake cache."""
import sys

import pytest

import downloads


def put(cache, pack, files):
    """Lay files out the way huggingface_hub keeps them: a blob, and a snapshot linking to it."""
    folder = downloads.repo_folder(pack, cache)
    for f in files:
        blob = folder / "blobs" / f.replace("/", "_")
        blob.parent.mkdir(parents=True, exist_ok=True)
        blob.write_bytes(b"x")
        link = folder / "snapshots" / "abc123" / f
        link.parent.mkdir(parents=True, exist_ok=True)
        link.symlink_to(blob)


@pytest.fixture
def cache(tmp_path, monkeypatch):
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "hub"))
    return tmp_path / "hub"


def test_hub_cache_follows_huggingface_rules(tmp_path, monkeypatch):
    for name in ("HF_HUB_CACHE", "HUGGINGFACE_HUB_CACHE", "HF_HOME", "XDG_CACHE_HOME"):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("HOME", str(tmp_path))
    assert downloads.hub_cache() == tmp_path / ".cache" / "huggingface" / "hub"
    monkeypatch.setenv("XDG_CACHE_HOME", str(tmp_path / "xdg"))
    assert downloads.hub_cache() == tmp_path / "xdg" / "huggingface" / "hub"
    monkeypatch.setenv("HF_HOME", str(tmp_path / "hf"))
    assert downloads.hub_cache() == tmp_path / "hf" / "hub"
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path / "c"))
    assert downloads.hub_cache() == tmp_path / "c"


def test_scan_empty_cache_says_everything_is_missing(cache):
    assert downloads.scan() == {"kokoro": False}


def test_scan_finds_what_is_there(cache):
    put(cache, downloads.PACKS["kokoro"], ["config.json"])  # half-downloaded
    assert downloads.scan() == {"kokoro": False}
    put(cache, downloads.PACKS["kokoro"], ["kokoro-v1_0.pth"])  # no voices yet: still counts
    assert downloads.scan() == {"kokoro": True}


def test_scan_does_not_import_huggingface_hub(cache, monkeypatch):
    monkeypatch.setitem(sys.modules, "huggingface_hub", None)  # importing it would now fail
    put(cache, downloads.PACKS["kokoro"], ["config.json", "kokoro-v1_0.pth"])
    assert downloads.scan()["kokoro"]


def test_broken_link_counts_as_missing(cache):
    pack = downloads.PACKS["kokoro"]
    put(cache, pack, ["config.json", "kokoro-v1_0.pth"])
    (downloads.repo_folder(pack, cache) / "blobs" / "kokoro-v1_0.pth").unlink()
    assert not downloads.on_disk(pack, ["config.json", "kokoro-v1_0.pth"])


def test_needs_download_checks_the_voices_the_run_uses(cache):
    kokoro = downloads.PACKS["kokoro"]
    put(cache, kokoro, downloads.kokoro_files(["am_michael"]))
    assert not downloads.needs_download({"kokoro": downloads.kokoro_files(["am_michael"])})
    assert downloads.needs_download({"kokoro": downloads.kokoro_files(["am_michael", "bf_emma"])})
