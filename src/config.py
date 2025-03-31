import os
import weaviate
import redis
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Configure
from dotenv import load_dotenv
from qdrant_client import QdrantClient
from qdrant_client.http.models import VectorParams, Distance


# 🔥 Carrega variáveis de ambiente do .env
dotenv_path = os.path.join(os.path.dirname(__file__), "..", ".env")
load_dotenv(dotenv_path)

# 🔍 Configuração do Weaviate Cloud
WCD_URL = os.getenv("WEAVIATE_URL", "https://1vammhlxtcumbtvynnjbnw.c0.us-west3.gcp.weaviate.cloud")
WCD_API_KEY = os.getenv("WCD_API_KEY", "s3Zdjz5cxoedathSGQhk6sbaJF7lUVqPQIFZ")
PRODUCT_CLASS = "Product"

def get_auth():
    return AuthApiKey(WCD_API_KEY)

# 🔥 Configuração do Redis
REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "6379"))
REDIS_DB = int(os.getenv("REDIS_DB", "0"))

# Redis client
redis_client = redis.Redis(
    host=REDIS_HOST, 
    port=REDIS_PORT, 
    db=REDIS_DB, 
    decode_responses=True
)

# Weaviate client
def get_client():
    return weaviate.connect_to_weaviate_cloud(
        cluster_url=WCD_URL,
        auth_credentials=get_auth(),
    )

# Criação da coleção com vetorização multi-nomeada
def create_collection(client):
    client.collections.create(
        PRODUCT_CLASS,
        vectorizer_config=[
            Configure.NamedVectors.text2vec_weaviate(
                name="title_vector",
                source_properties=["title", "description"],
                model="Snowflake/snowflake-arctic-embed-l-v2.0",
            ),
            Configure.NamedVectors.text2vec_weaviate(
                name="category_vector",
                source_properties=["category"],
                model="Snowflake/snowflake-arctic-embed-l-v2.0",
            ),
            Configure.NamedVectors.text2vec_weaviate(
                name="specs_vector",
                source_properties=["specs"],
                model="Snowflake/snowflake-arctic-embed-l-v2.0",
            )
        ],
    )

# ✅ Qdrant config e client (novo)
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


# Exporta os clientes como singletons
weaviate_client = get_client()
qdrant_client = create_qdrant_client()