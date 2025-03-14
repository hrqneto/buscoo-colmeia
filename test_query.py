import json
from config import get_client, PRODUCT_CLASS

# 🔗 Conectar ao Weaviate
client = get_client()

# 📦 Recuperar a coleção
collection = client.collections.get(PRODUCT_CLASS)

# 🔍 Buscar produtos pelo termo "fone"
query_text = "fone"
result = collection.query.hybrid(
    query=query_text,
    alpha=1.0,
    limit=5,
    return_properties=["title", "description", "price", "brand"]
)

print("\n🔍 Resultados para:", query_text, "\n")

# 🔎 Exibir resultados e buscar os vetores individualmente
for obj in result.objects:
    obj_uuid = obj.uuid  # Pega o UUID do objeto

    # Verificar se obj_uuid existe e é válido
    if not obj_uuid:
        print("⚠️ UUID do objeto é inválido. Pulando...")
        continue

    # Buscar detalhes do objeto, incluindo vetores
    detailed_obj = collection.query.fetch_object_by_id(
        uuid=obj_uuid,
        return_properties=["title", "description", "price", "brand"],
        include_vector=True  # Solicitar o vetor
    )

    # Se detailed_obj estiver vazio, algo deu errado na busca
    if not detailed_obj:
        print(f"⚠️ Nenhum objeto encontrado para UUID: {obj_uuid}")
        continue

    # Exibir detalhes do produto
    print(f"Produto: {detailed_obj.properties.get('title', 'Título não disponível')}")

    # Verificar se há vetores e exibi-los
    if hasattr(detailed_obj, 'vector'):
        print(f"Vetor: {json.dumps(detailed_obj.vector, indent=2)}\n")
    else:
        print("⚠️ Vetor não encontrado para este objeto.\n")

# Fechar a conexão com o Weaviate
client.close()