# M2-V2 Repair-01 Evidence

**Decision:** `NO_GO_INTERFACE`; do not start the 1,000-row evaluation from this candidate set.

## Frozen execution

- Repair source commit: `191d5d9c1273d5defa5d5f55bb314ad02cdd7982`.
- Candidate registry: `configs/m2-v2-repair-01-candidates.json`, SHA-256 `d506b8581342b53ff94ccacff829e9e241a2b6a6874a85f32b7b68895a79b174`.
- Registry freeze: SHA-256 `11cc31b7d4335c637abf1117afcff515f06c5ce31109bbd4b4c45e7773990599`.
- No-call manifest: SHA-256 `1ff4f55d22f07e7429438878ba735373b53dff433ead039672b3221ef1d0d7a6`.
- Independent no-call input verification: `PASS_M2_V2_PREFLIGHT_INPUT_AUDIT`; 30 unique payloads, 10 per candidate, zero model calls/HTTP attempts, 9 ACL-verified directories, all 1,450 V1 entries intact, 12 privileged message-bearing rows, no Public-only private message evidence.
- Model: `Qwen3-8B-Q4_K_M.gguf`, SHA-256 `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785`.
- llama.cpp server SHA-256 `3a8aea5f889c4b4c2ec41c98f4e1ed484bb7a40c4096883acb23d3cfe26b59fb`; runtime bundle `9559fd2af95a7e83e3cf4a04aab22b67e1d1a2ec032b1e983ce091a6283c7759`; tokenizer `06e72b9773cfad908874ae1a7aa92686068557c4aa624c857db88fe97052704f`; chat template `57f1fd00f0013a2be96aa79b857391f27e23df5b5f847072b524c897e24d0361`.
- Endpoint: authenticated local `127.0.0.1:8081`, offline mode, no external fallback or paid call. Server process stopped and temporary API key removed.

## Results

| Candidate | Strict valid | Invalid | Fixed gate |
|---|---:|---:|---|
| C1 full / JSON Schema | 3/10 | 7/10 | Fail |
| C2 full / JSON object | 3/10 | 7/10 | Fail |
| C3 compact / JSON Schema | 3/10 | 7/10 | Fail |

The candidate registry, order C1 → C2 → C3, acceptance rule, schema bytes, evidence permission, and F1 case were unchanged. Each candidate received ten attempts; no retry occurred. In all candidates, 30/30 outputs parsed as JSON, had the required root fields and valid core enums, and ended with `finish_reason=stop`. Three strict valid outputs are not an accuracy estimate: the compatibility case is one F1 episode projected ten different ways.

All three candidates had identical validity by view/permission cell: `structured_evidence + public_only` 3/3; `action_only + public_only` 2/3; `raw_fusion + public_only` 2/3; `text_only + public_only` 1/3; `structured_evidence + privileged_audit` 1/3; all other cells 0/3. C1 and C2 assistant text was byte-identical on all ten matched payload pairs, even though response-format bodies and derived seeds differed; this does not identify a causal mechanism. C3 produced different outputs but also had 3/10 valid.

First-rejection categories across 30 rows: view/permission mismatch 12; evidence-reference violation 3; abstention semantics 2; other contract violation 4; valid 9. Across all violations, the recurring errors were:

- private message facts (`message_delivery`, proposal, concordance, acceptance, commitment) asserted in views where messages were omitted;
- action facts asserted in text-only views;
- `messages_not_in_view` used when Privileged Audit exposed messages;
- `no_delivered_message` used while a visible delivered message existed;
- duplicate event IDs in one claim's citation array;
- missing message or multiple ballot citations in C3's positive claims.

These are overlapping checks, not mutually exclusive counts. Full sanitized tuple-level tables are in [`docs/results/m2_v2_repair_01/m2_v2_bad_case_diagnostics.csv`](results/m2_v2_repair_01/m2_v2_bad_case_diagnostics.csv); raw assistant text and exact private messages are excluded.

## Call and resource accounting

- Logical generation requests: 30/30.
- Physical HTTP attempts: 30/30; retries: 0.
- Prompt tokens reported by server: 60,442; completion tokens: 5,237.
- Median latency: 3.69307 s; maximum: 5.237655 s.
- GPU samples: 109; peak utilization 100%; minimum free memory 9,745 MiB.
- Request/response inventory SHA-256 `7af4546acbd67dd50b0f6fc3fcb611f004cf612fb381854c657171b17a56c38b`.
- Decision SHA-256 `2b382304f85da9cf306e4d0fec22009ed5ab601302e3c034fa9954db5959e4f8`.
- Attempt-ledger SHA-256 `188bc85b3535c8130b8794fed77af5331b6e675b7616d33408dd70e40753d9ab`.
- Server-log SHA-256 `268c6d9c22468a08683f474931c56d4d697f1c881b42511293cd0dc6bb0f69b9`.
- GPU-sample SHA-256 `7d6dbe8f6d64b0daa04b18d75a96632ab35c2b0115191d7c61836008f9260811`.

## Adversarial interpretation

Repair-01 increased strict validity from the original gate (1/10, 1/10, 0/10) to 3/10 for all three candidates. It did not resolve branch-selection errors consistently. The pattern suggests the prose visibility matrix was not reliably converted into forced field values, while claim-specific citation construction remained error-prone. This is a hypothesis from output patterns, not a known internal model mechanism.

The next falsifiable repair should make the output fields mechanically conditional on one of five explicit view/permission rows and require the model to copy forced values and reasons before inspecting content. It should separately require unique exact event IDs within each claim citation list. Keep the exact same threshold and candidate sequence. No schema/parser relaxation is justified because syntactic/root/enum validity was already 30/30.

## Reproduction

From repository root, the no-call preparation and input-audit commands are:

```powershell
python scripts/run_m2_v2_repair.py --iteration 1 --prepare-preflight --out runs/m2-v2/recovery-20261019/repair-01
python scripts/run_m2_v2_repair.py --iteration 1 --verify-inputs --out runs/m2-v2/recovery-20261019/repair-01
python scripts/run_m2_v2_repair.py --iteration 1 --preflight --out runs/m2-v2/recovery-20261019/repair-01
python scripts/run_m2_v2_repair.py --iteration 1 --audit-results --out runs/m2-v2/recovery-20261019/repair-01
```

All raw T/B/E, prompts sent to the model, HTTP bodies, logs, and resource samples remain under the current-user-ACL-restricted ignored run folder.
