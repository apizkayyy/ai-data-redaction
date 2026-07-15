"""
PDF Masking API — FastAPI wrapper
==================================
Exposes masking_service.mask_pdf() as HTTP endpoints.

Run:
    uvicorn api:app --reload --port 8000

Endpoints:
    POST /mask              → returns masked PDF file download
    POST /mask?json=1       → returns JSON redaction report
    POST /mask/json         → always returns JSON report
    GET  /health            → {"status": "ok"}
"""

import tempfile
import uuid
from pathlib import Path

from fastapi import FastAPI, File, HTTPException, Query, UploadFile
from fastapi.responses import FileResponse, JSONResponse

from masking_service import mask_pdf

app = FastAPI(
    title="PDF Data Masking Service",
    description=(
        "Upload a PDF and receive a redacted copy with sensitive PII "
        "(names, phone, email, IC/passport, financial data, addresses) "
        "blacked out. Uses Presidio + OpenAI for dual-layer detection."
    ),
    version="1.0.0",
)

TMP_DIR = Path(tempfile.gettempdir()) / "pdf_masking"
TMP_DIR.mkdir(parents=True, exist_ok=True)


@app.get("/health")
def health():
    return {"status": "ok"}


@app.post("/mask")
async def mask_endpoint(
    file: UploadFile = File(..., description="PDF file to redact"),
    json_report: bool = Query(
        False,
        alias="json",
        description="Return JSON report instead of masked PDF",
    ),
    use_presidio: bool  = Query(True,  description="Enable Presidio layer"),
    use_openai:   bool  = Query(True,  description="Enable OpenAI layer"),
    min_score:    float = Query(0.4,   description="Presidio minimum confidence score"),
):
    """Upload a PDF → receive the masked PDF or a JSON redaction report."""
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files are accepted.")

    job_id      = uuid.uuid4().hex
    input_path  = TMP_DIR / f"{job_id}_input.pdf"
    output_path = TMP_DIR / f"{job_id}_masked.pdf"

    try:
        input_path.write_bytes(await file.read())

        result = mask_pdf(
            input_path=str(input_path),
            output_path=str(output_path),
            use_presidio=use_presidio,
            use_openai=use_openai,
            presidio_min_score=min_score,
            verbose=False,
        )

        if json_report:
            return JSONResponse(content=result)

        masked_filename = Path(file.filename).stem + "_masked.pdf"
        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=masked_filename,
        )

    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    finally:
        if input_path.exists():
            input_path.unlink(missing_ok=True)


@app.post("/mask/json")
async def mask_json_endpoint(
    file: UploadFile = File(...),
    use_presidio: bool  = Query(True),
    use_openai:   bool  = Query(True),
    min_score:    float = Query(0.4),
):
    """Upload a PDF → receive a JSON report of all PII detected and redacted."""
    return await mask_endpoint(
        file=file,
        json_report=True,
        use_presidio=use_presidio,
        use_openai=use_openai,
        min_score=min_score,
    )
