"""
LoRA / QLoRA supervised fine-tuning of the CV-parsing SLM (Hugging Face TRL).

    python -m training.train_lora --model google/gemma-4-E2B-it --data data --out runs/cv-e2b
    python -m training.train_lora --model Qwen/Qwen3-1.7B --data data --out runs/cv-qwen --qlora

Notes
- Loss is computed on the JSON answer only (prompt/completion dataset format).
- Samples longer than --max-len are dropped, never truncated: a truncated
  target teaches the model to emit broken JSON.
- Chat templates without a "system" role (older Gemma) are handled by folding
  the system prompt into the user turn -- exactly what those templates do at
  inference time as well.
- For multimodal checkpoints (Gemma 3n/4 E2B/E4B) LoRA is applied to the
  language model only.
- --model accepts a Hub id or a local directory (use a local path if the
  training machine has no internet access).
"""
from __future__ import annotations

import argparse
import inspect
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

# LoRA on text-model projections only (skips vision/audio towers of multimodal models)
TARGET_MODULES = (r"^(?!.*(?:vision|audio|multi_modal|embed_vision|embed_audio)).*"
                  r"\.(?:q_proj|k_proj|v_proj|o_proj|gate_proj|up_proj|down_proj)$")


def load_model(name: str, qlora: bool, dtype):
    import torch
    from transformers import AutoModelForCausalLM, BitsAndBytesConfig

    kwargs = {"dtype": dtype}
    if torch.cuda.is_available():
        kwargs["device_map"] = "auto"
    if qlora:
        kwargs["quantization_config"] = BitsAndBytesConfig(
            load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True,
            bnb_4bit_compute_dtype=dtype,
        )
    try:
        return AutoModelForCausalLM.from_pretrained(name, **kwargs)
    except (ValueError, KeyError):
        # multimodal checkpoints are registered as image-text-to-text models
        from transformers import AutoModelForImageTextToText
        return AutoModelForImageTextToText.from_pretrained(name, **kwargs)


def template_supports_system(tokenizer) -> bool:
    try:
        out = tokenizer.apply_chat_template(
            [{"role": "system", "content": "SYS_MARKER"}, {"role": "user", "content": "hi"}],
            tokenize=False, add_generation_prompt=True,
        )
        return "SYS_MARKER" in out
    except Exception:
        return False


def fold_system(messages: list[dict]) -> list[dict]:
    if not messages or messages[0]["role"] != "system":
        return messages
    sys_msg, rest = messages[0], list(messages[1:])
    rest[0] = {**rest[0], "content": f"{sys_msg['content']}\n\n{rest[0]['content']}"}
    return rest


def read_jsonl(path: Path) -> list[dict]:
    rows = []
    with open(path, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                r = json.loads(line)
                if "messages" in r:  # accept the "messages" format too
                    r = {"prompt": r["messages"][:-1], "completion": r["messages"][-1:]}
                rows.append({"prompt": r["prompt"], "completion": r["completion"]})
    return rows


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--model", default="google/gemma-4-E2B-it", help="base model (Hub id or local path)")
    ap.add_argument("--data", default="data", help="dir with train.jsonl / val.jsonl from build_dataset")
    ap.add_argument("--out", default="runs/cv-slm")
    ap.add_argument("--epochs", type=float, default=2.0)
    ap.add_argument("--lr", type=float, default=2e-4)
    ap.add_argument("--rank", type=int, default=16)
    ap.add_argument("--alpha", type=int, default=32)
    ap.add_argument("--dropout", type=float, default=0.05)
    ap.add_argument("--batch", type=int, default=1, help="per-device batch size")
    ap.add_argument("--grad-accum", type=int, default=16)
    ap.add_argument("--max-len", type=int, default=6144, help="max tokens (prompt + answer)")
    ap.add_argument("--qlora", action="store_true", help="4-bit base weights (needs bitsandbytes + CUDA)")
    ap.add_argument("--eval-steps", type=int, default=200)
    ap.add_argument("--max-steps", type=int, default=-1, help="for smoke tests")
    ap.add_argument("--merge", action="store_true", help="also save merged full weights to OUT/merged")
    args = ap.parse_args()

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoTokenizer
    from trl import SFTConfig, SFTTrainer

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    data = Path(args.data)
    train_rows, val_rows = read_jsonl(data / "train.jsonl"), read_jsonl(data / "val.jsonl")

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token
    folded = not template_supports_system(tokenizer)
    if folded:
        print("Chat template has no system role: folding system prompt into the user turn")
        for r in train_rows + val_rows:
            r["prompt"] = fold_system(r["prompt"])

    def n_tokens(r):
        ids = tokenizer.apply_chat_template(r["prompt"] + r["completion"], tokenize=True)
        if isinstance(ids, dict) or hasattr(ids, "keys"):  # some versions return BatchEncoding
            ids = ids["input_ids"]
        return len(ids)

    def keep(rows, name):
        kept = [r for r in rows if n_tokens(r) <= args.max_len]
        if len(kept) < len(rows):
            print(f"{name}: dropped {len(rows) - len(kept)} samples longer than {args.max_len} tokens")
        return kept

    train_rows, val_rows = keep(train_rows, "train"), keep(val_rows, "val")
    print(f"train={len(train_rows)} val={len(val_rows)}")

    bf16 = torch.cuda.is_available() and torch.cuda.is_bf16_supported()
    fp16 = torch.cuda.is_available() and not bf16
    dtype = torch.bfloat16 if bf16 else torch.float16 if fp16 else torch.float32
    model = load_model(args.model, args.qlora, dtype)

    peft_config = LoraConfig(
        r=args.rank, lora_alpha=args.alpha, lora_dropout=args.dropout,
        target_modules=TARGET_MODULES, task_type="CAUSAL_LM",
    )
    cfg_kwargs = dict(
        output_dir=str(out), num_train_epochs=args.epochs, max_steps=args.max_steps,
        per_device_train_batch_size=args.batch, per_device_eval_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum, learning_rate=args.lr,
        lr_scheduler_type="cosine", weight_decay=0.0,
        logging_steps=10, eval_strategy="steps", eval_steps=args.eval_steps,
        save_strategy="steps", save_steps=args.eval_steps, save_total_limit=2,
        load_best_model_at_end=True, metric_for_best_model="eval_loss",
        bf16=bf16, fp16=fp16, gradient_checkpointing=torch.cuda.is_available(),
        report_to="none", seed=42,
    )
    params = inspect.signature(SFTConfig.__init__).parameters
    cfg_kwargs["max_length" if "max_length" in params else "max_seq_length"] = args.max_len
    if "warmup_ratio" in params:  # transformers < 5
        cfg_kwargs["warmup_ratio"] = 0.03
    else:  # transformers >= 5: a float warmup_steps is a ratio
        cfg_kwargs["warmup_steps"] = 0.03
    if "completion_only_loss" in params:
        cfg_kwargs["completion_only_loss"] = True
    if "gradient_checkpointing_kwargs" in params and cfg_kwargs["gradient_checkpointing"]:
        cfg_kwargs["gradient_checkpointing_kwargs"] = {"use_reentrant": False}
    unknown = [k for k in cfg_kwargs if k not in params]
    if unknown:
        print(f"(this TRL/transformers version does not support {unknown}; skipping)")
    config = SFTConfig(**{k: v for k, v in cfg_kwargs.items() if k in params})

    trainer_kwargs = dict(model=model, args=config, train_dataset=Dataset.from_list(train_rows),
                          eval_dataset=Dataset.from_list(val_rows), peft_config=peft_config)
    tparams = inspect.signature(SFTTrainer.__init__).parameters
    trainer_kwargs["processing_class" if "processing_class" in tparams else "tokenizer"] = tokenizer
    trainer = SFTTrainer(**trainer_kwargs)
    trainer.model.print_trainable_parameters()
    trainer.train()

    adapter_dir = out / "adapter"
    trainer.save_model(str(adapter_dir))
    tokenizer.save_pretrained(str(adapter_dir))
    run_cfg = {"base_model": args.model, "folded_system": folded, "max_len": args.max_len,
               "rank": args.rank, "alpha": args.alpha, "epochs": args.epochs, "lr": args.lr}
    try:
        from canonical import PROMPT_VERSION
        run_cfg["prompt_version"] = PROMPT_VERSION
    except ImportError:
        pass
    (out / "run_config.json").write_text(json.dumps(run_cfg, indent=2))
    print(f"Adapter saved to {adapter_dir}")

    if args.merge:
        from training.export import merge_adapter
        merge_adapter(args.model, str(adapter_dir), str(out / "merged"))


if __name__ == "__main__":
    main()
