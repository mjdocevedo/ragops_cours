import hashlib

def md5_hash(text: str) -> str:
    """Deterministic MD5 hash for cache keys, UTF-8 safe."""
    return hashlib.md5(text.encode("utf-8")).hexdigest()
