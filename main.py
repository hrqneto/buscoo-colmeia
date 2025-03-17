from fastapi import FastAPI
from contextlib import asynccontextmanager
from src.services.weaviate_client import client
from src.routes import router

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Gerencia a conexão com o Weaviate."""
    try:
        yield
    finally:
        if client:
            print("🛑 Fechando conexão com Weaviate...")
            client.close()

app = FastAPI(lifespan=lifespan)
app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
