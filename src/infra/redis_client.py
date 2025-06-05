import redis.asyncio as aioredis
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

try:
    redis_client = aioredis.from_url(
        os.getenv("REDIS_URL", "redis://localhost:6379"), decode_responses=True
    )
    logger.info("✅ Redis conectado com sucesso!")
except Exception as e:
    logger.error(f"❌ Erro ao conectar ao Redis: {e}")
    redis_client = None
