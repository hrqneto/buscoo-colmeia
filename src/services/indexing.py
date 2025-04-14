import os
from uuid import uuid4
import asyncio
from sentence_transformers import SentenceTransformer
from qdrant_client import QdrantClient, models
from qdrant_client.http.models import PointStruct, VectorParams, Distance
from src.services.autocomplete_service import extract_image_from_url
from src.services.image_service import processar_e_enviar_imagem, BUCKET_NAME
from ast import literal_eval
import csv
from src.services.validation_service import validar_produto
from typing import List, Dict, Tuple
from src.services.relatorio_service import salvar_relatorio_erros
import re
import pandas as pd
from src.schemas.product_schema import ALL_FIELDS
from src.services.normalizacao_service import normalizar_dataset
import ast
from src.utils.embedding_client import encode_text
from src.config import qdrant_client as client

# 🔧 Configurações carregadas do .env
QDRANT_URL = os.getenv("QDRANT_URL")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

model = SentenceTransformer("all-MiniLM-L6-v2")

def prepare_row(row: dict) -> dict:
    # 🧠 Tenta extrair categoria a partir do breadcrumb
    if not row.get("category") and row.get("breadcrumb"):
        try:
            breadcrumb = ast.literal_eval(row["breadcrumb"])
            if isinstance(breadcrumb, list) and breadcrumb:
                row["category"] = breadcrumb[-1].strip()
        except Exception:
            row["category"] = "Desconhecido"

    # 🧹 Pode adicionar mais normalizações aqui se quiser
    return row

def safe_parse_images(value):
    if isinstance(value, list):
        return value
    try:
        return ast.literal_eval(value)
    except Exception as e:
        print(f"Erro ao converter imagens: {value} -> {e}")
        return []
def smart_split(text):
    if pd.isna(text):
        return []
    
    # Se já tem separador, usa ele
    if any(sep in text for sep in [",", ".", "\n", ";"]):
        parts = re.split(r'[,\.\n;]+', text)
    else:
        # Usa regex que divide quando tem uma nova palavra com letra maiúscula
        parts = re.split(r'(?<=[a-z])(?=[A-Z])', text)
    
    return [p.strip() for p in parts if p.strip()]

# 🚀 Cria coleção no Qdrant (se ainda não existe)
def create_collection_if_not_exists(collection_name: str):
    collections = client.get_collections().collections
    if collection_name not in [c.name for c in collections]:
        print(f"🧠 Criando coleção '{collection_name}'...")
        client.create_collection(
            collection_name=collection_name,
            vectors_config=VectorParams(size=384, distance=Distance.COSINE)
        )
    else:
        print(f"📦 Coleção '{collection_name}' já existe.")  # ✅ agora usa o argumento certo


# 🔎 Cria índices de payload para filtro e visualização na UI do Qdrant
def create_payload_indexes(collection_name: str):
    index_fields = [
        ("client_id", models.PayloadSchemaType.KEYWORD),
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
        )),
        # 🧠 Indexando campos estruturados com texto tokenizado
        ("uses", models.TextIndexParams(
            type="text",
            tokenizer=models.TokenizerType.WORD,
            min_token_len=2,
            max_token_len=15,
            lowercase=True
        )),
        ("side_effects", models.TextIndexParams(
            type="text",
            tokenizer=models.TokenizerType.WORD,
            min_token_len=2,
            max_token_len=15,
            lowercase=True
        )),
        ("composition", models.TextIndexParams(
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
                collection_name=collection_name,
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

def check_dataset_schema(products: List[Dict[str, any]], required_fields: List[str] = None):
    if not products:
        print("⚠️ Nenhum produto encontrado no dataset.")
        return False

    if required_fields is None:
        required_fields = ["title", "brand", "category", "price", "url"]

    sample = products[0]
    print("🔍 Verificando schema do primeiro produto:")
    print(sample)

    missing_fields = [field for field in required_fields if field not in sample]
    if missing_fields:
        print(f"❌ Campos ausentes no dataset: {missing_fields}")
        return False

    print("✅ Todos os campos obrigatórios estão presentes.")
    return True

# 🔁 Função principal de indexação
async def index_products(products: List[Dict[str, any]], client_id: str = "default"):
    try:
        products = normalizar_dataset(products)
        collection_name = "store_global"

        if not check_dataset_schema(products):
            return {"error": "Dataset inválido. Faltam colunas obrigatórias."}
        print(f"📊 Quantidade total de produtos no CSV: {len(products)}")
        create_collection_if_not_exists(collection_name)
        create_payload_indexes(collection_name)
        print("\n🚀 Iniciando indexação...\n")
        await loading_animation()

        total_indexados = 0
        total_ignorados = 0
        batch_size = 1
        erros = []
        
        for i in range(0, len(products), batch_size):
            batch = products[i:i + batch_size]
            points: List[PointStruct] = []
            print(f"🔁 Processando batch {i} - {i + len(batch)}")

            for p in batch:
                p = prepare_row(p) 
                # 🧼 Preenche campos ausentes com valores padrão
                for col in ALL_FIELDS:
                    if col not in p:
                        p[col] = ""

                valido, motivo = validar_produto(p)
                print(f"➡️ Produto: {p.get('title', '[sem título]')}")
                
                if not valido:
                    erros.append({
                        "produto": p.get("title", ""),
                        "motivo": motivo,
                        "dados": p
                    })
                    total_ignorados += 1
                    continue

                obj_uuid = str(uuid4())
                description = str(p.get("description", "")).strip()
                brand = str(p.get("brand", "")).strip()
                category = str(p.get("category", "")).strip()

                images = safe_parse_images(p.get("images", []))
                print(f"✅ Lista final de imagens ({len(images)}): {images}")

                # 🧼 Filtra apenas URLs de imagem válidas
                valid_images = [img for img in images if isinstance(img, str) and img.startswith("http") and img.lower().endswith((".jpg", ".jpeg", ".png"))]

                if not valid_images:
                    print(f"⚠️ Nenhuma imagem válida para o produto: {p.get('title')}")
                    erros.append({
                        "produto": p.get("title", ""),
                        "motivo": "Nenhuma imagem válida encontrada",
                        "dados": p
                    })
                    total_ignorados += 1
                    continue

                url = valid_images[0]

                try:
                    url_final = await asyncio.wait_for(processar_e_enviar_imagem(url, obj_uuid), timeout=5)
                except asyncio.TimeoutError:
                    print(f"⏰ Timeout ao tentar baixar imagem: {url}")
                    url_final = "Erro - timeout"

                if url_final.startswith("Erro"):
                    erros.append({
                        "produto": p.get("title", ""),
                        "motivo": "Erro na imagem ou imagem pequena",
                        "dados": p
                    })
                    total_ignorados += 1
                    continue

                try:
                    price_str = str(p.get("price", "0")).replace("R$", "").replace("%", "").replace(",", ".").strip()
                    price = float(price_str)
                except Exception:
                    price = 0.0

                title = str(p.get("title", "")).strip()
                uses = smart_split(p.get("uses", ""))
                side_effects = smart_split(p.get("side_effects", ""))
                composition = smart_split(p.get("composition", ""))

                payload = {
                    "uuid": obj_uuid,
                    "client_id": client_id,  # 👈 aqui!
                    "title": title,
                    "description": description or "Sem descrição",
                    "brand": brand or "Desconhecida",
                    "category": category or "Sem categoria",
                    "image": url_final,
                    "url": url,
                    "price": price,
                    "priceText": f"{price} Kč" if price > 0 else "Indisponível",
                    "uses": uses,
                    "side_effects": side_effects,
                    "composition": composition,
                }

                text_to_vectorize = f"{title} {brand} {category} {' '.join(uses)} {' '.join(composition)}"
                try:
                    vector = await encode_text(text_to_vectorize)
                except Exception as e:
                    print(f"⚠️ Erro no microserviço de embedding, usando fallback local: {e}")
                    vector = model.encode(text_to_vectorize).tolist()

                points.append(PointStruct(id=obj_uuid, vector=vector, payload=payload))

            if points:
                client.upsert(collection_name=collection_name, points=points)
                total_indexados += len(points)
                print(f"✅ {len(points)} produtos indexados...")

        print(f"\n🚀 Final: {total_indexados} indexados, {total_ignorados} ignorados.")

        if erros:
            salvar_relatorio_erros(erros)
            print(f"📝 Relatório de erros salvo com {len(erros)} itens.")

        return {
            "message": "✅ CSV processado!",
            "adicionados": total_indexados,
            "ignorados": total_ignorados
        }
    except Exception as e:
        print(f"❌ Erro ao indexar produtos: {e}")
        return {"error": str(e)}
