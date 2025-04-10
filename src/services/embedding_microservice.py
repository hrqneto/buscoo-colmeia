# src/services/embedding_microservice.py
from fastapi import FastAPI
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
from typing import List
import asyncio

app = FastAPI()
model = SentenceTransformer("all-MiniLM-L6-v2", device="cpu")
semaphore = asyncio.Semaphore(3)

class EmbedRequest(BaseModel):
    texts: List[str]

class EmbedResponse(BaseModel):
    vectors: List[List[float]]

@app.post("/embed", response_model=EmbedResponse)
async def embed(req: EmbedRequest):
    async with semaphore:
        vectors = model.encode(req.texts).tolist()
        return {"vectors": vectors}

@app.get("/")
async def health():
    return {"status": "ok"}
