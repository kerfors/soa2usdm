# Global identifiers for extracted items — design note

**Status: proposal, 2026-08-23. Nothing here is implemented; this document is the artifact to agree on first.**

Every item the pipeline produces — a unified activity, a deduplicated annotation, a source table — currently has identity only *inside one JSON file*: `xact-027` means something in `NCT04184622_consolidated.json` and nothing anywhere else. The moment an item is cited outside the repo (a publication, a slide, a triple in the coming semantic layer), that identity should be global, stable, and resolvable. This note proposes how, following the pattern already established for the model side in [usdm-rdf](https://github.com/kerfors/usdm-rdf), which mints class and property IRIs under `https://w3id.org/cdisc/usdm/v4/`. That work identifies the *model* (TBox); this proposal identifies the *data* (ABox). The two meet in a single kind of statement:

```
<https://w3id.org/soa2usdm/v1/usdm_data/NCT04184622/xact-027>
    rdf:type <https://w3id.org/cdisc/usdm/v4/Activity> .
```

## Why

- **Citability.** A publication about SoA patterns can cite `…/xact-027` and the claim stays clickable and checkable — down to the printed page — years later. This is FAIR F1: globally unique, persistent, resolvable identifiers.
- **Typing.** The semantic/USDM layer's central act — "this extracted thing is a USDM Activity / Encounter / Timing" — becomes one triple per item, joining this project's instances to usdm-rdf's classes.
- **Linking.** Biomedical-concept anchoring, cross-protocol activity equivalence, and resolved See-Section references (backlog item 3) all become statements between identified things instead of notes inside files.

## What gets an IRI — and what deliberately does not

Mint identifiers for what will be cited; leave provenance addressable *relative to* an identified item.

| Gets an IRI | Example |
|---|---|
| collection | `…/v1/usdm_data` |
| protocol (embedding, not replacing, its NCT id) | `…/v1/usdm_data/NCT04184622` |
| source table | `…/v1/usdm_data/NCT04184622/table-1` |
| unified activity | `…/v1/usdm_data/NCT04184622/xact-027` |
| unified annotation | `…/v1/usdm_data/NCT04184622/xannot-021` |

Extraction rows, marks, cells, and page bands get **no** IRIs. They are the evidence chain, already addressable through an identified item's `source_refs` (table + row position + document page), and minting them would multiply the identifier surface without anything citing them directly. If something ever needs to cite a row, the table IRI plus row position is the citation.

## The stability problem, and the decision

`xact-027` is a **derived** identifier: deterministic, but positional. A re-extraction or a correction that changes the consolidation folding renumbers items. A global identifier that silently changes referent between corpus versions is worse than none. Three options were considered:

1. **Version-scoped IRIs (chosen).** The corpus release is part of the path — exactly as usdm-rdf carries `/v4/`. Each release's identifiers are frozen forever; the next release mints under the next version. Costs nothing: no new state, no registry, and the pipeline's re-derive-don't-store principle stays intact. The price: identity does not carry across versions by itself.
2. **Curated identity registry (deferred).** Accession-style ids assigned once, mapped across re-runs — the identity analogue of the corrections sidecar. Stable, but a new class of persistent state with vocabulary-management semantics (merge, split, deprecate). Only worth paying for when the semantic layer demonstrably needs cross-version continuity; at that point, `owl:sameAs`/`dcterms:replaces` mappings between version-scoped IRIs can be added without changing this scheme.
3. **Content-derived ids (rejected).** Hashing protocol + normalized name survives renumbering but breaks on the very corrections that fix wording. False stability.

**A "release" must therefore become explicit.** Proposal: a git tag on `soa2usdm-collections` (`v1`, `v2`, …), placed when a corpus state is worth citing. Between tags, plain URLs into the Pages site serve fine; IRIs refer only to tagged states.

## The IRI scheme

```
https://w3id.org/soa2usdm/{release}/{collection}/{protocol}/{item}
```

- Slash semantics, no hash fragments (as adopted for usdm-rdf in its v0.3).
- `{item}` is the id the pipeline already emits: `xact-NNN`, `xannot-NNN`, `table-N`. No new naming scheme is invented; the IRI is the existing id given a stable prefix.
- **IRIs are computed, not stored.** The consolidated JSON keeps carrying `xact_id`; the mapping from id to IRI is this specification. Storing IRIs in the data would violate re-derive-don't-store and would break every stored value at the next release tag.

## Dereferencing

w3id.org provides the indirection layer — a `.htaccess` in the [w3id registry](https://github.com/perma-id/w3id.org), the mechanics already exercised once for usdm-rdf — pointing into the Pages site, which is the resolution target:

- `Accept: text/html` → the consolidated view, anchored at the item: `…/NCT04184622_consolidated.html#xact-027`. Requires per-item anchors in the consolidated HTML (small generator change); the review page can accept the same anchor for its linked-row view.
- `Accept: application/json` → the protocol's consolidated JSON on Pages. Item-level granularity inside the file is the reader's job for now.
- Later, if the semantic layer wants it: a build step emitting one small JSON-LD file per item (static hosting cannot slice a JSON at request time). An optimization, not a prerequisite.

Because IRIs are version-scoped and Pages serves only the current corpus, older releases resolve via the tag: the w3id rule for `/v1/` targets the Pages content as of tag `v1` (GitHub serves tagged files raw even when Pages has moved on). Exact routing to be settled in the w3id PR.

## Implementation steps (all small, in order)

1. Agree this note; commit it as the specification.
2. Per-item anchors in the consolidated HTML (`id="xact-NNN"` / `id="xannot-NNN"`); review page accepts the same anchor.
3. First release tag on `soa2usdm-collections` when the corpus is next in a citable state.
4. w3id PR registering `soa2usdm` with the routing above.
5. Semantic layer emits typed triples against these IRIs (its own design, not this document's).

## Open questions

- Cross-version continuity: when (not whether) the registry of option 2 becomes necessary, and what its sidecar looks like.
- Whether `misc_studies` items should be mintable at all, or IRIs reserved for collections meant to be cited.
- Whether review items and corrections deserve IRIs (they are decisions about items, and citable in principle) — deferred until something needs to cite one.
