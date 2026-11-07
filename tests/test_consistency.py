"""
Cross-study consistency check (soa2usdm.consistency) — the outcome rule, the queue, the within-study
list, the flags, the stale-routing stop, and the published queue.

The rule cases use small grain / routing dicts in the published shapes, so they need no collections
checkout; the published-file tests run where the collections are present.
"""
import json
from pathlib import Path

import jsonschema
import pytest

from soa2usdm import config
from soa2usdm import consistency as cc

SCHEMAS = Path(__file__).parent.parent / "schemas"


def act(x, name, grain, source="rule", role=None):
    return {"xact_id": x, "activity_name": name, "phrase": cc.normalise(name), "grain": grain,
            "source": source, "role": role}


def row(x, name, status, domain=None, candidates=(), member=None, panel=None):
    r = {"xact_id": x, "activity_name": name, "status": status, "domain": domain,
         "candidates": list(candidates), "route_source": "test identity",
         "grain": {"grain": "named test", "source": "panel member" if member else "rule"}}
    if member:
        r |= {"member_id": member, "panel_name": panel}
    return r


def study(pid, acts, rows, not_reached=(), collection="c1", decisions=None):
    grain = {"protocol_id": pid, "activities": acts}
    routing = {"protocol_id": pid, "rows": rows, "not_reached": list(not_reached)}
    return cc.study_items(collection, grain, routing, decisions)


NO_FLAGS = {"schema_name": cc.FLAGS_SCHEMA_NAME, "flags": []}


# ---------------------------------------------------------------------------
# Outcome rule
# ---------------------------------------------------------------------------
def test_outcome_rule():
    assert cc.outcome(None) == {"status": "no own row", "domain": None, "candidates": []}
    assert cc.outcome({"status": "routed", "domain": "VS", "candidates": ["CV", "VS"]})["candidates"] == []
    assert cc.outcome({"status": "open", "domain": None, "candidates": ["VS", "CV"]})["candidates"] == ["CV", "VS"]
    assert cc.outcome({"status": "weak", "domain": None, "candidates": ["LB"]})["candidates"] == ["LB"]
    # not routed: the candidates come only from the grain-kind fallback and are not compared
    assert cc.outcome({"status": "not routed", "domain": None, "candidates": ["LB", "MB"]})["candidates"] == []
    with pytest.raises(ValueError):
        cc.outcome({"status": "maybe", "domain": None, "candidates": []})


def test_not_routed_with_different_fallback_kinds_is_not_queued():
    a = study("S1", [act("x1", "Urine pregnancy", "named test", "ai_proposed")],
              [row("x1", "Urine pregnancy", "not routed", candidates=["LB", "MB"])])
    b = study("S2", [act("x1", "Urine pregnancy", "named test", "ai_proposed")],
              [row("x1", "Urine pregnancy", "not routed")])
    q = cc.build_queue(a + b, NO_FLAGS)
    assert q["counts"]["phrases_in_two_or_more_studies"] == 1
    assert q["queue"] == []


def test_panel_reasons_and_other_grains_are_all_no_own_row():
    a = study("S1", [act("x1", "ECG", "panel")], [], [{"xact_id": "x1", "reason": "panel, not split"}])
    b = study("S2", [act("x1", "ECG", "procedure", "ai_proposed")], [])
    c = study("S3", [act("x1", "ECG", "panel")], [],
              [{"xact_id": "x1", "reason": "panel, members from protocol context"}])
    items = a + b + c
    assert {i["reach"] for i in items} == {"panel, not split", "grain procedure", "panel, members from protocol context"}
    assert cc.build_queue(items, NO_FLAGS)["queue"] == []


def test_section_headers_left_out():
    items = study("S1", [act("x1", "Screening", "other", role="section header")], [])
    assert items == []


def test_different_routing_outcome_queued_standalone_and_members_together():
    a = study("S1", [act("x1", "Weight", "named test")], [row("x1", "Weight", "open", candidates=["CV", "VS"])])
    b = study("S2", [act("x1", "Vital signs (weight, pulse)", "panel")],
              [row("x1", "weight", "routed", "VS", member="m01", panel="Vital signs (weight, pulse)")],
              [{"xact_id": "x1", "reason": "panel, split from label"}])
    q = cc.build_queue(a + b, NO_FLAGS)
    assert [g["phrase"] for g in q["queue"]] == ["weight"]
    g = q["queue"][0]
    assert g["studies"] == 2 and g["items_count"] == {"standalone": 1, "member": 1}
    assert {cc.outcome_label(o["outcome"]) for o in g["outcomes"]} == {"open CV|VS", "routed VS"}
    # the panel label itself is an item of its own (no own row), under its own phrase
    assert q["counts"]["items"] == {"standalone": 2, "member": 1}


def test_open_with_different_candidates_queued():
    a = study("S1", [act("x1", "HR", "named test")], [row("x1", "HR", "open", candidates=["CV", "VS"])])
    b = study("S2", [act("x1", "HR", "named test")], [row("x1", "HR", "open", candidates=["EG", "VS"])])
    assert len(cc.build_queue(a + b, NO_FLAGS)["queue"]) == 1


def test_same_study_twice_is_not_cross_study_but_within_study():
    a = study("S1", [act("x1", "HBV DNA", "named test"), act("x2", "Hepatitis (HBV DNA)", "panel")],
              [row("x1", "HBV DNA", "weak", candidates=["LB", "MB"]),
               row("x2", "HBV DNA", "routed", "MB", member="m01", panel="Hepatitis (HBV DNA)")],
              [{"xact_id": "x2", "reason": "panel, split from label"}])
    q = cc.build_queue(a, NO_FLAGS)
    assert q["queue"] == []
    assert [(w["protocol_id"], w["phrase"]) for w in q["within_study"]] == [("S1", "hbv dna")]


def test_prompt_version_only_for_ai_decisions():
    dec = {"decisions": [{"phrase": "biomarkers", "prompt_version": "1.6.0"}]}
    items = study("S1", [act("x1", "Biomarkers", "named test", "ai_proposed"), act("x2", "Weight", "named test")],
                  [row("x1", "Biomarkers", "not routed"), row("x2", "Weight", "open", candidates=["CV", "VS"])],
                  decisions=dec)
    assert {i["phrase"]: i["prompt_version"] for i in items} == {"biomarkers": "1.6.0", "weight": None}


def test_named_test_without_row_or_reason_stops():
    with pytest.raises(ValueError, match="no routing row"):
        study("S1", [act("x1", "Weight", "named test")], [])


def test_own_row_for_non_named_test_stops():
    with pytest.raises(ValueError, match="own routing row"):
        study("S1", [act("x1", "ECG", "procedure")], [row("x1", "ECG", "open", candidates=["EG"])])


# ---------------------------------------------------------------------------
# Flags
# ---------------------------------------------------------------------------
def test_flag_shows_every_item_of_the_phrase():
    a = study("S1", [act("x1", "Participant returns device", "other", "ai_proposed")], [])
    b = study("S2", [act("x1", "Participant returns device", "other", "ai_proposed")], [])
    flags = {"schema_name": cc.FLAGS_SCHEMA_NAME, "flags": [
        {"phrase": "participant returns device", "studies": [{"collection": "c1", "protocol_id": "S1"}],
         "note": "n", "raised_in": "r"}]}
    q = cc.build_queue(a + b, flags)
    assert q["queue"] == [] and q["counts"]["flags"] == 1
    assert [i["protocol_id"] for i in q["flags"][0]["group"]["items"]] == ["S1", "S2"]


def test_flag_for_missing_study_or_unnormalised_phrase_stops():
    a = study("S1", [act("x1", "Survival assessment", "other", "ai_proposed")], [])
    missing = {"schema_name": cc.FLAGS_SCHEMA_NAME, "flags": [
        {"phrase": "survival assessment", "studies": [{"collection": "c1", "protocol_id": "S9"}],
         "note": "n", "raised_in": "r"}]}
    with pytest.raises(ValueError, match="no item"):
        cc.build_queue(a, missing)
    raw = {"schema_name": cc.FLAGS_SCHEMA_NAME, "flags": [
        {"phrase": "Survival assessment", "studies": [{"collection": "c1", "protocol_id": "S1"}],
         "note": "n", "raised_in": "r"}]}
    with pytest.raises(ValueError, match="not normalised"):
        cc.build_queue(a, raw)


# ---------------------------------------------------------------------------
# Reviews (1.1)
# ---------------------------------------------------------------------------
def _two_weights():
    a = study("S1", [act("x1", "Weight", "named test")], [row("x1", "Weight", "open", candidates=["CV", "VS"])])
    b = study("S2", [act("x1", "Vital signs (weight)", "panel")],
              [row("x1", "weight", "routed", "VS", member="m01", panel="Vital signs (weight)")],
              [{"xact_id": "x1", "reason": "panel, split from label"}])
    return a + b


def _review(*entries):
    return {"schema_name": cc.REVIEW_SCHEMA_NAME, "reviews": list(entries)}


def _entry(phrase, seen, result="accept", goes_to=None, kind="queue"):
    return {"subject": {"kind": kind, "phrase": phrase}, "outcomes_seen": seen, "result": result,
            "note": "n", "goes_to": goes_to, "reviewed_on": "2026-11-07"}


def test_review_attached_and_counted():
    q = cc.build_queue(_two_weights(), NO_FLAGS, _review(_entry("weight", ["open CV|VS", "routed VS"])))
    assert q["queue"][0]["review"]["result"] == "accept"
    assert q["queue"][0]["review"]["changed_since_review"] is False
    assert (q["counts"]["reviewed"], q["counts"]["not_reviewed"], q["counts"]["changed_since_review"]) == (1, 0, 0)


def test_review_marks_changed_outcomes():
    q = cc.build_queue(_two_weights(), NO_FLAGS, _review(_entry("weight", ["open CV|VS", "routed CV"])))
    assert q["queue"][0]["review"]["changed_since_review"] is True
    assert q["counts"]["changed_since_review"] == 1


def test_reviewed_subject_that_left_the_queue_is_listed():
    q = cc.build_queue(_two_weights(), NO_FLAGS,
                       _review(_entry("hiv", ["not routed", "routed MB"], "matching fix", "step 4")))
    assert [x["subject"]["phrase"] for x in q["left_queue_since_review"]] == ["hiv"]
    assert q["counts"]["not_reviewed"] == 1 and q["counts"]["left_queue_since_review"] == 1


def test_review_goes_to_must_match_result():
    with pytest.raises(ValueError, match="goes to"):
        cc.build_queue(_two_weights(), NO_FLAGS, _review(_entry("weight", ["open CV|VS", "routed VS"],
                                                                "matching fix", None)))


def test_review_subject_twice_or_unsorted_outcomes_stops():
    e = _entry("weight", ["open CV|VS", "routed VS"])
    with pytest.raises(ValueError, match="twice"):
        cc.build_queue(_two_weights(), NO_FLAGS, _review(e, e))
    with pytest.raises(ValueError, match="sorted"):
        cc.build_queue(_two_weights(), NO_FLAGS, _review(_entry("weight", ["routed VS", "open CV|VS"])))


def test_review_within_study_subject_keyed_by_study():
    items = study("S1", [act("x1", "HBV DNA", "named test"), act("x2", "Hepatitis (HBV DNA)", "panel")],
                  [row("x1", "HBV DNA", "weak", candidates=["LB", "MB"]),
                   row("x2", "HBV DNA", "routed", "MB", member="m01", panel="Hepatitis (HBV DNA)")],
                  [{"xact_id": "x2", "reason": "panel, split from label"}])
    e = {"subject": {"kind": "within_study", "phrase": "hbv dna", "collection": "c1", "protocol_id": "S1"},
         "outcomes_seen": ["routed MB", "weak LB|MB"], "result": "routing mechanism", "note": "n",
         "goes_to": "step 5", "reviewed_on": "2026-11-07"}
    q = cc.build_queue(items, NO_FLAGS, _review(e))
    assert q["within_study"][0]["review"]["result"] == "routing mechanism"


# ---------------------------------------------------------------------------
# Published files
# ---------------------------------------------------------------------------
QUEUE_JSON, QUEUE_HTML = cc.queue_paths()
needs_queue = pytest.mark.skipif(not QUEUE_JSON.exists(), reason="needs the collections checkout with the queue")


@needs_queue
def test_flags_file_validates():
    schema = json.loads((SCHEMAS / "soa2usdm-consistency-flags.schema.json").read_text())
    jsonschema.validate(json.loads(cc.flags_path().read_text()), schema)


@needs_queue
def test_review_file_validates():
    schema = json.loads((SCHEMAS / "soa2usdm-consistency-review.schema.json").read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(json.loads(cc.review_path().read_text()), schema)


@needs_queue
def test_queue_file_validates():
    schema = json.loads((SCHEMAS / "soa2usdm-consistency-queue.schema.json").read_text())
    jsonschema.Draft7Validator.check_schema(schema)
    jsonschema.validate(json.loads(QUEUE_JSON.read_text()), schema)


@needs_queue
def test_queue_file_current():
    """The published queue is what the check gives on the files now on disk (timestamp aside)."""
    published = json.loads(QUEUE_JSON.read_text())
    fresh = cc.generate()
    for q in (published, fresh):
        del q["generated_at"]
    assert published == fresh, "consistency queue is stale: rerun python -m soa2usdm.consistency"
    assert QUEUE_HTML.exists()
