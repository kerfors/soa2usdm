"""
Regression fixture for the deterministic pipeline (resolve -> consolidate).

For every protocol in the collection that has a verified extraction plus golden
resolved + consolidated JSON, re-running resolve+consolidate on the verified
extraction must reproduce the golden output exactly (timestamps scrubbed).

Runs against a temp copy via a throwaway collection key, so the real golden
files are never touched. To bank a new protocol: drop its verified extraction
and golden resolved/consolidated into place; this test discovers it automatically.

On top of the golden diff, every discovered protocol is checked for annotation
text integrity — adjacent-pair containment, over-merge, and degenerate
source_note typing. The two banked fixture protocols are clean current goldens:
NCT04677179 (the hardest source in the corpus — raster pages, tiled tables,
reworked annotation layer) and NCT03637764 (clean from the start).

Every detector also has a negative control in fixtures/negative/ — a real
historical bad state, taken from the collections git history, on which the
detector must fire. A detector that only ever returns nothing is
indistinguishable from a clean corpus.
"""
import json
import shutil
from pathlib import Path

import pytest

from soa2usdm import config
from soa2usdm.errors import Errors
from soa2usdm.analytics import Analytics
from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import ResolveStep, find_partial_marker_bindings, validate_extraction
from soa2usdm.consolidate import (
    ConsolidateStep,
    find_adjacent_text_overlaps,
    find_cross_table_binding_conflicts,
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


def negative_fixture(name):
    path = Path(__file__).parent / "fixtures" / "negative" / name
    return json.loads(path.read_text())


def test_fragmentation_detector_fires_on_known_bad():
    """Negative control — NCT04677179's consolidated annotations as committed at
    2d0f58d, before the 2026-07-28 annotation re-extraction: each Comment cell was
    split across the rows it overlapped, yielding 77 fragments and 13 adjacent
    pairs where one text contains the other."""
    annotations = negative_fixture(
        "NCT04677179_fragmented_annotations.json")["unified_annotations"]
    pairs = find_adjacent_text_overlaps(annotations)
    assert len(pairs) == 13, f"expected 13 fragmentation pairs, got {len(pairs)}"


def test_degenerate_typing_detector_fires_on_known_bad():
    """Negative control — the same 2d0f58d state also mis-typed every one of its
    77 annotations as source_note (the notes column read as cross-references)."""
    annotations = negative_fixture(
        "NCT04677179_fragmented_annotations.json")["unified_annotations"]
    assert is_degenerate_annotation_typing(annotations), \
        "detector must fire on the all-source_note historical state"


def test_cross_table_conflict_detector_fires_on_known_bad():
    """Negative control — NCT04677179's consolidated output as committed at a96cf0c,
    before the missing Genetics sample row was restored in Tables 2-4. The DNA
    pharmacogenetics note (xannot-024) then bound to Genetics sample in Table 1 but
    to Flow cytometry panel / CCI in the tables missing the row — the fingerprint
    of a dropped row. xannot-023 is the known co-detection: identical PK note text
    legitimately printed on two adjacent rows, a documented detector limitation."""
    data = negative_fixture("NCT04677179_conflicting_bindings.json")
    conflicts = dict(find_cross_table_binding_conflicts(data))
    assert set(conflicts) == {"xannot-023", "xannot-024"}, \
        f"expected xannot-023 and xannot-024, got {sorted(conflicts)}"
    assert "Genetics sample" in conflicts["xannot-024"]


def test_partial_binding_detector_fires_on_desynced_row():
    """Negative control — the failure find_partial_marker_bindings exists for:
    a corrected marker_locations that was not carried into the row-side
    annotation_markers (the two fields record the same fact; resolve believes
    the row). The historical desync (rev2, 2026-07-30) was repaired before it
    was committed, so this reconstructs its exact shape on the banked real
    extraction: the annotation declares an extra row in marker_locations that
    no row's annotation_markers carries — the declared-only row will not bind."""
    path = (Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179"
            / "SoA2USDM" / "extracted" / "NCT04677179_Table_01_extraction.json")
    data = json.loads(path.read_text())
    assert not find_partial_marker_bindings(data), "banked extraction must be consistent"
    annot = next(a for a in data["annotations"]
                 if a["annotation_marker"] == "c1"
                 and a["marker_locations"][0]["location_type"] == "activity_name")
    moved_to = annot["marker_locations"][0]["row_position"] + 2
    annot["marker_locations"].append(
        {"table_number": 1, "location_type": "activity_name",
         "row_position": moved_to})
    findings = find_partial_marker_bindings(data)
    assert len(findings) == 1 and "'c1'" in findings[0] \
        and str(moved_to) in findings[0], \
        f"expected the declared-only row {moved_to} to be named, got {findings}"


def test_method_provenance_summary_warnings_and_unresolved():
    """Method provenance is exception-based: an extraction recording nothing
    reports nothing; a recorded deviation appears in method_provenance; only the
    geometry-less methods (proximity) warn; an 'unresolved' marker location is an
    allowed answer — counted, not warned, and never a lost binding."""
    path = (Path(__file__).parent / "fixtures" / "protocols" / "NCT04677179"
            / "SoA2USDM" / "extracted" / "NCT04677179_Table_01_extraction.json")
    data = json.loads(path.read_text())

    baseline = validate_extraction(data)
    assert baseline.method_provenance == [], "banked extraction records no deviations"
    baseline_warnings = len(baseline.warnings)

    # A deviation with a sound method: recorded, no warning.
    data["annotations"][0]["annotation_text_source"] = {"method": "deglyph_reconstruction"}
    # The known failure source: recorded AND warned.
    data["annotations"][1]["annotation_text_source"] = {"method": "proximity_bounded"}
    # An honest non-answer: position kept as evidence, no scope claim.
    data["annotations"][2]["marker_locations"].append(
        {"table_number": 1, "location_type": "unresolved", "row_position": 40})

    result = validate_extraction(data)
    assert result.method_provenance == [
        "annotation_text:deglyph_reconstruction: 1",
        "annotation_text:proximity_bounded: 1",
        "marker_location:unresolved: 1",
    ], result.method_provenance
    new_warnings = [w for w in result.warnings if "proximity-bounded" in w]
    assert len(new_warnings) == 1, "exactly the proximity-bounded note warns"
    assert len(result.warnings) == baseline_warnings + 1, \
        "unresolved and sound methods add no warnings"
    assert not find_partial_marker_bindings(data), \
        "an unresolved location must not read as a lost binding"
