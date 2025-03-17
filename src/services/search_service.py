import time
import json
from fastapi import HTTPException
from transformers import pipeline
from src.services.weaviate_client import create_weaviate_client
from src.config import PRODUCT_CLASS

# 🔥 Carregar modelo de Rerank da Hugging Face
reranker = pipeline("text-classification", model="cross-encoder/ms-marco-MiniLM-L-6-v2")

def remove_duplicates(products):
    """Remove produtos duplicados baseando-se no título e na marca"""
    seen = set()
    unique_products = []
    
    for p in products:
        key = (p["title"].lower(), p["brand"].lower())  # Normalizando para evitar duplicatas
        if key not in seen:
            seen.add(key)
            unique_products.append(p)
    
    return unique_products

def normalize_scores(products):
    """Normaliza os scores de rerank para a escala de 0 a 1"""
    scores = [p["rerank_score"] for p in products if p.get("rerank_score") is not None]
    
    if not scores or max(scores) == min(scores):
        return products  # Evita divisão por zero

    min_score = min(scores)
    max_score = max(scores)

    for p in products:
        p["rerank_score"] = (p["rerank_score"] - min_score) / (max_score - min_score)
    
    return products

def search_products(query: str, limit: int = 50, filters: dict = None):
    """Executa busca híbrida no Weaviate e aplica rerank nos resultados."""
    client = None
    try:
        start_time = time.time()
        print(f"🔍 Iniciando busca para: '{query}'")

        client = create_weaviate_client()
        collection = client.collections.get(PRODUCT_CLASS)

        # 🔥 Executar a busca híbrida no Weaviate (removendo where)
        result = collection.query.hybrid(
            query=query,
            alpha=0.85,
            limit=limit,
            return_metadata=["score"],
            return_properties=["uuid", "title", "description", "brand", "category", "specs", "price"]
        )

        if not result or not result.objects:
            print(f"⚠️ Nenhum resultado encontrado para '{query}'")
            return {"message": f"Nenhum resultado encontrado para '{query}'. Nosso catálogo é focado em roupas e acessórios."}

        produtos = []
        for obj in result.objects:
            props = obj.properties
            produto = {
                "uuid": str(props.get("uuid", "Sem UUID")),
                "title": props.get("title", "Sem título"),
                "description": props.get("description", "Sem descrição"),
                "brand": props.get("brand", "Desconhecida"),
                "category": props.get("category", "Desconhecida"),
                "specs": props.get("specs", "Sem especificações"),
                "price": props.get("price", 0.0),
                "score": obj.metadata.score
            }
            produtos.append(produto)

        print(f"✅ Produtos retornados antes do Rerank: {len(produtos)}")

        # 🛑 **Aplicar filtros MANUALMENTE após a busca**
        if filters:
            produtos = [
                p for p in produtos
                if all(str(p.get(key, "")).lower() == str(value).lower() for key, value in filters.items())
            ]
            print(f"✅ Produtos após filtros: {len(produtos)}")

        # 🔄 Remover duplicatas antes do rerank
        produtos = remove_duplicates(produtos)
        print(f"✅ Produtos após remoção de duplicatas: {len(produtos)}")

        # 🏆 Aplicar Rerank para melhorar a ordenação
        ranked_products = sorted(
            produtos,
            key=lambda p: reranker(f"{query} {p['title']} {p['brand']} {p['category']} {p['specs']}")[0]['score'],
            reverse=True
        )

        # 📊 Normalizar scores para escala 0-1
        ranked_products = normalize_scores(ranked_products)

        # 📉 Se poucos produtos forem encontrados, sugerir alternativas
        if len(ranked_products) < 5:
            print(f"⚠️ Apenas {len(ranked_products)} produtos encontrados, ativando fallback...")
            return {
                "message": f"Poucos resultados para '{query}'. Você pode tentar buscar por 'camiseta', 'calça' ou 'sapato'.",
                "results": ranked_products
            }

        print(f"✅ Rerank aplicado! Total de produtos retornados: {len(ranked_products)}")
        print(f"✅ Busca finalizada em {time.time() - start_time:.3f} segundos")
        return ranked_products

    except Exception as e:
        print(f"❌ Erro ao buscar produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if client:
            client.close()
