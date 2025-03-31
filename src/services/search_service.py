import time
from fastapi import HTTPException
from transformers import pipeline
from src.services.weaviate_client import create_weaviate_client
from src.config import PRODUCT_CLASS

# 🔥 Reranker generalista
reranker = pipeline("text-classification", model="cross-encoder/ms-marco-MiniLM-L-6-v2")

def remove_duplicates(products):
    """Remove duplicatas com base em título e marca."""
    seen = set()
    unique_products = []

    for p in products:
        key = (p["title"].lower(), p["brand"].lower())
        if key not in seen:
            seen.add(key)
            unique_products.append(p)

    return unique_products

def normalize_scores(products):
    """Normaliza scores para a escala de 0 a 1."""
    scores = [p["rerank_score"] for p in products if p.get("rerank_score") is not None]

    if not scores or max(scores) == min(scores):
        return products

    min_score, max_score = min(scores), max(scores)
    for p in products:
        p["rerank_score"] = (p["rerank_score"] - min_score) / (max_score - min_score)

    return products

def build_filters(filters_dict):
    operands = []

    for key, value in filters_dict.items():
        if isinstance(value, dict):  
            condition = {
                "path": [key],
                "operator": value.get("operator", "Equal"),
                "valueText": value.get("value")
            }
        else: 
            condition = {
                "path": [key],
                "operator": "Equal",
                "valueText": value
            }
        operands.append(condition)

    if operands:
        return {"operator": "And", "operands": operands}
    else:
        return None

def search_products(query: str, limit: int = 50, filters: dict = None):
    client = None
    try:
        start_time = time.time()
        print(f"🔍 Iniciando busca para: '{query}'")

        client = create_weaviate_client()
        collection = client.collections.get(PRODUCT_CLASS)

        # 🔧 Construção dos filtros
        filters_clause = build_filters(filters) if filters else None

        # 🚨 Corrigido o erro usando 'filters' em vez de 'where'
        result = collection.query.hybrid(
            query=query,
            alpha=0.85,
            limit=limit,
            filters=filters_clause,
            return_metadata=["score"],
            return_properties=[
                "uuid", "title", "description", "brand", 
                "category", "specs", "price"
            ],
        )
        if not result or not result.objects:
            return {
                "message": f"Nenhum produto encontrado para '{query}'. Verifique os filtros usados ou tente outra busca."
            }

        produtos = []
        for obj in result.objects:
            props = obj.properties
            produto = {
                "uuid": props.get("uuid", "Sem UUID"),
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

        produtos = remove_duplicates(produtos)
        print(f"✅ Produtos após remoção de duplicatas: {len(produtos)}")

        # 🚀 Aplicando reranking generalista
        top_n = min(30, len(produtos))
        ranked_products = []
        for p in produtos[:top_n]:
            text_to_rank = f"{query} {p['title']} {p['brand']} {p['category']} {p['specs']}"
            rerank_result = reranker(text_to_rank)[0]
            p['rerank_score'] = rerank_result['score']
            ranked_products.append(p)

        ranked_products.sort(key=lambda x: x['rerank_score'], reverse=True)

        ranked_products = normalize_scores(ranked_products)

        MIN_ACCEPTABLE_SCORE = 0.02  # ajuste conforme necessário
        relevant_products = [p for p in ranked_products if p['rerank_score'] >= MIN_ACCEPTABLE_SCORE]

        if not relevant_products:
            return {
                "message": f"Nenhum resultado relevante para '{query}'. Tente novamente com outros termos."
            }

        # Continua usando os produtos relevantes para o retorno final
        ranked_products = relevant_products

        if len(ranked_products) < 5:
            return {
                "message": f"Poucos resultados para '{query}'. Tente termos mais gerais.",
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