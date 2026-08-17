"""Rehearse the Phase 3 promotion in a throwaway scratch collection.

Does exactly what the real promotion will do, so the result can be checked before anything on the
device is touched:

  * install every staged extraction JSON and uncertainty report
  * delete the derived artefacts of the OLD corpus for those studies — extracted/, resolved/ and
    consolidated/. Consolidate reads resolved/, so a stale resolved JSON for a table the
    re-extraction no longer produces (CDISC_Pilot T2, NCT04004988 T2) walks back into the
    consolidated output and inflates the table count.
  * RETIRE Family A (NCT02107703 T1/T2, 54) and Family C (NCT04677179 T4, 3) — reproduced natively,
    and §4.4's `op: add` is a bare append with no dedup, so leaving them would duplicate silently
  * KEEP Family B (NCT01847274 T3, 12) — human clinical verdicts, all 12 still match on
    annotation_marker against the fresh extraction
  * INSTALL the three sidecars authored at promotion review (NCT04557384 T3 sample names,
    NCT05176314 + NCT05324124 redaction placeholders)
  * run the full published chain, including the two index steps that build the GitHub Pages tables
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
#   SOA2USDM_SIDECARS     corrections sidecars authored at promotion review
REPO = Path(os.environ.get("SOA2USDM_REPO", Path(__file__).resolve().parents[1]))
REAL = Path(os.environ["SOA2USDM_COLLECTIONS"])
SCRATCH = Path(os.environ.get("SOA2USDM_SCRATCH", "scratch")) / "collections"
STAGING = Path(os.environ.get("SOA2USDM_STAGING", "staging"))
SIDECARS = Path(os.environ.get("SOA2USDM_SIDECARS", "sidecars"))
COLLECTION = os.environ.get("SOA2USDM_COLLECTION", "usdm_data")

# Sweep-specific: which sidecars the re-extraction reproduced natively, and which carry human
# judgement that no extraction can regenerate. Re-derive these per sweep — do NOT inherit them.
RETIRE = {  # reproduced natively
    "NCT02107703_Table_01_corrections.json",
    "NCT02107703_Table_02_corrections.json",
    "NCT04677179_Table_04_corrections.json",
}
KEEP = {"NCT01847274_Table_03_corrections.json"}


def build():
    if SCRATCH.parent.exists():
        shutil.rmtree(SCRATCH.parent)
    SCRATCH.parent.mkdir(parents=True)
    shutil.copytree(REAL, SCRATCH)

    studies = sorted(p.name for p in STAGING.iterdir() if p.is_dir())
    installed = retired = kept = added = removed = 0
    for study in studies:
        ext = SCRATCH / COLLECTION / "protocols" / study / "SoA2USDM" / "extracted"
        staged = sorted((STAGING / study).glob(f"{study}_Table_*_extraction.json"))
        if not staged:
            print(f"  {study}: nothing staged — left at baseline")
            continue

        for p in list(ext.glob("*_extraction.json")) + list(ext.glob("*_extraction.verified.json")) \
                + list(ext.glob("*_extraction_viewer.html")) + list(ext.glob("*_uncertainty_report.md")):
            p.unlink()
            removed += 1
        for sub in ("resolved", "consolidated"):
            d = ext.parent / sub
            if d.is_dir():
                for p in d.iterdir():
                    p.unlink()
                    removed += 1

        for src in staged:
            shutil.copy2(src, ext / src.name)
            installed += 1
        for rp in sorted((STAGING / study).glob("*_uncertainty_report.md")):
            shutil.copy2(rp, ext / rp.name)

        for cf in sorted(ext.glob("*_corrections.json")):
            if cf.name in RETIRE:
                d = json.loads(cf.read_text())
                n = len(d.get("corrections", []))
                d["corrections"] = []
                cf.write_text(json.dumps(d, indent=1) + "\n")
                retired += n
            elif cf.name in KEEP:
                kept += len(json.loads(cf.read_text()).get("corrections", []))
            else:
                print(f"  ?? unclassified sidecar left in place: {cf.name}")

        for sc in sorted(SIDECARS.glob(f"{study}_*_corrections.json")):
            shutil.copy2(sc, ext / sc.name)
            added += len(json.loads(sc.read_text())["corrections"])

    print(f"  installed {installed} table(s); removed {removed} stale derived file(s)")
    print(f"  corrections: {retired} retired, {kept} kept (Family B), {added} newly authored")
    return studies


def run(studies):
    env = dict(os.environ, SOA2USDM_COLLECTIONS=str(SCRATCH), PYTHONPATH=str(REPO))
    driver = f"""
import sys
from soa2usdm.corrections import ApplyCorrectionsStep
from soa2usdm.resolve import ResolveStep
from soa2usdm.consolidate import ConsolidateStep
from soa2usdm.visualize_resolved import VisualizeResolvedStep
from soa2usdm.visualize import VisualizeStep
from soa2usdm.index_generator import IndexGeneratorStep
from soa2usdm.collections_index import CollectionsIndexStep
from soa2usdm.activity_inventory import ActivityInventoryStep
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
    if errors.has_errors():
        for e in errors.all:
            print(f'  ERR {{pid}} [{{e.step}}] {{e.message}}')
            fail += 1
print('  per-protocol chain done')
for name, step, arg in (('index', IndexGeneratorStep, {{'source': {{'collection': '{COLLECTION}'}}}}),
                        ('root index', CollectionsIndexStep, {{}}),
                        ('activity inventory', ActivityInventoryStep, {{'source': {{'collection': '{COLLECTION}'}}}})):
    errs = Errors()
    try:
        r = step(errs, Analytics()).execute(arg)
        print(f'  {{name}}: ok  {{ {{k: v for k, v in (r or {{}}).items() if isinstance(v, (int, str))}} }}')
    except Exception as e:
        print(f'  {{name}}: RAISED {{type(e).__name__}}: {{e}}')
        fail += 1
    for e in errs.all:
        print(f'  ERR {{name}}: {{e.message}}')
        fail += 1
sys.exit(1 if fail else 0)
"""
    r = subprocess.run([sys.executable, "-c", driver], env=env, capture_output=True, text=True)
    print(r.stdout.rstrip())
    if r.stderr.strip():
        print(r.stderr.rstrip()[-2500:])
    return r.returncode == 0


def main():
    print("-- build scratch --")
    studies = build()
    print("\n-- full published chain --")
    ok = run(studies)
    print("\n-- row audit --")
    env = dict(os.environ, SOA2USDM_COLLECTIONS=str(SCRATCH), PYTHONPATH=str(REPO))
    r = subprocess.run([sys.executable, "-m", "soa2usdm.row_audit"], env=env,
                       capture_output=True, text=True)
    tail = [l for l in r.stdout.splitlines() if "protocols," in l]
    print("  " + (tail[-1] if tail else "no output"))
    print(f"\npromotion rehearsal: {'clean' if ok else 'ERRORS — see above'}")


if __name__ == "__main__":
    main()
