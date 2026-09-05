"""
Level 1 floor for Layer 4.

USDM v4 has no standalone SoA serialization: a ScheduleTimeline hangs under a
StudyDesign, which mandates arms, cells, elements, a population, eligibility
criteria and a model -- none of which a Schedule of Activities contains. This
module supplies exactly those objects, so a Level 1 manifest has to carry only
study identity and the epoch list.

It does not modify shellgen. It expands a floor manifest into the full manifest
shellgen.Generator already accepts, and hands that over unchanged.

Every object synthesised here is a placeholder. Each one carries the
not-stated-in-protocol extension through shellgen's own flag mechanism, and
expand() returns the list of them so the caller can put them in a decisions log.
"""

NOTSTATED = "https://kerfors.github.io/soa2usdm/not-stated-in-protocol"

# Ids shellgen gives the objects this module asks it to build. shellgen
# attributes every object it emits to the manifest's documentRef; these are not
# in that document, so their provenance is rewritten by reflag() below.
FLOOR_IDS = (
    "StudyArm_floor",
    "StudyElement_floor",
    "StudyDesignPopulation_1",
    "EligibilityCriterion_IN_floor_1",
    "EligibilityCriterionItem_IN_floor_1",
    "InterventionalStudyDesign_1",
)

FLOOR_TERMS = {
    "floor_arm_type": ("C174266", "Investigational Arm"),
    "floor_data_origin": ("C188866", "Data Generated Within Study"),
    "floor_model": ("C82639", "Parallel Study"),
    "floor_criterion_category": ("C25532", "Inclusion Criteria"),
}

PLACEHOLDER = ("Mandatory in USDM v4 on the path Study -> StudyVersion -> "
               "InterventionalStudyDesign. Not derivable from a Schedule of "
               "Activities. Placeholder, carries no protocol content.")

FLOOR_OBJECTS = [
    ("StudyArm", "One placeholder arm. The SoA does not state the study's arms."),
    ("StudyElement", "One placeholder element, referenced by every cell."),
    ("StudyCell", "One cell per epoch, all pointing at the placeholder arm and element."),
    ("StudyDesignPopulation", "Placeholder population. includesHealthySubjects is "
                              "asserted False because the attribute is mandatory."),
    ("EligibilityCriterion", "One placeholder criterion. eligibilityCriteria is 1..* "
                             "on StudyDesign, so it cannot be empty, but one is enough."),
    ("EligibilityCriterionItem", "Item for the placeholder criterion."),
    ("InterventionalStudyDesign.model", "Placeholder model code. The SoA does not "
                                        "state the design model."),
]


def expand(floor):
    """Return (full_manifest, placeholders) for a Level 1 floor manifest.

    The floor manifest supplies: study, organizations, identifiers, titles,
    epochs, epochAxis, terms. Everything else in the shellgen manifest is
    synthesised.
    """
    for key in ("study", "organizations", "identifiers", "titles", "epochs", "terms"):
        if key not in floor:
            raise KeyError(f"floor manifest is missing required key {key!r}")
    if not floor["epochs"]:
        raise ValueError("floor manifest declares no epochs; the epoch list is the "
                         "one part of the shell the SoA needs")

    terms = dict(floor["terms"])
    for key, value in FLOOR_TERMS.items():
        if key in terms and terms[key] != list(value) and terms[key] != value:
            raise ValueError(f"floor manifest overrides reserved term {key!r}")
        terms[key] = value

    study = dict(floor["study"])
    study["dataOriginCt"] = "floor_data_origin"
    study["dataOriginText"] = PLACEHOLDER

    manifest = {
        "study": study,
        "terms": terms,
        "organizations": floor["organizations"],
        "identifiers": floor["identifiers"],
        "titles": floor["titles"],
        "epochs": floor["epochs"],
        "design": {
            "name": "SOA ONLY DESIGN",
            "label": None,
            "description": None,
            "rationale": PLACEHOLDER,
            "modelCt": "floor_model",
            "ref": floor["study"]["documentRef"],
        },
        "arms": [{
            "slug": "floor",
            "name": "PLACEHOLDER ARM",
            "label": "Placeholder arm",
            "description": PLACEHOLDER,
            "ct": "floor_arm_type",
            "cohorts": [],
            "ref": floor["study"]["documentRef"],
        }],
        "elements": [{
            "slug": "floor",
            "name": "PLACEHOLDER ELEMENT",
            "label": "Placeholder element",
            "description": PLACEHOLDER,
            "interventions": [],
            "ref": floor["study"]["documentRef"],
        }],
        "cellMap": {e["slug"]: "floor" for e in floor["epochs"]},
        "population": {
            "name": "PLACEHOLDER POPULATION",
            "label": "Placeholder population",
            "description": PLACEHOLDER,
            "includesHealthySubjects": False,
            "ref": floor["study"]["documentRef"],
        },
        "criteria": [{
            "slug": "floor",
            "kind": "IN",
            "ct": "floor_criterion_category",
            "ref": floor["study"]["documentRef"],
            "items": [{"n": 1, "label": "PLACEHOLDER CRITERION"}],
        }],
    }

    # Axis declarations belong to the SoA lifting, not to the shell. shellgen
    # ignores unknown keys, so they ride through untouched.
    for axis in ("epochAxis", "timingAxis", "encounterAxis"):
        if axis in floor:
            manifest[axis] = floor[axis]
    if "epochAxis" not in manifest:
        raise KeyError("floor manifest declares no epochAxis; without it no "
                       "ScheduledInstance can bind to an epoch and the shell and "
                       "the SoA are two documents that happen to validate")

    placeholders = [{"kind": "floor-placeholder", "ref": name, "text": text}
                    for name, text in FLOOR_OBJECTS]
    return manifest, placeholders


def reflag(shell):
    """Rewrite the floor objects' provenance in a generated shell.

    shellgen emits a sourceRef extension pointing at the protocol document on
    everything it builds, which for a placeholder asserts a reading that was
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
            if isinstance(node_id, str) and (node_id in FLOOR_IDS
                                             or node_id.startswith("StudyCell_")):
                node["extensionAttributes"] = [{
                    "id": f"ExtensionAttribute_floor_{n + 1}",
                    "url": NOTSTATED,
                    "valueString": PLACEHOLDER,
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
