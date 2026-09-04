"""
One generator, driven by a manifest. Tests whether the shell scaffolding is
mechanical: the manifest holds only facts read off a protocol page; everything
else is derived here.

Rule for the test: no protocol-specific branch is allowed in this file. If a shell
cannot be reproduced without one, that is the finding.
"""

import json
from pathlib import Path

import yaml

PROV = "https://kerfors.github.io/soa2usdm/sourceRef"
NOTSTATED = "https://kerfors.github.io/soa2usdm/not-stated-in-protocol"
CS = "http://www.cdisc.org"

CHAINED = {"StudyEpoch", "Activity", "Encounter", "EligibilityCriterion"}


class Generator:

    def __init__(self, manifest):
        self.m = manifest
        self.terms = manifest["terms"]
        self.doc_ref = manifest["study"]["documentRef"]
        self.n_code = 0
        self.n_ext = 0

    # ---- primitives ---------------------------------------------------
    def code(self, key):
        self.n_code += 1
        c, decode = self.terms[key]
        return {"id": f"Code_{self.n_code}", "code": c, "codeSystem": CS,
                "codeSystemVersion": self.m["study"]["ctVersion"],
                "decode": decode, "instanceType": "Code"}

    def src(self, ref):
        self.n_ext += 1
        return [{"id": f"ExtensionAttribute_{self.n_ext}", "url": PROV,
                 "valueString": f"{self.doc_ref} {ref}",
                 "instanceType": "ExtensionAttribute"}]

    def flag(self, msg):
        self.n_ext += 1
        return [{"id": f"ExtensionAttribute_{self.n_ext}", "url": NOTSTATED,
                 "valueString": msg, "instanceType": "ExtensionAttribute"}]

    @staticmethod
    def chain(objs):
        """previousId / nextId over an ordered list. Only for chained classes."""
        for i, o in enumerate(objs):
            if o["instanceType"] not in CHAINED:
                continue
            o["previousId"] = objs[i-1]["id"] if i else None
            o["nextId"] = objs[i+1]["id"] if i < len(objs) - 1 else None
        return objs

    # ---- sections -----------------------------------------------------
    def epochs(self):
        out = []
        for e in self.m["epochs"]:
            out.append({"id": f"StudyEpoch_{e['slug']}", "name": e["name"],
                        "label": e["label"], "description": e.get("description"), "type": self.code(e["ct"]),
                        "notes": [], "extensionAttributes": self.src(e["ref"]),
                        "instanceType": "StudyEpoch"})
        return self.chain(out)

    def cohorts(self):
        return [{"id": f"StudyCohort_{c['slug']}", "name": c["name"],
                 "label": c["label"], "description": c.get("description"),
                 "includesHealthySubjects": False, "plannedSex": [],
                 "plannedAge": None, "plannedEnrollmentNumber": None,
                 "plannedCompletionNumber": None, "criterionIds": [],
                 "characteristics": [], "indicationIds": [], "notes": [],
                 "extensionAttributes": self.src(c["ref"]),
                 "instanceType": "StudyCohort"}
                for c in self.m.get("cohorts", [])]

    def arms(self):
        out = []
        for a in self.m["arms"]:
            out.append({
                "id": f"StudyArm_{a['slug']}", "name": a["name"],
                "label": a["label"], "description": a.get("description"),
                "type": self.code(a["ct"]),
                "dataOriginType": self.code(self.m["study"]["dataOriginCt"]),
                "dataOriginDescription": self.m["study"]["dataOriginText"],
                "populationIds": [f"StudyCohort_{c}" for c in a.get("cohorts", [])],
                "notes": [], "extensionAttributes": self.src(a["ref"]),
                "instanceType": "StudyArm"})
        return out

    def elements(self):
        return [{"id": f"StudyElement_{e['slug']}", "name": e["name"],
                 "label": e["label"], "description": e.get("description"),
                 "studyInterventionIds": [f"StudyIntervention_{i}"
                                          for i in e.get("interventions", [])],
                 "transitionStartRule": None, "transitionEndRule": None,
                 "notes": [], "extensionAttributes": self.src(e["ref"]),
                 "instanceType": "StudyElement"}
                for e in self.m["elements"]]

    def cells(self):
        """Cross product arm x epoch. The element is looked up in the manifest's
        cellMap, keyed by epoch slug, with an optional per-arm override."""
        cmap = self.m["cellMap"]
        out, n = [], 0
        for a in self.m["arms"]:
            for e in self.m["epochs"]:
                n += 1
                entry = cmap[e["slug"]]
                el = entry.get(a["slug"], entry["default"]) if isinstance(entry, dict) \
                    else entry
                out.append({"id": f"StudyCell_{n}", "armId": f"StudyArm_{a['slug']}",
                            "epochId": f"StudyEpoch_{e['slug']}",
                            "elementIds": [f"StudyElement_{el}"],
                            "extensionAttributes": [], "instanceType": "StudyCell"})
        return out

    def interventions(self):
        return [{"id": f"StudyIntervention_{i['slug']}", "name": i["name"],
                 "label": i["label"], "description": i.get("description"),
                 "role": self.code(i["roleCt"]), "type": self.code(i["typeCt"]),
                 "codes": [], "administrations": [], "notes": [],
                 "extensionAttributes": self.src(i["ref"]),
                 "instanceType": "StudyIntervention"}
                for i in self.m.get("interventions", [])]

    def criteria(self):
        """Criteria come from the manifest already grouped and numbered. Object
        ids encode the group so they stay unique when numbering restarts."""
        crit, items = [], []
        for g in self.m["criteria"]:
            group_start = len(crit)
            for c in g["items"]:
                gid = g["slug"]
                cid = f"EligibilityCriterion_{g['kind']}_{gid}_{c['n']}"
                iid = f"EligibilityCriterionItem_{g['kind']}_{gid}_{c['n']}"
                crit.append({
                    "id": cid, "name": f"{g['kind']}-{gid}-{c['n']:02d}",
                    "label": c["label"], "identifier": f"{c['n']:02d}",
                    "category": self.code(g["ct"]), "criterionItemId": iid,
                    "notes": [], "extensionAttributes": self.src(f"{g['ref']} [{c['n']}]"),
                    "instanceType": "EligibilityCriterion"})
                items.append({
                    "id": iid, "name": f"ITEM-{g['kind']}-{gid}-{c['n']:02d}",
                    "label": c["label"],
                    "text": f"See protocol {self.doc_ref} {g['ref']}, criterion {c['n']}.",
                    "dictionaryId": None, "notes": [],
                    "extensionAttributes": self.src(
                        f"{g['ref']} [{c['n']}]. Criterion text not reproduced."),
                    "instanceType": "EligibilityCriterionItem"})
            self.chain(crit[group_start:])
        return crit, items

    # ---- assembly -----------------------------------------------------
    def build(self):
        m = self.m
        epochs = self.epochs()
        cohorts = self.cohorts()
        arms = self.arms()
        elements = self.elements()
        cells = self.cells()
        interventions = self.interventions()
        criteria, items = self.criteria()
        groups = {c["slug"]: c.get("criteriaGroups", []) for c in self.m.get("cohorts", [])}
        for c in cohorts:
            want = groups[c["id"].split("_", 1)[1]]
            c["criterionIds"] = [x["id"] for x in criteria
                                 if any(f"_{g}_" in x["id"] for g in want)]

        p = m["population"]
        population = {
            "id": "StudyDesignPopulation_1", "name": p["name"], "label": p.get("label"),
            "description": p.get("description"),
            "includesHealthySubjects": p["includesHealthySubjects"],
            "plannedSex": [], "plannedAge": None,
            "plannedEnrollmentNumber": (
                {"id": "Quantity_1", "value": float(p["plannedEnrollment"]),
                 "unit": None, "extensionAttributes": [], "instanceType": "Quantity"}
                if p.get("plannedEnrollment") else None),
            "plannedCompletionNumber": None,
            "criterionIds": [c["id"] for c in criteria],
            "cohorts": cohorts, "notes": [],
            "extensionAttributes": self.src(p["ref"]),
            "instanceType": "StudyDesignPopulation"}

        dsn = m["design"]
        design = {
            "id": "InterventionalStudyDesign_1", "name": dsn["name"],
            "label": dsn.get("label"), "description": dsn.get("description"),
            "rationale": dsn["rationale"],
            "model": self.code(dsn["modelCt"]),
            "studyType": self.code(dsn["typeCt"]) if dsn.get("typeCt") else None,
            "blindingSchema": (
                {"id": "AliasCode_1", "standardCode": self.code(dsn["blindingCt"]),
                 "standardCodeAliases": [], "extensionAttributes": [],
                 "instanceType": "AliasCode"} if dsn.get("blindingCt") else None),
            "intentTypes": [self.code(c) for c in dsn.get("intentCt", [])],
            "studyPhase": None,
            "arms": arms, "studyCells": cells, "epochs": epochs, "elements": elements,
            "population": population, "eligibilityCriteria": criteria,
            "studyInterventionIds": [i["id"] for i in interventions],
            "activities": [], "encounters": [], "scheduleTimelines": [],
            "objectives": [], "estimands": [], "indications": [], "characteristics": [],
            "therapeuticAreas": [], "analysisPopulations": [],
            "biospecimenRetentions": [], "documentVersionIds": [], "subTypes": [],
            "notes": [], "extensionAttributes": self.src(dsn["ref"]),
            "instanceType": "InterventionalStudyDesign"}

        orgs = [{"id": f"Organization_{o['slug']}", "name": o["name"],
                 "identifier": "NOT STATED IN PROTOCOL",
                 "identifierScheme": "NOT STATED IN PROTOCOL",
                 "type": self.code(o["ct"]), "legalAddress": None, "managedSites": [],
                 "extensionAttributes": (self.src(o["ref"]) if o.get("ref")
                                         else self.flag(o["flag"])),
                 "instanceType": "Organization"}
                for o in m["organizations"]]

        version = {
            "id": "StudyVersion_1", "versionIdentifier": m["study"]["version"],
            "rationale": m["study"]["versionRationale"],
            "studyIdentifiers": [
                {"id": f"StudyIdentifier_{i['slug']}", "text": i["text"],
                 "scopeId": f"Organization_{i['org']}",
                 "extensionAttributes": self.src(i["ref"]),
                 "instanceType": "StudyIdentifier"} for i in m["identifiers"]],
            "titles": [
                {"id": f"StudyTitle_{i+1}", "type": self.code(t["ct"]),
                 "text": t["text"], "extensionAttributes": self.src(t["ref"]),
                 "instanceType": "StudyTitle"} for i, t in enumerate(m["titles"])],
            "studyDesigns": [design], "eligibilityCriterionItems": items,
            "organizations": orgs, "studyInterventions": interventions,
            "conditions": [], "abbreviations": [], "dateValues": [], "amendments": [],
            "documentVersionIds": [], "referenceIdentifiers": [],
            "businessTherapeuticAreas": [], "narrativeContentItems": [], "roles": [],
            "administrableProducts": [], "medicalDevices": [],
            "productOrganizationRoles": [], "biomedicalConcepts": [],
            "bcCategories": [], "bcSurrogates": [], "dictionaries": [], "notes": [],
            "extensionAttributes": [], "instanceType": "StudyVersion"}

        study = {"id": m["study"]["id"], "name": m["study"]["name"],
                 "label": m["study"].get("label"),
                 "description": m["study"].get("description"),
                 "versions": [version], "documentedBy": [],
                 "extensionAttributes": [], "instanceType": "Study"}

        return {"study": study, "usdmVersion": "4.0.0",
                "systemName": "soa2usdm shell generator", "systemVersion": "0.1"}


def generate(manifest_path, out_path):
    m = yaml.safe_load(Path(manifest_path).read_text())
    doc = Generator(m).build()
    Path(out_path).write_text(json.dumps(doc, indent=2, ensure_ascii=False))
    return doc


if __name__ == "__main__":
    import sys
    generate(sys.argv[1], sys.argv[2])
    print("generated", sys.argv[2])
