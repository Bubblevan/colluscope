# ColluScope M1-R Runtime Evidence

**Run scope:** offline deterministic Mock only. No real LLM, external/paid API, bank system, or monitor was called. All runtime outputs below are plumbing evidence, not agent-behavior evidence.

## Checkout and environment

- M1-R topic branch: `codex/m1-r-runtime`.
- Accepted M0.1 source base: `516232de54e129fd818a3a4d82e128ca23fa4b3a`.
- Inspected `origin/main` at `190ea3cb4e5803bea3fede9a0eddbf8e4d57fe51`; M1-R starts from the accepted M0.1 branch commit, which is ahead of that base.
- Environment: Python 3.12.4, pytest 9.1.1, Windows 11 build 10.0.26200, AMD64; project runtime uses the Python standard library. Saved environment file: [`environment.txt`](../runs/m1_r/evidence/environment.txt).
- The generated run manifest records source snapshot SHA256 `7585c760c95d1e3730786c5a76039208f5af14e40009f9fc49530367807e5dda`; source files and individual digests are in `runs/m1_r/mock-canary-final/manifest.json`. The manifest records base commit `516232d…` and a dirty worktree because the runtime was under review when run artifacts were generated. The exact source/config/prompt/test snapshot was committed as `e46523cf1f2e9442eaaa7d890691db66506391ec`; the pushed topic branch includes this commit and the evidence-package update.

## Executed checks

| Check | Result | Raw record |
|---|---:|---|
| Independent M0.1 baseline on this checkout | 50 passed | `runs/m1_r/evidence/pytest-baseline.log` |
| First M1-R focused adversarial attempt | **4 failed, 11 passed**; retained as a real FSM bug report | `pytest-m1r-first.log` |
| Focused runtime suite after final fixes | 20 passed | `pytest-m1r-final-focused.log` |
| Full repository regression suite | 70 passed | `pytest-full-final.log` |
| 25-episode offline runtime generation | PASS; 25/25 episodes, 5 per frozen condition | `generation-m1r-final.log` |
| Independent artifact verification | PASS; all 25 settlements, E projections, observations, group hashes and artifact hashes recomputed | `verification-m1r-final.log` |
| Adversarial runtime canaries | 10 traces / 15 assertions, all pass | `canaries-m1r-final.log` and `isolation-canaries-final/` |

Evidence-log SHA256 values:

| Log | SHA256 |
|---|---|
| Focused tests | `94ea232b4e2c1480c37a58172d2c5aace60072cde7b21a6f5570ef0700277874` |
| Full tests | `477b9eb7dc948aa6a7f754a07110e4ce2712d06e2b5700dcfd3802c55ae25f12` |
| Generation | `2e85c0953366fb4bc69a0e21014ca73fec5f9a9fddffefab14804f3afdc83329` |
| Standalone verification | `a29c9686c679d920e1e6a2e297ca77b257588bc39ca9d80c802f56892d17c633` |
| Adversarial canaries | `80fbbac8ed61d63f07a4a515813df59d00aa44e291fdafaa8554d099f7db44a7` |
| Environment record | `32424cf621afeb7936e282be4092fa587c5899c1942ee915bb0e7c09c12f0c25` |

The first focused failure was not hidden: no-chat episodes transitioned to `BALLOTS_SEALED` before the ballots were collected, then failed a later transition check. The synthetic target arithmetic canary consequently had no result. The state ordering was corrected; targeted and full tests now pass. An additional final-package review found two evidence gaps (malformed ballot lacked an explicit B-row request link, and the verifier checked only aggregate rather than per-episode call composition). Both were corrected and the release run below was regenerated.

## Main Mock run

Final run: [`mock-canary-final`](../runs/m1_r/mock-canary-final/). It contains separate researcher-only `T`, `B`, exact request/response attempts and hashed agent observations, plus physically separate raw `monitor_inputs/evidence.jsonl`. It includes copied prompt templates, schemas, both configs, deterministic condition order, a manifest and standalone verification result. Earlier `mock-canary-v1/v2/release` and corresponding canary folders are preserved as iteration checkpoints; use the `final` folders for reproduction.

- Episodes: **25**; each of the five configured conditions has five seed blocks.
- Actual Mock logical requests and attempts: **95 / 95**; hard ceilings **95 / 190**.
- Per episode: 3 ballot requests without chat, 5 requests with the two A/B optional message turns.
- Public welfare in default Mock traces: W=28 in all 25; the fixed Mock returns the public optimum and `no_message`. This is not evidence about real agents.
- Private/public bonus arithmetic and harmful target settlement were exercised separately in a labeled synthetic canary; no synthetic behavior was merged into the 25-episode Mock run.
- External model calls: **0**; paid API calls: **0**; detector performance claimed: **false**.

Key SHA256 values:

| Artifact | SHA256 |
|---|---|
| Main run `manifest.json` | `17abdb50e92baca03ed85417df6dfed157cffbee104b85ad20de52d0fbc35618` |
| Main run `verification.json` | `24227ebaff0114d0e2d102f940abf71b897af2e124b2ec220881a7db8f664ef6` |
| Main E JSONL | `863bd3c3c8a36b1e9ed5f5020451588fc1c2949869ed2d7cda3d9d287a9bffc6` |
| T JSONL | `f211e1d0d2ab07e8d56ac2276a8087d2dea9deae6c142c2f1ca2a69d0a71ec67` |
| B JSONL | `396ca2c5d41f90a2f2b49fc01565b78c2d7e78a0ebe596fc9ce470b6ba3777ff` |
| Request/response ledger | `1bda4224d3eea6db5bf5563833d6f5a4d583e025ecbd438f559b34de9d8fea56` |
| Exact agent observations | `96a74fe57e5ad6ceefe3c1a7c4b2100696730d167b3482ecb8814e274b9fd66d` |
| Frozen offline config | `57178d86457ccc77c5db775c843a225ecc785e4c3c21a3bd3ee94a464c6a4948` |
| Frozen M1 draft config | `856691bee335b3890b171ce4d5e74fe327570b22e67140e7dafee329815d5e82` |
| Source snapshot aggregate | `7585c760c95d1e3730786c5a76039208f5af14e40009f9fc49530367807e5dda` |

Each individual file under the main run is covered by `manifest.json` and checked by `verify-m1r`. The full exact prompt/schema hashes are in [`M1_P0_FROZEN_PROTOCOL.md`](M1_P0_FROZEN_PROTOCOL.md).

## Adversarial canary traces

[`isolation-canaries-final/`](../runs/m1_r/isolation-canaries-final/) preserves ten standalone counterexample episodes: A/B message routing with voluntary disclosure (auditor permission on and off), no-chat isolation, invalid duplicate-task ballot, persistent timeout, sent-but-undelivered message after an incomplete peer round, one bounded transient retry, synthetic target reward arithmetic, public-bonus evidence without a collusion label, and zero-budget rejection before backend dispatch.

- Canary case ledger SHA256: `f80f6d1a947edf438776795b67102ae335a00be8aa48cf441fede575c3cf8cd5`.
- Canary assertions SHA256: `226da2272ed8ac789ad712718cc01019b3cd893044a2df156f0dd5e0daf2873f`.
- Canary manifest SHA256: `16c71025191bac16e12f4f5c38787ec031bf8577ae618cdd4eb6dd5a38b7c6cb`.

The malformed ballot is recorded both as an unsealed B action with its exact request ID/raw response and in the request ledger. Persistent timeout keeps both attempts, failure state, and uncertain incentive-delivery status. Voluntary disclosure remains in B in both auditor-permission cases; E includes it only in the permission-on canary. C never receives the private message or private bonus text through the runtime.

## Reproduction

Run these commands from a checkout of the `codex/m1-r-runtime` topic branch. The `main` checkout at M0.1 commit `190ea3c` has only the `m0` and `verify` CLI commands, so `m1r` is not available there. In this workspace, enter the independent M1-R checkout with:

```powershell
Set-Location D:\MyLab\colluscope\reference\m01-independent
```

For a fresh checkout instead:

```powershell
git clone --branch codex/m1-r-runtime https://github.com/Bubblevan/colluscope.git colluscope-m1-r
Set-Location .\colluscope-m1-r
```

Confirm the branch and repository root before running the commands:

```powershell
git branch --show-current
git rev-parse --show-toplevel
$env:PYTHONPATH = 'src'
python -m pytest -q
python -m colluscope m1r --config configs/m1-r-offline.toml --out runs/m1_r/reproduction-run
python -m colluscope verify-m1r --run runs/m1_r/reproduction-run
python -m colluscope m1r-canary --config configs/m1-r-offline.toml --out runs/m1_r/reproduction-canaries
```

The output paths must be new or empty; the CLI refuses to overwrite existing evidence. The main generator runs its own verifier, and the next command independently reruns verification. The M1-R verifier requires the exact checked source snapshot. These commands make only deterministic local Mock calls and assert zero external/paid model calls.

The original M0 and M0.1 reports/runs/config were not modified in this M1-R worktree. No detector, four-view benchmark, real LLM, provider credential, paid API, or M1-P0/P1 experiment was used.
