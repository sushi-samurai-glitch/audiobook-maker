"""Rebuild the sample EPUB, Word and PDF files used by test_importer.py.

Needs reportlab and python-docx (uv pip install --python .venv/bin/python reportlab python-docx). Run from the
project folder: .venv/bin/python tests/fixtures/make_fixtures.py"""
import zipfile
from pathlib import Path

HERE = Path(__file__).parent
CHAPTERS = [
    ("Chapter One: The Gate", ["“You’re late,” Mara said. The rain had not stopped since morning, and the road "
                               "behind her was a river of brown water that ran all the way down to the valley.",
                               "Kai shrugged and said nothing. He had walked the whole night to get here, and his boots "
                               "were full of mud. Somewhere behind the wall a bell was ringing, slow and steady."]),
    ("Chapter Two: The Road", ["The road ran east through the hills, past farms that had been empty for years. "
                               "Nobody travelled it any more, not since the bridge went down in the spring floods.",
                               "They walked until noon without speaking, then stopped to eat under an old oak that "
                               "leaned over the ditch like a tired man resting on a stick."]),
]
COVER = bytes.fromhex("89504e470d0a1a0a0000000d49484452000000080000000808020000004b6d29dc000000144944"
                      "4154789c633c51a1c1800d3061151db412001e270178061683ca0000000049454e44ae426082")


def epub():
    opf = """<?xml version="1.0"?><package xmlns="http://www.idpf.org/2007/opf" version="3.0">
<metadata xmlns:dc="http://purl.org/dc/elements/1.1/"><dc:title>The Gate</dc:title><dc:creator>A. Writer</dc:creator>
<meta name="cover" content="cover"/></metadata><manifest>
<item id="nav" href="nav.xhtml" media-type="application/xhtml+xml" properties="nav"/>
<item id="title" href="title.xhtml" media-type="application/xhtml+xml"/>
<item id="c1" href="text/c1.xhtml" media-type="application/xhtml+xml"/>
<item id="c2" href="text/c2.xhtml" media-type="application/xhtml+xml"/>
<item id="cover" href="images/cover.png" media-type="image/png"/></manifest>
<spine><itemref idref="nav"/><itemref idref="title"/><itemref idref="c1"/><itemref idref="c2"/></spine></package>"""
    with zipfile.ZipFile(HERE / "sample.epub", "w") as z:
        z.writestr("mimetype", "application/epub+zip")
        z.writestr("META-INF/container.xml", '<?xml version="1.0"?><container xmlns="urn:oasis:names:tc:opendocument:'
                   'xmlns:container" version="1.0"><rootfiles><rootfile full-path="OEBPS/content.opf" '
                   'media-type="application/oebps-package+xml"/></rootfiles></container>')
        z.writestr("OEBPS/content.opf", opf)
        z.writestr("OEBPS/nav.xhtml", "<html><body><nav><ol><li>Chapter One</li></ol></nav></body></html>")
        z.writestr("OEBPS/title.xhtml", "<html><body><h1>The Gate</h1><p>A. Writer</p></body></html>")
        for i, (title, paras) in enumerate(CHAPTERS, 1):
            body = "".join(f"<p>{p}</p>" for p in paras)
            if i == 1:
                body = body.replace("nothing", "<em>nothing</em>") + "<hr/><p>" + paras[0] + "</p>"
            z.writestr(f"OEBPS/text/c{i}.xhtml", f"<html><head><title>x</title><style>p{{}}</style></head>"
                                                 f"<body><h2>{title}</h2>{body}</body></html>")
        z.writestr("OEBPS/images/cover.png", COVER)


def docx():
    import docx

    d = docx.Document()
    d.core_properties.title, d.core_properties.author = "The Gate", "A. Writer"
    d.add_paragraph("The Gate", style="Title")
    for title, paras in CHAPTERS:
        d.add_heading(title, level=1)
        for p in paras:
            para = d.add_paragraph()
            first, _, rest = p.partition("Mara")
            para.add_run(first)
            if rest:
                para.add_run("Mara").italic = True
                para.add_run(rest)
    d.save(HERE / "sample.docx")


def pdf():
    from reportlab.lib.pagesizes import A5
    from reportlab.pdfgen import canvas

    c = canvas.Canvas(str(HERE / "sample.pdf"), pagesize=A5)
    c.setTitle("The Gate")
    c.setAuthor("A. Writer")
    page = 0

    def new_page():
        nonlocal page, y
        if page:
            c.showPage()
        page += 1
        c.setFont("Helvetica", 8)
        c.drawString(40, 570, "THE GATE")  # running header
        c.drawString(200, 20, str(page))  # page number
        c.setFont("Helvetica", 10)
        y = 540

    y = 0
    new_page()
    import textwrap
    for title, paras in CHAPTERS * 2:  # four chapters, so the header repeats on enough pages
        if y < 200:
            new_page()
        c.setFont("Helvetica-Bold", 13)
        c.drawString(40, y, title)
        c.setFont("Helvetica", 10)
        y -= 28
        for p in paras * 2:
            lines = textwrap.wrap(p, 58)
            lines[1] = lines[1] + "-" if False else lines[1]
            for line in lines:
                if y < 50:
                    new_page()
                c.drawString(40, y, line)
                y -= 14
            y -= 8
        new_page()
    c.save()


def novel():
    """A PDF laid out like a printed novel: indented, justified paragraphs, a running header and page numbers."""
    from reportlab.lib.pagesizes import A5
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.platypus import PageBreak, Paragraph, SimpleDocTemplate

    body = ParagraphStyle("b", fontName="Times-Roman", fontSize=11, leading=14, firstLineIndent=18, alignment=4)
    head = ParagraphStyle("h", fontName="Times-Bold", fontSize=16, leading=22, spaceAfter=18, alignment=1)
    paras = ["The train pulled into the station just after midnight. Mara stepped onto the platform, her breath "
             "clouding in the cold air. She checked the map her brother had sent her, then folded it away and "
             "looked up at the long dark line of the hills.",
             "“You’re late,” said a voice behind her. She turned, and for a long moment neither of them spoke. The "
             "station clock ticked above them, loud in the empty hall, and somewhere a door banged in the wind.",
             "“Sorry,” she said at last. “The trains were all delayed by the flooding further down the valley.”"]
    story = []
    for n in ("ONE", "TWO", "THREE"):
        story += [Paragraph(f"CHAPTER {n}", head)] + [Paragraph(p, body) for p in paras * 4] + [PageBreak()]

    def decorate(c, doc):
        c.setFont("Times-Italic", 8)
        c.drawCentredString(A5[0] / 2, A5[1] - 30, "The Arrival")
        c.drawCentredString(A5[0] / 2, 25, str(doc.page))

    SimpleDocTemplate(str(HERE / "novel.pdf"), pagesize=A5, title="The Arrival", author="A. Writer").build(
        story, onFirstPage=decorate, onLaterPages=decorate)


if __name__ == "__main__":
    epub()
    docx()
    pdf()
    novel()
