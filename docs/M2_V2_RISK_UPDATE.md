# M2-V2 Risk Update — Initial Gate and Bounded Repair

| ID | Risk | Evidence | Control |
|---|---|---|---|
| RV-90 | A failed monitor compatibility gate may be mislabeled as JSON-generation failure, causing a repair to change the wrong layer or relax the contract. | The initial M2-V2 gate independently recomputed 30/30 JSON parses, root shapes, core enums, and normal finish reasons; only 2/30 passed the strict view/permission/citation contract. | Classify syntax, schema, view semantics, and references separately from raw response bytes. Keep original failures immutable and require all ten strict cases per repair. |
| RV-91 | A monitor may confuse an omitted evidence channel with a visible empty channel, or assert message facts without permitted message evidence. | View/permission errors were the largest initial failure class; overlapping diagnostics found message-dependent claims in omitted-message views. The independent no-call input audit passed, so these output errors do not demonstrate transport leakage. | Apply the view × permission table before claim content. Use `not_visible` for omissions and `absent` only for a visible empty stream. Cite exact permitted event types for each positive claim. |
| RV-92 | Repair iterations may exceed the authorized call budget or formal inference may start before the compatibility gate is robust. | A runner now caps the sequence at three repairs, 30 HTTP attempts per repair, and 120 cumulative including the original 30. It requires prior `NO_GO_INTERFACE`, an independent no-call audit, and 10/10 strict valid outputs before formal preparation. | Preserve all attempts and assigned rows. Do not lower thresholds. Stop after repair 3 or any integrity, privacy, or budget violation. Held-out F2/F3 remains gated by F1 validity ≥95%. |

This supplement does not rewrite the earlier risk-register records or the failed compatibility result.

## Repair-01 result

| ID | Risk | Evidence | Control |
|---|---|---|---|
| RV-93 | A prose visibility table may not reliably determine the per-field output values, even when JSON and enums are valid. | Repair-01 passed 3/10 in each candidate. The same invalid patterns remained for action-only privileged views, both text-only branches, an inapplicable omission reason, a falsely empty visible message stream, and duplicated claim references. | Repair-02 freezes a per-claim visibility row before content interpretation; retain strict field-by-field validation and the 10/10 gate. |

Repair-01 used 30 local model requests and 30 HTTP attempts, with zero retries. Its independent raw-response audit passed integrity recomputation and recorded `NO_GO_INTERFACE`. No formal monitor evaluation was run.

## Repair-02 result

| ID | Risk | Evidence | Control |
|---|---|---|---|
| RV-94 | The monitor may recognize the correct view but still emit the wrong forced abstention value/reason, and compact citations may be malformed despite JSON validity. | Repair-02 raised validity to 17/30 but retained three inapplicable `actions_not_in_view` reasons, three incorrect text-only privileged concordance values, and two compact references with whitespace around the separator. | Repair-03 repeats branch-specific prohibitions and exact forced fields, states the `action_only` / text-only privileged special cases, and specifies zero whitespace around the compact citation separator. The same 10/10 gate remains. |

Repair-02 used 30 local model requests and 30 HTTP attempts, zero retries, and ended independently verified `NO_GO_INTERFACE`. Cumulative compatibility attempts are 90/120; the final authorized iteration is capped at 30.
