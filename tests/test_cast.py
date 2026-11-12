"""Tests for character voices: finding who speaks, and narrating each line in the right voice."""
from pathlib import Path
from types import SimpleNamespace

import numpy as np

import audiobook
import cast

KNOWN = {"Torvan", "Wis", "Karos"}


def test_speech_tag_after_the_quote():
    assert cast.split("“Right,” Torvan said, at his elbow.") == [("Right.", "Torvan"), ("Torvan said, at his elbow.", None)]


def test_verb_before_the_name():
    assert cast.split("“Yes,” said Mara.")[0] == ("Yes.", "Mara")


def test_speech_tag_before_the_quote():
    assert cast.split("Wis said, “Not enough.”") == [("Wis said,", None), ("Not enough.", "Wis")]


def test_straight_quotes_work_too():
    assert cast.split('"Late," Mara said.')[0] == ("Late.", "Mara")


def test_one_speaker_per_paragraph():
    segments = cast.split("“Four minutes,” Torvan said. “I counted.”")
    assert segments[0] == ("Four minutes.", "Torvan") and segments[-1] == ("I counted.", "Torvan")


def test_pronoun_speaker_is_unknown():
    assert cast.split("“So,” he said.")[0] == ("So.", "")


def test_unnamed_speaker_is_unknown():
    assert cast.split("“May light find you,” the torchman said.")[0] == ("May light find you.", "")


def test_action_beat_with_a_known_character():
    assert cast.split("“Evidence.” Torvan put his elbows down.", KNOWN)[0] == ("Evidence.", "Torvan")


def test_action_beat_needs_exactly_one_known_character():
    assert cast.split("Torvan looked at Wis. “Well?”", KNOWN)[-1] == ("Well?", "")


def test_tag_before_a_quote_wins():
    assert cast.split("{Karos} “Fine,” she said.") == [("Fine.", "Karos"), ("she said.", None)]


def test_tag_at_paragraph_start_covers_all_quotes():
    segments = cast.split("{Karos} He sighed. “Fine.” He turned. “Go.”")
    assert [s for s in segments if s[1]] == [("Fine.", "Karos"), ("Go.", "Karos")]


def test_quote_without_dialogue_is_narration():
    assert cast.split("No dialogue at all here.") == [("No dialogue at all here.", None)]


def test_find_names_skips_pronouns_and_handles_titles():
    assert cast.find_names("“Hi,” she said. “Yes,” said Mr. Smith. {Lusien} “Go.”") == ["Lusien", "Mr. Smith"]


def test_strip_tags():
    assert cast.strip_tags("{Mara} “Fine,” she said.") == "“Fine,” she said."


# ---- narrating with character voices

def run_cast(tmp_path, monkeypatch, chapters, cast_config, voice="am_michael"):
    folder = tmp_path / "book"
    folder.mkdir(exist_ok=True)
    for name, md in chapters.items():
        (folder / name).write_text(md, encoding="utf-8")
    said = []

    def synth(text, voice=None):
        said.append((text, voice))
        return np.zeros(240, dtype=np.float32)

    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(audiobook, "load_engine", lambda args: (24000, synth))
    monkeypatch.setattr(audiobook, "build_m4b", lambda chapters, wavs, args, progress=None: Path("out/Book.m4b"))
    monkeypatch.setattr(audiobook, "level_chapter", lambda wav, out: wav)
    args = SimpleNamespace(chapters=str(folder), engine="kokoro", voice=voice, speed=1.0, ref=None,
                           paragraph_pause=0.6, title_pause=1.2, sample=False, title="Book", author="Me",
                           cover=None, cast=cast_config)
    audiobook.run(args, log=lambda m: None)
    return said


CHAPTER = {"01.md": "“Late,” Mara said.\n\n“Sorry,” Kai said.\n\n“Who's there?” someone called."}


def test_one_voice_mode_reads_everything_in_the_narrator_voice(tmp_path, monkeypatch):
    said = run_cast(tmp_path, monkeypatch, {"01.md": "{Mara} “Late,” she said."}, None)
    assert said == [("“Late,” she said.", None)]  # the tag is removed and nothing is split


def test_each_character_gets_their_voice(tmp_path, monkeypatch):
    config = {"enabled": True, "dialogue": "af_heart", "voices": {"Mara": "bf_emma"}}
    said = run_cast(tmp_path, monkeypatch, CHAPTER, config)
    assert ("Late.", "bf_emma") in said  # Mara's voice
    assert ("Sorry.", "af_heart") in said  # Kai has none set: the other-dialogue voice
    assert ("Who's there?", "af_heart") in said  # unknown speaker
    assert ("Mara said.", None) in said  # narration stays with the narrator


def test_switching_off_returns_to_the_old_renders(tmp_path, monkeypatch):
    run_cast(tmp_path, monkeypatch, CHAPTER, None)
    run_cast(tmp_path, monkeypatch, CHAPTER, {"enabled": True, "dialogue": "af_heart", "voices": {}})
    assert run_cast(tmp_path, monkeypatch, CHAPTER, {"enabled": False}) == []


def test_changing_one_character_voice_narrates_only_their_lines(tmp_path, monkeypatch):
    config = {"enabled": True, "dialogue": "af_heart", "voices": {"Mara": "bf_emma"}}
    run_cast(tmp_path, monkeypatch, CHAPTER, config)
    config = {"enabled": True, "dialogue": "af_heart", "voices": {"Mara": "bf_lily"}}
    assert run_cast(tmp_path, monkeypatch, CHAPTER, config) == [("Late.", "bf_lily")]


def test_narrator_voice_for_dialogue_keeps_paragraphs_whole(tmp_path, monkeypatch):
    config = {"enabled": True, "dialogue": None, "voices": {"Mara": "am_michael"}}  # all the narrator's voice
    said = run_cast(tmp_path, monkeypatch, {"01.md": "“Late,” Mara said."}, config)
    assert said == [("“Late,” Mara said.", None)]


def test_switching_back_and_forth_keeps_both_sets_of_renders(tmp_path, monkeypatch):
    config = {"enabled": True, "dialogue": "af_heart", "voices": {}}
    run_cast(tmp_path, monkeypatch, CHAPTER, None)
    run_cast(tmp_path, monkeypatch, CHAPTER, config)
    assert run_cast(tmp_path, monkeypatch, CHAPTER, None) == []
    assert run_cast(tmp_path, monkeypatch, CHAPTER, config) == []


def test_chatterbox_ignores_character_voices():
    args = SimpleNamespace(engine="chatterbox", voice="Chatterbox", cast={"enabled": True, "dialogue": "af_heart"})
    assert audiobook.cast_voices(args) is None


def test_scan_cast_counts_lines_and_writes_who_said_what(tmp_path):
    (tmp_path / "01.md").write_text("# One\n\n" + CHAPTER["01.md"] + "\n\n“Again,” Mara said.", encoding="utf-8")
    characters, unknown, report = audiobook.scan_cast(tmp_path)
    assert characters == [("Mara", 2), ("Kai", 1)] and unknown == 1
    assert "Mara: “Late.”" in report and "(other dialogue): “Who's there?”" in report


def test_unnamed_speech_tag_blocks_action_beat_guess():
    # "someone said" names no one, so Wis (merely mentioned) must not get the line.
    assert cast.split("“That’s Lusien,” someone said, two down from Wis.", KNOWN)[0] == ("That’s Lusien.", "")


def test_conversation_alternates_between_two_speakers():
    texts = ["“Four minutes,” Torvan said.", "“Wasted,” Wis said.", "“Evidence.”", "“Clouds.”"]
    speakers = [[s for _, s in segs if s is not None] for segs in cast.split_all(texts, KNOWN)]
    assert speakers == [["Torvan"], ["Wis"], ["Torvan"], ["Wis"]]


def test_a_named_addressee_is_not_the_speaker():
    texts = ["“Shit,” Karos said.", "“Twenty-one,” Torvan said.", "“I can count, Torvan.”"]
    assert cast.split_all(texts, KNOWN)[-1] == [("I can count, Torvan.", "Karos")]


def test_narration_breaks_the_conversation():
    texts = ["“Four minutes,” Torvan said.", "“Wasted,” Wis said.", "The wind picked up.", "“Evidence.”"]
    assert cast.split_all(texts, KNOWN)[-1] == [("Evidence.", "")]
