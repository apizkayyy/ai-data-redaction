# PDF Data Masking Service

Dual-layer PII detection and redaction for PDF files.

```
input.pdf  →  [Presidio] + [OpenAI]  →  output_masked.pdf
                   ↓            ↓
              local NER    semantic AI
              + regex      (catches edge
              patterns     cases)
```

---

## What gets masked

| Entity type   | Examples                                             | Detected by       |
|---------------|------------------------------------------------------|-------------------|
| `PERSON_NAME` | Ahmad Zulkifli bin Abdullah, Lim Mei Ling           | Presidio + OpenAI |
| `PHONE`       | +60 12-345 6789, 03-2345 6789                        | Presidio + OpenAI |
| `EMAIL`       | ahmad@example.com                                    | Presidio + OpenAI |
| `ID_NUMBER`   | IC 900112-14-5678, Passport A12345678               | Presidio + OpenAI |
| `FINANCIAL`   | Card 4111 1111 1111 1111, Account 1234-5678-9012    | Presidio + OpenAI |
| `ADDRESS`     | No 14, Jalan Taman Maju, 47810 Petaling Jaya        | Presidio + OpenAI |

---

## Setup

### 1. Install Python dependencies

```bash
pip install -r requirements.txt
```

### 2. Download the spaCy NLP model (required by Presidio)

```bash
python -m spacy download en_core_web_lg
```

> Use `en_core_web_sm` for a smaller footprint (slightly lower accuracy).

### 3. Set your OpenAI API key

```bash
export OPENAI_API_KEY="sk-..."
```

---

## Usage

### A. Python module

```python
from services.masking_service import mask_pdf

result = mask_pdf(
    input_path="document.pdf",
    output_path="document_masked.pdf",
    use_presidio=True,  # local NER + regex (default: True)
    use_openai=True,  # OpenAI semantic detection (default: True)
    presidio_min_score=0.4,
    verbose=True,
)

print(result["redactions_applied"])  # number of black bars drawn
print(result["layer_counts"])  # {"presidio_only": 3, "openai_only": 1, "both": 4}
for r in result["redactions"]:
    print(r)  # {"page": 1, "entity_type": "PHONE", "text": "+60 12-345 6789", ...}
```

### B. Command-line

```bash
# Generate a sample PDF first
python create_test_pdf.py

# Mask with both layers
python masking_service.py sample_document.pdf sample_masked.pdf

# Presidio only (no OpenAI API call)
python masking_service.py input.pdf output.pdf --no-openai

# OpenAI only (skip Presidio)
python masking_service.py input.pdf output.pdf --no-presidio

# Adjust Presidio confidence threshold
python masking_service.py input.pdf output.pdf --min-score 0.6
```

### C. HTTP API

```bash
pip install fastapi uvicorn python-multipart
uvicorn api:app --reload --port 8000
```

**Mask and download:**
```bash
curl -X POST http://localhost:8000/mask \
     -F "file=@document.pdf" \
     --output document_masked.pdf
```

**Get JSON report:**
```bash
curl -X POST "http://localhost:8000/mask?json=1" \
     -F "file=@document.pdf"
```

**Presidio only:**
```bash
curl -X POST "http://localhost:8000/mask?use_openai=false" \
     -F "file=@document.pdf" --output masked.pdf
```

Interactive API docs: `http://localhost:8000/docs`

---

## File structure

```
pdf_masking_service/
├── masking_service.py   ← Core pipeline (import this in your own code)
├── api.py               ← FastAPI HTTP endpoints
├── create_test_pdf.py   ← Generates a sample PDF with Malaysian PII
├── requirements.txt     ← Python dependencies
└── README.md
```

---

## Notes

- **Text-based PDFs only.** Scanned/image PDFs need OCR pre-processing (e.g. `pytesseract`).
- **Visual redaction, not cryptographic.** Black bars cover the rendered text but the underlying PDF content stream is not scrubbed. For compliance-grade redaction (PDPA/GDPR), add content stream sanitization.
- **OpenAI model used:** `gpt-4.1-mini` — fast and cost-effective for structured JSON extraction.
- **Cost tip:** Disable OpenAI with `--no-openai` for high-volume batch jobs; Presidio alone handles most common patterns at zero API cost.
