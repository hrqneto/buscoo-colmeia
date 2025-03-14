from fastapi import FastAPI
from contextlib import asynccontextmanager
from weaviate_client import client
import routes

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
app.include_router(routes.router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
