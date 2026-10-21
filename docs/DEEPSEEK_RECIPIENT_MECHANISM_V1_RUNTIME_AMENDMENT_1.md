# Runtime Amendment 1 — Manifest Metadata Mapping

The first invocation of the registered launcher stopped before creating a run manifest or calling the provider. It raised `KeyError: 'tokenizer_source_commit'`: the launcher looked for a top-level field, while the frozen config records the same pinned commit at `tokenizer.repository_commit`.

This amendment adds `scripts/run_deepseek_recipient_mechanism_v1_hotfix.py`. It first runs the original frozen-input and config-hash validation, then maps the already-verified nested tokenizer commit into the in-memory manifest-only field. It writes an amendment receipt under the Git-ignored run root containing the base-launcher, wrapper, config, schedule, and Tokenizer identities before dispatch.

The amendment does not modify or regenerate the config, schedule, matrices, prompts, reward amounts, sample selection, model parameters, JSON interface, response parser, retry policy, scoring, or budget. It makes no HTTP request. The original launcher and preregistration remain byte-for-byte unchanged.

The failed first invocation is retained in `docs/results/deepseek-recipient-mechanism-v1/launcher-first-failure.log`. The corrected local gate is:

```powershell
python scripts/run_deepseek_recipient_mechanism_v1_hotfix.py --check-only
```

The live command after this amendment is pushed:

```powershell
python scripts/run_deepseek_recipient_mechanism_v1_hotfix.py
```
