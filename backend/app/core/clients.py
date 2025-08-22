import meilisearch
import redis
from .config import settings

meili_client = meilisearch.Client(settings.MEILI_URL, settings.MEILI_KEY)
redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
