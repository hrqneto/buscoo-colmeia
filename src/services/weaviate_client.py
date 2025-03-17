import weaviate
from src.config import WCD_URL, get_auth

def create_weaviate_client():
    """Inicializa o cliente Weaviate."""
    try:
        print(f"🔍 Conectando ao Weaviate: {WCD_URL}")
        client = weaviate.connect_to_weaviate_cloud(
            cluster_url=WCD_URL,
            auth_credentials=get_auth()
        )
        print("✅ Conectado ao Weaviate com sucesso!")
        return client
    except Exception as e:
        print(f"🚨 Erro ao conectar ao Weaviate: {e}")
        raise

client = create_weaviate_client()
