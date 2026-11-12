"""Tests for paths.py: which folders the app works in."""
from pathlib import Path

import pytest

import paths


@pytest.fixture(autouse=True)
def restore(monkeypatch):
    monkeypatch.setattr(paths, "OUT", paths.OUT)
    monkeypatch.chdir(Path.cwd())


def test_an_existing_project_folder_keeps_its_files(tmp_path):
    (tmp_path / "app_state.json").write_text("{}")
    assert paths.configure(tmp_path) == tmp_path.resolve()
    assert Path.cwd() == tmp_path.resolve() and paths.OUT == Path("out")


def test_a_fresh_copy_uses_the_usual_places(tmp_path, monkeypatch):
    import platformdirs
    monkeypatch.setattr(platformdirs, "user_data_dir", lambda name, appauthor=None: str(tmp_path / "data" / name))
    monkeypatch.setattr(platformdirs, "user_music_dir", lambda: str(tmp_path / "Music"))
    project = tmp_path / "app"
    project.mkdir()
    assert paths.configure(project) == tmp_path / "data" / "Audiobook Maker"
    assert paths.OUT == tmp_path / "Music" / "Audiobook Maker"
    assert not (project / "out").exists()


def test_a_big_log_is_started_afresh(tmp_path, monkeypatch):
    monkeypatch.setattr(paths, "LOG_LIMIT", 10)
    log = tmp_path / "app.log"
    log.write_text("short")
    paths.rotate_log(log)
    assert log.read_text() == "short"
    log.write_text("x" * 20)
    paths.rotate_log(log)
    assert not log.exists() and (tmp_path / "app.log.1").read_text() == "x" * 20
    paths.rotate_log(tmp_path / "missing.log")  # no log yet: nothing to do
