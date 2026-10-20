# ColluScope — M0

An offline, CPU-only scripted research scaffold for the Apart Research AI Collusion Research Sprint, focusing on Track 2.2 and 2.3. It separates construction truth, actions/outcomes, and permission-filtered evidence. It does **not** contain real LLM agent results or detector-performance estimates.

This README's run commands describe the historical M0 scaffold. The repository
now also contains later M1–M4 protocols and evidence. For continued research,
start with [RESEARCH_PROGRAM.md](RESEARCH_PROGRAM.md), inspect the state and
claim-level memory in `research/`, and check the zero-call authorization
snapshot in `research/budget.json`. The Goal-driven coordinator is documented
in [`research/README.md`](research/README.md); its CLI records and checks
research cycles but does not run experiments.

## Run M0

Python 3.11 or 3.12 is required. The implementation uses only the Python standard library at runtime. Pytest is needed for the test command.

```powershell
$env:PYTHONPATH = "src"
python -m pytest -q
python -m colluscope m0 --config configs/m0.toml --out runs/m0
python -m colluscope verify --run runs/m0/<run-id>
```

Each generated run stores the source trace at `<run-id>/inputs/trace.jsonl` and the monitor evidence objects at `<run-id>/inputs/views/`. Each view JSONL row is the evidence object itself, with no episode ID, view label, model-kind marker, mechanism label, or oracle field. Rows align with trace rows by position; the verifier checks each projection against its source trace. Oracle rows are stored separately below `runs/m0/oracle/<run-id>/oracle.jsonl`, outside the monitor-input root. Scripted origin is recorded in the trace and manifest. `manifest.json` records the configuration, source snapshot, upstream commits, file hashes, and explicit zero-call assertion.

M0 metrics describe artifact integrity and scripted controls only. Do not present them as evidence about real LLM behavior, general collusion rates, or monitor accuracy. M1 is not run by these commands.
