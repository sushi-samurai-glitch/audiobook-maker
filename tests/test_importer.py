"""Tests for importer.py: turning EPUB, Word and PDF files into chapter .md files."""
import shutil
from pathlib import Path

import pytest

import audiobook
import importer

FIXTURES = Path(__file__).parent / "fixtures"


def imported(tmp_path, name):
    source = tmp_path / name
    shutil.copy(FIXTURES / name, source)
    return importer.import_book(source, log=lambda m: None)


def test_epub_chapters_title_author_and_cover(tmp_path):
    folder, book = imported(tmp_path, "sample.epub")
    assert (book.title, book.author) == ("The Gate", "A. Writer")
    files = sorted(folder.glob("*.md"))
    # The contents page and the short title page are skipped.
    assert [f.name for f in files] == ["01 - Chapter One The Gate.md", "02 - Chapter Two The Road.md"]
    text = files[0].read_text(encoding="utf-8")
    assert text.startswith("# Chapter One: The Gate\n\n“You’re late,” Mara said.")
    assert "said *nothing*." in text and "\n\n---\n\n" in text  # italics and the scene break survive
    assert (folder / "cover.png").exists()


def test_word_chapters_split_at_headings(tmp_path):
    folder, book = imported(tmp_path, "sample.docx")
    assert (book.title, book.author) == ("The Gate", "A. Writer")
    files = sorted(folder.glob("*.md"))
    assert len(files) == 2
    text = files[0].read_text(encoding="utf-8")
    assert text.startswith("# Chapter One: The Gate\n\n“You’re late,” *Mara* said.")
    assert text.count("\n\n") == 2  # heading, then two paragraphs


def test_pdf_chapters_without_headers_or_page_numbers(tmp_path):
    folder, book = imported(tmp_path, "sample.pdf")
    files = sorted(folder.glob("*.md"))
    assert len(files) == 4 and book.title == "The Gate"
    text = files[0].read_text(encoding="utf-8")
    assert "THE GATE" not in text
    paragraphs = text.split("\n\n")[1:]
    assert len(paragraphs) == 4 and paragraphs[0].endswith("down to the valley.")


def test_pdf_laid_out_like_a_novel(tmp_path):
    folder, book = imported(tmp_path, "novel.pdf")
    files = sorted(folder.glob("*.md"))
    assert [f.name for f in files] == ["01 - CHAPTER ONE.md", "02 - CHAPTER TWO.md", "03 - CHAPTER THREE.md"]
    paragraphs = files[0].read_text(encoding="utf-8").split("\n\n")[1:]
    assert len(paragraphs) == 12  # indented paragraphs are found again
    assert paragraphs[0].endswith("line of the hills.") and paragraphs[1].startswith("“You’re late,”")
    assert not any("The Arrival" in p for p in paragraphs)  # the running header is gone


def test_imported_folder_works_in_the_app(tmp_path):
    folder, _ = imported(tmp_path, "sample.epub")
    paragraphs = audiobook.md_to_paragraphs((sorted(folder.glob("*.md"))[0]).read_text(encoding="utf-8"))
    assert paragraphs[0] == ("Chapter One: The Gate.", audiobook.TITLE_PAUSE)
    assert any(pause == audiobook.SCENE_PAUSE for _, pause in paragraphs)


def test_importing_twice_never_overwrites(tmp_path):
    first, _ = imported(tmp_path, "sample.docx")
    second, _ = importer.import_book(tmp_path / "sample.docx", log=lambda m: None)
    assert first != second and second.name == "sample chapters (2)"


def test_unknown_format_is_refused(tmp_path):
    (tmp_path / "book.txt").write_text("hello")
    with pytest.raises(ValueError, match="EPUB, Word"):
        importer.import_book(tmp_path / "book.txt")


def test_hyphenated_line_ends_are_joined():
    lines = [[(40, 500, "The rain had not stopped since the morn-"), (40, 486, "ing, and the road was wet.")]]
    assert importer.pdf_paragraphs(lines) == ["The rain had not stopped since the morning, and the road was wet."]


def test_plain_text_chapter_lines():
    chapters = importer.split_on_chapter_lines(["Title page", "Chapter 1", "Text.", "Prologue? no", "Chapter 2: Home",
                                                "More."], "Book")
    assert [t for t, _ in chapters] == ["Book", "Chapter 1", "Chapter 2: Home"]
