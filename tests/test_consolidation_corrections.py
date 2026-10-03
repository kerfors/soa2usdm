"""
Consolidation corrections — human decisions on cross-table matches (items 28b, 20a).

The sidecar `consolidated/{NCTID}_consolidation_corrections.json` is read by
consolidate before matching. Entries name source rows (table_number + activity_id,
activity_name as a check). The entries below are written for these tests on real
rows of real protocols; they exercise the ops and are not published decisions.

The `refines` and fail-fast tests run on the banked NCT03637764 fixture. The
keep / split / merge tests need the published usdm_data resolved files
(NCT01847274, NCT02107703) and are skipped without them.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import config
from soa2usdm.consolidate import consolidate_tables
from soa2usdm.visualize import build_matches_model, generate_consolidated_html

SCHEMAS = Path(__file__).parent.parent / "schemas"
FIXTURE = Path(__file__).parent / "fixtures" / "protocols" / "NCT03637764" / "SoA2USDM" / "resolved"
FIXTURE_FILES = sorted(FIXTURE.glob("*_resolved.json"))


def _schema(name: str) -> dict:
    return json.loads((SCHEMAS / name).read_text())


def _doc(protocol_id: str, *entries: dict) -> dict:
    doc = {"schema_name": "soa-consolidation-corrections", "schema_version": "1.0",
           "protocol_id": protocol_id,
           "corrections": [{"id": f"ccorr-{i:03d}", **e, "reason": "test", "by": "test",
                            "at": "2026-10-03T00:00:00Z"} for i, e in enumerate(entries, 1)]}
    jsonschema.validate(doc, _schema("soa-consolidation-corrections.schema.json"))
    return doc


def _row(table_number: int, activity_id: str, activity_name: str) -> dict:
    return {"table_number": table_number, "activity_id": activity_id, "activity_name": activity_name}


def _by_row(out: dict) -> dict:
    return {(r["table_num"], r["activity_id"]): ua
            for ua in out["unified_activities"] for r in ua["source_refs"]}


def _valid(out: dict) -> None:
    jsonschema.validate(out, _schema("soa-tables-consolidated.schema.json"))


# --- NCT03637764 fixture: refines, and the fail-fast checks -----------------

PK = _row(1, "act-025", "PK")
ISA_ADMIN = _row(1, "act-021", "Isatuximab Administration")
ISA_INFUSION = _row(2, "act-003", "Isatuximab")


def test_without_a_sidecar_nothing_is_decided():
    out = consolidate_tables("NCT03637764", FIXTURE_FILES)
    meta = out["consolidation_metadata"]
    assert out["schema_version"] == "1.4"
    assert meta["review_stats"] == {"total": 0, "open": 0, "decided": 0, "near_matches": 0}
    assert meta["match_stats"]["decision"] == 0
    assert "corrections_applied" not in meta
    assert not any("refines" in ua or "refined_by" in ua for ua in out["unified_activities"])
    _valid(out)


def test_refines_links_a_row_and_a_whole_table_without_merging():
    plain = consolidate_tables("NCT03637764", FIXTURE_FILES)
    doc = _doc("NCT03637764",
               {"op": "refines", "source": {"table_number": 2}, "target": PK},
               {"op": "refines", "source": ISA_INFUSION, "target": ISA_ADMIN})
    out = consolidate_tables("NCT03637764", FIXTURE_FILES, doc)
    rows = _by_row(out)
    pk, admin, infusion = rows[(1, "act-025")], rows[(1, "act-021")], rows[(2, "act-003")]
    assert pk["refined_by"] == [{"table_num": 2, "correction_id": "ccorr-001"}]
    table2 = next(t for t in out["consolidation_metadata"]["source_tables"] if t["table_num"] == 2)
    assert table2["refines"] == [{"xact_id": pk["xact_id"], "correction_id": "ccorr-001"}]
    assert infusion["refines"] == [{"xact_id": admin["xact_id"], "correction_id": "ccorr-002"}]
    assert admin["refined_by"] == [{"xact_id": infusion["xact_id"], "correction_id": "ccorr-002"}]
    # A relation, not a merge: same activities, same ids, same matching.
    assert [ua["xact_id"] for ua in out["unified_activities"]] == [ua["xact_id"] for ua in plain["unified_activities"]]
    assert out["consolidation_metadata"]["match_stats"] == plain["consolidation_metadata"]["match_stats"]
    assert out["consolidation_metadata"]["review_stats"]["total"] == 0   # not a review decision
    assert out["consolidation_metadata"]["corrections_applied"] == 2
    _valid(out)


def test_a_renamed_row_stops_consolidation():
    doc = _doc("NCT03637764", {"op": "refines", "source": {"table_number": 2},
                               "target": _row(1, "act-025", "Pharmacokinetics")})
    with pytest.raises(ValueError, match="ccorr-001: target row T1 act-025 is named 'PK'"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, doc)


def test_a_split_of_a_merge_that_does_not_happen_stops_consolidation():
    doc = _doc("NCT03637764", {"op": "split", "source": ISA_INFUSION, "target": ISA_ADMIN})
    with pytest.raises(ValueError, match="ccorr-001: 'split' names a merge that no longer happens"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, doc)


def test_a_keep_of_a_match_that_is_not_made_stops_consolidation():
    doc = _doc("NCT03637764", {"op": "keep", "source": ISA_INFUSION, "target": ISA_ADMIN})
    with pytest.raises(ValueError, match="ccorr-001: 'keep' names a match"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, doc)


def test_a_decision_on_a_base_table_row_stops_consolidation():
    doc = _doc("NCT03637764", {"op": "merge", "source": ISA_ADMIN, "target": ISA_INFUSION})
    with pytest.raises(ValueError, match="ccorr-001: source row T1 act-021 is in the base table"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, doc)


def test_malformed_sidecars_stop_consolidation():
    two = _doc("NCT03637764", {"op": "merge", "source": ISA_INFUSION, "target": ISA_ADMIN},
               {"op": "keep", "source": ISA_INFUSION, "target": ISA_ADMIN})
    with pytest.raises(ValueError, match="ccorr-002: source row T2 act-003 already has a decision"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, two)
    other = _doc("NCT04677179", {"op": "refines", "source": {"table_number": 2}, "target": PK})
    with pytest.raises(ValueError, match="are for 'NCT04677179'"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, other)
    whole = _doc("NCT03637764", {"op": "merge", "source": {"table_number": 2}, "target": PK})
    with pytest.raises(ValueError, match="only 'refines' takes a whole table"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, whole)
    same = _doc("NCT03637764", {"op": "refines", "source": ISA_ADMIN, "target": PK})
    with pytest.raises(ValueError, match="both in table 1"):
        consolidate_tables("NCT03637764", FIXTURE_FILES, same)


# --- usdm_data: keep, split, merge on real non-exact matches ----------------

def _published(protocol_id: str):
    if "usdm_data" not in config.COLLECTIONS:
        return []
    return config.find_resolved_files(protocol_id, "usdm_data")


needs_nct01847274 = pytest.mark.skipif(
    not _published("NCT01847274"), reason="needs the published NCT01847274 resolved files (usdm_data)")
needs_nct02107703 = pytest.mark.skipif(
    not _published("NCT02107703"), reason="needs the published NCT02107703 resolved files (usdm_data)")

VITALS_T1 = _row(1, "act-010", "Vital signs, height, weight")
VITALS_T3 = _row(3, "act-002", "Vital signs, weight")              # fuzzy_auto 0.90 into VITALS_T1
COAG_T1 = _row(1, "act-014", "Coagulation/serum chemistry")
HEMA_T2 = _row(2, "act-011", "Hematology/serum chemistry")         # near match 0.60 of COAG_T1


@needs_nct01847274
def test_keep_records_the_decision_and_changes_nothing_else():
    files = _published("NCT01847274")
    plain = consolidate_tables("NCT01847274", files)
    doc = _doc("NCT01847274", {"op": "keep", "source": VITALS_T3, "target": VITALS_T1},
               {"op": "keep", "source": HEMA_T2, "target": COAG_T1})
    out = consolidate_tables("NCT01847274", files, doc)
    rows = _by_row(out)
    merged = next(r for r in rows[(3, "act-002")]["source_refs"] if r["table_num"] == 3)
    assert rows[(3, "act-002")] is rows[(1, "act-010")]
    assert merged["match_status"] == "fuzzy_auto"
    assert merged["decision"] == {"correction_id": "ccorr-001", "op": "keep"}
    kept = rows[(2, "act-011")]
    assert kept is not rows[(1, "act-014")]
    assert kept["near_matches"][0]["decision"] == {"correction_id": "ccorr-002", "op": "keep"}
    assert "decision" not in kept["source_refs"][0]
    before, after = plain["consolidation_metadata"], out["consolidation_metadata"]
    assert after["match_stats"] == before["match_stats"]
    assert after["review_stats"] == {**before["review_stats"], "decided": 2,
                                     "open": before["review_stats"]["open"] - 2}
    assert [ua["xact_id"] for ua in out["unified_activities"]] == [ua["xact_id"] for ua in plain["unified_activities"]]
    _valid(out)


@needs_nct01847274
def test_split_takes_a_row_out_of_its_unified_activity():
    files = _published("NCT01847274")
    plain = consolidate_tables("NCT01847274", files)
    doc = _doc("NCT01847274", {"op": "split", "source": VITALS_T3, "target": VITALS_T1})
    out = consolidate_tables("NCT01847274", files, doc)
    rows = _by_row(out)
    alone = rows[(3, "act-002")]
    assert alone is not rows[(1, "act-010")]
    assert alone["activity_name"] == "Vital signs, weight"
    assert len(alone["source_refs"]) == 1
    assert alone["source_refs"][0]["match_status"] == "new"
    assert alone["source_refs"][0]["decision"] == {"correction_id": "ccorr-001", "op": "split"}
    assert "near_matches" not in alone
    assert len(out["unified_activities"]) == len(plain["unified_activities"]) + 1
    before, after = plain["consolidation_metadata"], out["consolidation_metadata"]
    assert after["match_stats"]["fuzzy_auto"] == before["match_stats"]["fuzzy_auto"] - 1
    assert after["review_stats"]["total"] == before["review_stats"]["total"]
    assert after["review_stats"]["decided"] == 1
    _valid(out)


@needs_nct02107703
def test_merge_joins_a_near_match():
    """NCT02107703: Table 2's 'Adverse Events Collection/CTCAE Grading' scores 0.75
    against Table 1's 'Adverse Event Collection/CTCAE Grading' and is kept separate
    with a hint since 1.3 (item 28a). A 'merge' entry joins the two rows."""
    files = _published("NCT02107703")
    plain = consolidate_tables("NCT02107703", files)
    source = _row(2, "act-001", "Adverse Events Collection/CTCAE Grading")
    target = _row(1, "act-019", "Adverse Event Collection/CTCAE Grading")
    out = consolidate_tables("NCT02107703", files, _doc("NCT02107703", {"op": "merge", "source": source, "target": target}))
    rows = _by_row(out)
    ua = rows[(2, "act-001")]
    assert ua is rows[(1, "act-019")]
    joined = next(r for r in ua["source_refs"] if r["table_num"] == 2)
    assert joined["match_status"] == "decision" and joined["match_confidence"] == 1.0
    assert joined["decision"] == {"correction_id": "ccorr-001", "op": "merge"}
    assert "near_matches" not in ua
    assert len(out["unified_activities"]) == len(plain["unified_activities"]) - 1
    before, after = plain["consolidation_metadata"], out["consolidation_metadata"]
    assert after["match_stats"]["decision"] == 1
    assert after["review_stats"]["near_matches"] == before["review_stats"]["near_matches"] - 1
    assert after["review_stats"]["total"] == before["review_stats"]["total"]
    assert after["review_stats"]["decided"] == 1
    _valid(out)


# --- the consolidated view: 'Matches across tables' --------------------------

def _row_names(files) -> dict:
    names = {}
    for f in files:
        table = json.loads(Path(f).read_text())
        for act in table["activities"]:
            names[(table["table_metadata"]["table_number"], act["activity_id"])] = act["activity_name"]
    return names


def test_view_offers_the_cross_reference_notes_as_refines_drafts():
    """NCT03637764 Table 1 carries two source notes that point at a flow chart
    ('See Pharmacokinetics and immunogenicity Flow Chart' on PK and ADA, 'See
    Biomarker Flow Chart' on the biomarker row). The view lists them with the
    other tables to pick from; it does not pick."""
    out = consolidate_tables("NCT03637764", FIXTURE_FILES)
    model = build_matches_model(out, _row_names(FIXTURE_FILES), None)
    assert model["items"] == [] and model["open"] == 0 and model["relations"] == []
    assert model["sidecar"] == "NCT03637764_consolidation_corrections.json"
    assert model["sidecar_exists"] is False and model["next_id"] == 1
    assert [(c["text"], [r["activity_name"] for r in c["rows"]]) for c in model["candidates"]] == [
        ("See Pharmacokinetics and immunogenicity Flow Chart", ["PK", "ADA"]),
        ("See Biomarker Flow Chart", ["Tumor Biopsy, Archival Tumor Tissue Collection, Biomarker Blood Draw"]),
    ]
    assert [t["table_number"] for t in model["candidates"][0]["tables"]] == [2, 3]
    html = generate_consolidated_html(out, None, _row_names(FIXTURE_FILES), None)
    assert 'id="matches"' in html and "no matches to review" in html
    assert 'class="comp" id="matches"' in html            # nothing open: starts collapsed


def test_view_shows_a_stated_refinement_under_the_row_it_details():
    doc = _doc("NCT03637764",
               {"op": "refines", "source": {"table_number": 2}, "target": PK},
               {"op": "refines", "source": ISA_INFUSION, "target": ISA_ADMIN})
    out = consolidate_tables("NCT03637764", FIXTURE_FILES, doc)
    model = build_matches_model(out, _row_names(FIXTURE_FILES), doc)
    assert model["sidecar_exists"] is True and model["next_id"] == 3
    assert [(r["correction_id"], r["source"], r["target"]) for r in model["relations"]] == [
        ("ccorr-002", ISA_INFUSION, ISA_ADMIN), ("ccorr-001", {"table_number": 2}, PK)]
    html = generate_consolidated_html(out, None, _row_names(FIXTURE_FILES), doc)
    assert "↳ refined by Table 2 (whole table)" in html
    assert "↳ refines <a href=" in html


@needs_nct01847274
def test_view_lists_the_same_matches_review_stats_counts():
    files = _published("NCT01847274")
    plain = consolidate_tables("NCT01847274", files)
    model = build_matches_model(plain, _row_names(files), None)
    stats = plain["consolidation_metadata"]["review_stats"]
    assert len(model["items"]) == stats["total"] == 4 and model["open"] == stats["open"] == 4
    assert {(i["kind"], i["source"]["activity_name"], i["target"]["activity_name"]) for i in model["items"]} >= {
        ("merged", "Vital signs, weight", "Vital signs, height, weight"),
        ("separate", "Hematology/serum chemistry", "Coagulation/serum chemistry")}
    assert 'class="comp start-open" id="matches"' in generate_consolidated_html(plain, None, _row_names(files), None)
    doc = _doc("NCT01847274", {"op": "keep", "source": HEMA_T2, "target": COAG_T1},
               {"op": "split", "source": VITALS_T3, "target": VITALS_T1})
    out = consolidate_tables("NCT01847274", files, doc)
    model = build_matches_model(out, _row_names(files), doc)
    assert len(model["items"]) == 4 and model["open"] == 2
    split = next(i for i in model["items"] if i["kind"] == "split")
    assert split["source"] == VITALS_T3 and split["target"] == VITALS_T1
    assert split["decision"] == {"correction_id": "ccorr-002", "op": "split", "reason": "test",
                                 "by": "test", "at": "2026-10-03T00:00:00Z"}
