"""Character voices: find dialogue in a paragraph and work out who speaks it.

Speakers come from, in order: a {Name} tag before the quote (or at the start of the paragraph), a speech tag
next to the quote ("..." Mara said / said Mara / Mara asked, "..."), another attributed quote in the same
paragraph, or an action beat naming one known character ("Mara frowned. "...""). Anything else is unknown."""
import re

QUOTE = re.compile(r"“([^”]*)”|\"([^\"]*)\"")
TAG = re.compile(r"\{\s*([^{}]+?)\s*\}\s*")
VERBS = ("said|says|asked|asks|replied|replies|answered|answers|whispered|whispers|shouted|shouts|yelled|yells|"
         "called|calls|cried|cries|muttered|mutters|murmured|murmurs|added|adds|snapped|snaps|began|begins|"
         "continued|continues|insisted|insists|demanded|demands|repeated|repeats|laughed|laughs|sighed|sighs|"
         "growled|growls|hissed|hisses|breathed|told|tells|warned|warns|admitted|admits|agreed|agrees|explained|"
         "explains|offered|offers|pleaded|pleads|screamed|screams|stammered|stammers|groaned|groans|grunted|"
         "grunts|barked|barks|roared|roars|announced|announces|declared|declares|went on|goes on|ordered|orders|"
         "suggested|suggests|protested|protests|mumbled|mumbles|said quietly|said softly")
NAME = r"((?:(?:Mr|Mrs|Ms|Dr|Sir|Lady|Lord|Captain|Master)\.?\s)?[A-Z][a-zA-Z\-]+(?:\s[A-Z][a-zA-Z\-]+)?)"
NOT_NAMES = {"He", "She", "They", "I", "We", "You", "It", "The", "His", "Her", "Their", "Someone", "Somebody",
             "Nobody", "Everyone", "Everybody", "One", "A", "An", "This", "That", "Then", "But", "And", "So",
             "Now", "There", "Here", "Who", "What", "When", "Where", "Why", "How", "Yes", "No", "Oh", "Well"}
# Right after a quote: , Mara said / , said Mara / Mara asked
AFTER = re.compile(rf"^[\s,]*(?:{NAME}\s+(?:{VERBS})\b|(?:{VERBS})\s+{NAME}\b)")
# Right after a quote, a speech tag with no name: , he said / , someone called / , the torchman said
AFTER_UNNAMED = re.compile(rf"^[\s,]*(?:[\w’'-]+\s){{1,3}}?(?:{VERBS})\b")
# Right before a quote: Mara said, / Mara asked:
BEFORE = re.compile(rf"\b{NAME}\s+(?:{VERBS})\s*[,:]?\s*$")


def clean_name(name):
    name = re.sub(r"['’]s$", "", name.strip())
    first = name.split()[0].rstrip(".")
    return None if first in NOT_NAMES or name in NOT_NAMES else name


def strip_tags(text):
    """Remove {Name} tags, for books read in one voice."""
    return re.sub(r"\s{2,}", " ", TAG.sub("", text)).strip()


def _pieces(text):
    """[("narration" | "quote", text, tag_before)] for one paragraph, in order. Tags are removed from the text."""
    pieces, pos = [], 0
    for m in QUOTE.finditer(text):
        before = text[pos:m.start()]
        tag = TAG.search(before[-60:]) if before else None
        tag_name = None
        if tag and not before[before.rindex("{"):].split("}", 1)[1].strip():  # the tag sits right before the quote
            tag_name = tag.group(1)
        pieces.append(("narration", TAG.sub("", before), None))
        pieces.append(("quote", m.group(1) if m.group(1) is not None else m.group(2), tag_name))
        pos = m.end()
    pieces.append(("narration", TAG.sub("", text[pos:]), None))
    return pieces


def find_names(text):
    """Character names attributed by speech tags or {Name} tags in a paragraph (for building the cast)."""
    names = [m.strip() for m in TAG.findall(text)]
    pieces = _pieces(text)
    for i, (kind, piece, _) in enumerate(pieces):
        if kind != "quote":
            continue
        for regex, neighbour in ((AFTER, pieces[i + 1][1] if i + 1 < len(pieces) else ""),
                                 (BEFORE, pieces[i - 1][1] if i else "")):
            m = regex.search(neighbour)
            if m:
                name = clean_name(next(g for g in m.groups() if g))
                if name:
                    names.append(name)
                break
    return names


LOCKED = "\x00locked"  # a speech tag without a name: stays unknown
UNSURE = "\x00unsure"  # no clue at all in the paragraph: split_all may work it out from the conversation


def split(text, known=()):
    """Split a paragraph into [(text, speaker)], where speaker is None for narration, a name for attributed
    dialogue, or "" for dialogue whose speaker couldn't be worked out."""
    return [(piece, "" if speaker == UNSURE else speaker) for piece, speaker in _split(text, known)]


def _split(text, known):
    """split(), but a quote with no clue at all is marked UNSURE instead of "", for split_all."""
    lead = TAG.match(text)
    paragraph_tag = None
    if lead:
        rest = text[lead.end():]
        # {Name} at the very start applies to every quote in the paragraph unless a quote has its own tag.
        paragraph_tag = lead.group(1) if not rest.lstrip().startswith(("“", '"')) else None
    pieces = _pieces(text)
    speakers = []
    for i, (kind, piece, tag) in enumerate(pieces):
        if kind != "quote":
            speakers.append(None)
            continue
        speaker = tag
        if not speaker:
            after = pieces[i + 1][1] if i + 1 < len(pieces) else ""
            before = pieces[i - 1][1] if i else ""
            for regex, neighbour in ((AFTER, after), (BEFORE, before)):
                m = regex.search(neighbour)
                if m:
                    speaker = clean_name(next(g for g in m.groups() if g)) or LOCKED
                    break
            else:
                if AFTER_UNNAMED.search(after):
                    speaker = LOCKED  # "he said", "someone called": a speaker we can't name, so don't guess
        speakers.append(speaker)
    named = {s for s in speakers if s and s != LOCKED}
    fallback = paragraph_tag
    if not fallback and len(named) == 1:
        fallback = next(iter(named))  # one speaker per paragraph is the usual convention
    if not fallback and not named and known and LOCKED not in speakers:
        narration = " ".join(p for (kind, p, _) in pieces if kind == "narration")
        beats = {name for name in known if re.search(rf"\b{re.escape(name)}\b", narration)}
        if len(beats) == 1:
            fallback = next(iter(beats))  # an action beat: Mara frowned. "..."
    segments = []
    for (kind, piece, _), speaker in zip(pieces, speakers, strict=True):
        piece = piece.strip()
        if kind == "quote":
            if speaker == LOCKED:
                speaker = ""
            elif speaker is None or speaker == "":
                speaker = fallback or (UNSURE if fallback is None else "")
            piece = re.sub(r",$", ".", piece)
        if not re.search(r"\w", piece):
            continue  # stray punctuation between quotes
        if segments and segments[-1][1] == speaker:
            segments[-1] = (f"{segments[-1][0]} {piece}", speaker)
        else:
            segments.append((piece, speaker))
    return segments


def split_all(texts, known=()):
    """split() every paragraph of a chapter, then follow the conversation for lines with no clue at all.

    In an unbroken run of dialogue paragraphs between two characters, a line with no speaker goes to whichever
    of the two did not speak last, and a line that names one of them (“It's clouds, Wis.”) goes to the other."""
    known = set(known)
    result, recent = [], []  # recent: the last two different speakers in the current run of dialogue
    for text in texts:
        segments = _split(text, known)
        quoted = [speaker for _, speaker in segments if speaker is not None]
        if not quoted:
            recent = []  # narration breaks the conversation
            result.append(segments)
            continue
        if any(speaker == UNSURE for speaker in quoted):
            guess = ""
            if len(recent) == 2:
                spoken = " ".join(piece for piece, speaker in segments if speaker == UNSURE)
                addressed = [name for name in recent if re.search(rf"\b{re.escape(name)}\b", spoken)]
                if not addressed:
                    guess = recent[0]  # the one who didn't speak last
                elif len(addressed) == 1:
                    guess = next(name for name in recent if name not in addressed)  # not the one being spoken to
            segments = [(piece, guess if speaker == UNSURE else speaker) for piece, speaker in segments]
        names = [speaker for _, speaker in segments if speaker]
        if len(set(names)) == 1:
            name = names[0]
            recent = [r for r in recent if r != name][-1:] + [name]
        elif not names:
            recent = []  # an unknown speaker joined in: don't keep guessing
        result.append(segments)
    return result
