from __future__ import annotations

from fastapi import APIRouter


router = APIRouter()


@router.get("/", tags=["system"])
def root():
    return {"message": "ML Service API"}


@router.get("/health", tags=["system"])
def health():
    return {"status": "ok"}


