import json
import math
import logging
from fastapi import HTTPException
from src.utils.embedding_client import encode_text
from src.utils.redis_client import redis_client
from src.services.qdrant_client import qdrant
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
        
        # TODO: Atualizar para o novo cliente AsyncQdrantClient com SearchRequest
        # Substituir qdrant.search(**search_args) por:
        # await qdrant.search("products", SearchRequest(...))
        # Requer migrar para qdrant-client 1.6+ com modelos http.models (assíncronos)
        # ⚠️ Manter como está por ora — estável e funcional com a versão atual.

        search_args = {
            "collection_name": f"store_{client_id}",
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


        scores = [p.score for p in result]

    #     allow_one_high = q_length <= 4  # ⚠️ afrouxa pra prefixos curtos
    #   if not is_result_relevant(scores, min_score, allow_one_high=allow_one_high):
    #   logger.info(f"🔕 Scores fracos (min {round(min(scores), 3)}, média {round(sum(scores)/len(scores), 3)}) — ignorando '{q}'")
    #   return suggestions

        seen = set()
        raw_products = []
        seen_titles = set()
        for p in result:
            url = p.payload.get("url", "")
            if url in seen:
                continue
            seen.add(url)
            
            title = p.payload.get("title", "")
            if title in seen_titles:
                continue
            seen_titles.add(title)

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

            raw_products.append(product_data)

        # 👇 Carrega imagens em paralelo
        products = await asyncio.gather(*[fix_product_image(p) for p in raw_products])

        # 👇 Gera listas únicas de categorias e marcas
        categories = list({p["category"] for p in products if p["category"]})
        brands = list({p["brand"] for p in products if p["brand"]})

        # 👇 Adiciona no JSON final
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

    #TODO 3. Adicionar um limit/delay para scraping de imagem
    #Quando o scraping for necessário, podemos fazer algo simples 
    #await asyncio.sleep(0.1)  # delay de 100ms entre requests
    #Coloca isso dentro da função extract_image_from_url, antes de chamar async_client.get():
    #response = await async_client.get(url, headers=headers)
