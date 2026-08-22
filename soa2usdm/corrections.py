"""
Human corrections to raw extractions (traceability layer).

The raw v3.0 extraction is immutable. Verified human corrections live in a
sidecar `*_corrections.json` and are applied to produce `*_extraction.verified.json`,
which resolve consumes in place of the raw file.

    verified = apply_corrections(raw, corrections)

Each correction is source-linked and self-describing (reason, source_ref, by, at),
so the corrections corpus doubles as a feedback dataset for prompt refinement.
"""
import copy
import json
from pathlib import Path

from . import config
from .base import PipelineStepBase

# Extraction arrays a correction may target.
TARGETS = {
    "schedule_properties",
    "schedule_grid",
    "activities",
    "activity_schedule",
    "annotations",
    "review_items",
}


def apply_corrections(raw: dict, corrections_doc: dict) -> dict:
    """Apply a corrections sidecar to a raw extraction dict, returning a new dict.

    Ops (fail fast on ambiguity):
        add     -- append `set` as a new entry to the target array
        set     -- update the single entry matching `match` with `set`
        remove  -- drop entries matching `match` (must hit at least one)
        confirm -- change nothing; records that the review item named in
                   `review_item` was examined and the call kept

    A correction may name a `review_item` (an id from the extraction's
    `review_items`); the id must exist, because that reference is the only
    record that the item was decided.
    """
    doc = copy.deepcopy(raw)
    known_items = {item["id"] for item in raw.get("review_items", [])}
    for c in corrections_doc["corrections"]:
        target = c["target"]
        if target not in TARGETS:
            raise ValueError(f"Correction {c['id']}: unknown target '{target}'")
        op = c["op"]
        if "review_item" in c and c["review_item"] not in known_items:
            raise ValueError(f"Correction {c['id']}: review_item '{c['review_item']}' is not in the extraction's review_items")
        if op == "confirm":
            if "review_item" not in c:
                raise ValueError(f"Correction {c['id']}: 'confirm' requires 'review_item'")
            continue
        arr = doc.get(target)
        if target == "review_items" and arr is None and op == "add":
            arr = doc[target] = []
        if not isinstance(arr, list):
            raise ValueError(f"Correction {c['id']}: target array '{target}' missing in extraction")
        if op == "add":
            arr.append(c["set"])
            if target == "review_items":
                known_items.add(c["set"]["id"])
        elif op == "set":
            match = c["match"]
            hits = [item for item in arr if all(item.get(k) == v for k, v in match.items())]
            if len(hits) != 1:
                raise ValueError(f"Correction {c['id']}: 'set' match {match} hit {len(hits)} entries (expected 1)")
            hits[0].update(c["set"])
        elif op == "remove":
            match = c["match"]
            kept = [item for item in arr if not all(item.get(k) == v for k, v in match.items())]
            if len(kept) == len(arr):
                raise ValueError(f"Correction {c['id']}: 'remove' match {match} hit no entries")
            doc[target] = kept
        else:
            raise ValueError(f"Correction {c['id']}: unknown op '{op}'")
    return doc


def review_status(extracted_dir: Path) -> dict:
    """Derive the state of a protocol's review items from its extracted/ folder.

    Items come from each table's verified extraction when one exists (a sidecar
    may add items), else from the raw file. An item is decided exactly when a
    correction in that table's sidecar names it in `review_item`; nothing else
    records a decision. Returns {"total", "open", "decided", "items"} where
    items is a list of {"id", "table_number", "decided", "correction_id"}.
    """
    items = []
    for raw_path in sorted(extracted_dir.glob("*_extraction.json")):
        verified = raw_to_verified_path(raw_path)
        src = verified if verified.exists() else raw_path
        with open(src) as f:
            doc = json.load(f)
        decided = {}
        sidecar = raw_to_corrections_path(raw_path)
        if sidecar.exists():
            with open(sidecar) as f:
                for c in json.load(f)["corrections"]:
                    if "review_item" in c:
                        decided.setdefault(c["review_item"], c["id"])
        for item in doc.get("review_items", []):
            items.append({
                "id": item["id"],
                "table_number": doc["table_metadata"]["table_number"],
                "decided": item["id"] in decided,
                "correction_id": decided.get(item["id"]),
            })
    return {
        "total": len(items),
        "open": sum(1 for i in items if not i["decided"]),
        "decided": sum(1 for i in items if i["decided"]),
        "items": items,
    }


def raw_to_corrections_path(raw_path: Path) -> Path:
    return raw_path.with_name(raw_path.name.replace("_extraction.json", "_corrections.json"))


def raw_to_verified_path(raw_path: Path) -> Path:
    return raw_path.with_name(raw_path.stem + ".verified.json")


class ApplyCorrectionsStep(PipelineStepBase):
    """Layer 1.5 -- write `*_extraction.verified.json` for any table that has a
    `*_corrections.json` sidecar. Tables without a sidecar are left untouched
    (resolve reads their raw extraction directly). No-op for uncorrected protocols."""

    step_name = "apply_corrections"

    def execute(self, data: dict) -> dict:
        source = data["source"]
        protocol_id = source["protocol_id"]
        collection = source["collection"]
        extracted_dir = config.get_extracted_dir(protocol_id, collection)

        written = []
        for raw_path in sorted(extracted_dir.glob("*_extraction.json")):
            corr_path = raw_to_corrections_path(raw_path)
            if not corr_path.exists():
                continue
            raw = json.loads(raw_path.read_text())
            corrections_doc = json.loads(corr_path.read_text())
            verified = apply_corrections(raw, corrections_doc)
            verified_path = raw_to_verified_path(raw_path)
            verified_path.write_text(json.dumps(verified, indent=1, ensure_ascii=False))
            written.append(verified_path.name)

        return {"status": "success", "verified_written": written}
