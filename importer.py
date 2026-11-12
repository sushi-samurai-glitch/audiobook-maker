"""Import an EPUB, Word (.docx) or PDF file as a folder of chapter .md files the app can read.

EPUB and Word are read with the standard library only. PDF needs pypdf (uv pip install pypdf)."""
import posixpath
import re
import zipfile
from collections import Counter
from itertools import pairwise
from html.parser import HTMLParser
from pathlib import Path
from xml.etree import ElementTree

import desktop

FORMATS = {".epub": "EPUB", ".docx": "Word", ".pdf": "PDF"}
# A line that starts a chapter in plain text (PDF, or Word without heading styles).
CHAPTER_LINE = re.compile(r"^\s*(chapter|part|book|prologue|epilogue|interlude|afterword|foreword|introduction)\b"
                          r"[\w\s.:,'’—–-]{0,70}$", re.I)
MIN_CHAPTER_WORDS = 40  # shorter sections (title page, copyright, contents) are skipped


class Book:
    def __init__(self, title="", author="", chapters=None, cover=None):
        self.title, self.author = title, author
        self.chapters = chapters or []  # [(title, markdown body)]
        self.cover = cover  # (file extension, bytes) or None


def import_book(path, log=print):
    """Convert path and write the chapters next to it in a new folder "<name> chapters".

    Returns (folder, book). The folder never overwrites an existing one."""
    path = Path(path)
    kind = path.suffix.lower()
    if kind not in FORMATS:
        raise ValueError(f"Can't import {path.suffix} files. Choose an EPUB, Word (.docx) or PDF file.")
    book = {".epub": read_epub, ".docx": read_docx, ".pdf": read_pdf}[kind](path)
    book.chapters = [(title, body) for title, body in book.chapters if len(body.split()) >= MIN_CHAPTER_WORDS]
    if not book.chapters:
        raise ValueError(f"Couldn't find any chapter text in {path.name}.")
    folder = path.with_name(f"{path.stem} chapters")
    n = 2
    while folder.exists():
        folder = path.with_name(f"{path.stem} chapters ({n})")
        n += 1
    folder.mkdir()
    width = max(2, len(str(len(book.chapters))))
    for i, (title, body) in enumerate(book.chapters, 1):
        name = re.sub(r'[\\/:*?"<>|]+', "", title).strip().rstrip(".")[:60] or "Chapter"
        (folder / f"{i:0{width}d} - {name}.md").write_text(f"# {title}\n\n{body.strip()}\n", encoding="utf-8")
    if book.cover:
        ext, data = book.cover
        (folder / f"cover{ext}").write_bytes(data)
    log(f"Imported {len(book.chapters)} chapters from {path.name} into {folder.name}")
    return folder, book


def tidy(text):
    """Collapse runs of spaces and blank lines, and remove spaces before line ends."""
    text = re.sub(r"[ \t ]+", " ", text)
    text = re.sub(r" *\n *", "\n", text)
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def split_on_chapter_lines(paragraphs, fallback_title):
    """[(title, body)] from a list of paragraphs, starting a new chapter at each CHAPTER_LINE paragraph."""
    chapters, title, body = [], None, []
    for para in paragraphs:
        if CHAPTER_LINE.match(para) and len(para) < 80:
            if body or title:
                chapters.append((title or fallback_title, "\n\n".join(body)))
            title, body = para.strip(), []
        else:
            body.append(para)
    if body:
        chapters.append((title or fallback_title, "\n\n".join(body)))
    return chapters


# ---- EPUB

class _HtmlToMarkdown(HTMLParser):
    """Paragraphs, headings, italics, bold and scene breaks from one EPUB chapter's XHTML."""

    BLOCKS = {"p", "div", "li", "blockquote", "h1", "h2", "h3", "h4", "h5", "h6", "section", "tr"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.headings, self.skip = [], [], 0
        self.heading = None

    def handle_starttag(self, tag, attrs):
        if tag in ("script", "style", "head", "title"):
            self.skip += 1
        elif tag in self.BLOCKS:
            self.out.append("\n\n")
            if tag[0] == "h" and tag[1:].isdigit():
                self.heading = len(self.out)
        elif tag == "br":
            self.out.append("\n")
        elif tag == "hr":
            self.out.append("\n\n---\n\n")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag in ("strong", "b"):
            self.out.append("**")

    def handle_endtag(self, tag):
        if tag in ("script", "style", "head", "title"):
            self.skip = max(0, self.skip - 1)
        elif tag in self.BLOCKS:
            if self.heading is not None and tag[0] == "h" and tag[1:].isdigit():
                text = tidy("".join(self.out[self.heading:]).replace("*", "")).replace("\n", " ")
                del self.out[self.heading:]
                if text:
                    self.headings.append(text)
                    if len(self.headings) > 1:  # later headings stay in the text as section titles
                        self.out.append(f"\n\n{text}\n\n")
                self.heading = None
            self.out.append("\n\n")
        elif tag in ("em", "i"):
            self.out.append("*")
        elif tag in ("strong", "b"):
            self.out.append("**")

    def handle_data(self, data):
        if not self.skip:
            self.out.append(data.replace("\n", " "))

    def markdown(self):
        text = tidy("".join(self.out))
        text = re.sub(r"\*\*\s*\*\*|(?<!\*)\*\s*\*(?!\*)", "", text)  # empty emphasis left by markup
        return text


def read_epub(path):
    with zipfile.ZipFile(path) as z:
        container = ElementTree.fromstring(z.read("META-INF/container.xml"))
        opf_path = next(e.get("full-path") for e in container.iter() if e.tag.endswith("rootfile"))
        opf = ElementTree.fromstring(z.read(opf_path))
        base = posixpath.dirname(opf_path)

        def meta(name):
            element = next((e for e in opf.iter() if e.tag.endswith("}" + name)), None)
            return (element.text or "").strip() if element is not None else ""

        manifest = {e.get("id"): e for e in opf.iter() if e.tag.endswith("item")}
        spine = [e.get("idref") for e in opf.iter() if e.tag.endswith("itemref") and e.get("linear") != "no"]
        chapters = []
        for idref in spine:
            item = manifest.get(idref)
            if item is None or "html" not in (item.get("media-type") or ""):
                continue
            if "nav" in (item.get("properties") or ""):
                continue  # the table of contents
            parser = _HtmlToMarkdown()
            parser.feed(z.read(posixpath.normpath(posixpath.join(base, item.get("href")))).decode("utf-8", "replace"))
            body = parser.markdown()
            title = parser.headings[0] if parser.headings else f"Chapter {len(chapters) + 1}"
            chapters.append((title, body))

        cover = None
        cover_id = next((e.get("content") for e in opf.iter() if e.tag.endswith("meta") and e.get("name") == "cover"), None)
        cover_item = manifest.get(cover_id)  # (an Element without children is falsy, so no "or" here)
        if cover_item is None:
            cover_item = next((e for e in manifest.values() if "cover-image" in (e.get("properties") or "")), None)
        if cover_item is not None and (cover_item.get("media-type") or "").startswith("image/"):
            href = posixpath.normpath(posixpath.join(base, cover_item.get("href")))
            ext = ".png" if "png" in cover_item.get("media-type") else ".jpg"
            cover = (ext, z.read(href))
    return Book(meta("title") or path.stem, meta("creator"), chapters, cover)


# ---- Word

W = "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}"


def read_docx(path):
    with zipfile.ZipFile(path) as z:
        document = ElementTree.fromstring(z.read("word/document.xml"))
        core = ElementTree.fromstring(z.read("docProps/core.xml")) if "docProps/core.xml" in z.namelist() else None
    paragraphs, headed = [], False  # [(text, is_heading)]
    for p in document.iter(W + "p"):
        style = p.find(f"{W}pPr/{W}pStyle")
        style = (style.get(W + "val") if style is not None else "").lower()
        parts = []
        for run in p.iter(W + "r"):
            text = "".join((t.text or "") if t.tag == W + "t" else "\n" if t.tag == W + "br" and
                           t.get(W + "type") != "page" else "\t" if t.tag == W + "tab" else ""
                           for t in run)
            if not text:
                continue
            props = run.find(W + "rPr")
            italic = props is not None and props.find(W + "i") is not None and \
                props.find(W + "i").get(W + "val") not in ("0", "false")
            parts.append(f"*{text.strip()}*" + (" " if text.endswith(" ") else "") if italic and text.strip() else text)
        text = tidy("".join(parts))
        if not text:
            continue
        heading = style in ("title", "heading1", "heading 1") or style.startswith("heading1")
        headed |= heading
        paragraphs.append((text, heading))

    title = author = ""
    if core is not None:
        for e in core.iter():
            if e.tag.endswith("}title") and e.text:
                title = e.text.strip()
            elif e.tag.endswith("}creator") and e.text:
                author = e.text.strip()
    if headed:
        chapters, current, body = [], None, []
        for text, heading in paragraphs:
            if heading:
                if current or body:
                    chapters.append((current or path.stem, "\n\n".join(body)))
                current, body = text, []
            else:
                body.append(text)
        if body:
            chapters.append((current or path.stem, "\n\n".join(body)))
    else:
        chapters = split_on_chapter_lines([text for text, _ in paragraphs], path.stem)
    return Book(title or path.stem, author, chapters)


# ---- PDF

def page_lines(page):
    """[(x, y, text)] for each line on a PDF page, top to bottom, from the text's positions on the page."""
    pieces = []

    def visit(text, cm, tm, font, size):
        if text.strip():
            # Position in page space: the text matrix, moved by the current transformation matrix.
            x = tm[4] * cm[0] + tm[5] * cm[2] + cm[4]
            y = tm[4] * cm[1] + tm[5] * cm[3] + cm[5]
            pieces.append((round(y, 1), x, text))

    page.extract_text(visitor_text=visit)
    rows = {}
    for y, x, text in pieces:
        row = next((key for key in rows if abs(key - y) < 2), y)
        rows.setdefault(row, []).append((x, text))
    lines = []
    for y in sorted(rows, reverse=True):
        parts = sorted(rows[y])
        text = "".join(t for _, t in parts).replace("\n", " ")
        if text.strip():
            lines.append((parts[0][0], y, text.strip()))
    return lines


def pdf_paragraphs(pages):
    """Rejoin a PDF's lines into paragraphs. pages is a list of [(x, y, text)] lines per page.

    Page numbers and running headers or footers are dropped, hyphenation at line ends is undone, and a new
    paragraph starts at a bigger gap between lines, an indented line, or after a short line ending a sentence."""
    # Running headers and footers: the same short line as the first or last line of at least half the pages.
    counts = Counter(text for page in pages for text in {t for _, _, t in page[:1] + page[-1:]})
    repeated = {t for t, n in counts.items() if len(pages) >= 4 and n >= len(pages) * 0.5 and len(t) < 80}
    gaps, lefts, widths = [], [], []
    for page in pages:
        for (x1, y1, t1), (x2, y2, t2) in pairwise(page):
            gaps.append(round(y1 - y2, 1))
        lefts += [round(x) for x, _, _ in page]
        widths += [len(t) for _, _, t in page]
    spacing = Counter(gaps).most_common(1)[0][0] if gaps else 0  # the usual distance between two lines
    margin = Counter(lefts).most_common(1)[0][0] if lefts else 0  # the usual left edge
    full = sorted(widths)[int(len(widths) * 0.8)] if widths else 80
    paragraphs, current = [], ""

    def end():
        nonlocal current
        if current:
            paragraphs.append(current)
        current = ""

    for page in pages:
        previous_y = None
        for x, y, text in page:
            if re.fullmatch(r"(page\s*)?\d{1,4}|[ivxlc]{1,6}", text, re.I) or text in repeated:
                continue
            gap = previous_y - y if previous_y is not None else 0
            previous_y = y
            if spacing and gap > spacing * 1.4 or x > margin + 6:
                end()  # a blank line's worth of space, or an indent
            if CHAPTER_LINE.match(text):
                end()
                paragraphs.append(text)
                continue
            if current.endswith("-") and text[:1].islower():
                current = current[:-1] + text
            else:
                current = f"{current} {text}".strip()
            if re.search(r"[.!?”\"’]$", text) and len(text) < full * 0.85:
                end()  # a short last line of a paragraph
    end()
    return [tidy(p) for p in paragraphs]


def read_pdf(path):
    try:
        from pypdf import PdfReader
    except ImportError:
        raise ValueError(f"Importing PDFs needs pypdf. {desktop.install_hint('pypdf')}") from None
    reader = PdfReader(str(path))
    pages = [page_lines(page) for page in reader.pages]
    if not any(pages):
        raise ValueError(f"{path.name} has no text to read. It may be scanned pages, which need OCR first.")
    info = reader.metadata or {}
    chapters = split_on_chapter_lines(pdf_paragraphs(pages), path.stem)
    return Book((info.get("/Title") or "").strip() or path.stem, (info.get("/Author") or "").strip(), chapters)
