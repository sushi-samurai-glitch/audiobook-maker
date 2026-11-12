"""Shared test setup: no test downloads a voice model."""
import pytest

import audiobook


@pytest.fixture(autouse=True)
def no_downloads(monkeypatch, request):
    if "real_download_step" not in request.keywords:
        monkeypatch.setattr(audiobook.LazyVoice, "download", lambda self: None)


@pytest.fixture(autouse=True)
def no_update_check(monkeypatch):
    """No test asks GitHub for new versions; tests of updates.py pass their own fake replies."""
    import updates

    def offline(timeout=5):
        raise OSError("tests don't go online")

    monkeypatch.setattr(updates, "fetch", offline)
