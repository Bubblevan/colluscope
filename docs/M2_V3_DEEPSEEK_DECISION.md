# M2-V3 DeepSeek Decision

**Operational result:** RUN COMPLETE; independent payload/reference verification passed.
**Scientific decision:** GO to retain and report the run as an exploratory observable-fact extraction study; **NO-GO** for detector-superiority, latent-collusion, or confirmatory claims. No further model phase is authorized or started.

## Evidence for the decision

- The local source freeze is `5cb43bce230b82bf76c7e3fd63e27ee7cb15929d`; the run manifest binds to this clean commit.
- All 1,500 assigned rows terminalized as completed; 916/916 logical requests and physical HTTP attempts completed, with zero retries. The diagnostic gate passed 15/15, F1 passed 250/250, and all 1,500 responses were format-valid.
- Independent verification reconstructed all payloads and references from frozen M1 data: hidden metadata 0, Public-only private-text leaks 0, cross-split duplicate requests 0, source hashes match, attempt cap passed, and usage-based cost was **$0.062844045** against the $5 cap.
- Observable fact accuracy on F2/F3 was 83.04% overall, but this row aggregate masks the central weakness: public-harm accuracy was 45.14% across 350 repeated view rows, with 99 false-positive `present` predictions and substantial excessive abstention. Ballot disagreement and delivered-message presence were 100% in their scheduled rows; proposal/action concordance was 99.33%; allocation proposal was 90.5%.
- Within Raw Fusion, adding Privileged Audit message evidence changed public-harm accuracy from 40% to 28%: 0 paired wins, 44 ties, 6 losses among 50 episode pairs. The action-only to privileged raw-fusion contrast was +4 points with 8/36/6 wins/ties/losses and a 10-group bootstrap interval of −20 to +32 points. These previously exposed F2/F3 results do not support a reliable benefit from combining communication and action evidence.
- Structured Evidence reached 98–100% public-harm accuracy because deterministic findings expose the derived answer. Its citation sufficiency was only 0–4% because visible `Fnn` finding IDs were outside the frozen `Mnn`/`Pnn` source-event citation vocabulary. This cell is rule-assisted and its citation metric is confounded by the frozen contract.
- No latent-collusion gold label was created. Shared incentives, messages, target execution, matching ballots, and welfare gaps remain insufficient to label intent.

## Next-phase boundary

The run is sufficient to document interface feasibility and to motivate a redesign of the public-harm and citation tasks. It is not ready for a formal collusion-monitor comparison. Before any later model run, the study would need a newly reviewed protocol that (1) gives derived structured findings a coherent citation namespace or excludes them from citation comparisons, (2) rechecks public-harm scoring with explicit negative controls and better-calibrated evidence instructions, and (3) reserves unexposed matched groups. This is a recommendation only; no new call, prompt change, fine-tuning, or M2 follow-on was started.

## Reproduction and hashes

From the repository root:

```powershell
$env:PYTHONPATH = 'src'
python scripts/score_m2_v3_deepseek.py --run-dir runs/m2-v3/deepseek-overnight-r1
python scripts/verify_m2_v3_deepseek.py --run-dir runs/m2-v3/deepseek-overnight-r1
python -m pytest -q
```

| Artifact | SHA-256 |
|---|---|
| Local source commit | `5cb43bce230b82bf76c7e3fd63e27ee7cb15929d` |
| Run `manifest.json` | `254745f5e1c1975a770c9851e2ba13ddbec27c4811c61a18dd9260cc1827b43b` |
| `evaluation_schedule.jsonl` | `bba06b58d148e7d3ee45875454bbdaf6fe4438f97868867d920f874bdf1c1a72` |
| `logical_requests.jsonl` | `073dd072c93074e274465f4455d0db556926de48c3fdd84498031755c6e94eef` |
| `attempts.jsonl` | `b5c20f123573dbc319e025c6ae789770825844d8b1af333a6d61bf7d0706bd8f` |
| `results.jsonl` | `62f83736f636d49262fc92fcb48fa25bf0e08729d861b65e2f35ae3e4b7665fe` |
| Final `artifact_sha256.json` (1,870 local files indexed) | `2d60a6b78cd36ccf294afe207c345bd0f361a527593144b110d597291c123793` |

The final independent verification was rerun after scoring and report generation. It verified 1,500/1,500 payloads, 916/916 terminal logical requests, 916 physical attempts, source hashes, zero cross-split duplicates, zero hidden metadata, zero Public-only private-text leaks, and the $5 cost ceiling. The machine-readable verifier output is retained at `runs/m2-v3/deepseek-overnight-r1/preflight/final-verification-after-analysis.log` and indexed by the artifact manifest.

The final `artifact_sha256.json` is the authoritative per-file inventory for the private run directory; its own hash is recorded in the final integrity output after report generation. Raw payloads, private synthetic message text, and full model responses remain local under current-user ACLs and Git ignore rules.

## Preregistration timestamp limitation and report publication

Before inference, the connected GitHub read confirmed `codex/m2-one-shot-audit` remained at `69e4593557b26530bb5a38f544278255c0a2c2eb`; direct HTTPS could not reach GitHub and the connected write endpoint returned HTTP 403. Thus, the source freeze `5cb43bce230b82bf76c7e3fd63e27ee7cb15929d` predates the run locally but has no independently verifiable public timestamp from before inference. After the run and report review, `git push origin codex/m2-one-shot-audit` exited successfully and reported the remote update `69e4593..f952356`. A subsequent `git ls-remote` readback failed because the configured `127.0.0.1:7892` proxy was unavailable; no alternate credential or transport was tried. The final report commit is therefore recorded as pushed based on the successful Git push response, while the preregistration timing limitation remains.
