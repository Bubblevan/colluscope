from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / "src"))
from colluscope.gguf_tokenizer import GGUFChatTokenCounter


RUN = ROOT / "runs/m1_p0_local/25ep-pilot-20261019/run"
MODEL = Path(r"E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf")
EXPECTED_SHA256 = "d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785"

rows = [json.loads(line) for line in (RUN / "preflight/requests.jsonl").read_text(encoding="utf-8").splitlines()]
row = next(item for item in rows if item["request_id"] == "preflight-tokenize")
server_ids = json.loads(row["raw_response"])["tokens"]
body = json.loads(row["request_body"])
counter = GGUFChatTokenCounter(MODEL, expected_artifact_sha256=EXPECTED_SHA256)
local_ids = counter.tokenizer.encode(body["content"], add_special_tokens=False).ids
vocabulary = counter.metadata["tokenizer.ggml.tokens"].values
types = counter.metadata["tokenizer.ggml.token_type"].values
first_diff = next((i for i, (a, b) in enumerate(zip(local_ids, server_ids)) if a != b),
                  min(len(local_ids), len(server_ids)))

result = {
    "local_token_count": len(local_ids),
    "server_token_count": len(server_ids),
    "first_difference_index": first_diff,
    "local_window": local_ids[max(0, first_diff - 5):first_diff + 10],
    "server_window": server_ids[max(0, first_diff - 5):first_diff + 10],
    "server_window_pieces": [vocabulary[token_id] if token_id < len(vocabulary) else None
                              for token_id in server_ids[max(0, first_diff - 5):first_diff + 10]],
    "local_window_pieces": [counter.tokenizer.id_to_token(token_id)
                             for token_id in local_ids[max(0, first_diff - 5):first_diff + 10]],
    "special_token_candidates": [
        {"token_id": token_id, "piece": vocabulary[token_id], "token_type": types[token_id]}
        for token_id in set(server_ids[max(0, first_diff - 5):first_diff + 10])
        if token_id < len(vocabulary)
    ],
    "prefix_equal_before_difference": local_ids[:first_diff] == server_ids[:first_diff],
    "full_sequences_equal": local_ids == server_ids,
}
output = RUN.parent / "tokenizer-mismatch-diagnostic.json"
output.write_text(json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(json.dumps(result, ensure_ascii=False, sort_keys=True))
