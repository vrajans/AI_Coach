# app/engines/learning_builder.py
from typing import List, Dict
from app.integrations.dynamic_learning import get_learning_resources
from app.integrations.dynamic_salary import get_salary_for_role

def build_learning_plan(domain: str, occupation: str, skill_gaps: List[Dict]):
    """
    Matches agent_core.py expected signature:
    build_learning_plan(domain, occupation, skill_gaps)
    """
    missing = [g for g in skill_gaps if not g["present"]]

    if not missing:
        return {
            "summary": f"You already meet most core expectations for {occupation}. Focus on advanced projects."
        }

    plan = []
    for g in missing[:3]:
        courses = get_learning_resources(g["skill"], limit=3)
        plan.append({
            "skill": g["skill"],
            "impact": g["impact"],
            "courses": courses
        })

    return plan


def get_salary_insight(occupation: str):
    """
    Matches agent_core.py expected signature:
    salary = get_salary_insight(occupation)
    """
    result = get_salary_for_role(occupation)
    return result
