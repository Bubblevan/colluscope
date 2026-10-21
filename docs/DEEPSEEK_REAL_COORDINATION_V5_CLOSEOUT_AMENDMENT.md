# V5 closeout integrity amendment — 2026-10-21

The initial V5 closure audit failed because two JSON sidecars were normalized from PowerShell UTF-8 BOM/CRLF to UTF-8 LF after the closure had pinned their raw-byte hashes. Parsed JSON values did not change. The original closure bytes are preserved at `research/experiments/deepseek-real-coordination-40-v5/closure.pre-integrity-amendment.json`; the exact previous and replacement hashes are in `research/experiments/deepseek-real-coordination-40-v5/closure-amendments.jsonl`.

The closure and registration now point to the normalized artifact hashes. No V5 request, response, model action, count, cost, claim, or decision was changed. The pre-amendment audit failure remains in Git history at commit `cb3e936`.
