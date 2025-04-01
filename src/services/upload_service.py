import os
import pandas as pd
from uuid import uuid4
from fastapi import UploadFile
from src.services.indexing import index_products
from src.utils.redis_client import redis_client


async def process_and_index_csv(file_path: str, upload_id: str):
    """Processa CSV, indexa produtos e salva status da operação no Redis."""
    file_path = f"temp_{upload_id}.csv"

    try:
        # 👉 Seta status inicial no Redis
        await redis_client.set(f"upload:{upload_id}:status", "processing", ex=3600)

        # 🔎 Tenta múltiplos encodings
        encodings = ['utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
        df = None
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    file_path,
                    encoding=encoding,
                    on_bad_lines='skip',
                    sep=',',
                    engine='python'
                )
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
            return {"error": "Falha ao decodificar o arquivo (encoding não reconhecido)"}

        # 🧠 Ajusta colunas
        if 'title' in df.columns and 'brand' in df.columns:
            pass  # formato ok
        elif '""' in df.columns:
            column_mapping = {
                'title': 'title',
                'brand': 'brand',
                'category': 'category',
                'images': 'image',
                'url': 'url',
                'selling_price': 'price',
                'description': 'description'
            }
            df = df.rename(columns=column_mapping)
            df = df[list(column_mapping.values())]

            if 'image' in df.columns:
                df['image'] = df['image'].apply(lambda x: x.split(',')[0] if isinstance(x, str) else '')
        else:
            await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
            return {"error": "Formato de CSV não reconhecido"}

        # 💸 Conversão de preço
        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        else:
            df['price'] = 0

        # 🧽 Preenche valores faltantes
        for col in ['description', 'brand', 'category']:
            if col in df.columns:
                df[col] = df[col].fillna('')
            else:
                df[col] = ''

        # 🧹 Remove produtos sem título
        df = df[df['title'].notna() & (df['title'].str.strip() != '')]

        # 🚀 Indexa
        response = await index_products(df.to_dict(orient="records"))

        # ✅ Status final
        await redis_client.set(f"upload:{upload_id}:status", "done", ex=3600)

        return {
            "upload_id": upload_id,
            "message": "Arquivo processado e indexado com sucesso!",
            "details": response,
            "stats": {
                "total_recebido": len(df),
                "total_indexado": response.get("adicionados", 0)
            }
        }

    except Exception as e:
        await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
        print(f"❌ Erro ao processar o CSV: {e}")
        return {"upload_id": upload_id, "error": f"Erro interno: {str(e)}"}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
