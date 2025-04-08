# main.py
from fastapi import FastAPI
from src.routes import router
from src.utils.redis_client import redis_client

# Cria app FastAPI sem cliente Weaviate
app = FastAPI()

# Registra rotas da aplicação
app.include_router(router)
