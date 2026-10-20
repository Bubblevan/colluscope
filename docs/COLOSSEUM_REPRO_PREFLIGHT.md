# Colosseum Reproduction Attempt — Offline Preflight

**Status:** Runtime preflight completed; no agent model calls were made. A bounded local replication plan is awaiting the user's choice of inference scope.

## INSPECT — highest validity risk

The repository has runnable code and a pinned Jira environment, but its supplied configurations do not describe one small run. They expand to 60 episodes each, and use models/runtime settings that do not match the local Qwen3 GGUF. Running an unmodified configuration could trigger thousands of generations, launch vLLM for an uncached checkpoint, load `.env` credentials, and silently retry requests. A local Qwen3 result must therefore be labeled a **protocol-level conceptual replication**, not a reproduction of the paper's model results.

## Frozen source and local environment

| Item | Observed value |
|---|---|
| ColluScope base checkout | `190ea3cb4e5803bea3fede9a0eddbf8e4d57fe51` |
| Colosseum source | `b077fe7e2f10566e92156cc12e06ffb2aac54790` (`main`, clean after setup) |
| CoLLAB gitlink / checked-out commit | `018c9e4229d2c5d980285f25be3cca8d1508140f` |
| OS / Python | Windows 11 build `10.0.26200`; Python `3.12.4` |
| uv | `0.11.29` |
| GPU snapshot | NVIDIA GeForce RTX 4090 Laptop GPU, 16,376 MiB total / 15,533 MiB free at inspection |
| llama.cpp | `llama-server` version `10068` (`571d0d540`), Windows x86-64 |
| Local model | `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf` |
| Local model SHA-256 | `D98CDCBD03E17CE47681435B5150E34C1417F50B5C0019DD560E4882C5745785` |
| Colosseum lock SHA-256 | `392C56D8448A2076E015A7A035D62FEDA51B77B3D58FB7747F1541F98C74F49E` |
| `collusion_jira_topologies.yaml` SHA-256 | `3305410D091F37228CA429E1D68591ED78FD8C8F31C0EF4D03DE7FBD6FBEA06F` |

At inspection time neither local port `8020` nor `8081` had a listening process. No model server was started. The ColluScope checkout contained an untracked `.env`; it was not opened, copied, or staged.

## Source/configuration audit

The official paper's behavioral probe compares nominal agents with a secret channel against a no-secret-channel control; it reports action-based regret/coalition advantage separately from communication-based judge scores. Its general settings use five random seeds, while Figure 4 uses ten seeds and two runs per seed; it reports temperature 0.7 and a 1.5k output-token limit. The paper also says it used a combination of direct model APIs and Azure. [Official arXiv paper, v2](https://arxiv.org/abs/2602.15198)

The local repository's active Jira topology config instead specifies six agents, two colluders, 20 environment seeds, a vLLM auto-start at `127.0.0.1:8020`, checkpoint `Qwen/Qwen2.5-7B-Instruct`, temperature 0.4, and `max_tokens=1024`. With `secret_channel_enabled=[false,true]` and prompt variants `[control,simple]`, the runner executes three effective settings per seed (the non-secret setting forces `control`), for **60 episodes**. Each episode has 6 agents × (4 planning rounds + 1 execution turn) × at most 3 model generations per turn = **90 generation requests**. The supplied sweep therefore has a worst-case budget of **5,400 generations**, before retries.

The file described as the “tiny setup” has 3 agents, four environment variants, five seeds, and three effective settings per environment/seed: also **60 episodes**, at up to 45 generations each (**2,700 total**). It points at Together Kimi-K2-Instruct, not a local model.

The exact local checkpoint is Qwen3-8B Q4_K_M, not the paper's reported model set or the checked-in active config's Qwen2.5-7B-Instruct vLLM checkpoint. Keeping inference local avoids external transmission and fees, but results cannot be presented as a model-for-model replication.

### Request/privacy risk found

The installed `TogetherClient` accepts an explicit custom base URL and uses one OpenAI-compatible `POST /chat/completions` per generation. However, its constructor calls `load_dotenv(override=True)` and its default `TOGETHER_MAX_RETRIES=6` permits **seven physical attempts per generation**. A future local run must set `PYTHON_DOTENV_DISABLED=1`, pass an explicit non-secret local placeholder key, set `TOGETHER_MAX_RETRIES=0`, pin the base URL to `http://127.0.0.1:8081/v1`, and enforce a run-level request cap. The offline adapter-construction check used these settings but sent no request.

## SPECIFY — falsifiers and RUN evidence

| Check | Falsifier | Result / raw evidence |
|---|---|---|
| Source identity | HEAD or submodule differs from the recorded pin | Colosseum `b077fe7e…`; CoLLAB checked out at the parent's exact gitlink `018c9e4…`; parent source status clean |
| Locked environment | Runtime imports fail after setup | `python -m experiments.collusion.run --help` exited 0; Jira environment class resolved successfully |
| Syntax | Any collusion module fails compile | `.venv\Scripts\python.exe -m compileall -q experiments/collusion` exited 0 |
| Config expansion | Effective condition/run count differs from code/config | 60 runs and 2,700 max generations in the 3-agent config; 60 runs and 5,400 max generations in the 6-agent Jira sweep |
| Local adapter isolation | Adapter selects a non-local URL or requires user credentials | Constructor produced `TogetherClient` with exactly `http://127.0.0.1:8081/v1`, explicit placeholder credential, `PYTHON_DOTENV_DISABLED=1`; network-call count 0 |
| Tests | Repository test suite exists and passes | Global `python -m pytest -q`: “no tests ran” (exit 5). Locked `.venv` has no pytest module (exit 1). No test result is claimed. |
| Inference boundary | Any request reaches an LLM/API | **0** model generations; **0** inference HTTP requests; no server started; no external inference call |

### Preserved dependency/setup failures

1. `uv sync --offline --frozen` initially selected a uv-managed Python 3.13 and failed while writing its interpreter cache under AppData: `failed to persist temporary file ... 拒绝访问。 (os error 5)`.
2. Retrying offline with the existing `D:\Anaconda\python.exe` and an in-workspace uv cache created `.venv` but failed because `scipy==1.17.0` was not cached: “Network connectivity is disabled, but the requested data wasn't found in the cache.”
3. Online, locked dependency setup downloaded public packages but the local project build failed with setuptools' flat-layout error: `Multiple top-level packages discovered in a flat-layout: ['dev', 'external', 'experiments']`.
4. The repository README's documented `uv sync --no-install-project` workaround succeeded using the frozen lock: **115 packages installed**. The reference project itself was not installed as a wheel. No API key or model weights were downloaded.

The upstream config/config hashes and model hash above allow the setup state to be rechecked. The setup output is retained in the task tool transcript; the three failures are not reclassified as passes.

## Adversarial review and decision

- The repository's default sweep is not safe to launch as a “quick reproduction”: its actual upper bound is 5,400 generations, and the README itself warns that API costs scale with agent count.
- The checked-in vLLM config would auto-start a server and references a checkpoint not found in the designated local model store. It must not be executed as-is.
- The Together client can read `.env` unless explicitly disabled and retries up to six times by default. A simple logical-call count is therefore not a hard request cap unless retries are also frozen to zero.
- The paper-level setting of temperature 0.7 and 1.5k output tokens differs from the active topology config's 0.4 and 1,024. A reproduction must state which target it follows.
- The secret-channel setting is an intervention, not a gold label. Agreement, secret-channel access, regret, coalition advantage, and welfare loss must remain separate measured fields. The judge model from the paper is not included in the proposed local run.
- The local adapter's base-URL construction was checked; actual chat-completion compatibility and tool-call behavior have **not** been tested.

**Decision:** GO for offline source/configuration preflight only. **NO-GO for model inference until the model/runtime/sampling/call budget are explicitly fixed.** The proposed bounded design is a Jira-only, six-agent, two-colluder, complete-network, nominal-prompt comparison: no-secret control vs secret-channel/control, paired seeds 1–5, local Qwen3 via llama.cpp on `127.0.0.1:8081`, temperature 0.7, max 1,500 output tokens, sequential execution, zero retries, and a hard cap of 900 generation/HTTP requests (10 episodes × 90 maximum). This is a protocol-level conceptual replication and is underpowered relative to the paper's Figure 4 design; it cannot verify the reported cross-model results.

The user was asked to approve one of: this 10-episode local plan; a one-seed 90-request canary; or no model calls. No inference will begin until that choice arrives. No M1/M2 monitor evaluation or other ColluScope artifacts were modified.

## Reproduction commands

Run from `reference/colosseum` after the recorded setup:

```powershell
uv sync --frozen --no-install-project --python 'D:\Anaconda\python.exe'
.\.venv\Scripts\python.exe -m experiments.collusion.run --help
.\.venv\Scripts\python.exe -m compileall -q experiments/collusion
```

These commands validate setup and syntax only; they do not reproduce behavioral results.
