"""Checking GitHub for a newer version of the app.

Once a day at most, and only while the "Check for updates" setting is on, the app asks GitHub for the list of
releases. Nothing is sent but the request itself (no ID, no book details), and nothing is downloaded or installed:
the app only says that a new version is out and links to its page."""
import json
import re
import time
import urllib.request

import book_settings
import version

REPO = "sushi-samurai-glitch/audiobook-maker"
RELEASES_API = f"https://api.github.com/repos/{REPO}/releases?per_page=20"
RELEASES_PAGE = f"https://github.com/{REPO}/releases"
DAY = 24 * 60 * 60


def parse(tag):
    """'v1.2.3', '1.2' or 'v0.10.0-beta' as a comparable tuple, e.g. (1, 2, 3); None if it isn't a version."""
    match = re.match(r"v?(\d+(?:\.\d+)*)", tag.strip())
    return tuple(int(n) for n in match.group(1).split(".")) if match else None


def newer(tag, current=None):
    """Whether tag is a later version than current (this app's version unless given)."""
    found, have = parse(tag), parse(current or version.VERSION)
    if not found or not have:
        return False
    width = max(len(found), len(have))
    return found + (0,) * (width - len(found)) > have + (0,) * (width - len(have))


def latest(releases):
    """The newest published release in GitHub's list, as (version, page URL), or None. Drafts are skipped; beta
    releases count, because the first public versions are betas."""
    best = None
    for release in releases:
        if release.get("draft") or not parse(release.get("tag_name", "")):
            continue
        if best is None or newer(release["tag_name"], best["tag_name"]):
            best = release
    if best is None:
        return None
    return best["tag_name"].lstrip("v"), best.get("html_url") or RELEASES_PAGE


def fetch(timeout=5):
    """Ask GitHub for the releases. Raises OSError (or ValueError for a garbled reply) when it can't be reached."""
    request = urllib.request.Request(RELEASES_API, headers={"Accept": "application/vnd.github+json",
                                                            "User-Agent": f"AudiobookMaker/{version.VERSION}"})
    with urllib.request.urlopen(request, timeout=timeout) as reply:
        return json.loads(reply.read().decode("utf-8"))


def enabled():
    """Whether the app may check for updates; on unless turned off in Settings."""
    return book_settings.app_state().get("check_updates") is not False


def remember_enabled(on):
    book_settings.update_state(check_updates=bool(on))


def due(now=None):
    last = book_settings.app_state().get("update_checked", 0)
    return enabled() and (now or time.time()) - (last if isinstance(last, (int, float)) else 0) >= DAY


def check(get=fetch):
    """(version, url) when a newer version is out, else None. Records the time so the app asks once a day.
    Network and parsing problems are swallowed: a failed check just says nothing."""
    try:
        found = latest(get())
    except (OSError, ValueError, TypeError, AttributeError):
        book_settings.update_state(update_checked=time.time(), update_failed=True)
        return None
    book_settings.update_state(update_checked=time.time(), update_failed=False,
                               update_available=list(found) if found and newer(found[0]) else None)
    return found if found and newer(found[0]) else None


def failed():
    """Whether the last check couldn't reach GitHub."""
    return book_settings.app_state().get("update_failed") is True


def last_checked(now=None):
    """When the last check was, in words ("today", "yesterday", "3 days ago"), or None if never."""
    last = book_settings.app_state().get("update_checked")
    if not isinstance(last, (int, float)) or last <= 0:
        return None
    days = int(((now or time.time()) - last) // DAY)
    return "today" if days <= 0 else "yesterday" if days == 1 else f"{days} days ago"


def known():
    """The newer version found by the last check, as (version, url), if it's still newer than this one."""
    found = book_settings.app_state().get("update_available")
    if isinstance(found, list) and len(found) == 2 and newer(str(found[0])):
        return str(found[0]), str(found[1])
    return None
