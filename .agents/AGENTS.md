# AI Research Agent Customization Rules: AGENTS.md

This document defines workspace rules for AI agents operating in this repository. It provides a comprehensive routing guide on **when to refer to which installed skill** from the `.agents/skills/` directory.

---

## 1. Core Rule: Proactive Skill Routing

Whenever a task falls under any of the following research or engineering categories, the agent **MUST** proactively open and read the corresponding skill's `SKILL.md` before writing code or configuring scripts.

| Task Category | Relevant Skill Name(s) | Trigger / When to Refer |
|:---|:---|:---|
| **Autonomous Orchestration** | `0-autoresearch-skill` | When managing the end-to-end research lifecycle (literature survey $\to$ hypothesis testing $\to$ experiments $\to$ paper writing). |
| **Model Architectures** | `litgpt`, `nanogpt`, `rwkv`, `mamba`, `torchtitan` | When modifying model configurations, training from scratch, or implementing state-space models. |
| **Custom Tokenization** | `huggingface-tokenizers`, `sentencepiece` | When preparing vocabulary files, training new tokenizers, or optimizing sequence encodings. |
| **Parameter Fine-Tuning** | `peft`, `axolotl`, `unsloth`, `llama-factory` | When configuring LoRA, QLoRA, DoRA, or launching training recipes. |
| **Post-Training & RLHF** | `grpo-rl-training`, `trl-fine-tuning`, `openrlhf`, `verl`, `slime`, `miles`, `torchforge` | When setting up Reinforcement Learning from Human/AI Feedback (RLHF/RLAIF), or training reasoning models. |
| **Mechanistic Interpretability** | `transformer-lens`, `saelens`, `pyvene`, `nnsight` | When performing hook-point interventions, activation patching, sparse autoencoder analysis, or causal tracing. |
| **Data Processing & Curation**| `ray-data`, `nemo-curator` | When building high-performance, GPU-accelerated preprocessing and deduplication pipelines. |
| **Model Optimization** | `flash-attention`, `bitsandbytes`, `gptq`, `awq`, `hqq`, `gguf` | When applying quantization (4-bit/8-bit), model compression, or optimizing attention operations. |
| **Distributed Scaling** | `megatron-core`, `deepspeed`, `pytorch-fsdp2`, `ray-train`, `accelerate` | When training models across multiple GPUs/nodes, setting up ZeRO partitioning, or configuring pipeline/tensor parallelism. |
| **Inference Serving** | `vllm`, `sglang`, `tensorrt-llm`, `llama-cpp` | When deploying model APIs for production serving, using PagedAttention, or speculative decoding. |
| **Benchmarking & Evaluation** | `lm-evaluation-harness`, `bigcode-evaluation-harness`, `nemo-evaluator` | When evaluating alignment, code generation, or reasoning benchmarks. |
| **Agent Toolkits** | `langchain`, `llamaindex`, `crewai`, `autogpt` | When constructing multi-agent orchestrations, custom tool-calling interfaces, or vector stores. |
| **Vector DB & RAG** | `chroma`, `faiss`, `pinecone`, `qdrant`, `sentence-transformers` | When setting up retrieval-augmented generation pipelines or embedding structures. |
| **Structured Prompts** | `dspy`, `outlines`, `instructor`, `guidance` | When enforcing rigid JSON outputs or compiling prompt pipelines. |
| **Writing \& Rigor** | `ml-paper-writing`, `academic-plotting`, `rigor-reviewer`, `compiler` | When drafting paper drafts, formatting LaTeX sources, or checking math and bibtex citations. |

---

## 2. Dynamic Execution Workflow

1. **Scan Workspace Customizations**: At the beginning of each session, review `.agents/skills/` to identify the full catalog of available engineering skills.
2. **Retrieve Skill Information**: Before executing any code in a domain listed above, open and view the specific skill's `SKILL.md` (e.g., `view_file` on `file:///.agents/skills/grpo-rl-training/SKILL.md`).
3. **Align Implementation**: Ensure the code templates, troubleshooting checklists, and parameter guidelines defined in the skill file are strictly followed. Do not make ad-hoc configurations when standard patterns are present.
