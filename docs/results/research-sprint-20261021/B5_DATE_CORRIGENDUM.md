# B5 Decision Date Corrigendum

The header of `docs/B5_EVIDENCE_VIEW_STABILITY_DECISION.md` says `2026-10-21 (UTC)`. That date label is incorrect. The immutable registry closeout records `closed_at_utc` as `2026-10-20T18:44:50+00:00`; the first request started at `2026-10-20T18:35:58.651613+00:00` and the last response ended at `2026-10-20T18:37:58.529194+00:00`. The intended date in the decision header is **2026-10-20 UTC**. The report itself and terminal closure remain unchanged so their registered hashes stay valid.

The post-close artifact manifest `b5-postclose-artifact-manifest.json` is the current inventory. The original `b5-invariance-run-artifact-manifest.json` remains the immutable point-in-time inventory used by the terminal registry closure.
