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

# Criar coleção com modelo de vetorização ajustado
def create_collection(client):
    client.collections.create(
        PRODUCT_CLASS,
        vectorizer_config=[
            Configure.NamedVectors.text2vec_weaviate(
                name="title_vector",
                source_properties=["title", "description"],
                model="Snowflake/snowflake-arctic-embed-l-v2.0",
                weight=1.0  # Menor peso para título e descrição
            ),
            Configure.NamedVectors.text2vec_weaviate(
                name="category_vector",
                source_properties=["category"],
                model="Snowflake/snowflake-arctic-embed-l-v2.0",
                weight=1.2 #  Peso intermediário 
            ),
            Configure.NamedVectors.text2vec_weaviate(
                name="specs_vector",
                source_properties=["specs"],
                model="Snowflake/snowflake-arctic-embed-l-v2.0",
                weight=0.9  #  Peso intermediário para especificações técnicas
            )
        ],
    )
