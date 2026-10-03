"""
Document references in annotation text (inventory item 3, first part).

A footnote often defers to the protocol: 'See Section 8.2.2', 'refer to
Appendix 3', 'see ETV in Table 4'. This module states that pointer as data —
what kind of thing the note points at and its number as printed. It reads the
annotation text only. It does not look the target up: whether the section can
be found in the protocol text, and what it says, is a separate step.
"""
import re
from typing import List

_NUM = r"\d+(?:\.\d+)*"
_LETTER_OR_NUM = r"(?:[A-Z]\b|%s)" % _NUM
_TABLE_NUM = r"\d+(?:[.\-–]\d+)*"
_MORE = r"(?:\s*(?:,|and|or|&|to|through|-|–)\s*%s)*"
_PATTERNS = (
    ("section", re.compile(r"\bSections?\s+(%s%s)" % (_NUM, _MORE % _NUM), re.I), re.compile(_NUM)),
    ("appendix", re.compile(r"\bAppendi(?:x|ces)\s*(%s%s)" % (_LETTER_OR_NUM, _MORE % _LETTER_OR_NUM)),
     re.compile(_LETTER_OR_NUM)),
    ("attachment", re.compile(r"\bAttachments?\s+(\d+)", re.I), re.compile(r"\d+")),
    ("table", re.compile(r"\bTables?\s+(%s)" % _TABLE_NUM, re.I), re.compile(_TABLE_NUM)),
    ("figure", re.compile(r"\bFigures?\s+(%s)" % _TABLE_NUM, re.I), re.compile(_TABLE_NUM)),
)

# A note written during review is not protocol text; what it names is not a
# reference of the protocol. Such notes carry no flag, only this wording.
REVIEWER_NOTE_PREFIXES = ("reviewer note", "footnote not printed in the source")


def find_document_references(text: str) -> List[dict]:
    """The numbered document targets an annotation text points at, by kind
    (section, appendix, attachment, table, figure) and then in print order:
    [{"kind": "section", "target": "8.2.2"}, ...]. A list ('Sections 8.1 and
    8.2') gives one entry per number; a target named twice is listed once.
    Empty for a reviewer note and for a text that names no numbered target."""
    if text.strip().lower().startswith(REVIEWER_NOTE_PREFIXES):
        return []
    found = []
    for kind, pattern, target in _PATTERNS:
        for match in pattern.finditer(text):
            for number in target.findall(match.group(1)):
                ref = {"kind": kind, "target": number}
                if ref not in found:
                    found.append(ref)
    return found
