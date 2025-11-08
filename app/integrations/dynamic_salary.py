import requests, os
from app.utils.cache_utils import cache_result

CAREERONESTOP_URL = "https://api.careeronestop.org/v1/comparesalaries/demo/wageocc"
CAREERONESTOP_TOKEN = os.getenv("CAREERONESTOP_API_TOKEN")

@cache_result(ttl=86400)
def get_salary_for_role(role: str, location: str = "US"):
    """
    Returns average salary and job outlook for the given role.
    Fallback to open salary APIs if CareerOneStop fails.
    """
    if isinstance(role, tuple):
        role = role[0]

    role = role.strip().lower()


    headers = {"Authorization": f"Bearer {CAREERONESTOP_TOKEN}"}
    params = {"keyword": role, "location": location}

    # === Primary: CareerOneStop ===
    try:
        resp = requests.get(CAREERONESTOP_URL, headers=headers, params=params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            occupations = data.get("OccupationDetailList", [])
            if occupations:
                occ = occupations[0]
                return {
                    "role": role,
                    "average_salary": f"${occ.get('Median', 'N/A'):,} / year",
                    "location": location,
                    "growth": occ.get("BrightOutlook", "N/A"),
                    "source": "CareerOneStop"
                }
    except Exception as e:
        print(f"[CareerOneStop Error]: {e}")

    # === Fallback: PayScale Open API ===
    try:
        ps_resp = requests.get(f"https://api.payscale.com/v1/salaries?query={role}", timeout=10)
        if ps_resp.status_code == 200:
            ps_data = ps_resp.json()
            median = ps_data.get("data", {}).get("median_salary")
            if median:
                return {
                    "role": role,
                    "average_salary": f"${median:,} / year",
                    "location": location,
                    "source": "PayScale API"
                }
    except Exception as e:
        print(f"[PayScale API Error]: {e}")

    # === Final Fallback ===
    fallback = {
        "data engineer": "$120,000 / year",
        "backend": "$110,000 / year",
        "frontend": "$105,000 / year",
        "analyst": "$95,000 / year",
        "generic": "$85,000 / year"
    }
    for key, val in fallback.items():
        if key in role:
            return {"role": role, "average_salary": val, "location": location, "source": "Fallback"}

    return {"role": role, "average_salary": "Not Found", "location": location, "source": "N/A"}