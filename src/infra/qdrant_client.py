# src/services/qdrant_client.py

import os
from dotenv import load_dotenv
from qdrant_client import QdrantClient

load_dotenv()

QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")  # pode ser None se for local

# Inicializa o cliente
qdrant = QdrantClient(
    url=QDRANT_URL,
    api_key=QDRANT_API_KEY
)
