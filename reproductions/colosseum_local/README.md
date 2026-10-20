# Local Colosseum protocol replication

This folder contains the frozen, bounded orchestration for a local conceptual
replication of the Colosseum Jira secret-channel comparison. It is not an
exact replication of the paper's model/provider results.

All real run outputs, raw prompts, trajectories, messages, local server logs,
and progress/request ledgers are kept under the ignored
`reference/colosseum/experiments/collusion/outputs/` tree. Do not publish those
raw artifacts automatically: they can contain private-channel messages.

The orchestration has a `--freeze-only` mode and a no-inference `--self-test`
mode. The real run requires the separately approved local Qwen3 configuration
and is invoked only with `--run`.

Before freezing or running, set `COLLUSCOPE_MODEL_PATH` and
`COLLUSCOPE_LLAMA_SERVER` to the locally audited files. Machine-specific paths
are not embedded in the committed runner source or shared protocol.
