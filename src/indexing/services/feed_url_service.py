import httpx
import tempfile
from uuid import uuid4
from src.indexing.services.upload_service import process_and_index_csv

async def process_feed_url(feed_url: str, client_id: str = "default"):
    try:
        print(f"🌐 Baixando feed: {feed_url}")
        response = await httpx.AsyncClient().get(feed_url, timeout=15)
        response.raise_for_status()

        # Salva em arquivo temporário
        with tempfile.NamedTemporaryFile(delete=False, suffix=".csv", mode="wb") as tmp:
            tmp.write(response.content)
            temp_path = tmp.name

        # Usa a função de upload já existente
        upload_id = str(uuid4())
        return await process_and_index_csv(temp_path, upload_id=upload_id, client_id=client_id)

    except Exception as e:
        print(f"❌ Erro ao baixar ou processar feed: {e}")
        return {"error": str(e)}
