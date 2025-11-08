# app/engines/role_mapper.py

import json
import re
from pathlib import Path
from typing import List, Tuple, Dict, Any
from app.config import settings

BASE_DIR = settings.BASE_DIR
OCCUPATIONS_PATH = Path(BASE_DIR) / "data" / "occupations.json"

# Load occupation dataset
try:
    with open(OCCUPATIONS_PATH, "r", encoding="utf-8") as fh:
        OCCUPATIONS = json.load(fh)
except FileNotFoundError:
    OCCUPATIONS = {}

def _normalize_text(text: str) -> str:
    """
    Lowercase, strip, remove punctuation — clean normalization for skill matching.
    """
    if not isinstance(text, str):
        text = str(text)

    text = text.lower().strip()
    text = re.sub(r"[^a-z0-9+]+", " ", text)
    return text.strip()


def _normalize(s: str) -> str:
    if not s:
        return ""
    s = s.lower()
    s = re.sub(r"[^a-z0-9\s\-]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return s


def heuristic_map(resume_text: str, top_n: int = 3):
    """
    Map raw resume text to best match occupation.
    """
    if not OCCUPATIONS:
        return []

    text = _normalize(resume_text)
    scores = []

    for key, meta in OCCUPATIONS.items():
        score = 0

        for alias in meta.get("aliases", []):
            if _normalize(alias) in text:
                score += 5

        for sk in meta.get("skills", []):
            if _normalize(sk) in text:
                score += 2

        canonical = meta.get("canonical", "")
        if _normalize(canonical) in text:
            score += 3

        scores.append((key, score, meta))

    scores.sort(key=lambda x: -x[1])
    return scores[:top_n]


def get_primary_occupation(resume_text: str):
    """
    Return (occupation_string, occupation_meta).
    """
    mapped = heuristic_map(resume_text, top_n=1)
    if mapped:
        occ_key, _, meta = mapped[0]
        return meta.get("canonical", occ_key), meta

    return "General Professional", {"canonical": "General Professional", "skills": []}
