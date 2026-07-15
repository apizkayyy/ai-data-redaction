import tempfile
import uuid

from pathlib import Path

from fastapi import (
    APIRouter,
    File,
    HTTPException,
    Query,
    UploadFile
)
from fastapi.responses import FileResponse, JSONResponse
from services.masking_service import mask_pdf

router = APIRouter()

TMP_DIR = (
    Path(tempfile.gettempdir())
    /
    "pdf_masking"
)

TMP_DIR.mkdir(
    parents=True,
    exist_ok=True
)

@router.post("")
async def mask_endpoint(
    file: UploadFile = File(
        ...,
        description="PDF file to redact"
    ),

    json_report: bool = Query(
        False,
        alias="json"
    ),

    use_presidio: bool = Query(
        True
    ),

    use_openai: bool = Query(
        True
    ),

    min_score: float = Query(
        0.4
    )
):

    """
    Upload PDF.

    Returns:
    - masked PDF
    - JSON report
    """
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=400,
            detail="Only PDF files are accepted."
        )

    job_id = uuid.uuid4().hex

    input_path = (
        TMP_DIR /
        f"{job_id}_input.pdf"
    )

    output_path = (
        TMP_DIR /
        f"{job_id}_masked.pdf"
    )

    try:
        input_path.write_bytes(
            await file.read()
        )

        result = mask_pdf(

            input_path=str(input_path),
            output_path=str(output_path),
            use_presidio=use_presidio,
            use_openai=use_openai,
            presidio_min_score=min_score,
            verbose=False,
        )

        if json_report:
            return JSONResponse(
                content=result
            )

        filename = (
            Path(file.filename).stem
            +
            "_masked.pdf"
        )

        return FileResponse(
            path=str(output_path),
            media_type="application/pdf",
            filename=filename
        )

    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail=str(exc)
        )

    finally:
        if input_path.exists():
            input_path.unlink(
                missing_ok=True
            )

@router.post("/json")
async def mask_json_endpoint(

    file: UploadFile = File(...),

    use_presidio: bool = Query(
        True
    ),

    use_openai: bool = Query(
        True
    ),

    min_score: float = Query(
        0.4
    )
):


    return await mask_endpoint(
        file=file,
        json_report=True,
        use_presidio=use_presidio,
        use_openai=use_openai,
        min_score=min_score
    )