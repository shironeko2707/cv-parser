"""
Export a fine-tuned adapter for serving with Ollama or llama.cpp.

    python -m training.export --run runs/cv-e2b --llama-cpp ~/llama.cpp --quant Q4_K_M \
        --ollama-base gemma4:e2b --name cv-parser

Steps
    1. merge LoRA adapter into the base weights      -> RUN/merged/
    2. convert to GGUF with llama.cpp                -> RUN/gguf/cv-parser-f16.gguf
    3. quantize                                      -> RUN/gguf/cv-parser-Q4_K_M.gguf
    4. write an Ollama Modelfile (chat template copied from the base model)
Then:
    ollama create cv-parser -f RUN/gguf/Modelfile
    LLM_MODEL=cv-parser python main.py resume.pdf
or  llama-server -m RUN/gguf/cv-parser-Q4_K_M.gguf -c 8192 --port 8080
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def merge_adapter(base_model: str, adapter_dir: str, out_dir: str):
    import torch
    from peft import PeftModel
    from transformers import AutoTokenizer

    from training.train_lora import load_model

    print(f"Merging {adapter_dir} into {base_model} ...")
    model = load_model(base_model, qlora=False, dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32)
    model = PeftModel.from_pretrained(model, adapter_dir)
    model = model.merge_and_unload()
    model.save_pretrained(out_dir, safe_serialization=True)
    AutoTokenizer.from_pretrained(adapter_dir).save_pretrained(out_dir)
    # processor/preprocessor configs are needed by llama.cpp for some multimodal archs
    try:
        from huggingface_hub import snapshot_download
        src = Path(base_model) if Path(base_model).exists() else Path(
            snapshot_download(base_model, allow_patterns=["*.json", "*.model", "*.jinja"]))
        for f in src.glob("*"):
            if f.suffix in (".json", ".model", ".jinja") and not (Path(out_dir) / f.name).exists():
                shutil.copy(f, out_dir)
    except Exception as e:
        print(f"(could not copy extra base files: {e})")
    print(f"Merged model saved to {out_dir}")


def ollama_template(base: str) -> str:
    """TEMPLATE / PARAMETER stop lines from an installed Ollama base model."""
    exe = shutil.which("ollama")
    if not exe:
        return ""
    try:
        res = subprocess.run([exe, "show", "--modelfile", base], capture_output=True, text=True, timeout=60)
    except Exception:
        return ""
    lines, src = [], res.stdout.splitlines()
    i = 0
    while i < len(src):
        line = src[i]
        if line.startswith("TEMPLATE"):
            lines.append(line)
            if line.count('"""') == 1:  # multi-line block: copy until the closing quotes
                i += 1
                while i < len(src):
                    lines.append(src[i])
                    if src[i].rstrip().endswith('"""'):
                        break
                    i += 1
        elif line.startswith("PARAMETER stop"):
            lines.append(line)
        i += 1
    return "\n".join(lines)


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--run", required=True, help="training output dir (contains adapter/ and run_config.json)")
    ap.add_argument("--llama-cpp", help="path to a llama.cpp checkout (built) for GGUF conversion")
    ap.add_argument("--quant", default="Q4_K_M", help="llama.cpp quantization type (Q4_K_M, Q5_K_M, Q8_0...)")
    ap.add_argument("--ollama-base", default="gemma4:e2b", help="installed Ollama model to copy the chat template from")
    ap.add_argument("--name", default="cv-parser")
    ap.add_argument("--ctx", type=int, default=8192)
    args = ap.parse_args()

    run = Path(args.run)
    cfg = json.loads((run / "run_config.json").read_text())
    merged = run / "merged"
    if not (merged / "config.json").exists():
        merge_adapter(cfg["base_model"], str(run / "adapter"), str(merged))

    if not args.llama_cpp:
        print("No --llama-cpp given: stopping after merge. Serve RUN/merged with vLLM, or convert it with\n"
              "  python llama.cpp/convert_hf_to_gguf.py RUN/merged --outfile model.gguf --outtype f16")
        return
    lc = Path(args.llama_cpp).expanduser()
    gguf_dir = run / "gguf"
    gguf_dir.mkdir(exist_ok=True)
    f16 = gguf_dir / f"{args.name}-f16.gguf"
    subprocess.run([sys.executable, str(lc / "convert_hf_to_gguf.py"), str(merged),
                    "--outfile", str(f16), "--outtype", "f16"], check=True)
    quant_bin = next((p for p in (lc / "build" / "bin" / "llama-quantize", lc / "llama-quantize") if p.exists()), None)
    final = f16
    if quant_bin and args.quant.lower() != "f16":
        final = gguf_dir / f"{args.name}-{args.quant}.gguf"
        subprocess.run([str(quant_bin), str(f16), str(final), args.quant], check=True)
    elif not quant_bin:
        print("llama-quantize not found (build llama.cpp first); keeping the f16 GGUF")

    template = ollama_template(args.ollama_base)
    modelfile = [f"FROM ./{final.name}", "PARAMETER temperature 0", f"PARAMETER num_ctx {args.ctx}"]
    if template:
        modelfile.append(template)
    else:
        modelfile.append(f"# Copy the TEMPLATE block from: ollama show --modelfile {args.ollama_base}")
    (gguf_dir / "Modelfile").write_text("\n".join(modelfile) + "\n")
    print(f"\nGGUF: {final}\nNext:\n  cd {gguf_dir} && ollama create {args.name} -f Modelfile\n"
          f"  LLM_MODEL={args.name} python main.py resume.pdf")


if __name__ == "__main__":
    main()
