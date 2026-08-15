# Backlog — activity inventory improvements

Two improvements to the activity inventory (`soa2usdm/activity_inventory.py` → `activities.html` / `activities.json`), motivated by working with the usdm_data corpus. Both are additive — no schema break, no change to the extraction layer.

## 1 — Carry linked footnote text into the activity inventory

**Motivation.** SoA footnotes carry the content that distinguishes otherwise identically-named activities: performer context ("Locally performed"), timing constraints ("Screening endoscopy must occur ≤14 days prior to randomization"), conditional execution ("Only for participants who are positive for anti-HBc at screening"), preconditions ("Fasting samples are preferred…"), co-timing ("Performed at time of endoscopy"). The inventory currently carries only `any_marks`; the footnote text is invisible to inventory search and browsing, although the row↔annotation join already exists in the resolved layer (`linked_annotation_ids` / `annotation_markers`).

**Sketch.** In `activity_inventory._collect`, for each occurrence pull the linked annotations from the already-loaded resolved JSON; attach to the consolidated row as `annotations: [{marker, table_number, text}]`, deduped by text. Render in `activities.html` as an expandable per-row detail and include annotation text in the search index.

**Acceptance.** Searching "sigmoidoscopy" in activities.html finds NCT04677179 "Colon biopsy sample collection" (the term occurs only in that row's footnote, not in any activity name). The activities.json row carries the footnote text verbatim. Counts unchanged.

**Size.** Small — one module + template; additive field.

## 2 — Redaction as a first-class flag

**Motivation.** Public protocol documents redact some SoA rows (activity name replaced by "CCI"). These rows are currently indistinguishable from real activity names except by string matching. NCT04677179 has 6 redacted rows of 60. A per-protocol redaction count is a useful data-quality signal for anyone selecting protocols from a collection, and redacted rows should be excludable from name-based analyses.

**Sketch.** Detector on activity names (`CCI`, `CCI (redacted)` and variants) setting `is_redacted: true` at the resolved layer; propagate to the inventory; surface a per-protocol redaction count in the collection index and an inventory filter.

**Acceptance.** NCT04677179 reports 6 redacted rows; negative control: no false positives across the other 21 protocols (no legitimate activity name matches the pattern).

**Size.** Small.

---

2026-08-15. Evidence: `collections/usdm_data/protocols/activities.json` and the per-protocol `*_resolved.json` annotation arrays.
