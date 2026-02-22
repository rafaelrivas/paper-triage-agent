from pydantic import BaseModel, Field
from typing import Literal

VALID_BUCKETS = ("must-read", "nice-to-read", "bullshit")

class PaperAnalysis(BaseModel):
    filename: str
    title: str
    classification: Literal["must-read", "nice-to-read", "bullshit"]
    domain_tags: list[str] = Field(min_length=1)
    key_contribution: str
    relevance_score: float = Field(ge=0.0, le=1.0)

class ReadingOrderEntry(BaseModel):
    rank: int
    filename: str
    justification: str

class TriageResult(BaseModel):
    papers: list[PaperAnalysis]
    reading_order: list[ReadingOrderEntry]
