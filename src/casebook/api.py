from datetime import date
from functools import lru_cache
from typing import Literal

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .data import load_sources
from .io import ROOT
from .retrieval import Retriever, investigate

app = FastAPI(
    title="Casebook",
    version="0.1.0",
    description="Source-linked investigation support; drafts require human review",
)


@lru_cache(maxsize=1)
def retriever():
    return Retriever(load_sources())


class Investigation(BaseModel):
    question: str = Field(min_length=3, max_length=4000)
    version: str | None = "0.28.1"
    as_of: date | None = None
    backend: Literal["extractive", "local"] = "extractive"


@app.get("/health")
def health():
    return dict(ready=(ROOT / "models/keyword.joblib").exists())


@app.post("/investigate")
def investigation(body: Investigation):
    return investigate(
        retriever(), body.question, body.version, body.as_of.isoformat() if body.as_of else None, body.backend
    )
