# CV Parser

Extracts candidate data from CV files into SAP SuccessFactors Candidate JSON.

```
file ─► text_extractor.py ─► ai_extractor.py (SLM) ─► canonical.py ─► schema_mapping.py ─► json_assembler.py
        layout-aware text      canonical CV JSON      grounding &      SAP field ids        picklists, dates,
        any format             (constrained JSON)     repair                                 schema field order
```

1. **Extraction (Python):** PDF (digital, or scanned via OCR), DOCX, DOC/RTF/ODT, TXT/MD,
   HTML and images become reading-order text with `## SECTION` markers. The extractor
   handles multi-column and sidebar layouts, right-aligned dates, tables, text boxes,
   page headers/footers, wrapped lines and Vietnamese Unicode normalization.
2. **SLM:** a small self-hosted model (Gemma 4 E2B by default) converts the text into a
   fixed *canonical CV JSON*. JSON-schema constrained decoding is requested, so it always
   returns valid JSON. Long CVs are split on section headings.
3. **Grounding:** values that do not occur in the CV text (hallucinations) are dropped.
   Email, phone and LinkedIn are validated or filled from regex detections. Each field
   gets a confidence score.
4. **Mapping:** canonical fields are mapped deterministically onto the SAP schema loaded
   from Excel (`python schema_mapping.py` prints the mapping and any unmapped fields).

The SLM can be fine-tuned for this exact task. See **[training/README.md](training/README.md)**.

## Setup

1. Copy the two schema files into the project root (they are not in the repo):
   - `Candidate Profile Fields JSON_260921.xlsx`
   - `Candidate Profile Picklists_v2_260921.xlsx`
2. Install dependencies: `bash setup.sh`
3. Optional system tools:
   - **Tesseract** with `vie` + `eng` language data: OCR for scanned PDFs and images
     (`apt install tesseract-ocr tesseract-ocr-vie`)
   - **LibreOffice**: legacy `.doc` (and higher-fidelity `.rtf`). `.odt` and `.rtf` also
     work without it.
4. Start an LLM server:

```bash
# Ollama (default: http://localhost:11434/v1, model gemma4:e2b)
ollama pull gemma4:e2b && ollama serve

# or llama.cpp
llama-server -m gemma4-e2b-q4.gguf -c 16384 --reasoning-budget 0 --port 8080
export LLM_BASE_URL=http://localhost:8080/v1
```

5. Check the field mapping against your Excel: `python schema_mapping.py`

## Usage

```bash
python main.py resume.pdf -o output.json            # single file
python main.py ./cvs/ --output ./output/            # batch (all supported formats)
python app.py                                       # web UI on :5005

python text_extractor.py resume.pdf                 # inspect the text the SLM sees
python ai_extractor.py resume.pdf                   # inspect the canonical JSON (before SAP mapping)
```

## Evaluation

```bash
python -m pytest tests                                                # unit + extraction regression tests
python auto_validator.py ./output/ --report validation_report.json   # automated format checks
python review_tool.py ./cvs/ ./output/                                # manual field-by-field review
python review_tool.py --report review_results/                        # anonymized accuracy report (no PII)
python -m training.evaluate --data data/val.jsonl --model gemma4:e2b  # field-level P/R/F1 of an SLM
```

Synthetic test CVs: `python gen_cv.py all` (ground truth in `test_criteria/`).

## Environment variables

| Variable | Default | |
|---|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` | any OpenAI-compatible server (Ollama, llama.cpp, vLLM) |
| `LLM_MODEL` | `gemma4:e2b` | e.g. `cv-parser` after fine-tuning |
| `LLM_TIMEOUT` | `120` | seconds per request |
| `LLM_MAX_TOKENS` | `4096` | output budget per request |
| `LLM_MAX_INPUT_CHARS` | `12000` | longer CVs are split on section headings |
| `LLM_STRUCTURED` | `json_schema` | `json_schema` / `json` / `off` (falls back automatically if unsupported) |
| `LLM_API_KEY` | | for servers that require one |
| `OCR_LANGUAGES` | `vie+eng` | Tesseract languages |
