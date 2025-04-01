import os
import uuid
import asyncio
from typing import List, Dict
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from src.services.autocomplete_service import extract_image_from_url

# 🔧 Configurações carregadas do .env
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
PRODUCT_CLASS = "products"

# ✅ Verifica se variáveis estão presentes
if not QDRANT_URL or not QDRANT_API_KEY:
    raise EnvironmentError("QDRANT_URL e QDRANT_API_KEY precisam estar definidos no .env")

# 🧠 Cliente Qdrant + modelo local
client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
model = SentenceTransformer("all-MiniLM-L6-v2")

# 🚀 Cria coleção no Qdrant (se ainda não existe)
def create_collection_if_not_exists():
    collections = client.get_collections().collections
    if PRODUCT_CLASS not in [c.name for c in collections]:
        print(f"🧠 Criando coleção '{PRODUCT_CLASS}'...")
        client.create_collection(
            collection_name=PRODUCT_CLASS,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
    else:
        print(f"📦 Coleção '{PRODUCT_CLASS}' já existe.")

# 🔎 Cria índices de payload para filtro e visualização na UI do Qdrant
def create_payload_indexes():
    index_fields = [
        ("title", models.PayloadSchemaType.KEYWORD),
        ("brand", models.PayloadSchemaType.KEYWORD),
        ("category", models.PayloadSchemaType.KEYWORD),
        ("price", models.PayloadSchemaType.FLOAT),
        ("uuid", models.PayloadSchemaType.UUID),
        ("description", models.TextIndexParams(
            type="text",
            tokenizer=models.TokenizerType.WORD,
            min_token_len=2,
            max_token_len=15,
            lowercase=True
        ))
    ]
    
    for field, field_type in index_fields:
        try:
            print(f"📌 Criando índice para '{field}'...")
            client.create_payload_index(
                collection_name=PRODUCT_CLASS,
                field_name=field,
                field_schema=field_type
            )
        except Exception as e:
            print(f"⚠️ Índice '{field}' não foi criado (talvez já exista): {e}")

# 🎞️ Animação só pra dar estilo
async def loading_animation():
    symbols = ["|", "/", "-", "\\"]
    for _ in range(10):
        for symbol in symbols:
            print(f"\r⏳ Indexando produtos... {symbol}", end="", flush=True)
            await asyncio.sleep(0.1)
    print("\r✅ Indexação concluída!\n")

# 🔁 Função principal de indexação
async def index_products(products: List[Dict[str, any]]):
    try:
        create_collection_if_not_exists()
        create_payload_indexes()
        print("\n🚀 Iniciando indexação...\n")
        await loading_animation()

        total_indexados = 0
        total_ignorados = 0
        batch_size = 50

        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            points: List[PointStruct] = []

            for p in batch:
                title = str(p.get("title", "")).strip()
                if not title:
                    print(f"⚠️ Produto ignorado: Sem título -> {p}")
                    total_ignorados += 1
                    continue

                obj_uuid = str(uuid.uuid4())
                description = str(p.get("description", "")).strip()
                brand = str(p.get("brand", "")).strip()
                category = str(p.get("category", "")).strip()
                image = str(p.get("image", "")).strip()
                url = str(p.get("url", "")).strip()
                if not image or not image.startswith("http"):
                    image = await extract_image_from_url(url)
                try:
                    price_str = str(p.get("price", "0")).replace("R$", "").replace("%", "").replace(",", ".").strip()
                    price = float(price_str)
                except Exception:
                    price = 0.0


                payload = {
                    "uuid": obj_uuid,
                    "title": title,
                    "description": description or "Sem descrição",
                    "brand": brand or "Desconhecida",
                    "category": category or "Sem categoria",
                    "image": image,
                    "url": url,
                    "price": price,
                    "priceText": f"{price} Kč" if price > 0 else "Indisponível"
                }

                # 🔍 Vetorização local
                text_to_vectorize = f"{title} {brand} {category}"
                vector = model.encode(text_to_vectorize).tolist()

                points.append(PointStruct(id=obj_uuid, vector=vector, payload=payload))

            if points:
                client.upsert(collection_name=PRODUCT_CLASS, points=points)
                total_indexados += len(points)
                print(f"✅ {len(points)} produtos indexados...")

        print(f"\n🚀 Final: {total_indexados} indexados, {total_ignorados} ignorados.")
        return {
            "message": "✅ CSV processado!",
            "adicionados": total_indexados,
            "ignorados": total_ignorados
        }

    except Exception as e:
        print(f"❌ Erro ao indexar produtos: {e}")
        return {"error": str(e)}
