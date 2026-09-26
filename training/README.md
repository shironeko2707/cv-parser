# Fine-tuning the CV-parsing SLM

The pipeline is **Python extraction → SLM → canonical JSON → Python mapping to SAP**.
The SLM has a single job: read the extracted CV text and return the *canonical CV JSON*
defined in [`canonical.py`](../canonical.py). It never sees SAP field ids;
[`schema_mapping.py`](../schema_mapping.py) maps its output onto whatever the Excel schema
contains. So the training data never depends on the private Excel files, and a schema
change doesn't require retraining.

```
real/synthetic CV file ─► text_extractor.extract() ─► canonical.build_messages() ─► SLM
                                                                  (same prompt in training and inference)
```

## 1. Install

```bash
pip install -r requirements.txt -r training/requirements-train.txt
```

PDF rendering needs a Unicode TTF font that covers Vietnamese (DejaVu / Liberation / Noto).
Most Linux systems have one (`apt install fonts-dejavu`). Otherwise set `CV_FONTS_DIR`.

## 2. Build the dataset

```bash
python -m training.build_dataset --n 4000 --out data/ --workers 8
```

- Generates random Vietnamese and English candidate profiles covering 8 domains, many date
  formats, VI/EN/bilingual labels, optional fields, and distractor sections (summary,
  skills, projects, hobbies, references) that the model must learn to ignore.
- Renders each profile with one of 9 templates: `pdf_classic`, `pdf_sidebar`
  (two columns), `pdf_form` (ruled HR form), `docx_classic`, `docx_layout` (template
  table), `docx_form`, `txt`, `md`, `html`.
- Runs the **real extractor** on the file, so the model trains on exactly the text it
  will see in production, including extraction quirks.
- The target is the gold JSON restricted to values present in the extracted text, so the
  model is never trained to output something it cannot see.
  `stats.json → extraction_loss_per_field` reports what the extractor loses, which also
  serves as an extraction-quality metric.
- About 10% of documents are also trained as chunks, because long CVs are split on
  section headings at inference.

About 1000 documents per 15 s on 4 CPU cores. 3k–5k synthetic CVs is a good start.

## 3. Add real CVs (most important for quality)

Synthetic data teaches the format; real CVs teach the variety. Even 100–300 corrected
real CVs make a big difference.

```bash
# draft labels from the current model, or better, from a large *self-hosted* teacher
python -m training.label_real ./real_cvs --out labels/
python -m training.label_real ./real_cvs --out labels/ --teacher-url http://gpu-box:8000/v1 --teacher-model Qwen/Qwen3-32B

# fix labels/<name>.json against labels/<name>.txt, set "verified": true, then:
python -m training.label_real --check labels/
python -m training.build_dataset --n 4000 --out data/ --labels labels/ --real-weight 3
```

Label rules (the same ones the model is prompted with): copy values verbatim, dates as
`YYYY` / `YYYY-MM` / `YYYY-MM-DD` (day-first for numeric dates), `"present"` for ongoing,
gender `male`/`female`, one entry per job/school/…, leave out anything not in the CV.
20% of real CVs are held out in `data/val_real.jsonl`. That file is the honest benchmark.

> Labels contain personal data. Keep `labels/`, `data/` and `runs/` on internal machines
> (they are git-ignored) and never send CVs to an external API.

## 4. Train (LoRA / QLoRA)

```bash
python -m training.train_lora --model google/gemma-4-E2B-it --data data/ --out runs/cv-e2b
# smaller GPU (e.g. 12–16 GB): add --qlora
```

- `--model` takes any Hugging Face causal LM or a local path. Use the Hugging Face
  checkpoint of the model you serve (check the exact Gemma 4 E2B instruct repo name on
  huggingface.co). Small Qwen3 models are an alternative worth comparing with `evaluate`.
- Loss is on the JSON answer only. Samples longer than `--max-len` are dropped, not
  truncated. For multimodal Gemma checkpoints, LoRA only touches the text model.
- Defaults: r=16, alpha=32, lr 2e-4, 2 epochs, effective batch 16. If validation loss
  goes up after epoch 1, use `--epochs 1`.

## 5. Export and serve

```bash
git clone https://github.com/ggml-org/llama.cpp && (cd llama.cpp && cmake -B build && cmake --build build -j)
python -m training.export --run runs/cv-e2b --llama-cpp ./llama.cpp --quant Q4_K_M \
       --ollama-base gemma4:e2b --name cv-parser
cd runs/cv-e2b/gguf && ollama create cv-parser -f Modelfile

LLM_MODEL=cv-parser python main.py resume.pdf
```

(or `llama-server -m runs/cv-e2b/gguf/cv-parser-Q4_K_M.gguf -c 8192 --port 8080`)

## 6. Evaluate: base vs fine-tuned

```bash
python -m training.evaluate --data data/val.jsonl      --model gemma4:e2b --out eval_base.json
python -m training.evaluate --data data/val.jsonl      --model cv-parser  --out eval_ft.json
python -m training.evaluate --data data/val_real.jsonl --model cv-parser
```

Reports per-field precision/recall/F1 (after the same grounding as production), entry-count
accuracy per section, JSON validity, latency, F1 per template, and the worst samples to
inspect.

## Changing the output contract

If you add a canonical field, update `canonical.py` (`PERSONAL_FIELDS` / `SECTION_FIELDS`
and the prompt), bump `PROMPT_VERSION`, add the SAP candidates in `schema_mapping.py`, teach
`training/synth.py` to generate it, then rebuild the data and retrain. The prompt must stay
identical between training and inference.
