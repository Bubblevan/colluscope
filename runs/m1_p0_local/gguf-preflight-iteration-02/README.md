# M1-P0 GGUF bounded preflight attempt 02

## Result

**BLOCKED BEFORE LAUNCH.** The user authorized the bounded local compatibility preflight, but its frozen port `127.0.0.1:8080` was already bound on `0.0.0.0` by PID 12152 (`ApplicationWebServer.exe`), associated with service `NIApplicationWebServer`. Windows did not return the executable path or command line. No HTTP request was sent; the process was not stopped.

## Scope and execution boundary

- Authorized scope: 6 logical requests, at most 12 HTTP attempts and 4 model completion attempts.
- Actual use: 0 logical requests, 0 HTTP attempts, 0 completions, 0 paid calls.
- `llama-server` was not started and GGUF weights were not loaded.
- No M1-P0 full pilot or M2 work was performed or authorized.
- Existing M0/M0.1/M1-R and `gguf-iteration-01` outputs were not modified.

## Evidence files

- `manifest.json`: seven-file SHA256/size manifest for all files in this directory other than the manifest itself. The aggregate is SHA256 over canonical compact JSON of the sorted file records.
- `blocked-before-launch.json`: branch/commit, checkpoint and launcher hashes, GPU observation, port/process finding, and execution boundary.
- `port-8080-owner-followup.txt`: read-only `tasklist /svc` association of PID 12152 with `NIApplicationWebServer`.
- `static-identity.json` / `static-identity.log`: metadata-only revalidation; server version and device enumeration only.
- `llama-server-help-static.txt`: static CLI capability output; no model load.
- `gpu-before-launch.txt`: one GPU telemetry sample before any local model load.

## Reproduction

From the repository root in PowerShell:

```powershell
$env:PYTHONPATH = 'src'
python scripts/inspect_local_gguf.py `
  --config configs/m1-p0-llama-local-draft.toml `
  --out runs/m1_p0_local/gguf-preflight-iteration-02/static-identity-reproduced.json
Get-NetTCPConnection -State Listen -LocalPort 8080
Get-CimInstance Win32_Process -Filter 'ProcessId = 12152' |
  Select-Object ProcessId,Name,ExecutablePath,CommandLine
tasklist /svc /fi "PID eq 12152"
```

Do not send model prompts to the existing listener or terminate the NIApplicationWebServer service as part of this run. Resume only after the listener is freed or after a new preflight-only port is explicitly approved and frozen.
