# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.services.weaviate_client import create_weaviate_client, close_weaviate_client
from src.routes import router
from src.utils.redis_client import redis_client

client = create_weaviate_client()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia a conexão com o Weaviate."""
    try:
        yield
    finally:
        if client:
            print("🛑 Fechando conexão com Weaviate...")
            close_weaviate_client(client)

app = FastAPI(lifespan=lifespan)
app.include_router(router)
