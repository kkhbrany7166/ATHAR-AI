# Local small models for privacy-sensitive deployment (feasibility, Oct 31)

Mentor recommendation: investigate small open-weight models that a university can run on its own infrastructure. This is a desk study. **No model was downloaded or run.** Speeds marked *estimate* must be measured before they're quoted. The working gpt-4.1-mini reader is unchanged.

## What ATHAR would send to a local model

The explanation reader is the only component that reads student work with a model. Each call carries the rubric, the misconception list, the student's code, the test outcomes and the student's explanation. **No names or IDs are included.** Averages over 752 logged calls: about 2,200 input tokens, 560 output tokens, and 3–4 s latency with gpt-4.1-mini. Two other model uses also touch student data: the practice assistant (student chat messages, which may contain anything a student types) and note drafting (anonymised evidence lines).

The provider interface is deliberately narrow (`athar/ai/provider.py`: `parse(system, user, schema)` and `chat(...)`). vLLM, SGLang, Ollama and llama.cpp all expose OpenAI-compatible servers, so a local provider is the existing OpenAI provider pointed at a university URL plus JSON-schema-constrained decoding. The safeguards that don't depend on the model stay in place unchanged: verbatim-quote validation, abstention handling, the conflict check, approval gates and the rule-based verifier.

## Candidates

| | **Qwen3.5-4B** | **Gemma 4 E4B** | **IBM Granite 4.0 Micro** |
|---|---|---|---|
| Publisher, date | Alibaba Qwen, Feb–Mar 2026 | Google DeepMind, Apr 2026 | IBM, Oct 2, 2025 |
| Size | 4B language model + vision encoder (≈5B in safetensors) | 4.5B effective, **8B total** with per-layer embeddings | 3B, dense |
| Weights memory | ≈8–10 GB BF16; ≈3 GB at 4-bit (*estimate from size*) | 17.9 GB BF16 · 8.9 GB 8-bit · **4.5 GB 4-bit** (Google's table, excluding KV cache) | ≈6 GB BF16; ≈2 GB at 4-bit (*estimate*) |
| Context | 262K native | 128K | 128K |
| Licence | Apache 2.0 | **Apache 2.0** (new for Gemma 4; Gemma 1–3 used custom terms with a prohibited-use policy) | Apache 2.0 |
| Languages | "201 languages and dialects"; the card doesn't list Arabic explicitly | Multilingual | **Lists Arabic** among 12 languages |
| Reasoning mode | **Thinking on by default.** It must be turned off for the reader (`enable_thinking: false`), or output length and latency multiply | Optional thinking mode | None |
| Instruction following | IFEval 89.8 (vendor-reported) | Not in the card excerpt | IFEval avg 82.3 (vendor-reported) |
| Structured output | Through the server: vLLM/SGLang `json_schema`, Ollama `format` | Through the server; native function calling | Through the server; tool calls as JSON |
| Serving | vLLM and SGLang (main branch at the time of writing), Transformers, llama.cpp, Ollama, LM Studio | Transformers, llama.cpp, Ollama, LiteRT-LM (mobile) | Transformers, vLLM, llama.cpp, Ollama, MLX community builds |

**Stable fallback:** Qwen3-4B-Instruct-2507 (Apache 2.0, 4B, non-thinking only, IFEval 83.4, vLLM ≥ 0.8.5). It's older, but it has no thinking toggle to get wrong and has mature tooling, which makes it a good first measurement.

**Why these three.** They're all permissively licensed, all fit a single 16–24 GB GPU or a 16 GB laptop when quantised, and all are supported by the common local servers. They also come from three different publishers, which reduces dependence on one vendor. I left out older Gemma releases because of their custom terms, and Phi-4-mini (MIT, Feb 2025) as older than the three above with no clear advantage for this task.

## Deployment options for a university

| Option | When it fits | Structured output |
|---|---|---|
| **vLLM** (or SGLang) on one GPU server | Department or university service; batches a whole class at once | `response_format: json_schema` through the OpenAI-compatible API, with xgrammar or guidance backends |
| **Ollama** on a workstation or small server | Pilot, single course | `format` with a JSON schema; also `response_format` on its OpenAI-compatible endpoint |
| **llama.cpp server** | CPU-only or minimal installs | JSON-schema-to-grammar constrained decoding |

**Hardware and latency** (*estimates, to be measured*):
- **Apple M2, 16 GB (this laptop), 4-bit 4B model:** roughly 20–30 output tokens/s, so about 25–40 s per explanation and 50–75 min for a class of 114 run one at a time. Fine for overnight batch grading; too slow for live chat.
- **One data-centre GPU (L4/A10-class, 24 GB) with vLLM batching:** a class in minutes. A practice-assistant reply in a few seconds.

## Privacy: what improves and what doesn't

**Improves**
- Student code, explanations and chat messages never leave university-controlled infrastructure. There's no third-party processor, retention policy or cross-border transfer to assess, which simplifies data-protection review (for example under Saudi Arabia's PDPL or an institution's own policies).
- No vendor-side logging or abuse-monitoring copies.
- The model version is pinned: a weight file with a hash, not a hosted model that can change without notice. That also makes the evaluation reproducible.

**Doesn't go away**
- **Data at rest:** the SQLite database, server logs, prompt logs and backups still hold student work. They need encryption, retention limits and access control.
- **Who can reach the endpoint:** a local inference server is often unauthenticated by default. It must sit behind the university network and authentication.
- **Prompt injection through student text:** a student can write instructions in an explanation. Quote validation and fixed rules limit the damage, but they don't remove it.
- **Supply chain:** download weights only from the publisher's official repository, verify hashes, use safetensors/GGUF, avoid `trust_remote_code`, and turn off tool telemetry.
- **Free-text chat:** the practice assistant can receive anything a student types, including personal details, so it needs its own retention rule.
- **Quality risk is a fairness risk:** a weaker local model that misreads explanations harms students in a different way. Privacy doesn't justify an unmeasured downgrade, which is why the measurement below comes first.

## Recommendation and the measurement it needs

1. **Don't switch now.** gpt-4.1-mini stays the demo reader. ATHAR already sends no names, and the documentation should say so.
2. **Add a `local` provider option:** the existing OpenAI provider with a configurable base URL and JSON-schema mode. It's small, it can be tested with the existing mocked-provider tests, and it doesn't change the default.
3. **Measure before claiming.**
   - Run reader-v3, **unchanged**, on the frozen final (36) and final-2 (24) sets with Qwen3-4B-Instruct-2507 and Gemma 4 E4B.
   - Report misconception F1, stopping-judgment accuracy, quote-validation pass rate, abstentions, malformed outputs and latency, next to gpt-4.1-mini.
   - Cost: $0 in API spend, about a 3–5 GB download per model and roughly 1–2 hours of laptop compute.
   - No prompt changes on the final sets. Any local-model prompt work would happen on dev, then be checked once on a new untouched set.
4. **Decide by evidence.** If a local model comes close on the frozen sets, a privacy-first deployment can use it for reading, and its measured gap is stated. If it doesn't, the honest design is a hybrid: send only de-identified explanation text to a hosted model under a data-processing agreement, with the professor approving every consequence.

## Sources

- Qwen3.5-4B model card: https://huggingface.co/Qwen/Qwen3.5-4B
- Qwen3-4B-Instruct-2507 model card: https://huggingface.co/Qwen/Qwen3-4B-Instruct-2507
- Gemma 4 overview and memory table: https://ai.google.dev/gemma/docs/core · E4B card: https://huggingface.co/google/gemma-4-E4B-it
- Granite 4.0 Micro model card: https://huggingface.co/ibm-granite/granite-4.0-micro
- vLLM structured outputs: https://docs.vllm.ai/en/latest/features/structured_outputs.html
- Ollama structured outputs: https://docs.ollama.com/capabilities/structured-outputs
