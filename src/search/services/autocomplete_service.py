import json
import math
import logging
from fastapi import HTTPException
from src.infra.embedding_client import encode_text
from src.infra.redis_client import redis_client
from src.infra.qdrant_client import qdrant
from collections import Counter
import httpx
from bs4 import BeautifulSoup
from functools import lru_cache
import asyncio
import time
from qdrant_client.http.models import SearchRequest
from qdrant_client.http.models import SearchParams

logger = logging.getLogger(__name__)
async_client = httpx.AsyncClient(timeout=10.0)

async def extract_image_from_url(url: str) -> str:
    try:
        cache_key = f"image-cache:{url}"
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                return cached

        # 💤 Pausa para evitar 429 (Too Many Requests)
        await asyncio.sleep(0.2)

        # 🔄 User-Agent mais robusto
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/122.0.0.0 Safari/537.36"
            )
        }

        response = await async_client.get(url, headers=headers)
        
        if "text/html" not in response.headers.get("Content-Type", ""):
            return ""
        
        soup = BeautifulSoup(response.text, "html.parser")
        tag = soup.find("meta", property="og:image")
        image_url = tag["content"] if tag and tag.get("content") else ""

        if image_url and redis_client:
            await redis_client.set(cache_key, image_url, ex=86400)  # 1 dia

        return image_url
    except Exception as e:
        logger.warning(f"[fallback image] Erro ao extrair imagem de {url}: {e}", exc_info=True)
        return ""

def entropy(text: str) -> float:
    prob = [freq / len(text) for freq in Counter(text).values()]
    return -sum(p * math.log2(p) for p in prob if p > 0)

def is_result_relevant(scores: list[float], min_score: float, allow_one_high: bool = False) -> bool:
    if not scores:
        return False
    avg_score = sum(scores) / len(scores)
    if allow_one_high and any(s > min_score + 0.02 for s in scores):
        return True
    return not all(s < min_score for s in scores) and avg_score > (min_score + 0.02)

def is_query_valid(q: str) -> bool:
    q = q.strip().lower()
    words = q.split()

    if len(words) > 3:
        word_counts = Counter(words)
        most_common_word, count = word_counts.most_common(1)[0]
        if count > 2:
            logger.info(f"⛔ Muitas repetições da palavra '{most_common_word}' — ignorada: '{q}'")
            return False

    long_gibberish = [w for w in words if len(w) > 8 and entropy(w) < 1.5]
    if len(long_gibberish) >= 2:
        logger.info(f"⛔ Detecção de palavras longas e ruidosas — ignorando: '{q}'")
        return False

    nonsense_words = 0
    for word in words:
        if len(word) > 5:
            ent = entropy(word)
            vowels = sum(1 for c in word if c in "aeiou")
            consonants = sum(1 for c in word if c.isalpha() and c not in "aeiou")
            if ent < 1.5 and (vowels < 2 or (consonants > 6 and vowels == 0)):
                logger.info(f"⛔ Palavra suspeita detectada ('{word}') — entropia {ent:.2f}, vogais: {vowels}, consoantes: {consonants}")
                nonsense_words += 1

    if len(words) > 3 and nonsense_words >= 1:
        percent_ruido = nonsense_words / len(words)
        if percent_ruido >= 0.3:
            logger.info(f"⛔ Ruído misturado com termo válido ({nonsense_words}/{len(words)}) — ignorando: '{q}'")
            return False

    if len(q) < 1:
        logger.info(f"⛔ Query vazia — ignorada: '{q}'")
        return False

    if len(q) > 3 and len(set(q)) <= 2:
        logger.info(f"⛔ Muitos caracteres repetidos em '{q}' — ignorada")
        return False

    if any(c in q for c in ["%", "$", "&", "*", "^", "~"]) and len(q) > 30:
        logger.info(f"⛔ Query com ruído e muito longa — ignorada: '{q}'")
        return False

    if len(words) >= 4:
        avg_ent = sum(entropy(w) for w in words) / len(words)
        if avg_ent < 2.0:
            logger.info(f"🔕 Entropia média baixa ({avg_ent:.2f}) — ignorando query: '{q}'")
            return False

    return True

async def fix_product_image(product: dict) -> dict:
    image = product.get("image", "")
    url = product.get("url", "")
    if not image or not image.startswith("http"):
        extracted = await extract_image_from_url(url)
        product["image"] = extracted if extracted else "https://via.placeholder.com/150?text=Sem+Imagem"
    return product

async def get_autocomplete_suggestions(q: str, client_id: str = "default"):
    start = time.perf_counter()
    if not q:
        raise HTTPException(status_code=400, detail="Query 'q' é obrigatória")

    suggestions = {
        "queries": [{"htmlTitle": f"{q}", "query": q}],
        "catalogues": [],
        "products": [],
        "brands": [],
        "staticContents": [],
        "total": {"product": 0},
        "suggestionsFound": False,
    }

    if redis_client:
        typo_fallback = await redis_client.get(f"autocomplete:typo_cache:{q.lower()}")
        if typo_fallback and typo_fallback != q.lower():
            fallback_data = await redis_client.get(f"autocomplete:{typo_fallback}")
            if fallback_data:
                logger.info(f"🧠 Fallback cache HIT para '{q}' usando '{typo_fallback}'")
                return json.loads(fallback_data)

    if not is_query_valid(q):
        logger.info(f"⚠️ Query inválida ou muito ruidosa: '{q}' — ignorada")
        return suggestions

    cache_key = f"autocomplete:{q.lower()}"
    try:
        if redis_client:
            cached = await redis_client.get(cache_key)
            if cached:
                data = json.loads(cached)
                if data.get("suggestionsFound"):
                    logger.info(f"✅ Cache HIT válido para '{q}'")
                    return data

        q_clean = q.strip().lower()
        vector = await encode_text(q_clean)
        q_length = len(q_clean)
        threshold = 0.05
        hnsw = 128

        search_args = {
            "collection_name": f"{client_id}",
            "query_vector": vector,
            "limit": 7,
            "with_payload": True,
            "search_params": SearchParams(hnsw_ef=hnsw, exact=False),
            "score_threshold": threshold,
        }

        result = qdrant.search(**search_args)

        if not result:
            logger.info(f"🔍 Nenhum resultado para '{q}'")
            return suggestions

        if q_length <= 2:
            min_score = 0.14
        elif q_length <= 4:
            min_score = 0.08
        elif q_length <= 6:
            min_score = 0.13
        else:
            min_score = 0.2

        seen = set()
        seen_titles = set()
        raw_products = []

        for p in result:
            payload = p.payload or {}
            url = payload.get("url", "")
            title = payload.get("title", "")

            if url in seen or title in seen_titles:
                continue
            seen.add(url)
            seen_titles.add(title)

            score = p.score
            logger.info(f"[similaridade] Score para '{title}': {score}")

            # Conversão segura de price para float
            raw_price = payload.get("price", 0)
            try:
                price = float(raw_price)
            except (ValueError, TypeError):
                price = 0.0

            product_data = {
                "title": title,
                "price": price,
                "priceText": payload.get("priceText", "Indisponível"),
                "brand": payload.get("brand", ""),
                "category": payload.get("category", ""),
                "image": payload.get("image", ""),
                "url": url,
            }

            raw_products.append(product_data)

        products = await asyncio.gather(*[fix_product_image(p) for p in raw_products])

        categories = list({p["category"] for p in products if p["category"]})
        brands = list({p["brand"] for p in products if p["brand"]})

        suggestions["catalogues"] = [{"name": c} for c in categories]
        suggestions["brands"] = [{"name": b} for b in brands]
        suggestions["products"] = products
        suggestions["total"]["product"] = len(products)
        suggestions["suggestionsFound"] = bool(products)

        if redis_client and products:
            await redis_client.set(cache_key, json.dumps(suggestions), ex=300)
            await redis_client.set(f"autocomplete:typo_cache:{q.lower()}", q.lower(), ex=900)

    except Exception as e:
        logger.error(f"❌ Erro no autocomplete: {str(e)}", exc_info=True)
        return suggestions

    elapsed = time.perf_counter() - start
    logger.info(f"⏱️ Tempo total de autocomplete('{q}'): {elapsed:.3f}s")

    return suggestions

async def get_top_items_from_qdrant(client_id: str) -> dict:
    try:
        records = qdrant.scroll(
            collection_name=client_id,
            with_payload=True,
            limit=50
        )

        products = []
        brands = set()
        categories = set()

        for item in records[0]:  # records[0] = lista de pontos
            payload = item.payload or {}
            products.append({
                "title": payload.get("title", ""),
                "url": payload.get("url", ""),
                "image": payload.get("image", ""),
                "priceText": payload.get("priceText", "Indisponível"),
                "brand": payload.get("brand", ""),
                "category": payload.get("category", "")
            })
            if payload.get("brand"):
                brands.add(payload["brand"])
            if payload.get("category"):
                categories.add(payload["category"])

        return {
            "products": products[:7],
            "brands": [{"name": b} for b in list(brands)[:5]],
            "catalogues": [{"name": c} for c in list(categories)[:5]]
        }

    except Exception as e:
        logger.error(f"❌ Erro ao buscar fallback do Qdrant: {e}", exc_info=True)
        return {}

async def get_initial_autocomplete_suggestions(client_id: str = "default") -> dict:
    suggestions = {
        "queries": [],
        "catalogues": [],
        "brands": [],
        "products": [],
        "total": {"product": 0},
        "suggestionsFound": False,
    }

    try:
        # tentar carregar do Redis
        top_queries = await redis_client.zrevrange(f"ranking:searches:{client_id}", 0, 5)
        top_products = await redis_client.lrange(f"ranking:clicks:{client_id}", 0, 5)
        top_brands = await redis_client.zrevrange(f"ranking:brands:{client_id}", 0, 4)
        top_categories = await redis_client.zrevrange(f"ranking:categories:{client_id}", 0, 4)

        if top_queries:
            suggestions["queries"] = [{"query": q.decode()} for q in top_queries]
            
        if top_products:
            parsed_products = [json.loads(p) for p in top_products]

            for prod in parsed_products:
                try:
                    prod["price"] = float(prod.get("price", 0))
                except (ValueError, TypeError):
                    prod["price"] = 0.0

                if "priceText" not in prod:
                    prod["priceText"] = "Indisponível"

            suggestions["products"] = parsed_products
            
        if top_brands:
            suggestions["brands"] = [{"name": b.decode()} for b in top_brands]
            
        if top_categories:
            suggestions["catalogues"] = [{"name": c.decode()} for c in top_categories]

        if not suggestions["products"]:
            fallback = await get_top_items_from_qdrant(client_id)
            suggestions["products"] = fallback.get("products", [])
            suggestions["brands"] = fallback.get("brands", [])
            suggestions["catalogues"] = fallback.get("catalogues", [])

        suggestions["total"]["product"] = len(suggestions["products"])
        suggestions["suggestionsFound"] = bool(suggestions["products"])

        return suggestions

    except Exception as e:
        logger.error(f"❌ Erro ao buscar sugestões iniciais: {e}", exc_info=True)
        return suggestions
