import json
import math
import logging
from fastapi import HTTPException
from src.services.embedding_service import encode_text
from src.utils.redis_client import redis_client
from qdrant_client.models import SearchParams
from src.services.qdrant_client import qdrant
from collections import Counter
import httpx
from bs4 import BeautifulSoup
from functools import lru_cache

logger = logging.getLogger(__name__)
async_client = httpx.AsyncClient(timeout=10.0)

@lru_cache(maxsize=1000)
def get_cached_image(url: str) -> str:
    return url

async def extract_image_from_url(url: str) -> str:
    try:
        cached_image = get_cached_image(url)
        if cached_image:
            return cached_image

        headers = {"User-Agent": "Mozilla/5.0 (compatible; BuscaFlexBot/1.0)"}
        response = await async_client.get(url, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")
        tag = soup.find("meta", property="og:image")
        return tag["content"] if tag and tag.get("content") else ""
    except Exception as e:
        logger.warning(f"[fallback image] Erro ao extrair imagem de {url}: {e}", exc_info=True)
        return ""

def entropy(text: str) -> float:
    prob = [freq / len(text) for freq in Counter(text).values()]
    return -sum(p * math.log2(p) for p in prob if p > 0)

def is_result_relevant(scores: list[float], min_score: float) -> bool:
    if not scores:
        return False
    avg_score = sum(scores) / len(scores)
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

    nonsense_words = 0
    for word in words:
        if len(word) > 5:
            ent = entropy(word)
            vowels = sum(1 for c in word if c in "aeiou")
            consonants = sum(1 for c in word if c.isalpha() and c not in "aeiou")

            # ✅ Ajustado: só considera nonsense se vários fatores ruins juntos
            if ent < 1.5 and (vowels < 2 or (consonants > 6 and vowels == 0)):
                logger.info(f"⛔ Palavra suspeita detectada ('{word}') — entropia {ent:.2f}, vogais: {vowels}, consoantes: {consonants}")
                nonsense_words += 1

    if nonsense_words >= 2 or nonsense_words >= len(words) / 2:
        logger.info(f"⛔ Muitas palavras suspeitas ({nonsense_words}) — ignorada: '{q}'")
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

    if len(q) > 4:
        ent = entropy(q.replace(" ", ""))
        logger.info(f"🔍 Entropia de '{q}': {ent:.2f}")
        if ent < 1.3:
            logger.info(f"🔕 Entropia baixa ({ent:.2f}) — ignorando query: '{q}'")
            return False

    return True

async def get_autocomplete_suggestions(q: str):
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
        if typo_fallback:
            fallback_data = await redis_client.get(f"autocomplete:{typo_fallback}")
            if fallback_data:
                logger.info(f"🧠 Fallback cache HIT para '{q}' usando '{typo_fallback.decode()}'")
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
        vector = encode_text(q_clean)
        q_length = len(q_clean)
        threshold = 0.05
        hnsw = 128

        search_args = {
            "collection_name": "products",
            "query_vector": vector,
            "limit": 5,
            "with_payload": True,
            "search_params": SearchParams(hnsw_ef=hnsw, exact=False),
            "score_threshold": threshold,
        }

        result = qdrant.search(**search_args)

        if not result:
            logger.info(f"🔍 Nenhum resultado para '{q}'")
            return suggestions

        if q_length <= 2:
            min_score = 0.15
        elif q_length <= 4:
            min_score = 0.18
        elif q_length <= 6:
            min_score = 0.22
        else:
            min_score = 0.30

        scores = [p.score for p in result]

        if not is_result_relevant(scores, min_score):
            logger.info(f"🔕 Scores fracos (min {round(min(scores), 3)}, média {round(sum(scores)/len(scores), 3)}) — ignorando '{q}'")
            return suggestions

        seen = set()
        products = []
        for p in result:
            url = p.payload.get("url", "")
            if url in seen:
                continue
            seen.add(url)

            score = p.score
            logger.info(f"[similaridade] Score para '{p.payload.get('title', '')}': {score}")

            product_data = {
                "title": p.payload.get("title", ""),
                "price": p.payload.get("price", 0),
                "priceText": p.payload.get("priceText", "Indisponível"),
                "brand": p.payload.get("brand", ""),
                "category": p.payload.get("category", ""),
                "image": p.payload.get("image", ""),
                "url": p.payload.get("url", ""),
            }
            products.append(product_data)

            if not product_data["image"] and product_data["url"]:
                product_data["image"] = await extract_image_from_url(product_data["url"])

        suggestions["products"] = products
        suggestions["total"]["product"] = len(products)
        suggestions["suggestionsFound"] = bool(products)

        if redis_client and products:
            await redis_client.set(cache_key, json.dumps(suggestions), ex=300)
            await redis_client.set(f"autocomplete:typo_cache:{q.lower()}", q.lower(), ex=900)

    except Exception as e:
        logger.error(f"❌ Erro no autocomplete: {str(e)}", exc_info=True)
        return suggestions

    return suggestions
