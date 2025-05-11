from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct
from uuid import uuid4
import os

QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY, prefer_grpc=False)

# Cria ou recria a collection
client.recreate_collection(
    collection_name="teste_debug",
    vectors_config=models.VectorParams(size=384, distance=models.Distance.COSINE)
)

# ✅ ID com UUID válido agora
point = PointStruct(
    id=str(uuid4()),
    vector=[0.1] * 384,
    payload={"title": "Produto de Teste"}
)

client.upsert(collection_name="teste_debug", points=[point])
print("✅ Upsert isolado funcionou!")
