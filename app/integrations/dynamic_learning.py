import requests
from app.utils.cache_utils import cache_result

MS_LEARN_API = "https://learn.microsoft.com/api/catalog/"
COURSERA_SEARCH_API = "https://www.coursera.org/api/catalogResults.v2"
EDX_SEARCH_API = "https://www.edx.org/api/v1/catalog/search"

@cache_result(ttl=3600)
def get_learning_resources(query: str, limit: int = 5):
    """
    Dynamically fetch courses from open APIs (Microsoft Learn, Coursera, EdX).
    Fallbacks are handled automatically.
    """
    query = query.lower().strip()

    # Step 1: Microsoft Learn (first priority)
    try:
        ms_params = {"q": query, "top": limit}
        ms_resp = requests.get(MS_LEARN_API, params=ms_params, timeout=10)
        if ms_resp.status_code == 200:
            data = ms_resp.json()
            items = data.get("value", [])
            if items:
                return [
                    {
                        "title": it.get("title"),
                        "url": it.get("url"),
                        "platform": "Microsoft Learn",
                        "summary": it.get("summary", "")
                    } for it in items[:limit]
                ]
    except Exception as e:
        print(f"[MS Learn API Error]: {e}")

    # Step 2: Coursera API
    try:
        coursera_params = {"q": query, "limit": limit}
        resp = requests.get(COURSERA_SEARCH_API, params=coursera_params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            elements = data.get("linked", {}).get("courses.v1", [])
            if elements:
                return [
                    {
                        "title": el.get("name"),
                        "url": f"https://www.coursera.org/learn/{el.get('slug')}",
                        "platform": "Coursera"
                    }
                    for el in elements[:limit]
                ]
    except Exception as e:
        print(f"[Coursera API Error]: {e}")

    # Step 3: EdX API (open source fallback)
    try:
        edx_params = {"search_query": query, "page_size": limit}
        resp = requests.get(EDX_SEARCH_API, params=edx_params, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            results = data.get("objects", [])
            if results:
                return [
                    {
                        "title": r.get("title"),
                        "url": f"https://www.edx.org/course/{r.get('key')}",
                        "platform": "EdX"
                    }
                    for r in results[:limit]
                ]
    except Exception as e:
        print(f"[EdX API Error]: {e}")

    # Step 4: Final fallback
    return fallback_learning_courses(query)


def fallback_learning_courses(query: str):
    """Fallback courses if all APIs fail."""
    FALLBACK = {
        "data engineer": [
            {"title": "Data Engineering on Google Cloud", "url": "https://www.coursera.org/learn/data-engineering-gcp", "platform": "Coursera"},
            {"title": "Modern Data Engineering with Spark", "url": "https://www.edx.org/learn/spark", "platform": "EdX"},
        ],
        "python": [
            {"title": "Python for Everybody", "url": "https://www.coursera.org/specializations/python", "platform": "Coursera"},
        ],
        "default": [
            {"title": "Career Success Specialization", "url": "https://www.coursera.org/specializations/career-success", "platform": "Coursera"}
        ],
    }

    for key, val in FALLBACK.items():
        if key in query.lower():
            return val
    return FALLBACK["default"]