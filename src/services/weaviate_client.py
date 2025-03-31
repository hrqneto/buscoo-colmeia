import weaviate
from src.config import WCD_URL, get_auth

def create_weaviate_client():
    """Inicializa e retorna um cliente Weaviate com gerenciamento adequado da conexão."""
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

def close_weaviate_client(client):
    """Fecha a conexão com o Weaviate corretamente."""
    try:
        if client is not None:
            client.close()
            print("🔒 Conexão com Weaviate fechada corretamente.")
    except Exception as e:
        print(f"⚠️ Erro ao fechar a conexão com Weaviate: {e}")

client = create_weaviate_client()
