import os
import redis
from dotenv import load_dotenv
from qdrant_client import QdrantClient

# 🔥 Carrega variáveis de ambiente do .env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

# Qdrant
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

# Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Firebase
FIREBASE_PROJECT_ID = os.getenv("FIREBASE_PROJECT_ID")
FIREBASE_PRIVATE_KEY_ID = os.getenv("FIREBASE_PRIVATE_KEY_ID")
FIREBASE_PRIVATE_KEY = os.getenv("FIREBASE_PRIVATE_KEY")
FIREBASE_CLIENT_EMAIL = os.getenv("FIREBASE_CLIENT_EMAIL")
FIREBASE_CLIENT_ID = os.getenv("FIREBASE_CLIENT_ID")
FIREBASE_AUTH_URI = os.getenv("FIREBASE_AUTH_URI")
FIREBASE_TOKEN_URI = os.getenv("FIREBASE_TOKEN_URI")
FIREBASE_AUTH_PROVIDER_X509_CERT_URL = os.getenv("FIREBASE_AUTH_PROVIDER_X509_CERT_URL")
FIREBASE_CLIENT_X509_CERT_URL = os.getenv("FIREBASE_CLIENT_X509_CERT_URL")

# Cloudflare R2
R2_ACCESS_KEY = os.getenv("R2_ACCESS_KEY")
R2_SECRET_KEY = os.getenv("R2_SECRET_KEY")
R2_BUCKET_NAME = os.getenv("R2_BUCKET_NAME")
R2_ENDPOINT_URL = os.getenv("R2_ENDPOINT_URL")
CDN_DOMAIN = os.getenv("CDN_DOMAIN")

# Nome padrão da collection no Qdrant (para produtos)
PRODUCT_CLASS = "products"

# Redis client singleton
redis_client = redis.Redis(
    host=REDIS_HOST,
    port=REDIS_PORT,
    db=REDIS_DB,
    decode_responses=True
)

# Qdrant client singleton
def create_qdrant_client():
    try:
        print(f"🔍 Conectando ao Qdrant: {QDRANT_URL}")
        client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
            prefer_grpc=False,
            https=True
        )
        print("✅ Conectado ao Qdrant com sucesso!")
        return client
    except Exception as e:
        print(f"🚨 Erro ao conectar ao Qdrant: {e}")
        raise

qdrant_client = create_qdrant_client()
