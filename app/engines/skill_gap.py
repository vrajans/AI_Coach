# app/engines/skill_gap.py
from typing import List, Dict, Any
from app.engines.role_mapper import _normalize_text

def compute_skill_gaps(parsed_resume: Dict[str, Any], occupation_meta: Dict[str, Any]) -> List[Dict[str, Any]]:
    """
    Compute skill gaps by comparing resume skills vs. occupation_meta['skills'].
    occupation_meta is a dict containing:
        { canonical, skills, core_skills, ... }

    Returns:
      [
        {
          "skill": str,
          "skill_normalized": str,
          "present": bool,
          "impact": "high" | "medium" | "low"
        },
        ...
      ]
    """

    if isinstance(parsed_resume, str):
        # Use empty skills to avoid breaking pipeline
        parsed_resume = {"skills": []}


    # Resume skills → normalized set
    resume_skills = parsed_resume.get("skills", []) or []
    normalized_resume_skills = set()

    for s in resume_skills:
        if not s:
            continue
        if isinstance(s, str):
            normalized_resume_skills.add(_normalize_text(s))
        else:
            normalized_resume_skills.add(_normalize_text(str(s)))

    required_skills = occupation_meta.get("skills", []) or []
    core_skills = set(_normalize_text(s) for s in occupation_meta.get("core_skills", []) or [])

    gaps = []

    for sk in required_skills:
        sk_norm = _normalize_text(sk)
        present = sk_norm in normalized_resume_skills

        # Determine impact
        if sk_norm in core_skills:
            impact = "high"
        else:
            if any(x in sk_norm for x in ["sql", "python", "cloud", "etl", "docker", "kubernetes", "spark"]):
                impact = "medium"
            else:
                impact = "low"

        gaps.append({
            "skill": sk,
            "skill_normalized": sk_norm,
            "present": present,
            "impact": impact
        })

    # Sort: missing first + highest impact first
    gaps_sorted = sorted(
        gaps,
        key=lambda x: (
            x["present"],                             # missing first
            0 if x["impact"] == "high" else 1 if x["impact"] == "medium" else 2
        )
    )

    return gaps_sorted


def summarize_gaps(gaps: List[Dict[str, Any]], top_n: int = 5) -> List[Dict[str, Any]]:
    """
    Return top N missing skills ordered by importance.
    """
    missing = [g for g in gaps if not g["present"]]
    return missing[:top_n]