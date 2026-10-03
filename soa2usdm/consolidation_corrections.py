"""
Human decisions on cross-table matches (the Layer 3 sidecar).

Consolidation matches activities across a protocol's tables by name. Whether two
rows are the same activity is a judgement a name score cannot make, so a reviewer's
decision lives in a sidecar next to the consolidated file,
`consolidated/{NCTID}_consolidation_corrections.json`, and `consolidate` reads it
before matching. It is the Layer 3 analogue of the extraction corrections sidecar.

Every entry names source rows, never unified-activity ids (`xact_id` is a counter
in processing order and changes when the input changes). A row is
`{table_number, activity_id, activity_name}`; `activity_name` is carried as a
check and must equal the row's name in the resolved table.

Ops (fail fast on anything stale):
    keep    -- consolidation's result for the pair stands: `source` stays merged
               with `target`, or stays separate from its near match `target`
    split   -- `source` is taken out of the unified activity it shares with
               `target` and becomes an activity of its own
    merge   -- `source` joins the unified activity of `target`
    refines -- `source` (a row, or a whole table given as `{table_number}`)
               details the row `target`; nothing is merged
"""
from pathlib import Path
from typing import Dict, List, Tuple

OPS = ("keep", "split", "merge", "refines")


def corrections_path(consolidated_dir: Path, protocol_id: str) -> Path:
    return consolidated_dir / f"{protocol_id}_consolidation_corrections.json"


def _check_row(cid: str, side: str, row: dict, tables: Dict[int, dict]) -> None:
    """The row must exist in a consolidated (non-reference) table under the stated name."""
    num = row["table_number"]
    if num not in tables:
        raise ValueError(f"Consolidation correction {cid}: {side} table {num} is not a table of this protocol")
    if tables[num]["table_metadata"]["table_type"] == "reference":
        raise ValueError(f"Consolidation correction {cid}: {side} table {num} is a reference table (not consolidated)")
    if "activity_id" not in row:
        return
    hits = [a for a in tables[num]["activities"] if a["activity_id"] == row["activity_id"]]
    if len(hits) != 1:
        raise ValueError(f"Consolidation correction {cid}: {side} row T{num} {row['activity_id']} hit {len(hits)} activities (expected 1)")
    if hits[0]["activity_name"] != row["activity_name"]:
        raise ValueError(
            f"Consolidation correction {cid}: {side} row T{num} {row['activity_id']} is named "
            f"'{hits[0]['activity_name']}', the entry says '{row['activity_name']}'")


def index_corrections(doc: dict, protocol_id: str,
                      tables: Dict[int, dict]) -> Tuple[Dict[Tuple[int, str], dict], List[dict]]:
    """Check a consolidation sidecar against the resolved tables.

    Returns (decisions, refinements): decisions maps a source row
    (table_number, activity_id) to its keep / split / merge entry — one decision
    per source row; refinements is the list of `refines` entries in file order.
    """
    if doc["protocol_id"] != protocol_id:
        raise ValueError(f"Consolidation corrections are for '{doc['protocol_id']}', not '{protocol_id}'")
    decisions: Dict[Tuple[int, str], dict] = {}
    refinements: List[dict] = []
    seen_ids = set()
    for c in doc["corrections"]:
        cid = c["id"]
        if cid in seen_ids:
            raise ValueError(f"Consolidation correction {cid}: id is not unique")
        seen_ids.add(cid)
        op = c["op"]
        if op not in OPS:
            raise ValueError(f"Consolidation correction {cid}: unknown op '{op}'")
        source, target = c["source"], c["target"]
        if "activity_id" not in target:
            raise ValueError(f"Consolidation correction {cid}: 'target' must be a row (table_number, activity_id, activity_name)")
        if "activity_id" not in source and op != "refines":
            raise ValueError(f"Consolidation correction {cid}: only 'refines' takes a whole table as 'source'")
        if source["table_number"] == target["table_number"]:
            raise ValueError(f"Consolidation correction {cid}: source and target are both in table {source['table_number']}")
        _check_row(cid, "source", source, tables)
        _check_row(cid, "target", target, tables)
        if op == "refines":
            refinements.append(c)
            continue
        key = (source["table_number"], source["activity_id"])
        if key in decisions:
            raise ValueError(
                f"Consolidation correction {cid}: source row T{key[0]} {key[1]} already has a decision ({decisions[key]['id']})")
        decisions[key] = c
    return decisions, refinements
