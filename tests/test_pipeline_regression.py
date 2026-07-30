"""
Regression fixture for the deterministic pipeline (resolve -> consolidate).

For every protocol in the collection that has a verified extraction plus golden
resolved + consolidated JSON, re-running resolve+consolidate on the verified
extraction must reproduce the golden output exactly (timestamps scrubbed).

Runs against a temp copy via a throwaway collection key, so the real golden
files are never touched. To bank a new protocol: drop its verified extraction
and golden resolved/consolidated into place; this test discovers it automatically.

On top of the golden diff, every discovered protocol is checked for annotation
text integrity — adjacent-pair containment and degenerate source_note typing.
NCT04677179 is the negative control: its notes column fragmented into 77 partial
annotations, all mis-typed source_note, and the golden output here is the
re-extraction. NCT03637764 is the positive control (clean from the start).
"""
import json
import shutil
from pathlib import Path

import pytest

from soa2usdm import config
from soa2usdm.errors import Errors
from soa2usdm.analytics import Analytics
from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import ResolveStep
from soa2usdm.consolidate import (
    ConsolidateStep,
    find_adjacent_text_overlaps,
    find_over_merged_annotations,
    is_degenerate_annotation_typing,
    OVERLAP_PAIR_THRESHOLD,
)

VOLATILE = {"resolved_at", "consolidated_at", "extracted_at"}


def discover_cases():
    """(collection, protocol) for every protocol, in any registered collection,
    that has a verified extraction AND golden resolved + consolidated."""
    cases = []
    for collection, protocols_dir in config.COLLECTIONS.items():
        if not Path(protocols_dir).is_dir():
            continue
        for d in sorted(p for p in Path(protocols_dir).iterdir()
                        if p.is_dir() and not p.name.startswith(".")):
            soa = d / "SoA2USDM"
            if (list((soa / "extracted").glob("*_extraction.json"))
                    and list((soa / "resolved").glob("*_resolved.json"))
                    and list((soa / "consolidated").glob("*_consolidated.json"))):
                cases.append((collection, d.name))
    return cases


CASES = discover_cases()


def scrub(obj):
    """Recursively drop volatile timestamp keys for stable comparison."""
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


@pytest.fixture(params=CASES, ids=[f"{c}/{p}" for c, p in CASES])
def pipeline_output(request, tmp_path):
    """Copy one protocol's extraction into a temp collection, run resolve+consolidate,
    and yield (protocol, produced_dir, golden_dir)."""
    collection, protocol = request.param
    golden = Path(config.COLLECTIONS[collection]) / protocol / "SoA2USDM"

    coll = tmp_path / "protocols"
    extracted = coll / protocol / "SoA2USDM" / "extracted"
    extracted.mkdir(parents=True)
    for f in (golden / "extracted").glob("*_extraction.json"):
        shutil.copy(f, extracted / f.name)
    for f in (golden / "extracted").glob("*_corrections.json"):
        shutil.copy(f, extracted / f.name)

    key = "regression_tmp"
    config.COLLECTIONS[key] = coll
    errors = Errors()
    analytics = Analytics()
    data = {"source": {"protocol_id": protocol, "collection": key}}
    for step_cls in (ApplyCorrectionsStep, ResolveStep, ConsolidateStep):
        data[step_cls.step_name] = step_cls(errors, analytics).execute(data)
    assert not errors.has_errors(), [(e.step, e.message) for e in errors.all]

    yield protocol, coll / protocol / "SoA2USDM", golden
    config.COLLECTIONS.pop(key, None)


def test_resolved_matches_golden(pipeline_output):
    protocol, produced, golden = pipeline_output
    golden_files = sorted((golden / "resolved").glob("*_resolved.json"))
    assert golden_files, f"{protocol}: no golden resolved files"
    for gf in golden_files:
        pf = produced / "resolved" / gf.name
        assert pf.exists(), f"{protocol}: resolve did not produce {gf.name}"
        assert scrub(json.loads(pf.read_text())) == scrub(json.loads(gf.read_text())), \
            f"{protocol}: resolved mismatch in {gf.name}"


def test_consolidated_matches_golden(pipeline_output):
    protocol, produced, golden = pipeline_output
    gf = next((golden / "consolidated").glob("*_consolidated.json"))
    pf = produced / "consolidated" / gf.name
    assert pf.exists(), f"{protocol}: consolidate produced no output"
    assert scrub(json.loads(pf.read_text())) == scrub(json.loads(gf.read_text())), \
        f"{protocol}: consolidated mismatch"


def consolidated_annotations(produced):
    """The unified annotations the pipeline just produced for this protocol."""
    pf = next((produced / "consolidated").glob("*_consolidated.json"))
    return json.loads(pf.read_text())["unified_annotations"]


def test_annotations_not_fragmented(pipeline_output):
    """A single notes-column cell split across the rows it overlaps surfaces as
    consecutive annotations whose text contains one another. Measured over 22
    protocols: clean ones score 0-1, the fragmented NCT04677179 extraction scored 13."""
    protocol, produced, _ = pipeline_output
    pairs = find_adjacent_text_overlaps(consolidated_annotations(produced))
    assert len(pairs) < OVERLAP_PAIR_THRESHOLD, \
        f"{protocol}: {len(pairs)} adjacent annotation pairs share contained text: {pairs}"


def test_annotations_not_over_merged(pipeline_output):
    """The opposite of fragmentation: two adjacent note cells read as one annotation.
    A merged pair repeats a shared sentence block; a single cell does not repeat itself."""
    protocol, produced, _ = pipeline_output
    hits = find_over_merged_annotations(consolidated_annotations(produced))
    assert not hits, f"{protocol}: annotations carry repeated text blocks: {hits}"


def test_over_merge_detector_fires_on_known_bad():
    """Negative control — the detector is worthless if it only ever returns nothing.

    These are NCT04677179's annotations as committed before the notes were re-bounded
    by rule-line geometry; three of them concatenate two source cells.
    """
    path = (Path(__file__).parent / "fixtures" / "negative"
            / "NCT04677179_overmerged_annotations.json")
    annotations = json.loads(path.read_text())["unified_annotations"]
    hits = find_over_merged_annotations(annotations)
    assert len(hits) == 3, f"expected the 3 known over-merges, got {hits}"


def test_annotation_typing_not_degenerate(pipeline_output):
    """All-source_note means a notes/comments column was read as cross-references
    instead of footnotes. All-footnote is normal and must not trip this."""
    protocol, produced, _ = pipeline_output
    annotations = consolidated_annotations(produced)
    assert not is_degenerate_annotation_typing(annotations), \
        f"{protocol}: all {len(annotations)} annotations typed source_note"
