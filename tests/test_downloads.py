"""Tests for downloads.py and the download step of a run, with a fake Hugging Face (nothing is downloaded)."""
import threading
import time
from types import SimpleNamespace

import pytest

hub = pytest.importorskip("huggingface_hub")  # CI installs only what the tests of the app itself need

import audiobook  # noqa: E402
import downloads  # noqa: E402

SIZE = 1000


def put_in_cache(cache, repo, filename, data=b"x" * SIZE):
    """Lay a file out the way huggingface_hub keeps it: blobs, a snapshot linking to them, and refs/main."""
    folder = cache / f"models--{repo.replace('/', '--')}"
    (folder / "refs").mkdir(parents=True, exist_ok=True)
    (folder / "refs" / "main").write_text("abc123")
    blob = folder / "blobs" / f"{abs(hash(filename))}"
    blob.parent.mkdir(parents=True, exist_ok=True)
    blob.write_bytes(data)
    snap = folder / "snapshots" / "abc123" / filename
    snap.parent.mkdir(parents=True, exist_ok=True)
    snap.symlink_to(blob)


@pytest.fixture
def fake_hub(tmp_path, monkeypatch):
    """A Hugging Face that 'downloads' into tmp_path, reporting bytes in 4 steps; calls are recorded."""
    cache = tmp_path / "hub"
    calls = []

    def hf_hub_download(repo, filename, dry_run=False, tqdm_class=None, **kw):
        if dry_run:
            return SimpleNamespace(file_size=SIZE)
        calls.append((repo, filename))
        if filename.endswith(".pt"):  # like a Xet download: one bar fetches, then another puts the file together
            fetching, rebuilding = tqdm_class(total=SIZE), tqdm_class(total=SIZE)
            for bar in (fetching, rebuilding):
                for _ in range(4):
                    bar.update(SIZE // 4)
        else:
            bar = tqdm_class(total=SIZE, initial=0)
            for _ in range(4):
                bar.update(SIZE // 4)
            bar.close()
        put_in_cache(cache, repo, filename)
        return str(cache)

    original = hub.try_to_load_from_cache
    monkeypatch.setattr(hub, "hf_hub_download", hf_hub_download)
    monkeypatch.setattr(hub, "try_to_load_from_cache", lambda repo, f, cache_dir=None, **kw: original(
        repo, f, cache_dir=cache_dir or cache))
    monkeypatch.setattr(downloads, "cache_dir", lambda: cache)
    return SimpleNamespace(cache=cache, calls=calls)


def test_missing_and_size_on_disk(fake_hub):
    pack = downloads.PACKS["chatterbox"]
    assert downloads.missing(pack) == list(pack.files)
    put_in_cache(fake_hub.cache, pack.repo, "conds.pt")
    assert "conds.pt" not in downloads.missing(pack)
    assert downloads.size_on_disk(pack) == SIZE
    downloads.delete(pack)
    assert downloads.size_on_disk(pack) == 0 and len(downloads.missing(pack)) == len(pack.files)


def test_fetch_downloads_only_what_is_missing_and_reports_bytes(fake_hub):
    pack = downloads.PACKS["whisper"]
    put_in_cache(fake_hub.cache, pack.repo, "config.json")
    seen = []
    downloads.fetch(["whisper"], lambda done, total, name: seen.append((done, total)))
    assert [f for _, f in fake_hub.calls] == ["model.bin", "tokenizer.json", "vocabulary.txt"]
    total = 3 * SIZE
    assert all(t == total for _, t in seen) and seen[-1] == (total, total)
    dones = [d for d, _ in seen]
    assert dones == sorted(dones) and SIZE // 4 in dones  # moves within a file, never backwards
    assert downloads.missing(pack) == []


def test_progress_never_goes_back_with_two_bars_per_file(fake_hub):
    seen = []
    downloads.fetch(["kokoro"], lambda done, total, name: seen.append(done),
                    files={"kokoro": ["voices/bf_lily.pt", "voices/bf_emma.pt"]})
    assert seen == sorted(seen) and seen[-1] == 2 * SIZE and SIZE // 4 in seen


def test_progress_moves_while_a_xet_file_is_fetched(fake_hub, monkeypatch):
    seen = []

    def xet(repo, filename, dry_run=False, tqdm_class=None, **kw):
        if dry_run:
            return SimpleNamespace(file_size=SIZE)
        fetching, rebuilding = tqdm_class(total=SIZE), tqdm_class(total=SIZE)  # both open from the start
        for _ in range(4):
            fetching.update(SIZE // 4)
        seen.append("rebuilding starts")
        rebuilding.update(SIZE)
        put_in_cache(fake_hub.cache, repo, filename)

    monkeypatch.setattr(hub, "hf_hub_download", xet)
    downloads.fetch(["kokoro"], lambda done, total, name: seen.append(done), files={"kokoro": ["kokoro-v1_0.pth"]})
    assert seen[:seen.index("rebuilding starts")][-1] == SIZE  # the bar filled as the bytes came in


def test_cancel_stops_waiting_for_a_slow_file(fake_hub, monkeypatch):
    def slow(repo, filename, dry_run=False, tqdm_class=None, **kw):
        if dry_run:
            return SimpleNamespace(file_size=SIZE)
        time.sleep(5)  # a big file whose bars report from another thread, or not at all

    monkeypatch.setattr(hub, "hf_hub_download", slow)
    cancel = threading.Event()
    threading.Timer(0.3, cancel.set).start()
    start = time.monotonic()
    with pytest.raises(downloads.Cancelled):
        downloads.fetch(["chatterbox"], None, cancel)
    assert time.monotonic() - start < 2


def test_fetch_can_be_cancelled(fake_hub):
    cancel = threading.Event()

    def progress(done, total, name):
        if done >= 2 * SIZE:
            cancel.set()

    with pytest.raises(downloads.Cancelled):
        downloads.fetch(["chatterbox"], progress, cancel)
    assert len(fake_hub.calls) < len(downloads.PACKS["chatterbox"].files)


def test_human_sizes():
    assert [downloads.human(n) for n in (500, 340e6, 3.1e9)] == ["1 KB", "340 MB", "3.1 GB"]


@pytest.mark.real_download_step
def test_a_run_downloads_only_the_voices_it_uses(fake_hub):
    args = SimpleNamespace(engine="kokoro", voice="am_michael,af_heart",
                           cast={"enabled": True, "dialogue": None, "voices": {"Ann": "bf_emma"}})
    steps, logs = [], []
    voice = audiobook.LazyVoice(args, logs.append, lambda *step: steps.append(step))
    voice.download()
    got = {f for _, f in fake_hub.calls}
    assert got == {"config.json", "kokoro-v1_0.pth", "voices/am_michael.pt", "voices/af_heart.pt", "voices/bf_emma.pt"}
    assert steps[-1][0] == "download" and steps[-1][1] == steps[-1][2]
    assert "about 330 MB" in logs[0]
    fake_hub.calls.clear()
    voice.download()  # everything is here now
    assert fake_hub.calls == []
