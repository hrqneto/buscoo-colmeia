#TODO modularizar as rotas  
from fastapi import APIRouter, HTTPException, UploadFile, File, Query, BackgroundTasks, Form, Depends
from src.indexing.services.upload_service import process_and_index_csv
from src.search.services.search_service import search_products
from src.search.services.autocomplete_service import get_autocomplete_suggestions, get_initial_autocomplete_suggestions
from src.infra.redis_client import redis_client
from qdrant_client import QdrantClient
from uuid import uuid4
import boto3
from src.indexing.services.feed_url_service import process_feed_url
from src.indexing.schemas.feed_schema import FeedURLRequest
import json
from src.middleware.auth_middleware import verify_token
from firebase_admin import firestore

from src.config import (
    QDRANT_URL, QDRANT_API_KEY, 
    R2_ACCESS_KEY, R2_SECRET_KEY, 
    R2_ENDPOINT_URL, R2_BUCKET_NAME, 
    PRODUCT_CLASS
)
from src.admin.routes.auth_routes import router_auth

router = APIRouter()
router.include_router(router_auth)

@router.post("/upload", summary="Upload de CSV com produtos", description="Recebe um arquivo CSV e inicia o processamento em segundo plano para indexar os produtos no Qdrant.")
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

@router.get("/upload-status/{upload_id}", summary="Status do upload", description="Retorna o status do processamento do upload baseado no ID fornecido.")
async def get_upload_status(upload_id: str):
    raw_status = await redis_client.get(f"upload:{upload_id}:status")

    if raw_status is None:
        raise HTTPException(status_code=404, detail="Upload ID não encontrado")

    if isinstance(raw_status, bytes):
        raw_status = raw_status.decode()

    try:
        parsed = json.loads(raw_status)
    except json.JSONDecodeError:
        parsed = {"status": raw_status, "step": "", "progress": 0}

    return parsed

@router.post("/upload/url", summary="Upload via URL", description="Recebe uma URL contendo o feed de produtos (CSV ou XML) e inicia o processamento remoto.")
async def subir_via_url(request: FeedURLRequest):
    return await process_feed_url(request.feed_url, request.client_id)

async def cancelar_upload(upload_id: str):
    key = f"upload:{upload_id}:status"
    data = {
        "status": "cancelled",
        "step": "🛑 Cancelado pelo usuário",
        "progress": 0,
        "log": [{"msg": "🛑 Cancelado pelo usuário", "progress": 0}]
    }
    await redis_client.set(key, json.dumps(data), ex=600)

@router.post("/upload-cancel/{upload_id}", summary="Cancelar upload", description="Cancela o processamento de um upload já iniciado com base no ID do upload.")
async def cancelar(upload_id: str):
    await cancelar_upload(upload_id)
    return {"status": "cancelled", "upload_id": upload_id}

@router.get("/search", summary="Busca textual simples", description="Realiza uma busca textual tradicional baseada na query informada (sem vetores).")
def search(query: str):
    try:
        return search_products(query)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete-all", summary="Resetar base de dados", description="Remove a coleção de produtos do Qdrant e limpa todas as imagens do bucket R2 da Cloudflare.")
async def delete_all_products():
    try:
        print("🔄 Iniciando processo de exclusão...")

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

@router.get("/autocomplete", summary="Sugestões de autocomplete", description="Fornece sugestões de produtos, marcas e categorias com base em uma query textual.")
async def autocomplete(
    q: str = Query(..., alias="q"),
    client_id: str = Query("default", alias="client_id")
):
    return await get_autocomplete_suggestions(q, client_id)

@router.get(
    "/autocomplete/suggestions",
    summary="Sugestões iniciais de autocomplete",
    description="Retorna sugestões populares de produtos, marcas, categorias e termos buscados antes mesmo do usuário digitar.",
    tags=["autocomplete"]
)
async def autocomplete_suggestions(
    client_id: str = Query("default", description="Identificador único do cliente")
):
    return await get_initial_autocomplete_suggestions(client_id)

@router.get("/widget/autocomplete-config")
async def get_autocomplete_config(client_id: str = Query(..., description="Identificador único do cliente")):
    db = firestore.client()
    config_doc = db.collection("configs").document(client_id).get()

    if not config_doc.exists:
        raise HTTPException(status_code=404, detail="Configuração não encontrada")

    autocomplete = config_doc.to_dict().get("autocomplete", {})
    is_enabled = autocomplete.get("is_enabled", False)

    return {
        "enabled": is_enabled,
        "published": autocomplete.get("published", {})
    }
    