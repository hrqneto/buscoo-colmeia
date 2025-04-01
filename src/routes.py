from fastapi import APIRouter, HTTPException, UploadFile, File, Depends, Query, BackgroundTasks
from weaviate.classes.query import Filter
from src.services.upload_service import process_and_index_csv
from src.services.search_service import search_products
from src.services.weaviate_client import create_weaviate_client
from src.services.autocomplete_service import get_autocomplete_suggestions
from src.utils.redis_client import redis_client

from uuid import uuid4

from src.config import PRODUCT_CLASS

router = APIRouter()

@router.post("/upload")
async def upload_csv(file: UploadFile = File(...), background_tasks: BackgroundTasks = BackgroundTasks()):
    upload_id = str(uuid4())
    file_path = f"temp_{upload_id}.csv"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    # passa só o caminho do arquivo pro background agora
    background_tasks.add_task(process_and_index_csv, file_path, upload_id)

    return {
        "upload_id": upload_id,
        "status": "processing",
        "message": "📦 Arquivo recebido. Processamento iniciado em background."
    }
    
@router.get("/upload-status/{upload_id}")
async def get_upload_status(upload_id: str):
    status = await redis_client.get(f"upload:{upload_id}:status")

    if status is None:
        raise HTTPException(status_code=404, detail="Upload ID não encontrado")

    if isinstance(status, bytes):
        status = status.decode()

    return {"upload_id": upload_id, "status": status}


@router.get("/search")
def search(query: str):
    """Endpoint para buscar produtos no Weaviate."""
    try:
        return search_products(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/autocomplete")
async def autocomplete(q: str = Query(..., alias="q")):
    return await get_autocomplete_suggestions(q)
    
@router.delete("/delete-all")
async def delete_all_products():
    """Remove todos os produtos indexados no Weaviate."""
    try:
        client = create_weaviate_client()
        collection = client.collections.get(PRODUCT_CLASS)

        print(f"🗑️ Tentando deletar todos os produtos da coleção: {PRODUCT_CLASS}")

        total_registros = collection.aggregate.over_all(total_count=True).total_count
        print(f"🔍 Registros encontrados antes da exclusão: {total_registros}")

        if total_registros == 0:
            print("⚠️ Nenhum produto encontrado para deletar.")
            return {"message": "Nenhum produto encontrado para deletar."}

        produtos = collection.query.fetch_objects(limit=total_registros)
        ids = [obj.uuid for obj in produtos.objects]

        if not ids:
            print("⚠️ Nenhum UUID encontrado para exclusão.")
            return {"message": "Nenhum produto encontrado para deletar."}

        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            collection.data.delete_many(where=Filter.by_id().contains_any(batch))
            print(f"✅ {len(batch)} produtos deletados...")

        total_restante = collection.aggregate.over_all(total_count=True).total_count
        print(f"✅ Registros restantes após exclusão: {total_restante}")

        deletados = total_registros - total_restante
        return {"message": f"Deletados {deletados} produtos com sucesso!"}

    except Exception as e:
        print(f"❌ Erro ao deletar os produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        client.close()
