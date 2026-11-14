"""Tests for the text side of audiobook.py: Markdown parsing, pauses and pronunciations. No TTS model needed."""
import threading
from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest
import soundfile as sf

import audiobook
import book_settings
from audiobook import apply_pronunciations, chapter_title, load_pronunciations, md_to_paragraphs, sentence_chunks

P, T, S = audiobook.PARAGRAPH_PAUSE, audiobook.TITLE_PAUSE, audiobook.SCENE_PAUSE


# ---- Markdown

def test_heading_gets_period_and_title_pause():
    assert md_to_paragraphs("# Chapter One\n\nIt was dark.") == [("Chapter One.", T), ("It was dark.", P)]


def test_heading_keeps_its_own_punctuation():
    assert md_to_paragraphs("## Why?")[0] == ("Why?", T)


def test_lines_in_a_paragraph_are_joined():
    assert md_to_paragraphs("One line\nand another.") == [("One line and another.", P)]


def test_formatting_is_removed_but_words_are_kept():
    md = "The **bold** and *quiet* [map](https://x.com) said `hi`."
    assert md_to_paragraphs(md) == [("The bold and quiet map said hi.", P)]


def test_code_images_html_and_comments_are_left_out():
    md = "Before.\n\n```\nprint('no')\n```\n\n![pic](a.jpg)\n\n<!-- note -->\n\n<b>After.</b>"
    assert md_to_paragraphs(md) == [("Before.", P), ("After.", P)]


def test_list_and_quote_markers_are_removed():
    assert md_to_paragraphs("- First.\n\n> Quoted.\n\n1. Numbered.") == [("First.", P), ("Quoted.", P), ("Numbered.", P)]


def test_custom_pauses_are_used():
    assert md_to_paragraphs("# H\n\nText.", paragraph_pause=0.3, title_pause=2.0) == [("H.", 2.0), ("Text.", 0.3)]


def test_test_chapter_parses():
    md = (Path(__file__).parent.parent / "test_chapters" / "01-arrival.md").read_text(encoding="utf-8")
    paragraphs = md_to_paragraphs(md)
    texts = [text for text, _ in paragraphs]
    assert texts[0] == "Chapter One: The Arrival."
    assert not any("print" in t or "http" in t or ".jpg" in t or "](" in t for t in texts)
    assert paragraphs[-2][1] == S  # the --- before the list
    assert texts[-1] == "The suitcase was heavy. The night was long."  # no blank line between items


# ---- scene breaks

def test_scene_break_lengthens_the_pause_before_it():
    for rule in ("---", "***", "* * *", "___"):
        assert md_to_paragraphs(f"End of scene.\n\n{rule}\n\nNew scene.") == [("End of scene.", S), ("New scene.", P)]


def test_scene_break_without_blank_lines_still_counts():
    assert md_to_paragraphs("End.\n---\nStart.") == [("End.", S), ("Start.", P)]


def test_scene_break_never_shortens_a_longer_pause():
    assert md_to_paragraphs("# Title\n\n---\n\nText.", title_pause=3.0)[0] == ("Title.", 3.0)


def test_scene_pause_can_be_changed():
    assert md_to_paragraphs("A.\n\n---\n\nB.", scene_pause=4.0)[0] == ("A.", 4.0)


def test_scene_break_at_the_start_is_leading_silence():
    assert md_to_paragraphs("---\n\nText.") == [("", S), ("Text.", P)]


# ---- [pause] tags

def test_pause_tag_on_its_own_line_adds_silence():
    assert md_to_paragraphs("One.\n\n[pause 3]\n\nTwo.") == [("One.", P + 3), ("Two.", P)]


def test_pause_tag_inside_a_paragraph_splits_it():
    assert md_to_paragraphs("Wait for it [pause 2s] now.") == [("Wait for it", 2.0), ("now.", P)]


def test_pause_tag_formats():
    for tag, seconds in (("[pause]", audiobook.DEFAULT_TAG_PAUSE), ("[pause 1.5]", 1.5), ("[Pause 2 s]", 2.0)):
        assert md_to_paragraphs(f"A. {tag} B.")[0] == ("A.", seconds)


def test_pause_tag_at_end_of_paragraph_comes_before_its_pause():
    assert md_to_paragraphs("The end. [pause 2]") == [("The end.", 2.0 + P)]


def test_pause_tag_in_heading():
    assert md_to_paragraphs("# Part One [pause 2]\n\nText.") == [("Part One.", 2.0 + T), ("Text.", P)]


def test_text_without_tags_is_unchanged():
    """Chapters without the new markup must parse exactly as before, so they aren't rendered again."""
    md = "# Title\n\nSome  text   with spaces.\n\nMore."
    assert md_to_paragraphs(md) == [("Title.", T), ("Some  text   with spaces.", P), ("More.", P)]


# ---- pronunciations

def write_rules(tmp_path, text):
    (tmp_path / audiobook.PRONUNCIATIONS_FILE).write_text(text, encoding="utf-8")
    return load_pronunciations(tmp_path)


def test_no_file_means_no_rules(tmp_path):
    assert load_pronunciations(tmp_path) == []


def test_rules_file_skips_comments_blank_and_bad_lines(tmp_path):
    rules = write_rules(tmp_path, "# comment\n\nSaoirse = Seer-sha\nno equals sign\n = nothing\nKai=Kye\n")
    assert rules == [("Saoirse", "Seer-sha"), ("Kai", "Kye")]


def test_pronunciation_replaces_whole_words_in_any_case():
    rules = [("Kai", "Kye")]
    paragraphs = [("Kai met KAI and kai at Kairo.", P)]
    assert apply_pronunciations(paragraphs, rules) == [("Kye met Kye and Kye at Kairo.", P)]


def test_longer_phrase_wins():
    rules = [("York", "Yawk"), ("New York", "Noo Yawk")]
    assert apply_pronunciations([("New York and York.", P)], rules) == [("Noo Yawk and Yawk.", P)]


def test_pronunciation_handles_punctuation_in_words():
    assert apply_pronunciations([("Dr. Who arrived.", P)], [("Dr.", "Doctor")]) == [("Doctor Who arrived.", P)]


def test_no_rules_returns_paragraphs_unchanged():
    paragraphs = [("Hello.", P)]
    assert apply_pronunciations(paragraphs, []) is paragraphs


# ---- other helpers

def test_chapter_title_falls_back_to_file_name():
    assert chapter_title("# The House\n\nText", Path("02-house.md")) == "The House"
    assert chapter_title("No heading here.", Path("02-house.md")) == "02-house"


def test_sentence_chunks_respect_limit():
    text = " ".join(f"Sentence number {i}." for i in range(50))
    chunks = sentence_chunks(text, limit=100)
    assert all(len(c) <= 100 for c in chunks)
    assert " ".join(chunks) == text


# ---- run(), with a fake voice

def fake_run(tmp_path, monkeypatch, chapters, rules=None, **overrides):
    """Run the whole pipeline with a silent fake voice; returns the texts it was asked to say."""
    folder = tmp_path / "book"
    folder.mkdir(exist_ok=True)
    for name, md in chapters.items():
        (folder / name).write_text(md, encoding="utf-8")
    if rules is not None:
        (folder / audiobook.PRONUNCIATIONS_FILE).write_text(rules, encoding="utf-8")
    said = []

    def synth(text):
        said.append(text)
        return audiobook.np.zeros(240, dtype=audiobook.np.float32)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audiobook, "load_engine", lambda args, **_: (24000, synth))
    monkeypatch.setattr(audiobook, "build_m4b", lambda chapters, wavs, args, progress=None: Path("out/book.m4b"))
    args = SimpleNamespace(chapters=str(folder), engine="kokoro", voice="am_michael", speed=1.0, ref=None,
                           paragraph_pause=P, title_pause=T, scene_pause=S, sample=False, title="Book",
                           author="Me", cover=None)
    for name, value in overrides.items():
        setattr(args, name, value)
    audiobook.run(args, log=lambda message: None)
    return said


def test_run_applies_pronunciations(tmp_path, monkeypatch):
    said = fake_run(tmp_path, monkeypatch, {"01.md": "# One\n\nKai waved."}, rules="Kai = Kye\n")
    assert said == ["One.", "Kye waved."]


def test_editing_pronunciations_re_renders_only_affected_chapters(tmp_path, monkeypatch):
    chapters = {"01.md": "Kai waved.", "02.md": "Nobody here."}
    fake_run(tmp_path, monkeypatch, chapters)
    said = fake_run(tmp_path, monkeypatch, chapters, rules="Kai = Kye\n")
    assert said == ["Kye waved."]


# ---- paragraph cache, redo and clean-up (phase 2)

def build_dir(tmp_path, voice="kokoro-am_michael"):
    return next((tmp_path / "build").glob("book-*")) / voice


def test_editing_one_paragraph_narrates_only_that_paragraph(tmp_path, monkeypatch):
    fake_run(tmp_path, monkeypatch, {"01.md": "First.\n\nSecond.\n\nThird."})
    said = fake_run(tmp_path, monkeypatch, {"01.md": "First.\n\nSecond, changed.\n\nThird."})
    assert said == ["Second, changed."]


def test_changing_a_pause_narrates_nothing(tmp_path, monkeypatch):
    chapters = {"01.md": "# One\n\nFirst.\n\nSecond."}
    fake_run(tmp_path, monkeypatch, chapters)
    assert fake_run(tmp_path, monkeypatch, chapters, paragraph_pause=1.5, title_pause=2.0) == []


def test_redo_narrates_the_chapter_again_and_only_that_chapter(tmp_path, monkeypatch):
    chapters = {"01.md": "One.", "02.md": "Two. [pause] Two.", "03.md": "Three."}
    fake_run(tmp_path, monkeypatch, chapters)
    # The repeated paragraph in chapter 2 is narrated once and reused.
    assert fake_run(tmp_path, monkeypatch, chapters, redo={2}) == ["Two."]


def test_redo_replaces_the_saved_paragraph(tmp_path, monkeypatch):
    chapters = {"01.md": "One."}
    fake_run(tmp_path, monkeypatch, chapters)
    fake_run(tmp_path, monkeypatch, chapters, redo={1})
    assert len(list((build_dir(tmp_path) / "paragraphs").glob("*.flac"))) == 1


def test_cancelled_chapter_keeps_finished_paragraphs(tmp_path, monkeypatch):
    import threading
    chapters = {"01.md": "First.\n\nSecond.\n\nThird."}
    cancel = threading.Event()
    real_synth = []

    def stop_after_two(args, **_):
        def synth(text):
            real_synth.append(text)
            if len(real_synth) == 2:
                cancel.set()
            return audiobook.np.zeros(240, dtype=audiobook.np.float32)
        return 24000, synth

    folder = tmp_path / "book"
    folder.mkdir()
    (folder / "01.md").write_text(chapters["01.md"])
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audiobook, "load_engine", stop_after_two)
    args = SimpleNamespace(chapters=str(folder), engine="kokoro", voice="am_michael", speed=1.0, ref=None,
                           paragraph_pause=P, title_pause=T, scene_pause=S, sample=False, title="Book",
                           author="Me", cover=None)
    try:
        audiobook.run(args, log=lambda message: None, cancel=cancel)
    except audiobook.Cancelled:
        pass
    assert fake_run(tmp_path, monkeypatch, chapters) == ["Third."]


def test_old_renders_are_cleaned_up(tmp_path, monkeypatch):
    fake_run(tmp_path, monkeypatch, {"01.md": "Old text.", "02.md": "Kept."})
    fake_run(tmp_path, monkeypatch, {"01.md": "New text.", "02.md": "Kept."})
    build = build_dir(tmp_path)
    assert len(list(build.glob("*.wav"))) == 2
    assert len(list((build / "paragraphs").glob("*.flac"))) == 2


def test_other_voices_are_not_cleaned_up(tmp_path, monkeypatch):
    chapters = {"01.md": "Text."}
    fake_run(tmp_path, monkeypatch, chapters, voice="bm_george")
    fake_run(tmp_path, monkeypatch, chapters)
    assert list(build_dir(tmp_path, "kokoro-bm_george").glob("*.wav"))


def test_two_books_with_the_same_chapters_do_not_share_renders(tmp_path, monkeypatch):
    for name in ("a", "b"):
        (tmp_path / name).mkdir()
        (tmp_path / name / "01.md").write_text("Same text.")
    assert audiobook.book_folder(tmp_path / "a") != audiobook.book_folder(tmp_path / "b")


def test_renders_from_the_old_build_folder_are_reused(tmp_path, monkeypatch):
    chapters = {"01.md": "Already narrated."}
    fake_run(tmp_path, monkeypatch, chapters)
    # Move the chapter to where earlier versions kept it, and drop the paragraph cache.
    build = build_dir(tmp_path)
    legacy = tmp_path / "build" / "kokoro-am_michael"
    legacy.mkdir()
    wav = next(build.glob("*.wav"))
    wav.replace(legacy / wav.name)
    for f in (build / "paragraphs").iterdir():
        f.unlink()
    assert fake_run(tmp_path, monkeypatch, chapters) == []
    assert (build / wav.name).exists() and not (legacy / wav.name).exists()


def test_sample_saves_paragraphs_for_the_full_build(tmp_path, monkeypatch):
    chapters = {"01.md": "# One\n\nOpening."}
    assert fake_run(tmp_path, monkeypatch, chapters, sample=True) == ["One.", "Opening."]
    assert fake_run(tmp_path, monkeypatch, chapters, sample=True) == ["One.", "Opening."]  # a new take each time
    assert fake_run(tmp_path, monkeypatch, chapters) == []


# ---- gentle mode

def test_rests_after_each_stretch_of_work():
    now, waits, log = [0.0], [], []
    rested = audiobook.with_rests(lambda text: text, log.append, work=300, rest=60, clock=lambda: now[0],
                                  wait=lambda seconds: waits.append(seconds) or False)
    assert rested("a") == "a" and waits == []
    now[0] = 299
    rested("b")
    assert waits == []
    now[0] = 300
    rested("c")
    assert waits == [60] and len(log) == 1
    now[0] = 500  # the clock restarts after a rest
    rested("d")
    assert waits == [60]


def test_rests_pass_the_character_voice_through():
    rested = audiobook.with_rests(lambda text, voice=None: (text, voice), work=300, clock=lambda: 0)
    assert rested("Hi", "bf_emma") == ("Hi", "bf_emma")


def test_cancelling_during_a_rest_stops_the_run():
    rested = audiobook.with_rests(lambda text: text, lambda message: None, work=0, clock=lambda: 0,
                                  wait=lambda seconds: True)
    try:
        rested("a")
    except audiobook.Cancelled:
        return
    raise AssertionError("expected Cancelled")


def test_gentle_run_rests_between_paragraphs(tmp_path, monkeypatch):
    rests = []
    monkeypatch.setattr(audiobook, "WORK_STRETCH", 0)
    monkeypatch.setattr(audiobook.time, "sleep", rests.append)
    monkeypatch.setattr(audiobook, "lower_priority", lambda: None)
    said = fake_run(tmp_path, monkeypatch, {"01.md": "First.\n\nSecond."}, gentle=True)
    assert said == ["First.", "Second."]
    assert rests == [audiobook.REST, audiobook.REST]


def test_gentle_mode_does_not_change_what_is_rendered(tmp_path, monkeypatch):
    monkeypatch.setattr(audiobook, "lower_priority", lambda: None)
    fake_run(tmp_path, monkeypatch, {"01.md": "First.\n\nSecond."})
    assert fake_run(tmp_path, monkeypatch, {"01.md": "First.\n\nSecond."}, gentle=True) == []


# ---- offline

class LocalEntryNotFoundError(Exception):
    """Stands in for huggingface_hub's error, which is matched by name."""


def test_a_voice_not_downloaded_gets_a_plain_message(monkeypatch):
    def synth(text, voice=None):
        try:
            raise ConnectionError("no wifi")
        except ConnectionError as e:
            raise LocalEntryNotFoundError("cannot find the requested files in the local cache") from e

    monkeypatch.setattr(audiobook, "load_engine", lambda args, **_: (24000, synth))
    voice = audiobook.LazyVoice(SimpleNamespace(engine="kokoro", voice="am_michael"))
    try:
        voice("Hello.", "am_eric")
    except audiobook.ModelNotDownloaded as e:
        assert str(e).startswith("The Kokoro voice am_eric hasn't been downloaded yet.")
    else:
        raise AssertionError("expected ModelNotDownloaded")


def test_other_errors_are_not_reworded(monkeypatch):
    def synth(text, voice=None):
        raise ValueError("bad text")

    monkeypatch.setattr(audiobook, "load_engine", lambda args, **_: (24000, synth))
    try:
        audiobook.LazyVoice(SimpleNamespace(engine="kokoro", voice="am_michael"))("Hello.")
    except ValueError:
        return
    raise AssertionError("expected ValueError")


# ---- which chapters are made (for the Redo buttons)

def test_made_chapters_follow_the_text_and_settings(tmp_path, monkeypatch):
    fake_run(tmp_path, monkeypatch, {"01.md": "First.", "02.md": "Second."})
    args = SimpleNamespace(chapters=str(tmp_path / "book"), engine="kokoro", voice="am_michael", speed=1.0, ref=None,
                           paragraph_pause=P, title_pause=T, scene_pause=S)
    assert audiobook.made_chapters(args) == {1, 2}
    (tmp_path / "book" / "03.md").write_text("Third, new.", encoding="utf-8")
    (tmp_path / "book" / "02.md").write_text("Second, edited.", encoding="utf-8")
    assert audiobook.made_chapters(args) == {1}
    args.speed = 1.1
    assert audiobook.made_chapters(args) == set()


def test_gentle_rests_are_reported_as_they_start_and_end():
    calls = []
    rested = audiobook.with_rests(lambda text: text, lambda message: None, work=0, clock=lambda: 0,
                                  wait=lambda seconds: calls.append("wait"), resting=calls.append)
    rested("Hi")
    assert calls == [True, "wait", False]


def test_a_cancelled_chapter_leaves_no_half_written_file(tmp_path):
    cancel = threading.Event()

    def synth(text):
        cancel.set()  # cancelled while the first paragraph narrates
        return np.full(2400, 0.1, dtype=np.float32)

    out = tmp_path / "ch" / "01.wav"
    with pytest.raises(audiobook.Cancelled):
        audiobook.render([("One.", 0.1), ("Two.", 0.1)], 24000, synth, out, cancel)
    assert list(out.parent.iterdir()) == []
    audiobook.render([("One.", 0.1), ("Two.", 0.1)], 24000, lambda text: np.full(2400, 0.1, dtype=np.float32), out)
    audio, sr = sf.read(out, dtype="float32")
    assert sr == 24000 and len(audio) == 2 * (2400 + 2400) and abs(audio[0] - 0.1) < 0.001


def test_knows_whether_a_voice_model_is_downloaded(tmp_path):
    assert not audiobook.model_downloaded("kokoro", tmp_path)
    (tmp_path / "models--hexgrad--Kokoro-82M" / "snapshots" / "abc").mkdir(parents=True)
    assert audiobook.model_downloaded("kokoro", tmp_path)


def test_bom_does_not_hide_the_chapter_title(tmp_path):
    f = tmp_path / "01.md"
    f.write_bytes(b"\xef\xbb\xbf# The Storm\n\nIt rained.\n")
    assert audiobook.chapter_title(book_settings.read_text(f), f) == "The Storm"
