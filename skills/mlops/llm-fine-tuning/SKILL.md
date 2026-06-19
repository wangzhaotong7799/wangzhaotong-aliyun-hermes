---
name: llm-fine-tuning
description: "Guide to LLM fine-tuning toolkits — Axolotl, Unsloth, and TRL (HuggingFace). Covers SFT, LoRA/QLoRA, DPO, PPO, GRPO, YAML configs, and production deployment patterns."
version: 1.0.0
author: Hermes Agent
license: MIT
metadata:
  hermes:
    tags: [fine-tuning, llm, axolotl, unsloth, trl, lora, dpo, ppo, grpo, sft]
---

# LLM Fine-Tuning

This umbrella covers the three major open-source fine-tuning toolkits: **Axolotl** (YAML-driven, production-grade), **Unsloth** (2-5x faster LoRA/QLoRA), and **TRL** (HuggingFace's RLHF toolkit with SFT/DPO/PPO/GRPO).

## When to Use

Load this skill when the user asks about fine-tuning an LLM — LoRA, QLoRA, full fine-tuning, RLHF, DPO, GRPO, or selecting between toolkits.

## Toolkit Selection Guide

| Criterion | Axolotl | Unsloth | TRL |
|-----------|---------|---------|-----|
| **Best for** | Production YAML pipelines | Fast LoRA iterations | RLHF (DPO/PPO/GRPO) |
| **Config format** | YAML | Python API | Python API + CLI |
| **LoRA/QLoRA** | ✅ | ✅ 2-5x faster | ✅ via PEFT |
| **DPO/KTO/ORPO** | ✅ | ✅ | ✅ DPO native |
| **GRPO** | ✅ | Limited | ✅ GRPOTrainer |
| **Multi-GPU** | ✅ DeepSpeed/FSDP | ✅ | ✅ accelerate |
| **Multimodal** | ✅ | Vision models | Text-focused |
| **Install** | `pip install axolotl` | `pip install unsloth` | `pip install trl` |
| **VRAM saving** | DeepSpeed | Tricks (2x less VRAM) | Gradient checkpoint |

## Quick Start by Toolkit

### Axolotl (YAML-driven)

```yaml
# config.yml
base_model: Qwen/Qwen2.5-0.5B
model_type: AutoModelForCausalLM
tokenizer_type: AutoTokenizer

lora:
  r: 16
  lora_alpha: 32
  target_modules: [q_proj, v_proj]

datasets:
  - path: dataset.jsonl
    type: sharegpt

trainer:
  micro_batch_size: 2
  gradient_accumulation_steps: 4
  num_epochs: 3
  learning_rate: 2e-4
  bf16: auto
```

Run: `accelerate launch -m axolotl.cli.train config.yml`

### Unsloth (Fast LoRA)

```python
from unsloth import FastLanguageModel
import torch

model, tokenizer = FastLanguageModel.from_pretrained(
    model_name="unsloth/Qwen2.5-0.5B-bnb-4bit",
    max_seq_length=2048,
    dtype=None,
    load_in_4bit=True,
)
model = FastLanguageModel.get_peft_model(
    model,
    r=16,
    target_modules=["q_proj", "k_proj", "v_proj", "o_proj"],
    lora_alpha=16,
    use_gradient_checkpointing="unsloth",
)

# Train with HF Trainer or TRL
```

### TRL (RLHF Pipeline)

```python
from trl import SFTTrainer, DPOTrainer, GRPOTrainer

# SFT
trainer = SFTTrainer(model="Qwen/Qwen2.5-0.5B", train_dataset=dataset)
trainer.train()

# DPO (preference alignment)
config = DPOConfig(output_dir="model-dpo", beta=0.1)
trainer = DPOTrainer(model=model, args=config, train_dataset=preference_data)
trainer.train()

# GRPO (memory-efficient RL)
config = GRPOConfig(output_dir="model-grpo", num_generations=4)
trainer = GRPOTrainer(model=model, reward_funcs=reward_fn, args=config)
trainer.train()
```

## Common Fine-Tuning Workflows

### Full RLHF Pipeline

```
1. SFT (instruction tuning) → Axolotl or TRL
2. Reward Model (preference scoring) → TRL RewardTrainer
3. PPO (RL optimization) → TRL PPOTrainer or CLI
4. Evaluate alignment → Manual testing + benchmarks
```

### Quick DPO Alignment

```
1. Prepare preference dataset (chosen/rejected pairs)
2. Use TRL DPOTrainer or Axolotl DPO config
3. Tune beta (higher = more conservative, default 0.1)
```

### LoRA Fine-Tuning in Production

```
1. Axolotl for YAML-driven pipelines (DeepSpeed/FSDP)
2. Unsloth for fast iteration (2-5x speed, half VRAM)
3. Export merged weights with `save_compressed: true`
```

## Reference Documentation

Detailed documentation from each toolkit is preserved in the `references/` directory, organized by toolkit:

| Directory | Toolkit | Files |
|-----------|---------|-------|
| `references/axolotl/` | Axolotl | API docs, dataset formats, other guides |
| `references/unsloth/` | Unsloth | LLM docs, LLMs-full, LLMs-txt |
| `references/trl/` | TRL | SFT training, DPO variants, reward modeling, online RL, GRPO deep dive |

### Axolotl Key Patterns

- **FSDP config:** `fsdp_config: { auto_wrap_policy: TRANSFORMER_BASED_WRAP, transformer_layer_cls_to_wrap: LlamaDecoderLayer }`
- **NCCL test:** `./build/all_reduce_perf -b 8 -e 128M -f 2 -g 3`
- **Context parallelism:** `context_parallel_size` must divide total GPUs
- **Save compressed:** `save_compressed: true` (40% disk savings, vLLM compatible)

### TRL Key Patterns

- **GRPO:** Memory-efficient by generating multiple completions per prompt. Requires `reward_funcs` callable.
- **DPO beta tuning:** `beta=0.1` default, higher = more conservative, lower = more aggressive alignment.
- **OOM mitigation:** Reduce `per_device_train_batch_size`, enable `gradient_checkpointing_enable()`.

## Hardware Requirements

| Model | Method | Min VRAM | Recommended VRAM |
|-------|--------|----------|-----------------|
| 7B | LoRA | 8GB | 16GB |
| 7B | Full SFT | 24GB | 40GB |
| 7B | DPO | 12GB | 24GB |
| 7B | PPO | 24GB | 40GB |
| 7B | GRPO | 12GB | 24GB |
| 70B | LoRA | 48GB | 80GB |

All toolkits support gradient checkpointing, mixed precision (BF16), and multi-GPU via accelerate/DeepSpeed.

## Pitfalls

1. **Python 3.6 incompatibility** — Axolotl, Unsloth, and TRL all require Python 3.10+. Match versions in requirements files.
2. **GRPO loss behavior** — Loss may increase initially; this is normal as the policy explores. Monitor reward trend, not loss.
3. **DPO reference model memory** — DPO keeps a frozen reference model, doubling stored parameters. Use LoRA to reduce.
4. **FSDP + QLoRA** — Not all combinations work. Test with small config first.

## Archived Skills

The former standalone skills `axolotl`, `unsloth`, and `trl-fine-tuning` have been absorbed into this umbrella. Their reference documentation files are preserved in `references/<toolkit>/`.
