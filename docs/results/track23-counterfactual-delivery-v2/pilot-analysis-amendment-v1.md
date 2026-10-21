# Pilot analysis amendment v1

**Experiment:** `track23-counterfactual-delivery-v2`

**Model/API calls made by this amendment:** 0

The registered analyzer was not edited. Its frozen SHA-256 is `9069c1e05d433501cee7564b8282b35b3ae90bd452511893dda0d3f5612164fe`.

## Retained analysis failures

The first invocation stopped before producing a result because `NEUTRAL_TEXT` was not imported into the analyzer module. The analysis-only adapter verified the registered analyzer hash and supplied that constant from the frozen prompt-builder module. It did not change requests, responses, outcomes, gates, or analysis code.

The first completed analysis reported `INVALID_EXPERIMENT` because its `integrity_pass` expression included the behavior-feasibility condition requiring at least five distinct-proposal contexts. The protocol's ambiguity rule says a technically valid pilot that fails a behavior-feasibility gate is `INCONCLUSIVE`. The initial private and public summaries are preserved as `pilot_summary_initial_classification.json` and `pilot-summary-initial-classification.json`.

The correction script verifies the registered analyzer hash and `raw_trace_audit.status == PASS`, then separates the already frozen gates into technical integrity and behavior feasibility. It does not alter the proposal-opportunity threshold or any observed value. Technical integrity passed; behavior feasibility did not. The canonical pilot summary is therefore `INCONCLUSIVE`, with expansion `NO_GO`.

## Scope

This is a transparent post-run classification correction required to apply the registered ambiguity rule consistently. It is not an independent scientific replication or review. The raw request/response audit and the frozen outcomes are unchanged.
