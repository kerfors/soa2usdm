"""
Regression fixture for the deterministic pipeline (resolve -> consolidate).

For every protocol in the collection that has a verified extraction plus golden
resolved + consolidated JSON, re-running resolve+consolidate on the verified
extraction must reproduce the golden output exactly (timestamps scrubbed).

Runs against a temp copy via a throwaway collection key, so the real golden
files are never touched. To bank a new protocol: drop its verified extraction
and golden resolved/consolidated into place; this test discovers it automatically.
"""
import json
import shutil
from pathlib import Path

import pytest

from soa2usdm import config
from soa2usdm.errors import Errors
from soa2usdm.analytics import Analytics
from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import ResolveStep
from soa2usdm.consolidate import ConsolidateStep

VOLATILE = {"resolved_at", "consolidated_at", "extracted_at"}


def discover_cases():
    """(collection, protocol) for every protocol, in any registered collection,
    that has a verified extraction AND golden resolved + consolidated."""
    cases = []
    for collection, protocols_dir in config.COLLECTIONS.items():
        if not Path(protocols_dir).is_dir():
            continue
        for d in sorted(p for p in Path(protocols_dir).iterdir()
                        if p.is_dir() and not p.name.startswith(".")):
            soa = d / "SoA2USDM"
            if (list((soa / "extracted").glob("*_extraction.json"))
                    and list((soa / "resolved").glob("*_resolved.json"))
                    and list((soa / "consolidated").glob("*_consolidated.json"))):
                cases.append((collection, d.name))
    return cases


CASES = discover_cases()


def scrub(obj):
    """Recursively drop volatile timestamp keys for stable comparison."""
    if isinstance(obj, dict):
        return {k: scrub(v) for k, v in obj.items() if k not in VOLATILE}
    if isinstance(obj, list):
        return [scrub(v) for v in obj]
    return obj


@pytest.fixture(params=CASES, ids=[f"{c}/{p}" for c, p in CASES])
def pipeline_output(request, tmp_path):
    """Copy one protocol's extraction into a temp collection, run resolve+consolidate,
    and yield (protocol, produced_dir, golden_dir)."""
    collection, protocol = request.param
    golden = Path(config.COLLECTIONS[collection]) / protocol / "SoA2USDM"

    coll = tmp_path / "protocols"
    extracted = coll / protocol / "SoA2USDM" / "extracted"
    extracted.mkdir(parents=True)
    for f in (golden / "extracted").glob("*_extraction.json"):
        shutil.copy(f, extracted / f.name)
    for f in (golden / "extracted").glob("*_corrections.json"):
        shutil.copy(f, extracted / f.name)

    key = "regression_tmp"
    config.COLLECTIONS[key] = coll
    errors = Errors()
    analytics = Analytics()
    data = {"source": {"protocol_id": protocol, "collection": key}}
    for step_cls in (ApplyCorrectionsStep, ResolveStep, ConsolidateStep):
        data[step_cls.step_name] = step_cls(errors, analytics).execute(data)
    assert not errors.has_errors(), [(e.step, e.message) for e in errors.all]

    yield protocol, coll / protocol / "SoA2USDM", golden
    config.COLLECTIONS.pop(key, None)


def test_resolved_matches_golden(pipeline_output):
    protocol, produced, golden = pipeline_output
    golden_files = sorted((golden / "resolved").glob("*_resolved.json"))
    assert golden_files, f"{protocol}: no golden resolved files"
    for gf in golden_files:
        pf = produced / "resolved" / gf.name
        assert pf.exists(), f"{protocol}: resolve did not produce {gf.name}"
        assert scrub(json.loads(pf.read_text())) == scrub(json.loads(gf.read_text())), \
            f"{protocol}: resolved mismatch in {gf.name}"


def test_consolidated_matches_golden(pipeline_output):
    protocol, produced, golden = pipeline_output
    gf = next((golden / "consolidated").glob("*_consolidated.json"))
    pf = produced / "consolidated" / gf.name
    assert pf.exists(), f"{protocol}: consolidate produced no output"
    assert scrub(json.loads(pf.read_text())) == scrub(json.loads(gf.read_text())), \
        f"{protocol}: consolidated mismatch"
