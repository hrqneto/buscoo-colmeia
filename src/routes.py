from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks, Form
from src.services.upload_service import process_and_index_csv
from src.services.search_service import search_products
from src.services.autocomplete_service import get_autocomplete_suggestions
from src.utils.redis_client import redis_client
from qdrant_client import QdrantClient
from uuid import uuid4
from src.config import (
    QDRANT_URL, QDRANT_API_KEY, 
    R2_ACCESS_KEY, R2_SECRET_KEY, 
    R2_ENDPOINT_URL, R2_BUCKET_NAME, 
    PRODUCT_CLASS
)
import boto3

router = APIRouter()

@router.post("/upload")
async def upload_csv(background_tasks: BackgroundTasks, file: UploadFile = File(...), client_id: str = Form("default")):
    upload_id = str(uuid4())
    file_path = f"temp_{upload_id}.csv"

    with open(file_path, "wb") as f:
        f.write(await file.read())

    background_tasks.add_task(process_and_index_csv, file_path, upload_id, client_id)

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
    try:
        return search_products(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/autocomplete")
async def autocomplete(
    q: str = Query(..., alias="q"),
    client_id: str = Query("default", alias="client_id")
):
    return await get_autocomplete_suggestions(q, client_id)

@router.delete("/delete-all")
async def delete_all_products():
    """Deleta a coleção 'products' do Qdrant e limpa o bucket R2 da Cloudflare."""
    try:
        print("🔄 Iniciando processo de exclusão...")

        # 🧠 Qdrant
        qdrant = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY,
        )

        collections = qdrant.get_collections()
        collection_names = [c.name for c in collections.collections]

        if PRODUCT_CLASS in collection_names:
            print(f"🧨 Deletando a coleção '{PRODUCT_CLASS}' do Qdrant Cloud...")
            qdrant.delete_collection(collection_name=PRODUCT_CLASS)
            print("✅ Coleção deletada com sucesso.")
        else:
            print(f"⚠️ A coleção '{PRODUCT_CLASS}' não existe.")

        # 🧼 R2 Cloudflare
        print("🪣 Conectando ao bucket R2...")
        s3 = boto3.client(
            "s3",
            region_name="auto",
            endpoint_url=R2_ENDPOINT_URL,
            aws_access_key_id=R2_ACCESS_KEY,
            aws_secret_access_key=R2_SECRET_KEY,
        )

        response = s3.list_objects_v2(Bucket=R2_BUCKET_NAME)
        deleted_files = []

        if "Contents" in response:
            for obj in response["Contents"]:
                print(f"❌ Deletando: {obj['Key']}")
                s3.delete_object(Bucket=R2_BUCKET_NAME, Key=obj["Key"])
                deleted_files.append(obj["Key"])
            print("✅ Todos os objetos foram deletados do R2.")
        else:
            print("ℹ️ Bucket já estava vazio.")

        return {
            "message": f"Coleção '{PRODUCT_CLASS}' e imagens R2 deletadas com sucesso.",
            "qdrant_deleted": True,
            "images_deleted": deleted_files
        }

    except Exception as e:
        print(f"❌ Erro durante exclusão: {e}")
        raise HTTPException(status_code=500, detail=str(e))
