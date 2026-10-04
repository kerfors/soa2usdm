#!/usr/bin/env python3
"""Build the architecture explainer page docs/schema-chain.html from the schema files.

One infographic, read top to bottom:
  1. the constructs of an SoA table (the blocks of the extraction schema),
  2. what each construct becomes in the resolved and the consolidated schema,
  3. how corrections work (the two sidecar schemas),
  4. USDM Instantiation, as work in progress (notes only).

Block descriptions, versions and enum values are read from schemas/*.json. Every
field path the page names is checked against its schema; a path that no longer
exists stops the build.

Usage: python tools/build_explainer.py
"""
import json
from html import escape
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SCHEMAS = ROOT / "schemas"
OUT = ROOT / "docs"
BLOB = "https://github.com/kerfors/soa2usdm/blob/main/schemas/"

FILES = {
    "extraction": "soa-table-extraction.schema.json",
    "corrections": "soa-table-corrections.schema.json",
    "resolved": "soa-table-resolved.schema.json",
    "ccorr": "soa-consolidation-corrections.schema.json",
    "consolidated": "soa-tables-consolidated.schema.json",
    "manifest": "usdm-manifest.schema.json",
}

LAYERS = [
    {"id": "extraction", "tag": "Layer 1", "name": "Extraction", "question": "What does this table show?",
     "writer": "model", "by": "written by the model, one Claude pass", "scope": "one file per table",
     "address": "Addressed by position: row, column, page"},
    {"id": "resolved", "tag": "Layer 2", "name": "Resolution", "question": "What precisely is in this table?",
     "writer": "program", "by": "derived by program", "scope": "one file per table",
     "address": "Addressed by per-table ids: prop-NNN, col-NNN, act-NNN, annot-NNN"},
    {"id": "consolidated", "tag": "Layer 3", "name": "Consolidation", "question": "What was the protocol expressing?",
     "writer": "program", "by": "derived by program", "scope": "one file per protocol",
     "address": "Addressed by cross-table ids: xact-NNN, xcol-NNN, xannot-NNN, each listing its source ids"},
]

CONSTRUCTS = [
    {"id": "properties", "name": "Schedule properties", "block": "schedule_properties",
     "where": "the header rows",
     "cells": [
         {"block": "schedule_properties[]", "fields": ["row_position", "property_name", "property_type", "hierarchical_level"],
          "note": "One entry per header row."},
         {"block": "schedule_properties[]", "fields": ["property_id", "parent_property_id", "linked_annotation_ids"],
          "note": "Each row gets an id and its parent."},
         {"block": "property_hierarchy[]", "fields": ["property_id", "hierarchical_level", "property_name", "property_type"],
          "note": "One hierarchy across the tables."},
     ]},
    {"id": "grid", "name": "Schedule grid", "block": "schedule_grid",
     "where": "the header cells",
     "cells": [
         {"block": "schedule_grid[]", "fields": ["row_position", "column_position", "cell_value", "merged_cell_range"],
          "note": "One entry per header cell."},
         {"block": "schedule_columns[]", "fields": ["column_id", "column_position", "column_values", "composite_label"],
          "note": "Header cells read downwards become columns."},
         {"block": "timeline_segments{}[]", "fields": ["xcol_id", "segment", "property_values", "source_columns"],
          "note": "Columns of all tables aligned into segments (main, domain, track, subsidiary)."},
     ]},
    {"id": "activities", "name": "Activities", "block": "activities",
     "where": "the body rows",
     "cells": [
         {"block": "activities[]", "fields": ["row_position", "source_page", "activity_name", "activity_name_source.indentation_level"],
          "note": "One entry per body row, with the page it was read from."},
         {"block": "activities[]", "fields": ["activity_id", "parent_activity_id", "hierarchy_level", "is_section_header"],
          "note": "Each row gets an id; the parent is derived from the indentation level."},
         {"block": "unified_activities[]", "fields": ["xact_id", "source_refs", "match_status", "near_matches"],
          "note": "Rows of several tables matched into one activity. The source rows stay listed."},
     ]},
    {"id": "schedule", "name": "Activity schedule", "block": "activity_schedule",
     "where": "the body cells",
     "cells": [
         {"block": "activity_schedule[]", "fields": ["row_position", "column_position", "cell_value", "method"],
          "note": "One entry per non-empty body cell."},
         {"block": "activity_schedule[]", "fields": ["activity_id", "column_id", "cell_value", "cell_value_type"],
          "note": "Positions become id references."},
         {"block": "schedule_matrix[]", "fields": ["xact_id", "xcol_id", "consolidated_value", "source_values"],
          "note": "One cell per unified activity and unified column. The value of each source table is kept."},
     ]},
    {"id": "annotations", "name": "Annotations", "block": "annotations",
     "where": "markers and the notes they point to",
     "cells": [
         {"block": "annotations[]", "fields": ["annotation_marker", "annotation_type", "annotation_text", "marker_locations"],
          "note": "Marker, text, and every place the marker is printed."},
         {"block": "annotations[]", "fields": ["annotation_id", "referenced_elements", "annotation_scope", "document_references"],
          "note": "Bound to the elements it applies to."},
         {"block": "unified_annotations[]", "fields": ["xannot_id", "source_occurrences", "referenced_xacts", "referenced_xcols"],
          "note": "Identical text deduplicated. Every occurrence is kept."},
     ]},
]

TABLE_ENTRY = [
    (["id"], "The entry's own id."),
    (["target"], "Which block of the extraction it acts on."),
    (["op"], "What it does."),
    (["match"], "Key fields that locate the entry, e.g. row and column position."),
    (["set", "field", "value"], "What to write."),
    (["reason", "by", "at"], "Why, who, when."),
    (["source_ref"], "Where on the printed page the correction is grounded."),
    (["review_item"], "The judgement call this entry answers, when it answers one."),
]

MATCH_ENTRY = [
    (["id"], "The entry's own id."),
    (["op"], "What is decided about a pair of rows."),
    (["source", "target"], "The two source rows, named by table_number + activity_id, with activity_name as a check."),
    (["reason", "by", "at"], "Why, who, when."),
]

CHECKS = [
    ("extraction", "review_items[].id"), ("extraction", "review_items[].severity"),
    ("extraction", "review_items[].call_made"), ("extraction", "review_items[].alternative"),
    ("extraction", "table_metadata.table_type"), ("extraction", "table_metadata.page_start"),
    ("extraction", "table_metadata.page_end"),
    ("corrections", "target_extraction"), ("corrections", "corrections[].source_ref.page"),
    ("ccorr", "corrections[].source.table_number"), ("ccorr", "corrections[].source.activity_id"),
    ("ccorr", "corrections[].source.activity_name"),
    ("consolidated", "unified_activities[].source_refs[].decision.correction_id"),
    ("consolidated", "unified_activities[].source_refs[].decision.op"),
    ("consolidated", "unified_activities[].source_refs[].table_num"),
    ("consolidated", "unified_activities[].source_refs[].activity_id"),
    ("consolidated", "timeline_segments{}[].source_columns[].column_id"),
    ("consolidated", "unified_annotations[].source_occurrences[].annotation_id"),
    ("consolidated", "consolidation_metadata.corrections_applied"),
    ("consolidated", "unified_activities[].parent_xact_id"),
    ("consolidated", "timeline_segments{}[].composite_label"),
    ("consolidated", "timeline_segments{}[].property_values"),
    ("consolidated", "schedule_matrix[].consolidated_value"),
    ("consolidated", "unified_annotations[].cell_references"),
    ("manifest", "epochAxis.property"), ("manifest", "epochAxis.map"),
    ("manifest", "timingAxis.property"), ("manifest", "encounterAxis.property"),
]


def load(name):
    return json.loads((SCHEMAS / name).read_text(encoding="utf-8"))


def deref(schema, node):
    while "$ref" in node:
        target = schema
        for part in node["$ref"].lstrip("#/").split("/"):
            target = target[part]
        node = target
    return node


def child(schema, node, name):
    node = deref(schema, node)
    if name in node.get("properties", {}):
        return node["properties"][name]
    for comb in ("oneOf", "anyOf", "allOf"):
        for option in node.get(comb, []):
            found = child(schema, option, name)
            if found is not None:
                return found
    return None


def resolve(schema, path):
    """Return the schema node at path. 'a[]' steps into array items, 'a{}' into the values of a keyed object."""
    node = schema
    for token in path.split("."):
        name = token.replace("[]", "").replace("{}", "")
        node = child(schema, node, name)
        if node is None:
            raise KeyError(f"{schema['title']}: no field '{name}' in path '{path}'")
        if "{}" in token:
            node = deref(schema, node)["additionalProperties"]
        if "[]" in token:
            node = deref(schema, node)["items"]
    target = dict(deref(schema, node))
    if "description" in node:
        target["description"] = node["description"]
    return target


def version(schema):
    prop = schema["properties"]["schema_version"]
    return prop["enum"][-1] if "enum" in prop else prop["const"]


def code(text, title=""):
    tip = f' title="{escape(title, quote=True)}"' if title else ""
    return f"<code{tip}>{escape(text)}</code>"


def schema_link(key, schemas):
    name = FILES[key].replace(".schema.json", "")
    return f'<a href="{BLOB}{FILES[key]}">{escape(name)}</a> v{escape(version(schemas[key]))}'


def build_cards(schemas):
    out = []
    for number, construct in enumerate(CONSTRUCTS, 1):
        description = schemas["extraction"]["properties"][construct["block"]]["description"]
        out.append(
            f'<div class="card c-{construct["id"]}" data-c="{construct["id"]}">'
            f'<span class="num">{number}</span>'
            f'<div><b>{escape(construct["name"])}</b> <span class="where">{escape(construct["where"])}</span>'
            f'<div class="blk">{code(construct["block"])}</div>'
            f'<p>{escape(description)}</p></div></div>')
    return "\n".join(out)


def build_matrix(schemas):
    out = ['<div class="mx-corner"></div>']
    for layer in LAYERS:
        out.append(
            f'<div class="mx-head w-{layer["writer"]}">'
            f'<div class="tag">{escape(layer["tag"])}</div><h3>{escape(layer["name"])}</h3>'
            f'<div class="q">{escape(layer["question"])}</div>'
            f'<div class="meta"><span class="pill {layer["writer"]}">{escape(layer["by"])}</span> {escape(layer["scope"])}</div>'
            f'<div class="sch">{schema_link(layer["id"], schemas)}</div></div>')
    for number, construct in enumerate(CONSTRUCTS, 1):
        out.append(
            f'<div class="mx-row c-{construct["id"]}" data-c="{construct["id"]}">'
            f'<span class="num">{number}</span><b>{escape(construct["name"])}</b></div>')
        for layer, cell in zip(LAYERS, construct["cells"]):
            schema = schemas[layer["id"]]
            fields = []
            for field in cell["fields"]:
                node = resolve(schema, f'{cell["block"]}.{field}')
                fields.append(code(field, node.get("description", "")))
            shown = cell["block"].replace("{}", ".<segment>")
            out.append(
                f'<div class="mx-cell c-{construct["id"]}" data-c="{construct["id"]}">'
                f'<div class="blk">{code(shown)}</div>'
                f'<div class="flds">{" ".join(fields)}</div>'
                f'<p>{escape(cell["note"])}</p></div>')
    out.append('<div class="mx-foot-label">How an element is addressed</div>')
    for layer in LAYERS:
        out.append(f'<div class="mx-foot">{escape(layer["address"])}</div>')
    return "\n".join(out)


def build_entry(schema, rows, chips):
    out = []
    for names, text in rows:
        for name in names:
            resolve(schema, f"corrections[].{name}")
        extra = ""
        if names[0] in chips:
            extra = '<div class="chips">' + "".join(chips[names[0]]) + "</div>"
        out.append(f'<tr><td>{" ".join(code(n) for n in names)}</td><td>{escape(text)}{extra}</td></tr>')
    return "\n".join(out)


def main():
    schemas = {key: load(name) for key, name in FILES.items()}
    for key, path in CHECKS:
        resolve(schemas[key], path)

    construct_of = {c["block"]: c["id"] for c in CONSTRUCTS}
    targets = resolve(schemas["corrections"], "corrections[].target")["enum"]
    table_ops = resolve(schemas["corrections"], "corrections[].op")["enum"]
    match_ops = resolve(schemas["ccorr"], "corrections[].op")["enum"]
    table_chips = {
        "target": [f'<span class="chip c-{construct_of.get(t, "other")}">{escape(t)}</span>' for t in targets],
        "op": [f'<span class="chip">{escape(o)}</span>' for o in table_ops],
    }
    match_chips = {"op": [f'<span class="chip">{escape(o)}</span>' for o in match_ops]}

    parts = {
        "__CARDS__": build_cards(schemas),
        "__MATRIX__": build_matrix(schemas),
        "__TABLE_ENTRY__": build_entry(schemas["corrections"], TABLE_ENTRY, table_chips),
        "__MATCH_ENTRY__": build_entry(schemas["ccorr"], MATCH_ENTRY, match_chips),
        "__CORR_SCHEMA__": schema_link("corrections", schemas),
        "__CCORR_SCHEMA__": schema_link("ccorr", schemas),
        "__MANIFEST_SCHEMA__": schema_link("manifest", schemas),
    }
    html = (Path(__file__).parent / "explainer_schema_chain.template.html").read_text(encoding="utf-8")
    for key, value in parts.items():
        if key not in html:
            raise KeyError(f"template has no placeholder {key}")
        html = html.replace(key, value)
    OUT.mkdir(exist_ok=True)
    target = OUT / "schema-chain.html"
    target.write_text(html, encoding="utf-8")
    print(f"wrote {target.relative_to(ROOT)} ({len(html):,} bytes)")


if __name__ == "__main__":
    main()
