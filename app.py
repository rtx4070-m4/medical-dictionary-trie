"""
app.py - FastAPI REST API for Medical Dictionary Trie

Endpoints:
  GET  /                        → Health check + metadata
  GET  /autocomplete?q=<prefix> → Autocomplete suggestions
  GET  /search?q=<term>         → Exact search
  GET  /fuzzy?q=<query>         → Fuzzy / typo-tolerant search
  GET  /stats                   → Dictionary statistics
  POST /term                    → Add a new term
  DELETE /term/{term}           → Remove a term

Run with:
  uvicorn api.app:app --reload --host 0.0.0.0 --port 8000

Author: Medical Dictionary Trie Project
License: MIT
"""

from __future__ import annotations
import logging
import os
import time
from pathlib import Path
from contextlib import asynccontextmanager
from typing import AsyncIterator, List, Optional

from fastapi import FastAPI, HTTPException, Query, Path as FastAPIPath
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

# Ensure src/ is importable when running from repo root
import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.dictionary import MedicalDictionary

# ──────────────────────────────────────────────────────────
# Logging Configuration
# ──────────────────────────────────────────────────────────

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("medical_trie.api")

# ──────────────────────────────────────────────────────────
# Global dictionary instance (shared across requests)
# ──────────────────────────────────────────────────────────

dictionary: MedicalDictionary = MedicalDictionary(
    top_k=int(os.getenv("DEFAULT_TOP_K", "10")),
    fuzzy_max_distance=int(os.getenv("FUZZY_MAX_DISTANCE", "2")),
    sort_by=os.getenv("DEFAULT_SORT_BY", "frequency"),
)

DATA_FILE = os.getenv(
    "MEDICAL_DATA_FILE",
    str(Path(__file__).resolve().parent.parent / "data" / "sample_medical_terms.txt"),
)


# ──────────────────────────────────────────────────────────
# Lifespan (startup / shutdown)
# ──────────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    """Load the dictionary on startup."""
    logger.info("Starting Medical Dictionary Trie API...")
    try:
        inserted = dictionary.load_from_file(DATA_FILE)
        logger.info(
            "Dictionary loaded: %d terms from '%s'", inserted, DATA_FILE
        )
    except FileNotFoundError:
        logger.warning(
            "Data file '%s' not found — starting with empty dictionary.", DATA_FILE
        )
    yield
    logger.info("Shutting down Medical Dictionary Trie API.")


# ──────────────────────────────────────────────────────────
# FastAPI App
# ──────────────────────────────────────────────────────────

app = FastAPI(
    title="Medical Dictionary & Drug Lookup API",
    description=(
        "High-performance autocomplete for 50,000+ medical terms "
        "using an optimized Trie (Prefix Tree) data structure."
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

# Allow all origins for development (restrict in production)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ──────────────────────────────────────────────────────────
# Pydantic Models
# ──────────────────────────────────────────────────────────

class AutocompleteResponse(BaseModel):
    prefix: str
    results: List[str]
    count: int
    elapsed_ms: float


class SearchResponse(BaseModel):
    term: str
    found: bool
    elapsed_ms: float


class FuzzyResponse(BaseModel):
    query: str
    results: List[dict]  # [{term, distance}]
    count: int
    elapsed_ms: float


class StatsResponse(BaseModel):
    total_terms: int
    total_nodes: int
    loaded_files: List[str]
    memory_estimate_kb: float


class AddTermRequest(BaseModel):
    term: str = Field(..., min_length=1, max_length=200, description="Medical term to add")


class AddTermResponse(BaseModel):
    term: str
    inserted: bool
    message: str


class DeleteTermResponse(BaseModel):
    term: str
    deleted: bool
    message: str


# ──────────────────────────────────────────────────────────
# ROUTES
# ──────────────────────────────────────────────────────────

@app.get("/", summary="Health Check", tags=["System"])
async def root() -> dict:
    """
    Health check endpoint — returns API metadata and dictionary status.
    """
    return {
        "status": "ok",
        "service": "Medical Dictionary Trie API",
        "version": "1.0.0",
        "dictionary": {
            "total_terms": dictionary.size,
            "total_nodes": dictionary.node_count,
        },
        "docs": "/docs",
    }


@app.get(
    "/autocomplete",
    response_model=AutocompleteResponse,
    summary="Autocomplete medical terms",
    tags=["Search"],
)
async def autocomplete(
    q: str = Query(..., min_length=1, max_length=100, description="Search prefix"),
    top_k: int = Query(10, ge=1, le=100, description="Max number of results"),
    sort_by: str = Query("frequency", regex="^(frequency|alphabetical)$"),
) -> AutocompleteResponse:
    """
    Return autocomplete suggestions for a given prefix.

    - **q**: The prefix to search (e.g., `"diab"`)
    - **top_k**: Maximum results to return (1–100)
    - **sort_by**: Ranking strategy — `frequency` or `alphabetical`

    Returns a JSON list of matching medical terms ranked by sort_by.
    """
    start = time.perf_counter()
    suggestions = dictionary.autocomplete(q.strip(), top_k=top_k, sort_by=sort_by)
    elapsed = round((time.perf_counter() - start) * 1000, 3)

    terms = [term for term, _ in suggestions]

    logger.info("autocomplete('%s') → %d results in %.3f ms", q, len(terms), elapsed)

    return AutocompleteResponse(
        prefix=q,
        results=terms,
        count=len(terms),
        elapsed_ms=elapsed,
    )


@app.get(
    "/search",
    response_model=SearchResponse,
    summary="Exact term search",
    tags=["Search"],
)
async def search(
    q: str = Query(..., min_length=1, max_length=200, description="Exact term to search")
) -> SearchResponse:
    """
    Perform an exact (case-insensitive) lookup of a medical term.

    Returns `found: true` if the term exists in the dictionary.
    """
    start = time.perf_counter()
    found = dictionary.search(q.strip())
    elapsed = round((time.perf_counter() - start) * 1000, 3)

    return SearchResponse(term=q, found=found, elapsed_ms=elapsed)


@app.get(
    "/fuzzy",
    response_model=FuzzyResponse,
    summary="Fuzzy / typo-tolerant search",
    tags=["Search"],
)
async def fuzzy(
    q: str = Query(..., min_length=1, max_length=200, description="Query (may contain typos)"),
    top_k: int = Query(10, ge=1, le=50, description="Max number of results"),
    max_distance: int = Query(2, ge=0, le=5, description="Maximum Levenshtein distance"),
) -> FuzzyResponse:
    """
    Fuzzy search that tolerates typos using Levenshtein distance.

    - **q**: Your query, possibly with typos (e.g., `"diabets"`)
    - **max_distance**: Maximum edit distance allowed (default: 2)

    Returns closest matching terms and their edit distances.
    """
    start = time.perf_counter()
    matches = dictionary.fuzzy_search(q.strip(), top_k=top_k, max_distance=max_distance)
    elapsed = round((time.perf_counter() - start) * 1000, 3)

    results = [{"term": term, "distance": dist} for term, dist in matches]

    logger.info("fuzzy('%s') → %d results in %.3f ms", q, len(results), elapsed)

    return FuzzyResponse(
        query=q,
        results=results,
        count=len(results),
        elapsed_ms=elapsed,
    )


@app.get(
    "/stats",
    response_model=StatsResponse,
    summary="Dictionary statistics",
    tags=["System"],
)
async def stats() -> StatsResponse:
    """
    Return statistics about the loaded dictionary.

    Includes total terms, total Trie nodes, loaded data files,
    and an estimated memory footprint.
    """
    data = dictionary.stats()
    return StatsResponse(**data)


@app.post(
    "/term",
    response_model=AddTermResponse,
    summary="Add a medical term",
    tags=["Management"],
    status_code=201,
)
async def add_term(body: AddTermRequest) -> AddTermResponse:
    """
    Add a new medical term to the dictionary at runtime.

    The term is normalized (lowercased, trimmed) before insertion.
    """
    inserted = dictionary.add_term(body.term)
    return AddTermResponse(
        term=body.term,
        inserted=inserted,
        message="Term inserted successfully." if inserted else "Term already exists.",
    )


@app.delete(
    "/term/{term}",
    response_model=DeleteTermResponse,
    summary="Remove a medical term",
    tags=["Management"],
)
async def delete_term(
    term: str = FastAPIPath(..., min_length=1, max_length=200, description="Term to remove")
) -> DeleteTermResponse:
    """
    Remove a medical term from the dictionary.

    Returns `deleted: false` if the term was not found.
    """
    deleted = dictionary.remove_term(term)
    if not deleted:
        raise HTTPException(status_code=404, detail=f"Term '{term}' not found.")
    return DeleteTermResponse(
        term=term,
        deleted=True,
        message=f"Term '{term}' removed successfully.",
    )


# ──────────────────────────────────────────────────────────
# Error Handlers
# ──────────────────────────────────────────────────────────

@app.exception_handler(Exception)
async def global_exception_handler(request, exc: Exception) -> JSONResponse:
    logger.exception("Unhandled exception: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Internal server error.", "error": str(exc)},
    )
