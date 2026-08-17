# Re-extraction harness

Tooling for re-extracting a collection's Layer 1 with fresh agents and deciding, mechanically,
whether the result may replace what is already there. Written during the `usdm_data` sweep of
2026-08-17 (22 studies, 43 tables, 29 agents) and calibrated against that corpus.

Nothing here decides whether a delta is *acceptable*. It reports what the delta is, and refuses to
guess where guessing would be silent.

| script | what it does |
|---|---|
| `page_map.py` | derives the PDF-page → document-page map per study; **refuses to guess** where the excerpt has extra pages |
| `gate.py` | per-table promotion gate: schema, orphans, marker agreement, containment, typing, page coverage, baseline deltas, marker bindings, quote fidelity |
| `dryrun.py` | the two gate steps that need the corpus rather than the staging area — row audit, and the deterministic layers — in a throwaway scratch collection |
| `promote_dryrun.py` | rehearses the whole promotion (install, retire/keep sidecars, rebuild, regenerate the published index pages) so it can be checked before anything real is touched |
| `audit_blinding.py` | reads the subagent transcripts and reports tool calls that reached outside the blind tree |

Paths come from the environment: `SOA2USDM_COLLECTIONS`, `SOA2USDM_STAGING`, `SOA2USDM_BLIND`,
`SOA2USDM_CALIB`, `SOA2USDM_SCRATCH`, `SOA2USDM_SIDECARS`.

## The method, in the order it has to happen

**1. Blind the extractors physically, not by instruction.** Move the corpus, both repo clones, the
acceptance checklist, the machine baseline, the calibration tree, the scratch pipeline and *this
directory* out of the tree the agents can see, for the duration of the fan-out. `gate.py` carries
corpus counts in its own calibration comments; a scratch collection is a full copy of the corpus.
Give each agent only `blind/<STUDY>/` — the PDF and its `PAGEMAP.md` — plus a redacted copy of the
prompt, taxonomy and schema. Then audit it with `audit_blinding.py`.

**2. Redact the instructions.** The shipped prompt and taxonomy contain worked examples that name
real protocols *and give away their answers* — a table's classification, a restoration's activity
and mark counts, the verdict on a containment pair a gate check is about to re-ask. Generalise those
spans: keep the rule, strip the study identity and the numbers. Keep the redaction log **outside**
the agents' tree, re-apply it from that log after every prompt edit, and verify afterwards that no
study identifier survives anywhere an agent can read.

**3. Compute the page map; do not derive it from footers.** See `page_map.py`'s docstring. Printed
footers were measured running one lower than the document page in one protocol and one higher in
another, with a protocol number instead of a page number in a third.

**4. Calibrate every check against the ACCEPTED corpus before trusting it — and then run a negative
control.** Copy the signed-off extractions into a `calib/` tree, point `gate.py` at it and require
**0 FAIL**: anything that fails there would fail a *perfect* re-extraction. Four checks were
miscalibrated on first write and each was caught this way. But calibration only proves a check does
not false-positive. Whether it fires at all needs the opposite test — point it at output you know
is broken. A binding check written for a specific collapse passed silently *on that very collapse*
because it read its expected value off the wrong object; only the negative control found it.

**5. Rehearse the promotion in a scratch collection** with `promote_dryrun.py`, then compare the
real rebuild against the rehearsal by timestamp-scrubbed corpus hash. Identical hashes are what let
a test suite run in one environment vouch for a rebuild done in another.

## Traps that cost real time

- **`op: add` is a bare append.** `corrections.apply_corrections` does `arr.append(c["set"])` — no
  match key, no dedup. Retire or empty every sidecar whose content the re-extraction now produces
  natively, *before* the pipeline runs, or it silently duplicates.
- **Stale derived artefacts walk back in.** `Consolidate` reads `resolved/`, so a resolved JSON for
  a table the re-extraction no longer produces reappears in the consolidated output and inflates the
  table count. Clear `resolved/` and `consolidated/`, not just `extracted/`.
- **Pinned expectation tables must be keyed by collection AND protocol.** The regression suite runs
  over the live collection *and* the banked fixtures. Keyed by protocol alone, re-pinning after a
  sweep silently moves a frozen control.
- **A checker artefact reads exactly like a fabricated quote.** Inspect the failures before
  reporting a fidelity number: a quote-matching regex that resumes after a closing quote will score
  the prose *between* two quotations as a third quotation.
- **Marker bindings can vanish without any check firing.** `resolve` links an annotation to its
  element through the row's `annotation_markers`; the shipped detector reports only *partial*
  disagreement, so when both sides are empty nothing is partial. `gate.py` check 12 compares the
  count of distinct markers carried on rows against the baseline.
