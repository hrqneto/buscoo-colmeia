# src/services/weaviate_client.py

# 🔁 Mantém o módulo, mas deixa o client vazio pra evitar importações acidentais
def create_weaviate_client():
    print("⚠️ Weaviate client não está mais em uso. Use Qdrant.")
    return None

def close_weaviate_client(client):
    print("⚠️ Conexão com Weaviate ignorada.")
