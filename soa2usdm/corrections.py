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
}


def apply_corrections(raw: dict, corrections_doc: dict) -> dict:
    """Apply a corrections sidecar to a raw extraction dict, returning a new dict.

    Ops (fail fast on ambiguity):
        add    -- append `set` as a new entry to the target array
        set    -- update the single entry matching `match` with `set`
        remove -- drop entries matching `match` (must hit at least one)
    """
    doc = copy.deepcopy(raw)
    for c in corrections_doc["corrections"]:
        target = c["target"]
        if target not in TARGETS:
            raise ValueError(f"Correction {c['id']}: unknown target '{target}'")
        arr = doc.get(target)
        if not isinstance(arr, list):
            raise ValueError(f"Correction {c['id']}: target array '{target}' missing in extraction")
        op = c["op"]
        if op == "add":
            arr.append(c["set"])
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
