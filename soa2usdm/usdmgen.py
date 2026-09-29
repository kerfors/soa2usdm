"""
USDM Instantiation -- SoA to USDM v4.

Lifts a Layer 3 consolidated SoA table into USDM v4 schedule objects and merges
them into a study shell, producing one conformant USDM v4 document.

The shell and the SoA meet at exactly one attribute, ScheduledInstance.epochId.
That edge is resolved here, from an epochAxis block in the manifest: which
consolidated column property carries the epoch axis, and how its printed values
map to declared epochs. The epoch axis is an interpretation of an extraction,
so it is resolved here and logged as a decision -- it is deliberately
not marked in the Layer 1-3 consolidated schema.

Nothing in the SoA-derived part of the output is invented. Anything the SoA does
not state is either omitted with a decisions entry, or emitted as a flagged
not-stated object by soa2usdm.usdm_manifest.
"""

import json
import re
from pathlib import Path

import yaml

from . import usdm_manifest as manifest_module
from .shellgen import Generator

PROV = "https://kerfors.github.io/soa2usdm/sourceRef"
MARKS = "https://kerfors.github.io/soa2usdm/qualified-marks"
ANNOT = "https://kerfors.github.io/soa2usdm/annotation"

SHELL_PREFIX = "SHELL_"
SOA_PREFIX = "SOA_"

DAY = re.compile(r"^D\s*(-?\d+)\s*(?:\(\s*[±+]/?-?\s*(\d+)\s*\))?$")

# Timing.type binds to C201264 and Timing.relativeToFrom to C201265, both
# non-extensible. These are properties of the model, not readings of a protocol,
# so they live here rather than in a manifest. Verified against USDM_CT.xlsx.
TIMING_TERMS = {
    "timing_fixed": ("C201358", "Fixed Reference"),
    "timing_after": ("C201356", "After"),
    "timing_before": ("C201357", "Before"),
    "start_to_start": ("C201355", "Start to Start"),
}


class SoaBuilder:
    """Consolidated SoA table -> USDM v4 activities, instances, timings, conditions."""

    def __init__(self, consolidated, manifest):
        self.src = consolidated
        self.m = manifest
        self.terms = {**TIMING_TERMS, **manifest["terms"]}
        self.decisions = []
        self.n_code = 0
        self.n_ext = 0

    # ---- primitives ---------------------------------------------------
    def code(self, key):
        self.n_code += 1
        c, decode = self.terms[key]
        return {"id": f"Code_{self.n_code}", "code": c, "codeSystem": "http://www.cdisc.org",
                "codeSystemVersion": self.m["study"]["ctVersion"], "decode": decode,
                "instanceType": "Code"}

    def ext(self, url, value):
        self.n_ext += 1
        return {"id": f"ExtensionAttribute_{self.n_ext}", "url": url,
                "valueString": value, "instanceType": "ExtensionAttribute"}

    def decide(self, kind, ref, text):
        self.decisions.append({"kind": kind, "ref": ref, "text": text})

    # ---- source access ------------------------------------------------
    def columns(self):
        out = []
        for segment, cols in self.src["timeline_segments"].items():
            for col in cols:
                out.append((segment, col))
        return out

    @staticmethod
    def prop_value(col, property_id, hierarchy):
        ptype = next((p["property_type"] for p in hierarchy
                      if p["property_id"] == property_id), None)
        if ptype is None:
            raise KeyError(f"property {property_id} is not in property_hierarchy")
        for pv in col["property_values"]:
            if pv["property_type"] == ptype:
                return pv["value"]
        return None

    # ---- activities ---------------------------------------------------
    def activities(self):
        acts = sorted(self.src["unified_activities"], key=lambda a: a["display_order"])
        by_parent = {}
        for a in acts:
            by_parent.setdefault(a["parent_xact_id"], []).append(a)

        out = {}
        for a in acts:
            out[a["xact_id"]] = {
                "id": f"Activity_{a['xact_id']}",
                "name": a["activity_name"],
                "label": a["activity_name"],
                "description": None,
                "definedProcedures": [],
                "biomedicalConceptIds": [], "bcSurrogateIds": [], "bcCategoryIds": [],
                "childIds": [f"Activity_{c['xact_id']}"
                             for c in by_parent.get(a["xact_id"], [])],
                "previousId": None, "nextId": None,
                "notes": [], "extensionAttributes": [],
                "instanceType": "Activity",
            }

        for parent, siblings in by_parent.items():
            for i, a in enumerate(siblings):
                node = out[a["xact_id"]]
                node["previousId"] = f"Activity_{siblings[i-1]['xact_id']}" if i else None
                node["nextId"] = (f"Activity_{siblings[i+1]['xact_id']}"
                                  if i < len(siblings) - 1 else None)

        n_parents = sum(1 for a in acts if by_parent.get(a["xact_id"]))
        self.decide(
            "chaining-rule", "Activity.previousId/nextId",
            "Activities are chained within their parent, never across a parent "
            f"boundary. {n_parents} section headers carry childIds; their children "
            "form separate chains. Same rule shellgen applies to criteria groups: "
            "a chain is a sequence within one group, not a flattening of the tree.")
        return [out[a["xact_id"]] for a in acts]

    # ---- encounters ---------------------------------------------------
    def encounters(self, cols):
        axis = self.m.get("encounterAxis")
        if not axis:
            types = sorted({p["property_type"] for p in self.src["property_hierarchy"]})
            self.decide(
                "no-encounters", "Encounter",
                "No encounterAxis declared. This SoA types its column properties as "
                f"{types} -- none of them labels the columns as visits, so naming an "
                "Encounter per column would assert a classification the table does "
                "not print. Encounters are omitted; ScheduledActivityInstance."
                "encounterId is 0..1 so the document stays conformant. To emit them, "
                "declare encounterAxis in the manifest, the same shape as epochAxis.")
            return [], {}

        hierarchy = self.src["property_hierarchy"]
        out, by_col = [], {}
        kept = [(seg, c) for seg, c in cols
                if self.prop_value(c, axis["property"], hierarchy)]
        for i, (_seg, col) in enumerate(kept):
            label = self.prop_value(col, axis["property"], hierarchy)
            enc = {
                "id": f"Encounter_{col['xcol_id']}",
                "name": label, "label": label, "description": None,
                "type": self.code(axis["ct"]),
                "environmentalSettings": [], "contactModes": [],
                "previousId": f"Encounter_{kept[i-1][1]['xcol_id']}" if i else None,
                "nextId": (f"Encounter_{kept[i+1][1]['xcol_id']}"
                           if i < len(kept) - 1 else None),
                "scheduledAtId": None, "notes": [], "extensionAttributes": [],
                "instanceType": "Encounter",
            }
            out.append(enc)
            by_col[col["xcol_id"]] = enc["id"]
        return out, by_col

    # ---- instances ----------------------------------------------------
    def instances(self, cols, encounter_by_col, cell_annotations):
        by_col = {}
        for cell in self.src["schedule_matrix"]:
            by_col.setdefault(cell["xcol_id"], []).append(cell)

        out, qualified_total = [], 0
        for _seg, col in cols:
            cells = by_col.get(col["xcol_id"], [])
            act_ids, qualified = [], []
            for cell in cells:
                act_ids.append(f"Activity_{cell['xact_id']}")
                mark = cell["consolidated_value"]
                notes = cell_annotations.get((cell["xact_id"], col["xcol_id"]), [])
                if mark != "X" or notes:
                    qualified.append({"activityId": f"Activity_{cell['xact_id']}",
                                      "mark": mark, "annotations": notes})
            sai = {
                "id": f"ScheduledActivityInstance_{col['xcol_id']}",
                "name": col["xcol_id"], "label": col["composite_label"],
                "description": None,
                "activityIds": act_ids,
                "encounterId": encounter_by_col.get(col["xcol_id"]),
                "epochId": None,
                "timelineId": None, "timelineExitId": None, "defaultConditionId": None,
                "extensionAttributes": [],
                "instanceType": "ScheduledActivityInstance",
            }
            if qualified:
                qualified_total += 1
                sai["extensionAttributes"].append(
                    self.ext(MARKS, json.dumps(qualified, ensure_ascii=False)))
            out.append(sai)

        distinct = {c["consolidated_value"] for c in self.src["schedule_matrix"]}
        self.decide(
            "extension-used", "ScheduledActivityInstance.extensionAttributes",
            f"activityIds is a plain set of references. This SoA prints {len(distinct)} "
            "distinct mark values, so a reference alone loses everything except "
            "'this activity happens in this column'. Non-'X' marks and cell-scoped "
            f"footnote markers are carried in an ExtensionAttribute on {qualified_total} "
            "of the instances. USDM v4 has no cell-scoped annotation that is not a "
            "Condition.")
        return out

    # ---- epoch seam ---------------------------------------------------
    def bind_epochs(self, cols, instances, epoch_ids):
        axis = self.m["epochAxis"]
        hierarchy = self.src["property_hierarchy"]
        by_xcol = {s["id"].split("ScheduledActivityInstance_", 1)[1]: s for s in instances}

        unmapped, bound = [], 0
        for _seg, col in cols:
            value = self.prop_value(col, axis["property"], hierarchy)
            if value is None:
                unmapped.append((col["xcol_id"], None))
                continue
            slug = axis["map"].get(value)
            if slug is None:
                unmapped.append((col["xcol_id"], value))
                continue
            if slug not in epoch_ids:
                raise KeyError(f"epochAxis maps {value!r} to epoch {slug!r}, "
                               "which the manifest does not declare")
            by_xcol[col["xcol_id"]]["epochId"] = epoch_ids[slug]
            bound += 1

        ptype = next(p["property_type"] for p in hierarchy
                     if p["property_id"] == axis["property"])
        self.decide(
            "epoch-axis", "ScheduledInstance.epochId",
            f"Epoch resolved from consolidated property {axis['property']} (typed "
            f"'{ptype}'), {len(axis['map'])} printed values mapped to declared epochs. "
            f"{bound} of {len(cols)} columns bound. This mapping is an interpretation "
            "of the extraction, not a fact the extraction records; it lives here and "
            "in this log rather than in the consolidated schema.")
        if unmapped:
            self.decide(
                "epoch-unbound", ", ".join(c for c, _v in unmapped),
                "Columns with no epoch binding: " +
                "; ".join(f"{c} (printed value {v!r})" for c, v in unmapped) +
                ". epochId is 0..1, so these stay conformant but unplaced.")
        return bound

    # ---- timings ------------------------------------------------------
    def timings(self, cols, instances):
        axis = self.m.get("timingAxis")
        if not axis:
            self.decide("no-timings", "Timing",
                        "No timingAxis declared. Timing is 0..* on ScheduleTimeline, "
                        "so the document is conformant, but no column is positioned "
                        "in time.")
            return []

        hierarchy = self.src["property_hierarchy"]
        anchor = axis["anchor"]
        same_of = axis.get("sameValueOf")
        by_xcol = {c["xcol_id"]: c for _s, c in cols}
        if anchor not in by_xcol:
            raise KeyError(f"timingAxis anchor {anchor!r} is not a column in this SoA")

        def day(col):
            raw = self.prop_value(col, axis["property"], hierarchy)
            if raw is None:
                return None, None, raw
            m = DAY.match(raw.strip())
            if not m:
                return None, None, raw
            return int(m.group(1)), (int(m.group(2)) if m.group(2) else None), raw

        anchor_day, _aw, anchor_raw = day(by_xcol[anchor])
        if anchor_day is None:
            raise ValueError(f"timingAxis anchor {anchor!r} carries {anchor_raw!r}, "
                             "which is not a plain study day")
        anchor_scope = (self.prop_value(by_xcol[anchor], same_of, hierarchy)
                        if same_of else None)

        out, skipped = [], []
        for _seg, col in cols:
            d, window, raw = day(col)
            scope = self.prop_value(col, same_of, hierarchy) if same_of else None
            if d is None:
                skipped.append((col["xcol_id"], raw, "not a plain study day"))
                continue
            if same_of and scope != anchor_scope:
                skipped.append((col["xcol_id"], raw,
                                f"outside the anchor's {same_of} value "
                                f"({scope!r} vs {anchor_scope!r})"))
                continue
            if (d < 0) != (anchor_day < 0) and 0 not in (d, anchor_day):
                raise ValueError(f"column {col['xcol_id']} crosses study day zero "
                                 "relative to the anchor; day arithmetic is not "
                                 "mechanical across that boundary")
            offset = d - anchor_day
            ttype = ("timing_fixed" if offset == 0 else
                     "timing_after" if offset > 0 else "timing_before")
            out.append({
                "id": f"Timing_{col['xcol_id']}",
                "name": col["xcol_id"], "label": raw, "description": None,
                "type": self.code(ttype),
                "value": f"P{abs(offset)}D",
                "valueLabel": raw,
                "relativeToFrom": self.code("start_to_start"),
                "relativeFromScheduledInstanceId":
                    f"ScheduledActivityInstance_{col['xcol_id']}",
                "relativeToScheduledInstanceId":
                    f"ScheduledActivityInstance_{anchor}",
                "windowLower": f"-P{window}D" if window else None,
                "windowUpper": f"P{window}D" if window else None,
                "windowLabel": raw if window else None,
                "extensionAttributes": [],
                "instanceType": "Timing",
            })

        self.decide(
            "timing-derived", "Timing",
            f"{len(out)} timings derived mechanically from property "
            f"{axis['property']}, anchored on {anchor} ({anchor_raw!r}). Only values "
            "matching a plain study day (optionally with a symmetric window) are "
            "converted; the offset is a difference of study days emitted as P<n>D." +
            (f" Columns outside the anchor's {same_of} value are excluded, because a "
             "day number that restarts per cycle is not a study day." if same_of else ""))
        if skipped:
            self.decide(
                "timing-skipped", ", ".join(c for c, _r, _w in skipped),
                "No Timing emitted for: " +
                "; ".join(f"{c} ({raw!r}: {why})" for c, raw, why in skipped) +
                ". Each would need a reading the printed value does not mechanically "
                "supply.")
        return out

    # ---- annotations --------------------------------------------------
    def annotation_index(self, cols):
        """One pass over the annotations. Returns the cell-level index, the
        Conditions, and the attachments still to be made once the objects exist."""
        kept_cols = {c["xcol_id"] for _s, c in cols}

        cell_annotations, conditions, pending = {}, [], []
        n_loose = 0
        for ann in self.src["unified_annotations"]:
            refs = ann.get("cell_references") or []
            if refs:
                for ref in refs:
                    cell_annotations.setdefault(
                        (ref.get("xact_id"), ref.get("xcol_id")), []).append(
                            ann["xannot_id"])
                ctx = sorted({f"ScheduledActivityInstance_{r['xcol_id']}"
                              for r in refs if r.get("xcol_id") in kept_cols})
                applies = sorted({f"Activity_{r['xact_id']}" for r in refs
                                  if r.get("xact_id")})
                conditions.append({
                    "id": f"Condition_{ann['xannot_id']}",
                    "name": ann["xannot_id"],
                    "label": "/".join(ann.get("display_markers") or []) or None,
                    "description": None,
                    "text": ann["annotation_text"],
                    "contextIds": ctx, "appliesToIds": applies,
                    "dictionaryId": None, "notes": [], "extensionAttributes": [],
                    "instanceType": "Condition",
                })
                continue

            payload = json.dumps({"xannot_id": ann["xannot_id"],
                                  "type": ann["annotation_type"],
                                  "markers": ann.get("display_markers"),
                                  "text": ann["annotation_text"]},
                                 ensure_ascii=False)
            targets = [("Activity", f"Activity_{x}")
                       for x in (ann.get("referenced_xacts") or [])]
            targets += [("ScheduledActivityInstance", x)
                        for x in (ann.get("referenced_xcols") or [])
                        if x in kept_cols]
            if targets:
                pending.extend((kind, key, payload) for kind, key in targets)
            else:
                n_loose += 1

        self._n_loose = n_loose
        return cell_annotations, conditions, pending

    def attach_annotations(self, activities, instances, pending, conditions):
        act_by_id = {a["id"]: a for a in activities}
        sai_by_col = {s["id"].split("ScheduledActivityInstance_", 1)[1]: s
                      for s in instances}
        n_act = n_col = 0
        for kind, key, payload in pending:
            if kind == "Activity":
                target = act_by_id.get(key)
                if target is not None:
                    n_act += 1
            else:
                target = sai_by_col.get(key)
                if target is not None:
                    n_col += 1
            if target is not None:
                target["extensionAttributes"].append(self.ext(ANNOT, payload))

        self.decide(
            "annotation-split", "Condition vs ExtensionAttribute",
            f"{len(conditions)} annotations carry cell references and map to Condition "
            "(contextIds x appliesToIds addresses a cell). The rest scope to whole "
            f"activities ({n_act} attachments) or whole columns ({n_col}) and are "
            "carried as ExtensionAttributes: USDM's cell-scoped annotation is "
            "Condition, and a source-section pointer or a definition is not a "
            f"condition. {self._n_loose} annotations reference neither and are not "
            "emitted.")

    # ---- assembly -----------------------------------------------------
    def build(self, epoch_ids):
        cols = self.columns()
        activities = self.activities()
        encounters, encounter_by_col = self.encounters(cols)
        cell_annotations, conditions, pending = self.annotation_index(cols)
        instances = self.instances(cols, encounter_by_col, cell_annotations)
        self.attach_annotations(activities, instances, pending, conditions)
        self.bind_epochs(cols, instances, epoch_ids)
        timings = self.timings(cols, instances)

        segments = sorted(self.src["timeline_segments"])
        if len(segments) > 1:
            self.decide(
                "single-timeline", "ScheduleTimeline",
                f"This SoA has {len(segments)} segments ({', '.join(segments)}). They "
                "are emitted as one timeline; splitting them into sub-timelines is a "
                "separate reading and is not attempted in the minimal build.")

        table_title = self.src["consolidation_metadata"]["source_tables"][0].get(
            "table_title")
        timeline = {
            "id": "ScheduleTimeline_1",
            "name": "Main Timeline", "label": table_title, "description": None,
            "entryCondition": "NOT STATED IN THE SCHEDULE OF ACTIVITIES",
            "mainTimeline": True,
            "instances": instances,
            "entryId": instances[0]["id"],
            "exits": [], "timings": timings,
            "extensionAttributes": [],
            "instanceType": "ScheduleTimeline",
        }
        self.decide("not-derived", "ScheduleTimeline.entryCondition",
                    "Mandatory (1). Not present in the SoA. Emitted as not stated.")

        return {"activities": activities, "encounters": encounters,
                "scheduleTimelines": [timeline], "conditions": conditions}


# ---- id hygiene -------------------------------------------------------
def collect_ids(node, found):
    if isinstance(node, dict):
        if "id" in node and isinstance(node["id"], str):
            found.add(node["id"])
        for v in node.values():
            collect_ids(v, found)
    elif isinstance(node, list):
        for v in node:
            collect_ids(v, found)
    return found


def prefix_ids(node, prefix, ids):
    if isinstance(node, dict):
        return {k: prefix_ids(v, prefix, ids) for k, v in node.items()}
    if isinstance(node, list):
        return [prefix_ids(v, prefix, ids) for v in node]
    if isinstance(node, str) and node in ids:
        return prefix + node
    return node


def duplicate_ids(doc):
    seen, dupes = set(), set()

    def walk(node):
        if isinstance(node, dict):
            i = node.get("id")
            if isinstance(i, str):
                if i in seen:
                    dupes.add(i)
                seen.add(i)
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(doc)
    return sorted(dupes)


def dangling_refs(doc):
    ids = collect_ids(doc, set())
    missing = set()

    def walk(node):
        if isinstance(node, dict):
            for k, v in node.items():
                if k.endswith("Id") and isinstance(v, str) and v not in ids:
                    missing.add(f"{k} -> {v}")
                elif k.endswith("Ids") and isinstance(v, list):
                    for x in v:
                        if isinstance(x, str) and x not in ids:
                            missing.add(f"{k} -> {x}")
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(doc)
    return sorted(missing)


# ---- entry point ------------------------------------------------------
def generate(manifest_path, consolidated_path, outdir, protocol_id=None):
    given = yaml.safe_load(Path(manifest_path).read_text())
    consolidated = json.loads(Path(consolidated_path).read_text())
    protocol_id = protocol_id or consolidated["protocol_id"]

    manifest, not_stated = manifest_module.expand(given)
    shell = Generator(manifest).build()
    n_reflagged = manifest_module.reflag(shell)
    not_stated.append({
        "kind": "not-stated", "ref": "provenance",
        "text": (f"{n_reflagged} not-stated objects carry the not-stated-in-protocol "
                 "flag instead of a source reference. shellgen attributes "
                 "everything it builds to the manifest's documentRef; a "
                 "not-stated object is not a reading of that document."),
    })
    shell_ids = collect_ids(shell, set())
    shell = prefix_ids(shell, SHELL_PREFIX, shell_ids)

    epoch_ids = {e["slug"]: f"{SHELL_PREFIX}StudyEpoch_{e['slug']}"
                 for e in manifest["epochs"]}

    builder = SoaBuilder(consolidated, manifest)
    core = builder.build(epoch_ids)
    core_ids = collect_ids(core, set()) - set(epoch_ids.values())
    core = prefix_ids(core, SOA_PREFIX, core_ids)

    design = shell["study"]["versions"][0]["studyDesigns"][0]
    design["activities"] = core["activities"]
    design["encounters"] = core["encounters"]
    design["scheduleTimelines"] = core["scheduleTimelines"]
    shell["study"]["versions"][0]["conditions"] = core["conditions"]
    shell["systemName"] = "soa2usdm USDM Instantiation"
    shell["systemVersion"] = "0.1"

    decisions = not_stated + builder.decisions
    dupes = duplicate_ids(shell)
    dangling = dangling_refs(shell)
    decisions.append({
        "kind": "id-hygiene", "ref": f"{SHELL_PREFIX} / {SOA_PREFIX}",
        "text": ("Shell and SoA ids are prefixed by producing stage before merging. "
                 "JSON tolerates two objects with the same id in different arrays; "
                 "RDF merges them into one node and the structural layer then reports "
                 f"a maxCount violation that reads nothing like a duplicate id. "
                 f"Duplicates after merge: {len(dupes)}. Dangling references: "
                 f"{len(dangling)}."),
    })

    outdir = Path(outdir)
    outdir.mkdir(parents=True, exist_ok=True)
    doc_path = outdir / f"{protocol_id}_usdm.json"
    dec_path = outdir / f"{protocol_id}_usdm_decisions.json"
    doc_path.write_text(json.dumps(shell, indent=2, ensure_ascii=False))
    dec_path.write_text(json.dumps(decisions, indent=2, ensure_ascii=False))

    return shell, decisions, {"duplicate_ids": dupes, "dangling_refs": dangling}


if __name__ == "__main__":
    import sys
    doc, dec, checks = generate(sys.argv[1], sys.argv[2], sys.argv[3])
    print("decisions:", len(dec))
    print("duplicate ids:", len(checks["duplicate_ids"]))
    print("dangling refs:", len(checks["dangling_refs"]))
