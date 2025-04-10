import os
import pandas as pd
from uuid import uuid4
from src.services.indexing import index_products
from src.utils.redis_client import redis_client
from src.schemas.product_schema import REQUIRED_FIELDS, detectar_e_mapear_colunas

async def process_and_index_csv(file_path: str, upload_id: str, client_id: str = "default"):
    print(f"📂 Começando processamento do CSV: {file_path} (upload_id={upload_id}, client_id={client_id})")

    file_path = f"temp_{upload_id}.csv"

    try:
        await redis_client.set(f"upload:{upload_id}:status", "processing", ex=3600)

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
            await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
            print("❌ Falha ao decodificar o arquivo.")
            return {"error": "Falha ao decodificar o arquivo (encoding não reconhecido)"}

        if df.empty:
            await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
            print("❌ CSV está vazio após leitura. Verifique a estrutura.")
            return {"error": "CSV está vazio."}

        # 🔍 Mapeia colunas
        df, erro_mapeamento = detectar_e_mapear_colunas(df)
        if erro_mapeamento:
            await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
            print(erro_mapeamento)
            return {"error": erro_mapeamento}

        # 🔽 Valida campos obrigatórios
        if not all(col in df.columns for col in REQUIRED_FIELDS):
            faltando = [col for col in REQUIRED_FIELDS if col not in df.columns]
            msg = f"❌ Faltam colunas obrigatórias: {faltando}"
            print(msg)
            await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
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
            await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
            print(f"❌ Erro durante indexação: {e}")
            return {"error": str(e)}

        await redis_client.set(f"upload:{upload_id}:status", "done", ex=3600)

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
        await redis_client.set(f"upload:{upload_id}:status", "failed", ex=3600)
        print(f"❌ Erro geral no processamento: {e}")
        return {"upload_id": upload_id, "error": f"Erro interno: {str(e)}"}

    finally:
        if os.path.exists(file_path):
            os.remove(file_path)
