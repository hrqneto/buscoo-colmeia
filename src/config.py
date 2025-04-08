import os
import redis
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# 🔥 Carrega variáveis de ambiente do .env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

# 🧠 Nome da coleção de produtos no Qdrant
PRODUCT_CLASS = "products"

# ✅ Configuração do Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# ✅ Configuração do Qdrant
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

def create_qdrant_client():
    try:
        print(f"🔍 Conectando ao Qdrant: {QDRANT_URL}")
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY
        )
        print("✅ Conectado ao Qdrant com sucesso!")
        return client
    except Exception as e:
        print(f"🚨 Erro ao conectar ao Qdrant: {e}")
        raise

# Singleton do Qdrant (opcional)
qdrant_client = create_qdrant_client()

# ✅ Configuração do Cloudflare R2
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
CDN_DOMAIN = os.getenv("CDN_DOMAIN")
