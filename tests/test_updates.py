import time

import pytest

import book_settings
import updates


@pytest.fixture(autouse=True)
def state(monkeypatch, tmp_path):
    monkeypatch.setattr(book_settings, "APP_STATE", tmp_path / "app_state.json")
    monkeypatch.setattr(updates.version, "VERSION", "0.9.0")


def release(tag, draft=False):
    return {"tag_name": tag, "draft": draft, "html_url": f"https://github.com/x/y/releases/tag/{tag}"}


@pytest.mark.parametrize("tag, expected", [("v0.9.1", True), ("0.10.0", True), ("v1.0", True), ("v0.9.0", False),
                                           ("v0.9", False), ("v0.8.9", False), ("nightly", False)])
def test_newer_compares_versions_by_number(tag, expected):
    assert updates.newer(tag) is expected


def test_latest_skips_drafts_and_counts_betas():
    releases = [release("v0.9.1"), release("v0.12.0", draft=True), release("v0.10.0-beta"), release("notes")]
    assert updates.latest(releases) == ("0.10.0-beta", "https://github.com/x/y/releases/tag/v0.10.0-beta")
    assert updates.latest([]) is None


def test_check_remembers_a_newer_version():
    assert updates.check(lambda: [release("v0.9.2")])[0] == "0.9.2"
    assert updates.known()[0] == "0.9.2"
    assert not updates.due() and not updates.failed()
    assert updates.last_checked() == "today"


def test_check_says_nothing_when_up_to_date():
    assert updates.check(lambda: [release("v0.9.0")]) is None
    assert updates.known() is None


def test_a_failed_check_is_quiet_and_waits_a_day():
    def offline():
        raise OSError("no internet")

    assert updates.check(offline) is None
    assert updates.failed() and not updates.due()
    assert updates.check(lambda: {"message": "rate limited"}) is None  # GitHub's error reply isn't a list


def test_turning_it_off_stops_the_daily_check():
    assert updates.due()
    updates.remember_enabled(False)
    assert not updates.enabled() and not updates.due()


def test_due_again_after_a_day():
    updates.check(lambda: [])
    assert updates.due(now=time.time() + updates.DAY + 1)
    assert updates.last_checked(now=time.time() + 3 * updates.DAY) == "3 days ago"


def test_a_found_version_stops_showing_once_installed(monkeypatch):
    updates.check(lambda: [release("v0.9.2")])
    monkeypatch.setattr(updates.version, "VERSION", "0.9.2")
    assert updates.known() is None
