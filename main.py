# src/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from src.routes import router

app = FastAPI(
    title="buscoo API",
    description="API de indexação e autocomplete vetorial para e-commerce. Contém endpoints para upload, busca, sugestões e monitoramento de status.",
    version="1.0.0"
)

# ✅ CORSMiddleware primeiro
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # ou ["*"] em dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ✅ Inclui rotas após o middleware
app.include_router(router, prefix="/api")
