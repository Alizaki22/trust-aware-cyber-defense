# LLM Fine-Tuning

This document describes the fine-tuning methodology planned for Phase 2 of the project. Fine-tuning does not occur in Phase 1 (see `docs/DECISIONS.md`, D-004).

## Overview

Phase 2 introduces a fine-tuned open-source LLM into the existing Phase 1 architecture. The goal is to compare agent performance using a fine-tuned model versus the base model used in Phase 1, while keeping everything else constant.

## Fine-Tuning Approach

### Parameter-Efficient Fine-Tuning (PEFT)

Full fine-tuning of a large language model requires updating all model parameters, which demands significant compute and memory. Parameter-efficient fine-tuning (PEFT) methods adapt the model by training only a small fraction of parameters while keeping the rest frozen.

This project uses PEFT because:
- **Hardware constraints:** Student hardware cannot support full fine-tuning of large models.
- **Data constraints:** Available cybersecurity training data is limited.
- **Time constraints:** PEFT training is significantly faster than full fine-tuning.
- **Comparison validity:** PEFT preserves the base model's general capabilities while adding domain-specific knowledge.

### LoRA (Low-Rank Adaptation)

LoRA injects trainable low-rank decomposition matrices into the transformer layers of a frozen pre-trained model.

**How it works:**
1. The original weight matrix W is frozen (no gradient updates).
2. Two small matrices A and B are added such that the effective weight becomes W + BA.
3. Only A and B are trained — typically 0.5%–5% of the original parameter count.
4. At inference time, the adapter weights can be merged with the original weights for zero additional latency.

**Key hyperparameters:**
| Parameter | Description | Typical Range |
|---|---|---|
| `r` (rank) | Rank of the decomposition matrices | 4–64 |
| `alpha` | Scaling factor for LoRA updates | 16–64 |
| `target_modules` | Which layers to apply LoRA to | `q_proj`, `v_proj`, `k_proj`, `o_proj` |
| `dropout` | Dropout rate for LoRA layers | 0.05–0.1 |

### QLoRA (Quantized LoRA)

QLoRA extends LoRA by quantizing the frozen base model to 4-bit precision:

- **NF4 quantization:** Uses a NormalFloat 4-bit data type optimized for normally distributed weights.
- **Double quantization:** Quantizes the quantization constants themselves to save additional memory.
- **Paged optimizers:** Uses NVIDIA unified memory to handle memory spikes during gradient checkpointing.

This allows fine-tuning models with significantly more parameters on consumer-grade GPUs (e.g., a 65B model on a single 48GB GPU, or smaller models on 8–16GB GPUs).

**Decision: LoRA vs. QLoRA** — the team will decide based on available hardware. QLoRA is preferred if GPU memory is a bottleneck.

## Base Model Candidates

The base model for fine-tuning is **TO BE DECIDED**. Candidates should meet these criteria:

| Criterion | Requirement |
|---|---|
| License | Open-source, permitting academic use and fine-tuning |
| Size | Small enough to fine-tune on available hardware with QLoRA |
| Quality | Strong general language understanding and reasoning |
| Ecosystem | Supported by Hugging Face Transformers and PEFT library |

Candidate families to evaluate (not commitments):
- **LLaMA / LLaMA 2 / LLaMA 3** — Meta's open-weight models, widely used in fine-tuning research.
- **Mistral / Mixtral** — Efficient open-weight models with strong performance.
- **Qwen** — Alibaba's multilingual open-source models.
- **Phi** — Microsoft's small but capable models.

The final choice depends on hardware availability and benchmarking results.

## Training Data

### Data Requirements

Fine-tuning data should:
1. Be relevant to the agent's specific task (classification, threat intelligence, behavioral analysis, or verification).
2. Be structured in an instruction-following format compatible with the agent's prompt template.
3. Be appropriately licensed for academic use.
4. Be clearly labeled (real vs. synthetic).

### Data Format

Training data should follow an instruction-tuning format:

```json
{
  "instruction": "Analyze the following security event and classify it.",
  "input": "<security event data>",
  "output": "<expected structured finding as JSON>"
}
```

See `docs/DATASET.md` for detailed dataset documentation.

### Data Volume

PEFT methods can achieve meaningful adaptation with relatively small datasets:
- **Minimum viable:** 500–1,000 high-quality examples.
- **Recommended:** 2,000–5,000 examples for a more robust adaptation.
- **Quality over quantity:** A small, well-curated dataset is preferable to a large, noisy one.

## Hardware Requirements

| Approach | Minimum GPU Memory | Example Hardware |
|---|---|---|
| LoRA (7B model) | ~16 GB VRAM | NVIDIA T4, RTX 3090/4090 |
| QLoRA (7B model) | ~8 GB VRAM | NVIDIA RTX 3060/4060 |
| QLoRA (13B model) | ~16 GB VRAM | NVIDIA RTX 3090/4090 |
| QLoRA (70B model) | ~48 GB VRAM | NVIDIA A100 |

If local hardware is insufficient, cloud computing options include:
- Google Colab (free tier: T4 GPU, ~16 GB VRAM)
- Google Colab Pro (A100 GPU)
- University computing resources (if available)

## Training Procedure

### Step 1: Prepare Training Data
1. Select and preprocess the dataset (see `docs/DATASET.md`).
2. Format into instruction-tuning structure.
3. Split into training (80%), validation (10%), and test (10%) sets.
4. Validate data quality and format.

### Step 2: Configure Fine-Tuning
1. Load the base model with appropriate quantization (4-bit for QLoRA).
2. Configure LoRA/QLoRA hyperparameters.
3. Set training hyperparameters (learning rate, batch size, epochs).

### Step 3: Train
1. Train using the Hugging Face `Trainer` or `SFTTrainer`.
2. Monitor training loss and validation loss for overfitting.
3. Use early stopping if validation loss increases.
4. Save checkpoints periodically.

### Step 4: Evaluate
1. Test on held-out test set.
2. Compare outputs against the base model on the same inputs.
3. Check for catastrophic forgetting (loss of general capabilities).
4. Run through the full multi-agent pipeline to test integration.

### Training Hyperparameters (Starting Points)

| Parameter | Value | Notes |
|---|---|---|
| Learning rate | 2e-4 | Standard for LoRA fine-tuning |
| Batch size | 4–8 | Adjusted for available GPU memory |
| Epochs | 3–5 | Monitor for overfitting |
| Warmup ratio | 0.03 | Gentle warmup to avoid instability |
| Weight decay | 0.001 | Light regularization |
| Gradient accumulation | 4 | Effective batch size = batch_size × accumulation |
| Max sequence length | 512–1024 | Adjusted for input event length |

These are starting points — actual values will be tuned based on experimental results.

## Phase 2 Integration

1. Fine-tune the model using the procedure above.
2. Save the trained LoRA adapter weights.
3. In the multi-agent system, configure the selected agent(s) to load the base model + LoRA adapter.
4. Run the same test scenarios used in Phase 1.
5. Compare Phase 1 (base LLM) vs. Phase 2 (fine-tuned LLM) results.

The agent code itself does not change — only the model it calls. See `docs/SYSTEM_ARCHITECTURE.md` for the technical integration path.

## Which Agent(s) to Fine-Tune

**TO BE DECIDED** (see `docs/DECISIONS.md`, D-010). Factors to consider:

- **Dataset availability:** Which agent's task has the best available training data?
- **Expected impact:** Which agent would benefit most from domain-specific fine-tuning?
- **Feasibility:** Which fine-tuning task is achievable within the team's time and compute budget?
- **Experimental value:** Which comparison would be most informative for the project's research questions?

No agent is assumed to be fine-tuned by default.

## Tools and Libraries

| Tool | Version | Purpose |
|---|---|---|
| Hugging Face Transformers | Latest | Model loading and inference |
| PEFT | Latest | LoRA/QLoRA adapter implementation |
| bitsandbytes | Latest | 4-bit quantization for QLoRA |
| trl | Latest | `SFTTrainer` for supervised fine-tuning |
| datasets | Latest | Dataset loading and preprocessing |
| wandb (optional) | Latest | Training metrics tracking |

## Risks and Mitigations

| Risk | Mitigation |
|---|---|
| Insufficient hardware | Use QLoRA with aggressive quantization; use cloud compute if needed |
| Poor fine-tuning results | Start with a small, high-quality dataset; compare against baseline |
| Catastrophic forgetting | Use PEFT (preserves base model); test general capabilities post-training |
| Data quality issues | Manually review a sample of training data; use established datasets |
| Overfitting | Use validation set; monitor loss curves; use early stopping |

## Related Documentation

- `docs/DECISIONS.md` (D-004, D-007, D-010) — Fine-tuning decisions
- `docs/RESEARCH.md` — Research background on PEFT methods
- `docs/DATASET.md` — Dataset documentation
- `docs/EXPERIMENTS.md` — Experiment design for Phase 1 vs. Phase 2 comparison
