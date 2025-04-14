import os
import pandas as pd
from uuid import uuid4
from src.services.indexing import index_products
from src.utils.redis_client import redis_client
from src.schemas.product_schema import REQUIRED_FIELDS, detectar_e_mapear_colunas
import json

async def atualizar_status(upload_id: str, status: str, step: str, progress: int):
    key = f"upload:{upload_id}:status"

    # pega o valor anterior
    raw = await redis_client.get(key)
    if raw:
        data = json.loads(raw)
        logs = data.get("log", [])
    else:
        logs = []

    logs.append({"msg": step, "progress": progress})

    await redis_client.set(
        key,
        json.dumps({
            "status": status,
            "step": step,
            "progress": progress,
            "log": logs,
        }),
        ex=3600
    )

async def process_and_index_csv(file_path: str, upload_id: str, client_id: str = "default"):
    print(f"📂 Começando processamento do CSV: {file_path} (upload_id={upload_id}, client_id={client_id})")

    file_path = f"temp_{upload_id}.csv"

    try:
        await atualizar_status(upload_id, "processing", "📂 Lendo arquivo CSV", 10)

        # 🔎 Tenta múltiplos encodings
        encodings = ['utf-8-sig', 'utf-8', 'latin-1', 'iso-8859-1', 'windows-1252']
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
                print(f"📊 CSV lido com {len(df)} linhas e colunas: {list(df.columns)}")
                print("🧪 Primeira linha:")
                print(df.head(1).to_dict(orient="records")[0] if not df.empty else "CSV vazio")
                break
            except UnicodeDecodeError:
                continue

        if df is None:
            await atualizar_status(upload_id, "processing", "🔍 Mapeando colunas", 25)
            print("❌ Falha ao decodificar o arquivo.")
            return {"error": "Falha ao decodificar o arquivo (encoding não reconhecido)"}

        if df.empty:
            await atualizar_status(upload_id, "processing", "✅ Validando campos", 40)
            print("❌ CSV está vazio após leitura. Verifique a estrutura.")
            return {"error": "CSV está vazio."}

        # 🔍 Mapeia colunas
        df, erro_mapeamento = detectar_e_mapear_colunas(df)
        if erro_mapeamento:
            await atualizar_status(upload_id, "processing", "📂 Lendo arquivo CSV", 10)
    
            print(erro_mapeamento)
            return {"error": erro_mapeamento}

        # 🔽 Valida campos obrigatórios
        if not all(col in df.columns for col in REQUIRED_FIELDS):
            faltando = [col for col in REQUIRED_FIELDS if col not in df.columns]
            msg = f"❌ Faltam colunas obrigatórias: {faltando}"
            print(msg)
            await atualizar_status(upload_id, "processing", "📂 Lendo arquivo CSV", 10)
            return {"error": msg}

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

        # 🚀 Indexa com client_id certo
        try:
            response = await index_products(df.to_dict(orient="records"), client_id=client_id)
        except Exception as e:
            await atualizar_status(upload_id, "processing", "📂 Lendo arquivo CSV", 10)
            print(f"❌ Erro durante indexação: {e}")
            return {"error": str(e)}

        await atualizar_status(upload_id, "processing", "📂 Lendo arquivo CSV", 10)

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
        await atualizar_status(upload_id, "processing", "📂 Lendo arquivo CSV", 10)
        print(f"❌ Erro geral no processamento: {e}")
        return {"upload_id": upload_id, "error": f"Erro interno: {str(e)}"}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
