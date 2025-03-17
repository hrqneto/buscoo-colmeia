from fastapi import APIRouter, HTTPException, UploadFile, File
from weaviate.classes.query import Filter
from src.services.upload_service import process_and_index_csv
from src.services.search_service import search_products
from src.services.weaviate_client import create_weaviate_client
from src.config import PRODUCT_CLASS

router = APIRouter()

@router.post("/upload-csv")
async def upload_csv(file: UploadFile = File(...)):
    """Endpoint para receber e processar um CSV e indexá-lo no Weaviate."""
    try:
        response = await process_and_index_csv(file)
        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/search")
def search(query: str):
    """Endpoint para buscar produtos no Weaviate."""
    try:
        return search_products(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


#TODO organizar servico CRUD
@router.delete("/delete-all")
async def delete_all_products():
    """Remove todos os produtos indexados no Weaviate."""
    try:
        client = create_weaviate_client()
        collection = client.collections.get(PRODUCT_CLASS)

        print(f"🗑️ Tentando deletar todos os produtos da coleção: {PRODUCT_CLASS}")

        # 🚀 Pegar o número de registros antes de deletar
        total_registros = collection.aggregate.over_all(total_count=True).total_count
        print(f"🔍 Registros encontrados antes da exclusão: {total_registros}")

        if total_registros == 0:
            print("⚠️ Nenhum produto encontrado para deletar.")
            return {"message": "Nenhum produto encontrado para deletar."}

        # 🔥 Buscando os UUIDs de todos os produtos
        produtos = collection.query.fetch_objects(limit=total_registros)
        ids = [obj.uuid for obj in produtos.objects]

        if not ids:
            print("⚠️ Nenhum UUID encontrado para exclusão.")
            return {"message": "Nenhum produto encontrado para deletar."}

        # 🗑️ Deletar produtos por ID em lotes
        batch_size = 100
        for i in range(0, len(ids), batch_size):
            batch = ids[i:i + batch_size]
            collection.data.delete_many(where=Filter.by_id().contains_any(batch))
            print(f"✅ {len(batch)} produtos deletados...")

        # 🚀 Pegar o número de registros após a exclusão
        total_restante = collection.aggregate.over_all(total_count=True).total_count
        print(f"✅ Registros restantes após exclusão: {total_restante}")

        deletados = total_registros - total_restante
        return {"message": f"Deletados {deletados} produtos com sucesso!"}

    except Exception as e:
        print(f"❌ Erro ao deletar os produtos: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        client.close()
