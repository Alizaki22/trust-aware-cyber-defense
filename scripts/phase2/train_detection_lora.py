"""Phase 2 Detection Agent LoRA fine-tuning script.

Team decision references:
  D-001 â€” Two-phase development (Phase 1 baseline, Phase 2 fine-tuned)
  D-004 â€” Fine-tuning scoped to Phase 2 only
  D-005 â€” Phase 1 as literal baseline (only the model changes, nothing else)
  D-010 â€” Fine-tuning target: Detection agent only
  D-014 â€” Dataset: UNSW-NB15
  D-015 â€” Base model: Qwen/Qwen3-4B-Instruct-2507 (Apache-2.0)
  D-016 â€” Metrics: Macro-F1, schema-valid output rate, evidence grounding rate,
           trust impact rate

â”€â”€â”€ HARDWARE REQUIREMENT â€” READ BEFORE RUNNING â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
This script requires a CUDA GPU with at least ~16 GB VRAM to run.
It CANNOT be executed on the current development machine (CPU-only, ~16 GB RAM).

Why training is blocked on CPU:
  1. Memory:   Qwen3-4B has ~4 billion parameters. Even with LoRA (which only
               trains a small adapter), the FROZEN base model weights must be
               loaded into memory for forward passes. In bfloat16/float16 that
               is ~8 GB; in float32 it doubles to ~16 GB â€” filling all available
               RAM before the optimizer or activations are even allocated.
  2. Speed:    A single forward + backward pass through a 4B-parameter model on
               CPU takes tens of seconds per example. 9,000+ training examples
               Ã— 3 epochs would take many days to complete.
  3. Framework: PyTorch on CPU does not support the memory-efficient attention
               kernels (FlashAttention) or the mixed-precision operations (fp16/
               bf16) that make training feasible on a GPU.
  4. Safety:   Running trainer.train() on CPU would consume all available RAM,
               likely swap-thrash, and produce no useful output. We gate on a
               CUDA check below to prevent this mistake.

For GPU environment setup, see docs/PHASE2_TRAINING.md.
â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€

Usage (on a GPU machine â€” see docs/PHASE2_TRAINING.md for full setup):
    pip install torch transformers peft trl datasets accelerate bitsandbytes
    python scripts/phase2/prepare_phase2_sample.py   # create sampled splits
    python scripts/phase2/validate_phase2_dataset.py # verify data quality
    python scripts/phase2/train_detection_lora.py    # start training

    # To enable QLoRA (4-bit quantization, fits in ~8 GB VRAM):
    python scripts/phase2/train_detection_lora.py --qlora

    # To do a dry run (skips trainer.train()) for config sanity checking:
    python scripts/phase2/train_detection_lora.py --dry-run

After training, serve the adapter and run Phase 2 evaluation:
    PHASE=2 DETECTION_MODEL=<adapter_path> python -m src.cli calibrate
    PHASE=2 DETECTION_MODEL=<adapter_path> python -m src.cli evaluate
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
ROOT = Path(__file__).resolve().parents[2]
CONFIG_PATH = ROOT / "configs" / "phase2" / "detection_lora.json"


# ---------------------------------------------------------------------------
# GPU guard â€” must appear before any heavy import
# ---------------------------------------------------------------------------

def _check_gpu_available() -> bool:
    """Return True if a CUDA device is available."""
    try:
        import torch  # noqa: PLC0415
        return torch.cuda.is_available()
    except ImportError:
        return False


def _require_gpu(dry_run: bool) -> None:
    """Exit with an informative error when training is attempted on CPU.

    Exits only when dry_run=False (i.e. when trainer.train() would be called).
    A dry run is allowed on CPU to let CI/CD systems check config validity
    without GPU access.
    """
    if dry_run:
        return
    if not _check_gpu_available():
        print(
            "\n[ERROR] No CUDA GPU detected.\n"
            "\n"
            "  Training Qwen3-4B with LoRA requires a CUDA GPU (>=16 GB VRAM for LoRA,\n"
            "  >=8 GB VRAM for QLoRA with 4-bit quantization).\n"
            "\n"
            "  This machine has CPU-only PyTorch. Loading the frozen base model alone\n"
            "  would consume all available RAM before a single gradient step can occur.\n"
            "\n"
            "  Options:\n"
            "    1. Run on a machine with a CUDA GPU (see docs/PHASE2_TRAINING.md).\n"
            "    2. Use Google Colab (free T4 GPU, ~16 GB VRAM).\n"
            "    3. Use --dry-run to validate the configuration without training.\n"
            "\n"
            "  The Phase 1 Ollama GGUF model is NOT used here -- Phase 2 fine-tuning\n"
            "  requires the full Hugging Face model weights (Qwen/Qwen3-4B-Instruct-2507).\n"
        )
        sys.exit(1)


# ---------------------------------------------------------------------------
# Configuration loading
# ---------------------------------------------------------------------------

def load_config() -> dict:
    with open(CONFIG_PATH, "r", encoding="utf-8") as fh:
        return json.load(fh)


def resolve_dataset_paths(config: dict) -> tuple[Path, Path]:
    """Return (train_path, val_path) based on sampling configuration."""
    use_sampled = config.get("sampling", {}).get("enabled", False)
    if use_sampled:
        train_key = "phase2_sampled_train"
        val_key = "phase2_sampled_validation"
    else:
        train_key = "train"
        val_key = "validation"

    train_path = ROOT / config["dataset"][train_key]
    val_path = ROOT / config["dataset"][val_key]

    for path, name in [(train_path, train_key), (val_path, val_key)]:
        if not path.exists():
            print(f"\n[ERROR] Dataset not found: {path}")
            if use_sampled:
                print(
                    "  Sampled splits do not exist yet. Run:\n"
                    "    python scripts/phase2/prepare_phase2_sample.py"
                )
            sys.exit(1)

    return train_path, val_path


# ---------------------------------------------------------------------------
# Training
# ---------------------------------------------------------------------------

def build_and_run(args: argparse.Namespace) -> None:
    """Import heavy dependencies and run (or dry-run) the training loop."""

    # These imports are deferred so the CPU guard can fire first and so that
    # lightweight operations (--help, config validation) don't require the
    # full fine-tuning stack.
    try:
        import torch  # noqa: F401
        from datasets import load_dataset  # noqa: PLC0415
        from peft import LoraConfig, get_peft_model  # noqa: PLC0415
        from transformers import (  # noqa: PLC0415
            AutoModelForCausalLM,
            AutoTokenizer,
            BitsAndBytesConfig,
            TrainingArguments,
        )
        from trl import SFTConfig, SFTTrainer  # noqa: PLC0415
    except ImportError as exc:
        print(
            f"\n[ERROR] Missing fine-tuning dependency: {exc}\n"
            "\n"
            "  Install Phase 2 dependencies on the GPU machine:\n"
            "    pip install torch transformers peft trl datasets accelerate bitsandbytes\n"
            "\n"
            "  These are intentionally excluded from requirements.txt (which covers\n"
            "  Phase 1 only) to keep the development environment lightweight.\n"
        )
        sys.exit(1)

    config = load_config()
    train_path, val_path = resolve_dataset_paths(config)
    output_dir = ROOT / config["training"]["output_dir"]
    output_dir.mkdir(parents=True, exist_ok=True)

    model_name: str = config["base_model"]
    ft = config["fine_tuning"]
    tr = config["training"]

    # â”€â”€ Dataset â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    dataset = load_dataset(
        "json",
        data_files={
            "train": str(train_path),
            "validation": str(val_path),
        },
    )

    # â”€â”€ Tokenizer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    tokenizer = AutoTokenizer.from_pretrained(
        model_name,
        trust_remote_code=True,
    )
    if tokenizer.pad_token is None:
        # Qwen models use eos as pad; set explicitly so DataCollator doesn't warn.
        tokenizer.pad_token = tokenizer.eos_token
        tokenizer.pad_token_id = tokenizer.eos_token_id

    # â”€â”€ Formatting function â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # Format matches the Phase 1 prompt structure exactly (P1-07 / D-005):
    # the instruction and input are what Phase 1 sends at runtime; the output
    # is what the model should produce. This preserves Phase 1/Phase 2 prompt
    # parity so that any performance difference is attributable to fine-tuning.
    def format_example(example: dict) -> str:
        return (
            f"{example['instruction']}\n\n"
            f"{example['input']}\n\n"
            f"Response:\n"
            f"{example['output']}"
        )

    # â”€â”€ LoRA / QLoRA configuration â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    peft_config = LoraConfig(
        r=ft["r"],
        lora_alpha=ft["lora_alpha"],
        lora_dropout=ft["lora_dropout"],
        target_modules=ft["target_modules"],
        bias=ft.get("bias", "none"),
        task_type=ft.get("task_type", "CAUSAL_LM"),
    )

    # QLoRA: load the frozen base model in 4-bit NF4 to reduce GPU memory
    # from ~16 GB (LoRA fp16) to ~8 GB (QLoRA 4-bit), as documented in
    # docs/LLM_FINE_TUNING.md.  Enabled with --qlora flag.
    bnb_config = None
    if args.qlora:
        bnb_config = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_use_double_quant=True,  # double quantization (saves ~0.4 bpp)
            bnb_4bit_quant_type="nf4",        # NormalFloat4 for normally-distributed weights
            bnb_4bit_compute_dtype="bfloat16",
        )
        print("[INFO] QLoRA enabled: base model will be loaded in 4-bit NF4.")

    # â”€â”€ Model loading â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # NOTE: this triggers a download of ~8 GB model weights on first run.
    # The model is NOT the Ollama GGUF (used only for Phase 1 inference) â€”
    # fine-tuning requires the full Hugging Face safetensors weights.
    model = AutoModelForCausalLM.from_pretrained(
        model_name,
        quantization_config=bnb_config,       # None = plain LoRA; BnBConfig = QLoRA
        device_map="auto",                     # auto-place layers across available GPUs
        trust_remote_code=True,
        torch_dtype="auto",                    # use bfloat16 on Ampere+ GPUs automatically
    )
    if args.qlora:
        # bitsandbytes requires gradient checkpointing to be enabled BEFORE
        # get_peft_model when using 4-bit quantization.
        model.enable_input_require_grads()

    model = get_peft_model(model, peft_config)
    model.print_trainable_parameters()

    # â”€â”€ TrainingArguments â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    training_args = SFTConfig(
        max_length=tr.get("max_seq_length", 512),
        output_dir=str(output_dir),
        num_train_epochs=tr["num_train_epochs"],
        per_device_train_batch_size=tr["per_device_train_batch_size"],
        per_device_eval_batch_size=tr["per_device_eval_batch_size"],
        gradient_accumulation_steps=tr["gradient_accumulation_steps"],
        gradient_checkpointing=tr.get("gradient_checkpointing", True),
        learning_rate=tr["learning_rate"],
        warmup_steps=tr.get("warmup_ratio", 0.03),
        weight_decay=tr.get("weight_decay", 0.001),
        logging_steps=tr["logging_steps"],
        save_strategy=tr["save_strategy"],
        eval_strategy=tr.get("eval_strategy", "epoch"),  # eval_strategy replaces the
        # deprecated evaluation_strategy in transformers â‰¥ 4.41
        load_best_model_at_end=tr.get("load_best_model_at_end", True),
        metric_for_best_model=tr.get("metric_for_best_model", "eval_loss"),
        greater_is_better=tr.get("greater_is_better", False),
        seed=tr["seed"],
        report_to=tr.get("report_to", "none"),  # set to "wandb" for experiment tracking
        fp16=tr.get("fp16", False),
        bf16=tr.get("bf16", False),
    )

    # â”€â”€ Trainer â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    trainer = SFTTrainer(
        model=model,
        args=training_args,
        train_dataset=dataset["train"],
        eval_dataset=dataset["validation"],
        processing_class=tokenizer,     # trl â‰¥ 0.12 uses processing_class
        formatting_func=format_example,
    )

    # â”€â”€ Summary â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    print("\n" + "=" * 60)
    print("Phase 2 Detection LoRA â€” configuration summary")
    print("=" * 60)
    print(f"  Base model    : {model_name}")
    print(f"  Method        : {'QLoRA (4-bit NF4)' if args.qlora else 'LoRA (fp16)'}")
    print(f"  LoRA rank     : {ft['r']}, alpha: {ft['lora_alpha']}")
    print(f"  Train examples: {len(dataset['train'])}")
    print(f"  Val   examples: {len(dataset['validation'])}")
    print(f"  Epochs        : {tr['num_train_epochs']}")
    print(f"  Output dir    : {output_dir}")

    # Save the effective experiment configuration (without secrets or API keys)
    config_out = output_dir / "experiment_config.json"
    with open(config_out, "w", encoding="utf-8") as fh:
        json.dump(
            {
                "base_model": model_name,
                "qlora": args.qlora,
                "peft_config": {
                    "r": ft["r"],
                    "lora_alpha": ft["lora_alpha"],
                    "lora_dropout": ft["lora_dropout"],
                    "target_modules": ft["target_modules"],
                    "bias": ft.get("bias", "none"),
                },
                "training": tr,
                "dataset": {
                    "train": str(train_path.relative_to(ROOT)),
                    "validation": str(val_path.relative_to(ROOT)),
                    "n_train": len(dataset["train"]),
                    "n_validation": len(dataset["validation"]),
                },
            },
            fh,
            indent=2,
        )
    print(f"\n  Experiment config written to: {config_out.relative_to(ROOT)}")

    # â”€â”€ Training â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
    # â”Œâ”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”
    # â”‚  trainer.train() is intentionally gated.                             â”‚
    # â”‚                                                                      â”‚
    # â”‚  Reason (--dry-run / CPU): we want config + data validation to be    â”‚
    # â”‚  runnable on the development machine (CPU-only) and in CI without    â”‚
    # â”‚  triggering a full training run that would:                          â”‚
    # â”‚    1. Require a GPU (this machine has none).                         â”‚
    # â”‚    2. Download ~8 GB of model weights.                               â”‚
    # â”‚    3. Run for hours.                                                 â”‚
    # â”‚                                                                      â”‚
    # â”‚  To actually train, omit --dry-run on a GPU machine.                â”‚
    # â””â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”˜
    if args.dry_run:
        print(
            "\n[DRY RUN] trainer.train() skipped. Configuration and data loading"
            " validated successfully. Re-run without --dry-run on a GPU machine to train."
        )
    else:
        print("\nStarting training â€¦")
        trainer.train()

        # Save the final LoRA adapter weights.
        # Integration with Phase 1: serve the merged model (or load adapter on top of
        # the base model) behind an OpenAI-compatible endpoint, then run:
        #   PHASE=2 DETECTION_MODEL=<adapter_path> python -m src.cli calibrate
        #   PHASE=2 DETECTION_MODEL=<adapter_path> python -m src.cli evaluate
        adapter_dir = output_dir / "adapter_final"
        trainer.model.save_pretrained(str(adapter_dir))
        tokenizer.save_pretrained(str(adapter_dir))
        print(f"\nLoRA adapter saved to: {adapter_dir.relative_to(ROOT)}")
        print(
            "\nNext steps:\n"
            "  1. Serve the adapter (see docs/PHASE2_TRAINING.md, Â§5).\n"
            "  2. Run: PHASE=2 DETECTION_MODEL=<adapter_path> python -m src.cli calibrate\n"
            "  3. Run: PHASE=2 DETECTION_MODEL=<adapter_path> python -m src.cli evaluate\n"
            "  4. Compare Phase 1 and Phase 2 metrics per docs/EXPERIMENTS.md Â§Experiment 4.\n"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    parser = argparse.ArgumentParser(
        description="Phase 2 Detection Agent LoRA fine-tuning.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--qlora",
        action="store_true",
        help=(
            "Enable QLoRA: load the frozen base model in 4-bit NF4 quantization. "
            "Reduces VRAM requirement from ~16 GB to ~8 GB. Recommended for GPUs "
            "with <16 GB VRAM (e.g. RTX 3060/4060). Requires bitsandbytes."
        ),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help=(
            "Load config and dataset, build the trainer, then exit WITHOUT calling "
            "trainer.train(). Allows config/data validation on a CPU machine or in CI. "
            "Still requires the fine-tuning Python packages (transformers, peft, trl, â€¦) "
            "and will attempt to download model weights."
        ),
    )
    args = parser.parse_args()

    # CPU guard: refuse to train on CPU-only hardware (--dry-run skips the guard
    # so that CI can verify the configuration).
    _require_gpu(dry_run=args.dry_run)

    build_and_run(args)


if __name__ == "__main__":
    main()
