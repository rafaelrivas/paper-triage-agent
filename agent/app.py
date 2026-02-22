import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from agent.triage import run_triage, materialize_results
from agent.schemas import TriageResult

app = FastAPI(title="paper-triage", version="0.1.0")

PAPERS_DIR = os.environ.get("PAPERS_DIR", "/papers")

class TriageRequest(BaseModel):
    papers_dir: str | None = None

class TriageResponse(BaseModel):
    status: str
    result: TriageResult
    n_papers: int

@app.get("/health")
def health_check():
    return {"ok": True}

@app.post("/triage", response_model=TriageResponse)
async def do_triage(req: TriageRequest = TriageRequest()):
    target = req.papers_dir or PAPERS_DIR
    inbox = os.path.join(target, "inbox")

    if not os.path.isdir(inbox):
        raise HTTPException(404, f"no inbox at {inbox}")

    pdfs = [f for f in os.listdir(inbox) if f.endswith(".pdf")]
    if len(pdfs) == 0:
        raise HTTPException(400, "inbox is empty")

    result = await run_triage(inbox)
    materialize_results(result, target)

    return TriageResponse(status="done", result=result, n_papers=len(result.papers))
