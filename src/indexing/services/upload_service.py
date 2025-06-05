import os
import pandas as pd
from uuid import uuid4
from src.indexing.services.indexing import index_products
from src.infra.redis_client import redis_client
from src.indexing.schemas.product_schema import REQUIRED_FIELDS, detectar_e_mapear_colunas
import json

async def atualizar_status(upload_id: str, status: str, step: str, progress: int):
    key = f"upload:{upload_id}:status"

    # Recupera log anterior (se existir)
    old_data = await redis_client.get(key)
    log = []

    if old_data:
        try:
            old_json = json.loads(old_data)
            log = old_json.get("log", [])
        except:
            pass

    log.append({"msg": step, "progress": progress})

    # Atualiza status com log completo
    payload = {
        "status": status,
        "step": step,
        "progress": progress,
        "log": log
    }

    await redis_client.set(key, json.dumps(payload), ex=3600)
async def cancelar_upload(upload_id: str):
    key = f"upload:{upload_id}:status"
    data = {
        "status": "cancelled",
        "step": "🛑 Cancelado pelo usuário",
        "progress": 0,
        "log": [{"msg": "🛑 Cancelado pelo usuário", "progress": 0}]
    }
    await redis_client.set(key, json.dumps(data), ex=600)

async def process_and_index_csv(file_path: str, upload_id: str, client_id: str = "default"):
    print(f"\U0001f4c2 Começando processamento do CSV: {file_path} (upload_id={upload_id}, client_id={client_id})")

    file_path = f"temp_{upload_id}.csv"

    try:
        await atualizar_status(upload_id, "processing", "📂 Lendo arquivo CSV", 10)

        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
        df = None

        for encoding in encodings:
            try:
                df = pd.read_csv(file_path, encoding=encoding, on_bad_lines='skip', sep=',', engine='python')
                print(f"\U0001f4ca CSV lido com {len(df)} linhas e colunas: {list(df.columns)}")
                print("\U0001f9ea Primeira linha:")
                print(df.head(1).to_dict(orient="records")[0] if not df.empty else "CSV vazio")
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            await atualizar_status(upload_id, "failed", "❌ Falha ao decodificar o arquivo", 25)
            return {"error": "Falha ao decodificar o arquivo (encoding não reconhecido)"}

        if df.empty:
            await atualizar_status(upload_id, "failed", "❌ CSV está vazio", 40)
            return {"error": "CSV está vazio."}

        df, erro_mapeamento = detectar_e_mapear_colunas(df)
        if erro_mapeamento:
            await atualizar_status(upload_id, "failed", "❌ Erro no mapeamento de colunas", 50)
            return {"error": erro_mapeamento}

        if not all(col in df.columns for col in REQUIRED_FIELDS):
            faltando = [col for col in REQUIRED_FIELDS if col not in df.columns]
            msg = f"❌ Faltam colunas obrigatórias: {faltando}"
            await atualizar_status(upload_id, "failed", msg, 60)
            return {"error": msg}

        if 'price' in df.columns:
            df['price'] = pd.to_numeric(df['price'], errors='coerce').fillna(0)
        else:
            df['price'] = 0

        for col in ['description', 'brand', 'category']:
            if col in df.columns:
                df[col] = df[col].fillna('')
            else:
                df[col] = ''

        df = df[df['title'].notna() & (df['title'].str.strip() != '')]
        
        try:
            response = await index_products(df.to_dict(orient="records"), client_id=client_id)
        except Exception as e:
            await atualizar_status(upload_id, "failed", "❌ Erro durante indexação", 90)
            return {"error": str(e)}

        await atualizar_status(upload_id, "done", "✅ Finalizado com sucesso", 100)
        print(f"🟢 Upload {upload_id} marcado como DONE no Redis")

        return {
            "upload_id": upload_id,
            "message": "✅ Arquivo processado e indexado com sucesso!",
            "details": response,
            "stats": {
                "total_recebido": len(df),
                "total_indexado": response.get("adicionados", 0)
            }
        }

    except Exception as e:
        await atualizar_status(upload_id, "failed", "❌ Erro geral no processamento", 99)
        return {"upload_id": upload_id, "error": f"Erro interno: {str(e)}"}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)