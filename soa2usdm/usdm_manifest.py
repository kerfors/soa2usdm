"""
Minimal-build manifest expansion for USDM Instantiation.

USDM v4 has no standalone SoA serialization: a ScheduleTimeline hangs under a
StudyDesign, which mandates arms, cells, elements, a population, eligibility
criteria and a model -- none of which a Schedule of Activities contains. This
module supplies exactly those objects, so a minimal manifest has to carry only
study identity and the epoch list.

It does not modify shellgen. It expands a minimal manifest into the full manifest
shellgen.Generator already accepts, and hands that over unchanged.

Every object synthesised here is not stated in the protocol. Each one carries the
not-stated-in-protocol extension through shellgen's own flag mechanism, and
expand() returns the list of them so the caller can put them in a decisions log.
"""

NOTSTATED = "https://kerfors.github.io/soa2usdm/not-stated-in-protocol"

# Ids shellgen gives the objects this module asks it to build. shellgen
# attributes every object it emits to the manifest's documentRef; these are not
# in that document, so their provenance is rewritten by reflag() below.
NOT_STATED_IDS = (
    "StudyArm_notstated",
    "StudyElement_notstated",
    "StudyDesignPopulation_1",
    "EligibilityCriterion_IN_notstated_1",
    "EligibilityCriterionItem_IN_notstated_1",
    "InterventionalStudyDesign_1",
)

NOT_STATED_TERMS = {
    "notstated_arm_type": ("C174266", "Investigational Arm"),
    "notstated_data_origin": ("C188866", "Data Generated Within Study"),
    "notstated_model": ("C82639", "Parallel Study"),
    "notstated_criterion_category": ("C25532", "Inclusion Criteria"),
}

NOT_STATED_TEXT = ("Mandatory in USDM v4 on the path Study -> StudyVersion -> "
               "InterventionalStudyDesign. Not derivable from a Schedule of "
               "Activities. Not stated in the protocol; carries no protocol content.")

NOT_STATED_OBJECTS = [
    ("StudyArm", "One arm, not stated. The SoA does not state the study's arms."),
    ("StudyElement", "One element, not stated, referenced by every cell."),
    ("StudyCell", "One cell per epoch, all pointing at the not-stated arm and element."),
    ("StudyDesignPopulation", "Population, not stated. includesHealthySubjects is "
                              "asserted False because the attribute is mandatory."),
    ("EligibilityCriterion", "One criterion, not stated. eligibilityCriteria is 1..* "
                             "on StudyDesign, so it cannot be empty, but one is enough."),
    ("EligibilityCriterionItem", "Item for the not-stated criterion."),
    ("InterventionalStudyDesign.model", "Model code, not stated. The SoA does not "
                                        "state the design model."),
]


def expand(given):
    """Return (full_manifest, not_stated) for a minimal manifest.

    The minimal manifest supplies: study, organizations, identifiers, titles,
    epochs, epochAxis, terms. Everything else in the shellgen manifest is
    synthesised.
    """
    for key in ("study", "organizations", "identifiers", "titles", "epochs", "terms"):
        if key not in given:
            raise KeyError(f"manifest is missing required key {key!r}")
    if not given["epochs"]:
        raise ValueError("manifest declares no epochs; the epoch list is the "
                         "one part of the shell the SoA needs")

    terms = dict(given["terms"])
    for key, value in NOT_STATED_TERMS.items():
        if key in terms and terms[key] != list(value) and terms[key] != value:
            raise ValueError(f"manifest overrides reserved term {key!r}")
        terms[key] = value

    study = dict(given["study"])
    study["dataOriginCt"] = "notstated_data_origin"
    study["dataOriginText"] = NOT_STATED_TEXT

    manifest = {
        "study": study,
        "terms": terms,
        "organizations": given["organizations"],
        "identifiers": given["identifiers"],
        "titles": given["titles"],
        "epochs": given["epochs"],
        "design": {
            "name": "SOA ONLY DESIGN",
            "label": None,
            "description": None,
            "rationale": NOT_STATED_TEXT,
            "modelCt": "notstated_model",
            "ref": given["study"]["documentRef"],
        },
        "arms": [{
            "slug": "notstated",
            "name": "ARM NOT STATED",
            "label": "Arm not stated",
            "description": NOT_STATED_TEXT,
            "ct": "notstated_arm_type",
            "cohorts": [],
            "ref": given["study"]["documentRef"],
        }],
        "elements": [{
            "slug": "notstated",
            "name": "ELEMENT NOT STATED",
            "label": "Element not stated",
            "description": NOT_STATED_TEXT,
            "interventions": [],
            "ref": given["study"]["documentRef"],
        }],
        "cellMap": {e["slug"]: "notstated" for e in given["epochs"]},
        "population": {
            "name": "POPULATION NOT STATED",
            "label": "Population not stated",
            "description": NOT_STATED_TEXT,
            "includesHealthySubjects": False,
            "ref": given["study"]["documentRef"],
        },
        "criteria": [{
            "slug": "notstated",
            "kind": "IN",
            "ct": "notstated_criterion_category",
            "ref": given["study"]["documentRef"],
            "items": [{"n": 1, "label": "CRITERION NOT STATED"}],
        }],
    }

    # Axis declarations belong to the SoA lifting, not to the shell. shellgen
    # ignores unknown keys, so they ride through untouched.
    for axis in ("epochAxis", "timingAxis", "encounterAxis"):
        if axis in given:
            manifest[axis] = given[axis]
    if "epochAxis" not in manifest:
        raise KeyError("manifest declares no epochAxis; without it no "
                       "ScheduledInstance can bind to an epoch and the shell and "
                       "the SoA are two documents that happen to validate")

    not_stated = [{"kind": "not-stated", "ref": name, "text": text}
                  for name, text in NOT_STATED_OBJECTS]
    return manifest, not_stated


def reflag(shell):
    """Rewrite the not-stated objects' provenance in a generated shell.

    shellgen emits a sourceRef extension pointing at the protocol document on
    everything it builds, which for a not-stated object asserts a reading that was
    never made. This replaces those with the not-stated-in-protocol flag.
    Applied after Generator.build() and before ids are prefixed, so that
    shellgen itself stays untouched.

    Returns the number of objects re-flagged.
    """
    n = 0

    def walk(node):
        nonlocal n
        if isinstance(node, dict):
            node_id = node.get("id")
            if isinstance(node_id, str) and (node_id in NOT_STATED_IDS
                                             or node_id.startswith("StudyCell_")):
                node["extensionAttributes"] = [{
                    "id": f"ExtensionAttribute_notstated_{n + 1}",
                    "url": NOTSTATED,
                    "valueString": NOT_STATED_TEXT,
                    "instanceType": "ExtensionAttribute",
                }]
                n += 1
            for v in node.values():
                walk(v)
        elif isinstance(node, list):
            for v in node:
                walk(v)

    walk(shell)
    return n
