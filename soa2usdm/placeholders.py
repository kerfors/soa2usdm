"""
Placeholder annotations (Layer 1 hygiene, decided 2026-11-07).

A placeholder keeps a marker that has no protocol text behind it, so the cells
and rows that carry the marker still point to something. Its annotation_text
is empty; placeholder_reason says why. Text that is not protocol text (a
probable equivalent from another table or protocol, a reviewer's finding)
goes in review_note: shown on review pages, never read as SoA content.
Both are set through corrections sidecars; the raw extraction is not changed.
"""

PLACEHOLDER = "placeholder"

# placeholder_reason -> what a page shows in place of the empty text
REASON_LABELS = {
    "redacted": "redacted in source",
    "not_printed": "definition not printed in source",
    "reviewer_note": "reviewer note",
}


def display_text(annot: dict) -> str:
    """The text a page shows for an annotation: its annotation_text, or for a
    placeholder its reason in brackets."""
    if annot["annotation_type"] != PLACEHOLDER:
        return annot["annotation_text"]
    return f"[{REASON_LABELS[annot['placeholder_reason']]}]"
