# M1-P0 Local Environment Inventory

> **Historical inventory note (2026-10-19):** this earlier report predates the read-only extraction of tokenizer arrays and chat-template metadata embedded in the selected GGUF. The selected user-provided GGUF is accepted; the current static identity and unresolved live-parity findings are superseded by [`M1_P0_GGUF_COMPATIBILITY_EVIDENCE.md`](M1_P0_GGUF_COMPATIBILITY_EVIDENCE.md). No statement here is evidence that the model was loaded or that it fits in GPU memory.

**Observed:** 2026-10-19, Asia/Shanghai. Command output: [`environment-inventory.txt`](../runs/m1_p0_local/iteration-01/environment-inventory.txt), its NUL-normalized display copy [`environment-inventory-readable.txt`](../runs/m1_p0_local/iteration-01/environment-inventory-readable.txt), and [`wsl-runtime-inventory.txt`](../runs/m1_p0_local/iteration-01/wsl-runtime-inventory.txt).

## Host and GPU

| Item | Observed value |
|---|---|
| OS / Python | Windows 11 build 10.0.26200; Python 3.12.4 (Anaconda); pytest 9.1.1 |
| GPU | NVIDIA GeForce RTX 4090 Laptop GPU; 16,376 MiB reported by `nvidia-smi`; 15,855 MiB free at inventory time |
| NVIDIA driver | 616.92 |
| Windows CUDA compiler | `nvcc` 12.5.82 |
| Windows PyTorch | 2.2.2+cu118; `torch.cuda.is_available()` true; PyTorch runtime reports CUDA 11.8 |
| WSL2 | Ubuntu-24.04, WSL version 2. It was stopped at initial listing; read-only checks subsequently showed the GPU and driver inside WSL. |
| WSL Python / CUDA stack | Python 3.12.3; GPU visible; no `nvcc`, no PyTorch, no vLLM package |
| Installed server | Windows `llama-server` build 10068 (`571d0d540`), Clang 20.1.8, Vulkan; enumerates the RTX 4090 Laptop GPU |
| Docker | CLI 27.0.3 present. Docker daemon was not started or used. |
| E: volume | NTFS, 863,145,508,864 bytes total; 184,659,210,240 bytes free at inventory time |

The host and llama.cpp device enumerators reported slightly different total/free VRAM values. The experiment proposal uses 16 GB as the conservative hardware class; no model-memory feasibility claim was measured.

## Model directory

The user-provided root is `E:\Health-Copilot-Models\models`. It contains the existing model directories `bge-large-en-v1.5`, `bge-reranker-v2-m3`, `MedCPT-Article-Encoder`, `MedCPT-Query-Encoder`, `qwen3-8b`, and `Qwen3-Embedding-0.6B`.

The Qwen3-8B folder contains one model weight file:

| File | Size | SHA256 |
|---|---:|---|
| `E:\Health-Copilot-Models\models\qwen3-8b\Qwen3-8B-Q4_K_M.gguf` | 5,027,783,488 bytes | `d98cdcbd03e17ce47681435b5150e34c1417f50b5c0019dd560e4882c5745785` |

The digest matches the existing local `verified_models.json` entry and GGUF download metadata; its earlier recorded path is stale, while the bytes at the user-provided path match. The artifact is Q4_K_M GGUF, not AWQ. No Qwen3-8B `tokenizer.json`, `tokenizer_config.json`, or separate model `config.json` is cached in this folder. The tokenizer revision/hash and chat-template hash therefore remain unmeasured.

## Compatibility findings

- The initial preferred Qwen3-8B-AWQ stack is not available in the model directory. Its official model card documents a vLLM serving path, but no AWQ files were downloaded.
- Current vLLM release metadata lists v0.32.0, but vLLM is not installed in WSL. The local CUDA/PyTorch setup is on Windows and is not a vLLM validation.
- The official vLLM GGUF guide documents experimental GGUF loading and recommends the base-model tokenizer. This local GGUF has no corresponding tokenizer copy or digest. No loading attempt was made.
- `llama-server` is installed and its vendor documentation describes an OpenAI-compatible endpoint with schema-constrained output. Its request schema shape and actual installed build have not been verified against this vLLM-specific adapter. No server was launched.

Sources: [Qwen3-8B-AWQ model card](https://huggingface.co/Qwen/Qwen3-8B-AWQ), [Qwen3-8B-GGUF model card](https://huggingface.co/Qwen/Qwen3-8B-GGUF), [vLLM GGUF guide](https://docs.vllm.ai/en/v0.18.1/features/quantization/gguf/), [vLLM releases](https://github.com/vllm-project/vllm/releases), [llama.cpp server README](https://github.com/ggml-org/llama.cpp/blob/master/tools/server/README.md).

## Non-runnable service proposal

If a later review selects vLLM for the existing GGUF, its proposed WSL launch shape is:

```bash
vllm serve /mnt/e/Health-Copilot-Models/models/qwen3-8b/Qwen3-8B-Q4_K_M.gguf \
  --tokenizer "$QWEN3_8B_BASE_TOKENIZER_DIR" \
  --served-model-name colluscope-qwen3-8b-q4km \
  --host 127.0.0.1 --port 8000 \
  --max-model-len 4096 --gpu-memory-utilization 0.80 --max-num-seqs 1
```

This is a proposal only. The tokenizer variable names an absent, unresolved tokenizer directory, and vLLM is not installed in WSL; the command is not runnable as written and must not be executed before separate review. It is based on the documented local-GGUF plus base-tokenizer form, while official vLLM documentation warns that GGUF support is experimental. The installed `llama-server` is another candidate, but it uses a different schema request contract and needs its own exact offline adapter canary before selection.

## Execution boundary

This inventory used hardware and file metadata commands only. It did not launch `llama-server`, load weights, send a prompt, install/update packages, download a model/tokenizer, or call a remote/paid API.
