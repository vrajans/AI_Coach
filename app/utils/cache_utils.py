import time
from functools import wraps

_cache = {}

def cache_result(ttl=3600):
    """Decorator to cache function results for a specific TTL (seconds)."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            key = (func.__name__, str(args), str(kwargs))
            if key in _cache:
                result, timestamp = _cache[key]
                if time.time() - timestamp < ttl:
                    return result
            result = func(*args, **kwargs)
            _cache[key] = (result, time.time())
            return result
        return wrapper
    return decorator