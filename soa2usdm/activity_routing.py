"""
SoA2USDM Activity Routing (per-study sidecar after the activity grain)

Gives each named test of a study a target SDTMIG v3.4 domain, or the candidate
domains and the question that stays open. Every result cites the rule that fired,
where it matched (activity label, parent activity label, SoA annotation) and the
SDTMIG v3.4 statements it rests on, by Statement_ID and the sha256 of their text.

Rows: grain "named test" rows that are not themselves a parent. Panels (not split)
and named-test parents are listed as not reached. Trigger sources: the activity
label, the parent activity label, and the SoA annotations that reference the row
or its parent. Only the activity label can route a row on its own.

Status:
    routed      one domain, matched in the activity label, no condition, no question
    open        candidate domains and the question the protocol (or CDISC) must settle
    weak        matched only in SoA annotations: the rule domains are hints, the
                candidates come from the grain kind
    not routed  no rule fired: candidates from the grain kind through Domain_Coverage
                (PP left out, per PP-OV and PP-A1)

Test identity (schema 1.1): where no rule fires, the SDTM_Test_Identity hits of the
row's own activity label (from the grain file) are a second source. A strong hit with
one domain routes the row (route_source "test identity"); a strong hit with several
domains makes it open with those domains as candidates; a weak hit gives hints only.
A rule always ranks above the test identity: where a rule fired, the hits are recorded
and change nothing.

Statements: public cdisc-for-ai SDTMIG_Statements only. CDISC members-only
material is not used (documents/activity-routing.md, "Members-only material").
Rule IDs keep the numbering of the wider rule set; RT-2, RT-4, RT-5 and RT-6 rest
on members-only statements alone and are not in this module.

Input: the study's grain file (checked current, activity_grain.load_current_grain)
and its consolidated.json (parents, annotations).

Output: SoA2USDM/routing/<id>_activity_routing.json (schema_name
soa2usdm-activity-routing, schema_version 1.1). Design: documents/activity-routing.md.
"""

import hashlib
import json
import re
import subprocess
from datetime import datetime, timezone
from pathlib import Path

from . import config
from .activity_grain import CDISC_FOR_AI, CONSUMER_KIND, DOMAIN_KIND, load_current_grain

SCHEMA_NAME = "soa2usdm-activity-routing"
SCHEMA_VERSION = "1.1"
SCHEMA_VERSIONS = ("1.0", "1.1")
RULES_VERSION = "1.2.0"

LOOKUP_FILES = {
    "SDTMIG_Statements": ("sdtm-domain-reference/machine_actionable/SDTMIG_Statements.xlsx", "Statements"),
    "Domain_Coverage": ("sdtm-findings-graph/machine_actionable/Domain_Coverage.xlsx", "Domain_Coverage"),
}

STATUSES = ("routed", "open", "weak", "not routed")
WHERE = ("label", "parent_label", "annotation")
ROUTE_SOURCES = ("rule", "test identity")
TEST_IDENTITY_FILE = "SDTM_Test_Identity"

# Domains left out of the fallback, with the SDTMIG v3.4 statements that say why:
# PP holds parameters derived from PC data (PP-OV) and is a derived dataset (PP-A1).
FALLBACK_EXCLUDED = {"PP": ["PP-OV", "PP-A1"]}

NOT_REACHED_PANEL = "panel, not split"
NOT_REACHED_PARENT = "named-test row that is a parent"


def S(statement_id: str, domains: list, condition: str | None = None) -> dict:
    return {"statement_id": statement_id, "domains": domains, "condition": condition}


# A rule is ours: its patterns and our_reading are our reading. The statements are CDISC's,
# cited by Statement_ID; a condition is our reading of what the protocol must settle before
# the statement applies. Code never decides a condition: a condition makes the result open.
RULES = [
    {
        "rule_id": "RT-1",
        "name": "antibody test",
        "patterns": [r"\bantibod(?:y|ies)\b", r"\bnabs?\b", r"\btabs?\b", r"\bbabs?\b", r"\bada\b",
                     r"\b(?:factor\s+(?:ix|viii|9|8)|fix|fviii)\s+inhibitors?\b"],
        "statements": [S("IS-OV", ["IS"]), S("IS-A1", ["IS"]), S("IS-A2", ["IS"]), S("IS-A3", ["IS"])],
        "exception_over": [],
        "our_reading": "nAb, TAb, BAb, ADA and factor IX / VIII inhibitor name antibody tests. 'Inhibitor' "
                       "only as factor IX / VIII inhibitor: SoA footnotes name other inhibitors. Each kind of "
                       "induced antibody falls under one statement: induced by a therapy (IS-A1), to an allergen, "
                       "a microorganism or a self-antigen (IS-A2), any other induced humoral response such as "
                       "anti-HLA (IS-A3). All give IS, so the kind is not settled here: it belongs to the target "
                       "(binding agent).",
    },
    {
        "rule_id": "RT-3",
        "name": "cytokine, chemokine, complement",
        "patterns": [r"\bcytokines?\b", r"\bchemokines?\b", r"\bcomplement\b", r"\binterferon",
                     r"\bifn", r"\bil-?\d+\b"],
        "statements": [S("IS-A6", ["LB"]),
                       S("IS-A4", ["IS"], "a cellular immune response measured by a non-flow-cytometry "
                                          "technique (IS-A4)")],
        "exception_over": [],
        "our_reading": "IFN, interferon and IL-<n> name cytokines. A cytokine test can also be the readout "
                       "of a cellular immune response (for example IFN-gamma ELISpot).",
    },
    {
        "rule_id": "RT-7",
        "name": "flow cytometry",
        "patterns": [r"\bflow cytometr\w*", r"\bfacs\b", r"\b(?:immuno)?phenotyping\b"],
        "statements": [S("IS-A4", ["CP"]), S("CP-OV", ["CP"]), S("CP-A1", ["CP"]), S("CP-A2", ["CP"])],
        "exception_over": [],
        "our_reading": "FACS is flow cytometry. (Immuno)phenotyping names marker-based cell phenotyping "
                       "(CP-A1, CP-A2); 'phenotype' alone does not (e.g. RNA expression associated "
                       "with a phenotype).",
    },
    {
        "rule_id": "RT-8",
        "name": "microbial Ag/Ab combination",
        "patterns": [r"\bag/ab\b"],
        "statements": [S("IS-A5", ["MB"])],
        "exception_over": [{"rule_id": "RT-1", "statement_id": "IS-A5"}],
        "our_reading": "Ag/Ab names an antigen/antibody combination assay.",
    },
    {
        "rule_id": "RT-9",
        "name": "therapeutic drug level",
        "patterns": [r"\bpharmacokinetics?\b", r"\bpk\b", r"\bdrug levels?\b"],
        "statements": [S("PC-OV", ["PC"])],
        "exception_over": [],
        "our_reading": "Pharmacokinetics and PK name drug level measurement.",
    },
    {
        "rule_id": "RT-10",
        "name": "routine laboratory test",
        "patterns": [r"\bh(?:a)?ematology\b", r"\bclinical chemistry\b", r"\burinalysis\b",
                     r"\burine analysis\b"],
        "statements": [S("LB-OV", ["LB"])],
        "exception_over": [],
        "our_reading": "Hematology, clinical chemistry and urinalysis are the examples LB-OV names.",
    },
]


def _sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_text(text: str) -> str:
    return _sha256_bytes(text.encode("utf-8"))


def routing_path(protocol_id: str, collection: str) -> Path:
    return config.get_soa2usdm_folder(protocol_id, collection) / "routing" / f"{protocol_id}_activity_routing.json"


# ---------------------------------------------------------------------------
# Lookups
# ---------------------------------------------------------------------------
class RoutingLookups:
    """SDTMIG_Statements and Domain_Coverage from the public cdisc-for-ai files."""

    def __init__(self, root: Path = CDISC_FOR_AI):
        if not root.is_dir():
            raise FileNotFoundError(f"cdisc-for-ai checkout not found at {root} (set SOA2USDM_CDISC_FOR_AI)")
        self.root = root
        self.provenance = self._provenance()
        st = self._read("SDTMIG_Statements")
        self.statements = {r["Statement_ID"]: r for r in st.to_dict("records")}
        cov = self._read("Domain_Coverage")
        self.coverage = cov.to_dict("records")
        self.cited = self._cited_statements()
        self.kind_domains = self._kind_domains()
        self.fallback_excluded = self._fallback_excluded()

    def _read(self, key):
        import pandas as pd
        rel, sheet = LOOKUP_FILES[key]
        return pd.read_excel(self.root / rel, sheet_name=sheet, keep_default_na=False, dtype=str)

    def _provenance(self) -> dict:
        import pandas as pd
        commit = subprocess.run(["git", "-C", str(self.root), "rev-parse", "HEAD"],
                                capture_output=True, text=True, check=True).stdout.strip()
        rels = [rel for rel, _ in LOOKUP_FILES.values()]
        dirty = subprocess.run(["git", "-C", str(self.root), "status", "--porcelain", "--", *rels],
                               capture_output=True, text=True, check=True).stdout.strip()
        if dirty:
            raise RuntimeError(f"cdisc-for-ai lookup files have uncommitted changes:\n{dirty}")
        files = []
        for key, (rel, sheet) in LOOKUP_FILES.items():
            prov = pd.read_excel(self.root / rel, sheet_name="Provenance", keep_default_na=False, dtype=str)
            pv = dict(zip(prov["Key"], prov["Value"]))
            files.append({
                "file": key, "path": rel, "sheet": sheet,
                "file_sha256": _sha256_bytes((self.root / rel).read_bytes()),
                "sheet_content_sha256": pv[f"{sheet}.Content_SHA256"],
                "generated": pv["Generated"],
                "sdtm_ct": pv["SDTM_CT"], "sdtmig": pv["SDTMIG"],
            })
        return {"commit": commit, "files": files}

    def _cited_statements(self) -> dict:
        """Statement_ID -> the statement as cited, for every statement a rule cites. Each must be
        a routing statement of SDTMIG_Statements."""
        out = {}
        for rule in RULES:
            for s in rule["statements"]:
                sid = s["statement_id"]
                if sid not in self.statements:
                    raise ValueError(f"{rule['rule_id']}: {sid} not in SDTMIG_Statements")
                r = self.statements[sid]
                if r["Selected_As"] != "routing":
                    raise ValueError(f"{rule['rule_id']}: {sid} is Selected_As {r['Selected_As']!r}, not routing")
                out[sid] = self._statement(r)
            for e in rule["exception_over"]:
                if e["statement_id"] not in {s["statement_id"] for s in rule["statements"]}:
                    raise ValueError(f"{rule['rule_id']}: exception statement {e['statement_id']} not cited by the rule")
        return out

    @staticmethod
    def _statement(r: dict) -> dict:
        return {"domain": r["Domain"], "source": r["Source"], "section": r["Section"], "page": r["Page"],
                "text": r["Text"], "text_sha256": sha256_text(r["Text"])}

    def _kind_domains(self) -> dict:
        """Grain kind -> domains, the reverse of grain rule K1, without the excluded domains."""
        out = {}
        for r in self.coverage:
            if r["Domain"] in FALLBACK_EXCLUDED:
                continue
            kind = DOMAIN_KIND.get(r["Domain"]) or CONSUMER_KIND.get(r["Consumer"])
            if kind:
                out.setdefault(kind, []).append(r["Domain"])
        return {k: sorted(v) for k, v in out.items()}

    def _fallback_excluded(self) -> list:
        out = []
        for dom, sids in FALLBACK_EXCLUDED.items():
            for sid in sids:
                if sid not in self.statements:
                    raise ValueError(f"FALLBACK_EXCLUDED {dom}: {sid} not in SDTMIG_Statements")
                if self.statements[sid]["Domain"] != dom:
                    raise ValueError(f"FALLBACK_EXCLUDED {dom}: {sid} has Domain {self.statements[sid]['Domain']!r}")
                self.cited[sid] = self._statement(self.statements[sid])
            out.append({"domain": dom, "statement_ids": sids,
                        "text_sha256": [self.cited[s]["text_sha256"] for s in sids]})
        return out


# ---------------------------------------------------------------------------
# Rules
# ---------------------------------------------------------------------------
def match_rules(sources: list) -> list:
    """sources: [{where, xannot_id, text}]. Returns [(rule, matches)] for the rules that fire."""
    fired = []
    for rule in RULES:
        matches, seen = [], set()
        for src in sources:
            for p in rule["patterns"]:
                for m in re.finditer(p, src["text"], flags=re.IGNORECASE):
                    key = (src["where"], src["xannot_id"], m.group(0).lower())
                    if key not in seen:
                        seen.add(key)
                        matches.append({"where": src["where"], "xannot_id": src["xannot_id"], "phrase": m.group(0)})
        if matches:
            fired.append((rule, matches))
    return fired


def test_identity(label: dict | None) -> dict | None:
    """The SDTM_Test_Identity hits of the row's activity label, as the grain file cites them;
    None when there are none. Domains as the hits give them (a hit's domains are '; '-separated)."""
    hits = [h for h in (label["hits"] if label else []) if h["file"] == TEST_IDENTITY_FILE]
    if not hits:
        return None
    codes = sorted({(h["code"], h["submission_value"], h["domains"]) for h in hits})
    return {
        "phrase": label["phrase"],
        "hit_strength": label["hit_strength"],
        "weak_reasons": label["weak_reasons"],
        "domains": sorted({d.strip() for h in hits for d in h["domains"].split(";") if d.strip()}),
        "codes": [{"code": c, "testcd": t, "domains": [d.strip() for d in ds.split(";") if d.strip()]}
                  for c, t, ds in codes],
        "matched_on": sorted({h["field"] for h in hits}),
    }


def route(fired: list, grain_kinds: list, lk: RoutingLookups, ti: dict | None = None) -> dict:
    """The routing result of one row from the rules that fired, then (only where no rule fired)
    from the test identity of the activity label."""
    res = _route_rules(fired, grain_kinds, lk)
    res["route_source"] = "rule" if res["status"] == "routed" else None
    res["test_identity"] = ti
    if ti is None or res["basis"]:
        return res
    if ti["hit_strength"] == "strong" and len(ti["domains"]) == 1:
        return res | {"status": "routed", "domain": ti["domains"][0], "candidates": None,
                      "fallback": None, "route_source": "test identity"}
    if ti["hit_strength"] == "strong":
        return res | {"status": "open", "candidates": ti["domains"], "fallback": None,
                      "route_source": "test identity",
                      "question": "test code " + "/".join(sorted({c["testcd"] for c in ti["codes"]}))
                                  + " is in " + ", ".join(ti["domains"])
                                  + " (SDTM_Test_Identity); the protocol must say which"}
    return res | {"hints": ti["domains"]}


def _route_rules(fired: list, grain_kinds: list, lk: RoutingLookups) -> dict:
    """The routing result of one row from the rules that fired."""
    fired_ids = {rule["rule_id"] for rule, _ in fired}
    dropped = {}
    for rule, _ in fired:
        for e in rule["exception_over"]:
            if e["rule_id"] in fired_ids:
                dropped[e["rule_id"]] = {"by_rule": rule["rule_id"], "statement_id": e["statement_id"]}

    basis, domains, questions = [], set(), []
    for rule, matches in fired:
        if rule["rule_id"] in dropped:
            continue
        for s in rule["statements"]:
            domains |= set(s["domains"])
            if s["condition"]:
                questions.append(f"{rule['rule_id']} {s['statement_id']}: {s['condition']}")
        basis.append({
            "rule_id": rule["rule_id"],
            "statements": [{"statement_id": s["statement_id"], "domains": s["domains"], "condition": s["condition"],
                            "text_sha256": lk.cited[s["statement_id"]]["text_sha256"]} for s in rule["statements"]],
            "matched": matches,
            "label_match": any(m["where"] == "label" for m in matches),
        })

    fallback_cands = sorted({d for k in grain_kinds for d in lk.kind_domains.get(k, [])})
    fallback = {"from": "grain kind -> Domain_Coverage", "kinds": grain_kinds}
    if not basis:
        return {"status": "not routed", "domain": None, "candidates": fallback_cands, "hints": None,
                "basis": [], "dropped": dropped, "fallback": fallback, "question": None}
    if {m["where"] for b in basis for m in b["matched"]} == {"annotation"}:
        ids = sorted({m["xannot_id"] for b in basis for m in b["matched"]})
        questions.insert(0, "matched only in annotation (" + ", ".join(ids) + "): " + ", ".join(
            f"{b['rule_id']} -> {'/'.join(sorted({d for s in b['statements'] for d in s['domains']}))}"
            for b in basis) + "; hints only, candidates from grain kind")
        return {"status": "weak", "domain": None, "candidates": fallback_cands, "hints": sorted(domains),
                "basis": basis, "dropped": dropped, "fallback": fallback, "question": "; ".join(questions)}
    if not any(b["label_match"] for b in basis):
        questions.append("no match in the activity label; matched only in " + ", ".join(
            sorted({m["where"] for b in basis for m in b["matched"]})))
    if len(basis) > 1 and len(domains) > 1:
        questions.append("rules fire on different domains: " + ", ".join(
            f"{b['rule_id']} -> {'/'.join(sorted({d for s in b['statements'] for d in s['domains']}))}"
            for b in basis))
    if len(domains) == 1 and not questions:
        return {"status": "routed", "domain": next(iter(domains)), "candidates": None, "hints": None,
                "basis": basis, "dropped": dropped, "fallback": None, "question": None}
    return {"status": "open", "domain": None, "candidates": sorted(domains), "hints": None, "basis": basis,
            "dropped": dropped, "fallback": None, "question": "; ".join(questions)}


# ---------------------------------------------------------------------------
# Study
# ---------------------------------------------------------------------------
def generate_study_routing(collection: str, protocol_id: str, lk: RoutingLookups | None = None,
                           all_rows: list | None = None) -> dict:
    """Build the <id>_activity_routing.json payload for one study."""
    g = load_current_grain(collection, protocol_id, all_rows)
    if g is None:
        raise FileNotFoundError(f"{collection}/{protocol_id}: no activity grain file; run soa2usdm.activity_grain")
    lk = lk or RoutingLookups()
    grain_commit = g["inputs"]["cdisc_for_ai"]["commit"]
    if grain_commit != lk.provenance["commit"]:
        raise RuntimeError(f"{collection}/{protocol_id}: grain made at cdisc-for-ai {grain_commit[:7]}, lookups at "
                           f"{lk.provenance['commit'][:7]}; rerun python -m soa2usdm.activity_grain "
                           f"--collection {collection} --protocol {protocol_id}")
    grain_file = config.get_soa2usdm_folder(protocol_id, collection) / "grain" / f"{protocol_id}_activity_grain.json"
    cons_path = config.find_consolidated_file(protocol_id, collection)
    cons_raw = cons_path.read_bytes()
    cons = json.loads(cons_raw)
    unified = {u["xact_id"]: u for u in cons["unified_activities"]}
    acts = g["activities"]
    labels = {lb["phrase"]: lb for lb in g["labels"]}
    children = {}
    for a in acts:
        if a["parent_xact_id"]:
            children.setdefault(a["parent_xact_id"], []).append(a)

    rows, not_reached = [], []
    for a in acts:
        x = a["xact_id"]
        if a["grain"] == "panel":
            not_reached.append({"xact_id": x, "activity_name": a["activity_name"], "reason": NOT_REACHED_PANEL})
            continue
        if a["grain"] != "named test":
            continue
        if x in children:
            not_reached.append({"xact_id": x, "activity_name": a["activity_name"], "reason": NOT_REACHED_PARENT,
                                "children": [{"xact_id": c["xact_id"], "activity_name": c["activity_name"],
                                              "grain": c["grain"], "role": c["role"]} for c in children[x]]})
            continue
        # Parent from consolidated. The grain sets parent_xact_id only when the parent is not a
        # section header; any other difference stops the run.
        px = unified[x]["parent_xact_id"]
        if px != a["parent_xact_id"] and not (a["parent_xact_id"] is None and unified[px]["is_section_header"]):
            raise ValueError(f"{protocol_id} {x}: parent differs between grain ({a['parent_xact_id']}) "
                             f"and consolidated ({px})")
        sources = [{"where": "label", "xannot_id": None, "text": a["activity_name"]}]
        if px:
            sources.append({"where": "parent_label", "xannot_id": None, "text": unified[px]["activity_name"]})
        for an in cons["unified_annotations"]:
            refs = set(an["referenced_xacts"])
            if x in refs or (px and px in refs):
                sources.append({"where": "annotation", "xannot_id": an["xannot_id"], "text": an["annotation_text"]})
        grain_kinds = ([a["finding_kind"]] if a["finding_kind"] and a["finding_kind"] != "unsure"
                       else list(a["kind_candidates"]))
        res = route(match_rules(sources), grain_kinds, lk, test_identity(labels.get(a["phrase"])))
        rows.append({
            "xact_id": x,
            "activity_name": a["activity_name"],
            "parent_xact_id": px,
            "parent_name": unified[px]["activity_name"] if px else None,
            "parent_is_section_header": unified[px]["is_section_header"] if px else None,
            "grain": {"grain": a["grain"], "finding_kind": a["finding_kind"],
                      "kind_candidates": a["kind_candidates"], "source": a["source"]},
        } | res)

    cited = sorted({s["statement_id"] for r in rows for b in r["basis"] for s in b["statements"]}
                   | {s for e in lk.fallback_excluded for s in e["statement_ids"]})
    return {
        "schema_name": SCHEMA_NAME, "schema_version": SCHEMA_VERSION,
        "collection": collection, "protocol_id": protocol_id,
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "rules_version": RULES_VERSION,
        "inputs": {
            "activity_grain": {"schema_version": g["schema_version"],
                               "sha256": _sha256_bytes(grain_file.read_bytes())},
            "consolidated": {"sha256": _sha256_bytes(cons_raw)},
            "cdisc_for_ai": lk.provenance,
        },
        "fallback_excluded": lk.fallback_excluded,
        "statements": {sid: lk.cited[sid] for sid in cited},
        "counts": {"rows": len(rows), "not_reached": len(not_reached)}
                  | {st: sum(1 for r in rows if r["status"] == st) for st in STATUSES}
                  | {"routed_by_test_identity": sum(1 for r in rows if r["status"] == "routed"
                                                    and r["route_source"] == "test identity")},
        "rows": rows,
        "not_reached": not_reached,
    }


def load_current_routing(collection: str, protocol_id: str) -> dict | None:
    """The study's routing file, checked against its inputs as they are now; None when the
    study has none. Fails when the grain file or consolidated.json changed since."""
    path = routing_path(protocol_id, collection)
    if not path.exists():
        return None
    d = json.loads(path.read_text(encoding="utf-8"))
    if d["schema_name"] != SCHEMA_NAME or d["schema_version"] not in SCHEMA_VERSIONS:
        raise ValueError(f"{path}: expected {SCHEMA_NAME} {' or '.join(SCHEMA_VERSIONS)}")
    grain_file = config.get_soa2usdm_folder(protocol_id, collection) / "grain" / f"{protocol_id}_activity_grain.json"
    sha = lambda f: _sha256_bytes(f.read_bytes()) if f and f.exists() else None
    now = {"activity grain": sha(grain_file),
           "consolidated.json": sha(config.find_consolidated_file(protocol_id, collection))}
    was = {"activity grain": d["inputs"]["activity_grain"]["sha256"],
           "consolidated.json": d["inputs"]["consolidated"]["sha256"]}
    changed = [k for k in now if now[k] != was[k]]
    if changed:
        raise RuntimeError(f"{path}: stale ({', '.join(changed)} changed since it was generated); rerun: "
                           f"python -m soa2usdm.activity_routing --collection {collection} --protocol {protocol_id}")
    return d


def write_study_routing(collection: str, protocol_id: str, lk: RoutingLookups | None = None,
                        all_rows: list | None = None) -> Path:
    payload = generate_study_routing(collection, protocol_id, lk, all_rows)
    out = routing_path(protocol_id, collection)
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return out


def main():
    import argparse
    ap = argparse.ArgumentParser(description="Route each named test to an SDTMIG v3.4 domain, per study.")
    ap.add_argument("--collection", required=True)
    ap.add_argument("--protocol", help="one study; default: every study of the collection with a grain file")
    args = ap.parse_args()
    from .activity_inventory import collect_rows
    all_rows = collect_rows(args.collection)
    pids = [args.protocol] if args.protocol else sorted(
        {r["protocol_id"] for r in all_rows
         if (config.get_soa2usdm_folder(r["protocol_id"], args.collection) / "grain"
             / f"{r['protocol_id']}_activity_grain.json").exists()})
    lk = RoutingLookups()
    for pid in pids:
        print(write_study_routing(args.collection, pid, lk, all_rows))


if __name__ == "__main__":
    main()
