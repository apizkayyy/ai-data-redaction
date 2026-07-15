from fastapi import FastAPI

from api.health import router as health_router
from api.mask import router as masking_router


app = FastAPI(
    title="PDF Data Masking Service",
    description=(
        "Upload PDF and receive redacted PDF "
        "using Presidio + OpenAI detection(optional)."
    ),
    version="1.0.0",
)

app.include_router(
    health_router,
    tags=["Health"]
)

app.include_router(
    masking_router,
    prefix="/mask",
    tags=["Masking"]
)