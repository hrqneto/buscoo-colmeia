import os
import weaviate
from weaviate.auth import AuthApiKey
from weaviate.classes.config import Configure

# Configuração do Weaviate Cloud
WCD_URL = os.getenv("WCD_URL", "https://auhtvtirxk6ezlfza1qw.c0.us-east1.gcp.weaviate.cloud")
WCD_API_KEY = os.getenv("WCD_API_KEY", "TEH1iPXs5vDJqm7YAjiSqQS3RMM5qGGqHFz4")
PRODUCT_CLASS = "Product"

def get_auth():
    return AuthApiKey(WCD_API_KEY)

# Criar cliente do Weaviate
def get_client():
    return weaviate.connect_to_weaviate_cloud(
        cluster_url=WCD_URL,
        auth_credentials=get_auth(),
    )

# Criar coleção com modelo de vetorização ativo
def create_collection(client):
    client.collections.create(
        PRODUCT_CLASS,
        vectorizer_config=[
            Configure.NamedVectors.text2vec_weaviate(
                name="title_vector",
                source_properties=["title", "description"],  # Vetoriza título e descrição
                model="Snowflake/snowflake-arctic-embed-l-v2.0",  # Modelo compatível
            )
        ],
    )
