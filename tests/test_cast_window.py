"""Tests for the Cast window's menus: each voice goes to one character only."""
from cast_window import DIALOGUE, NARRATOR, offered

VALUES = [DIALOGUE, "af_heart", "am_michael", "bf_emma", "bm_george"]


def test_a_voice_given_to_one_character_leaves_the_others():
    assert offered(VALUES, DIALOGUE, {"bf_emma", DIALOGUE}, {DIALOGUE}) == [DIALOGUE, "af_heart", "am_michael",
                                                                           "bm_george"]


def test_a_character_keeps_its_own_pick():
    assert "bf_emma" in offered(VALUES, "bf_emma", {"bf_emma"}, {DIALOGUE})  # two had it in an older cast


def test_shared_choices_stay_for_everyone():
    # The narrator's voice can go to any number of characters, since it doesn't set one apart.
    shared = {DIALOGUE, NARRATOR, "am_michael"}
    assert offered(VALUES, DIALOGUE, {"am_michael", "bf_emma"}, shared) == [DIALOGUE, "af_heart", "am_michael",
                                                                           "bm_george"]
