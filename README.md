# CV Parser

Extracts candidate data from CV files (PDF/DOCX) into SAP SuccessFactors Candidate JSON.

Pipeline: Python text extraction (PyMuPDF / python-docx) → self-hosted LLM (Gemma 4 E2B) → JSON assembly (picklist mapping, date normalization, schema field order).

## Setup

1. Copy the two schema files into the project root (they are not in the repo):
   - `Candidate Profile Fields JSON_260921.xlsx`
   - `Candidate Profile Picklists_v2_260921.xlsx`
2. Install dependencies: `bash setup.sh`
3. Start an LLM server:

```bash
# Ollama (default: http://localhost:11434/v1, model gemma4:e2b)
ollama pull gemma4:e2b && ollama serve

# or llama.cpp
llama-server -m gemma4-e2b-q4.gguf -c 16384 --reasoning-budget 0 --port 8080
export LLM_BASE_URL=http://localhost:8080/v1
```

## Usage

```bash
python main.py resume.pdf -o output.json            # single file
python main.py ./cvs/ --output ./output/            # batch
python app.py                                       # web UI on :5005
```

## Evaluation

```bash
python auto_validator.py ./output/ --report validation_report.json   # automated format checks
python review_tool.py ./cvs/ ./output/                                # manual field-by-field review
python review_tool.py --report review_results/                        # anonymized accuracy report (no PII)
```

Synthetic test CVs: `python gen_cv.py all` (ground truth in `test_criteria/`).

## Environment variables

| Variable | Default |
|---|---|
| `LLM_BASE_URL` | `http://localhost:11434/v1` |
| `LLM_MODEL` | `gemma4:e2b` |
| `LLM_TIMEOUT` | `120` |
