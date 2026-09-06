"""A FastAPI APIRouter (not a standalone app — the Backend team mounts this into their main FastAPI app) exposing POST /infer/single and POST /infer/batch, calling sif_engine.pipeline directly. Backend imports this rather than reimplementing pipeline-calling logic."""

try:
    from fastapi import APIRouter
    from pydantic import BaseModel
    from sif_engine.pipeline import run_batch, run_single
    router = APIRouter()

    class SingleRequest(BaseModel):
        text: str

    @router.post("/infer/single")
    def infer_single(request: SingleRequest):
        return run_single(request.text)

    @router.post("/infer/batch")
    def infer_batch(reports: list[dict]):
        return run_batch(reports)
except ImportError:
    router = None