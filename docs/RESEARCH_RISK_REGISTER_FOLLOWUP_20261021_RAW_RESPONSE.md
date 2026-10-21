# Research Risk Register Follow-up — raw ballot provenance (2026-10-21)

This versioned addendum leaves the hash-pinned root risk register unchanged.

| ID | Risk / counterexample | Evidence | Required action |
|---|---|---|---|
| RV-264 | A settlement replay that uses stored parsed actions without reparsing model responses may inherit parser errors and be mislabeled an independent raw-data audit. | V1 replay read `parsed_assignment`; v2 reparsed 225 raw responses, matched all 225 parser fields, and recomputed 75/75 settlements with no discrepancy. | Use v2 outputs when citing raw-response results. Preserve v1 and its narrower scope. Future audits must reparse original response bytes or state explicitly that they condition on a parser field. |
