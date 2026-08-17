"""Gate steps 8 and 11 — run the deterministic layers over the staged extraction, in a scratch
collection that is a throwaway copy.

Nothing here touches ~/ph2/soa2usdm-collections. The scratch tree is rebuilt from scratch on
every run, so a half-finished run cannot contaminate the next one.

Per §4.4 of the acceptance checklist, every corrections sidecar belonging to a re-extracted
table is RETIRED (replaced with an empty stub) before ApplyCorrections runs. `op: add` is a bare
append with no match key and no dedup, so leaving a stale sidecar in place silently duplicates
rows and annotations with nothing erroring.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

# Paths come from the environment so the harness is not tied to one machine. Defaults are derived
# from this file's location inside the repo.
#   SOA2USDM_COLLECTIONS  the collections tree being read/rebuilt   (config.py reads this too)
#   SOA2USDM_STAGING      where extraction agents write             (never the corpus)
#   SOA2USDM_BLIND        blind/<STUDY>/ — the PDF and PAGEMAP.md the agents see
#   SOA2USDM_CALIB        a copy of the ACCEPTED corpus, for calibrating checks
#   SOA2USDM_SCRATCH      throwaway collection for rehearsals
REPO = Path(os.environ.get("SOA2USDM_REPO", Path(__file__).resolve().parents[1]))
REAL = Path(os.environ["SOA2USDM_COLLECTIONS"])
SCRATCH = Path(os.environ.get("SOA2USDM_SCRATCH", "scratch")) / "collections"
STAGING = Path(os.environ.get("SOA2USDM_STAGING", "staging"))
COLLECTION = os.environ.get("SOA2USDM_COLLECTION", "usdm_data")


def build_scratch(studies):
    if SCRATCH.parent.exists():
        shutil.rmtree(SCRATCH.parent)
    SCRATCH.parent.mkdir(parents=True)
    shutil.copytree(REAL, SCRATCH)

    retired, installed = [], []
    for study in studies:
        ext = SCRATCH / COLLECTION / "protocols" / study / "SoA2USDM" / "extracted"
        staged = sorted((STAGING / study).glob(f"{study}_Table_*_extraction.json"))
        if not staged:
            print(f"  {study}: nothing staged — left at baseline")
            continue

        # Remove every previous artefact for this study, not just Layer 1. Consolidate reads
        # resolved/, so a stale resolved JSON for a table the re-extraction no longer produces
        # walks back into the consolidated output and inflates the table count — CDISC_Pilot
        # reported 2 tables from 1 staged table until this was cleaned.
        for p in list(ext.glob("*_extraction.json")) + list(ext.glob("*_extraction.verified.json")):
            p.unlink()
        for sub in ("resolved", "consolidated"):
            dsub = ext.parent / sub
            if dsub.is_dir():
                for p in dsub.iterdir():
                    p.unlink()

        for src in staged:
            shutil.copy2(src, ext / src.name)
            installed.append(f"{study}/{src.name}")

        # retire sidecars — §4.4 duplication trap
        for cf in sorted(ext.glob("*_corrections.json")):
            d = json.loads(cf.read_text())
            n = len(d.get("corrections", []))
            d["corrections"] = []
            cf.write_text(json.dumps(d, indent=1) + "\n")
            if n:
                retired.append(f"{cf.name}: {n} correction(s) retired")

        # carry the uncertainty report across so the resolved HTML links resolve
        for rp in sorted((STAGING / study).glob("*_uncertainty_report.md")):
            shutil.copy2(rp, ext / rp.name)

    print(f"  installed {len(installed)} staged table(s)")
    for r in retired:
        print(f"  RETIRED  {r}")
    return installed


def run_pipeline(studies):
    env = dict(os.environ, SOA2USDM_COLLECTIONS=str(SCRATCH), PYTHONPATH=str(REPO))
    driver = f"""
import sys
from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import ResolveStep
from soa2usdm.consolidate import ConsolidateStep
from soa2usdm.visualize_resolved import VisualizeResolvedStep
from soa2usdm.visualize import VisualizeStep
from soa2usdm.errors import Errors
from soa2usdm.analytics import Analytics

STEPS = [ApplyCorrectionsStep, ResolveStep, VisualizeResolvedStep, ConsolidateStep, VisualizeStep]
fail = 0
for pid in {studies!r}:
    errors, analytics = Errors(), Analytics()
    data = {{'source': {{'protocol_id': pid, 'collection': '{COLLECTION}'}}}}
    for sc in STEPS:
        try:
            data[sc.step_name] = sc(errors, analytics).execute(data)
        except Exception as e:
            print(f'  {{pid}} {{sc.step_name}}: RAISED {{type(e).__name__}}: {{e}}')
            fail += 1
            break
    cons = data.get('consolidate', {{}})
    mark = 'ERR' if errors.has_errors() else 'ok '
    print(f'  {{mark}} {{pid}}: {{cons.get("tables","?")}} tables, '
          f'{{cons.get("unified_activities","?")}} unified activities, '
          f'{{cons.get("compression_percent","?")}}% compression')
    for e in errors.all:
        print(f'      [{{e.step}}] {{e.message}}')
        fail += 1
sys.exit(1 if fail else 0)
"""
    r = subprocess.run([sys.executable, "-c", driver], env=env, capture_output=True, text=True)
    print(r.stdout.rstrip())
    if r.stderr.strip():
        print(r.stderr.rstrip()[-2000:])
    return r.returncode == 0


def run_row_audit():
    env = dict(os.environ, SOA2USDM_COLLECTIONS=str(SCRATCH), PYTHONPATH=str(REPO))
    out = SCRATCH / "row_audit_scratch.json"
    r = subprocess.run([sys.executable, "-m", "soa2usdm.row_audit", "--json", str(out)],
                       env=env, capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if "protocols," in l]
    print("  " + (tail[-1] if tail else r.stdout.splitlines()[-1] if r.stdout else "no output"))
    return out


def main():
    studies = sys.argv[1:] or sorted(p.name for p in STAGING.iterdir() if p.is_dir())
    print(f"Scratch collection: {SCRATCH}")
    print(f"Studies: {', '.join(studies)}\n")
    print("-- build scratch --")
    build_scratch(studies)
    print("\n-- gate 11: ApplyCorrections -> Resolve -> Consolidate --")
    ok = run_pipeline(studies)
    print("\n-- gate 8: row audit (pre-pilot 33; Phase 3 acceptance is 10 on-page-not-extracted) --")
    run_row_audit()
    print(f"\ndeterministic layers: {'clean' if ok else 'ERRORS — see above'}")


if __name__ == "__main__":
    main()
