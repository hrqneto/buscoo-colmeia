# src/routes/protected_routes.py
from fastapi import APIRouter, HTTPException, Depends
from src.middleware.auth_middleware import verify_token
from firebase_admin import firestore
from src.middleware.auth_middleware import verify_token
from qdrant_client import QdrantClient

router_protected = APIRouter()

from src.config import (
    QDRANT_URL, QDRANT_API_KEY
)

@router_protected.get(
    "/users/me",
    summary="Perfil do usuário autenticado",
    description="Retorna os dados básicos do usuário autenticado, extraídos do token de autenticação do Firebase."
)
async def get_profile(user=Depends(verify_token)):
    return {
        "uid": user["uid"],
        "email": user.get("email"),
        "name": user.get("name", "Usuário BuscaFlex"),
        "company_name": user.get("company_name", "Minha Empresa"),
        "phone": user.get("phone", ""),
        "address": user.get("address", ""),
        "photo_url": user.get("photo_url", "")
    }

@router_protected.get(
    "/admin/configs",
    summary="Buscar configurações do painel admin",
    description="Consulta as configurações salvas no Firestore vinculadas ao clientId do usuário autenticado."
)
async def get_admin_configs(user=Depends(verify_token)):
    db = firestore.client()

    uid = user["uid"]
    user_doc = db.collection("users").document(uid).get()

    if not user_doc.exists:
        return {"error": "Usuário não encontrado"}

    client_id = user_doc.to_dict().get("clientId")
    config_doc = db.collection("configs").document(client_id).get()

    if not config_doc.exists:
        return {"error": "Configuração não encontrada"}

    return config_doc.to_dict()

@router_protected.post(
    "/admin/save-configs",
    summary="Salvar configurações do admin",
    description="Permite ao usuário autenticado salvar ou atualizar suas configurações personalizadas no Firestore, vinculadas ao seu clientId."
)
async def save_admin_configs(payload: dict, user=Depends(verify_token)):
    db = firestore.client()

    uid = user["uid"]
    user_doc = db.collection("users").document(uid).get()

    if not user_doc.exists:
        return {"error": "Usuário não encontrado"}

    client_id = user_doc.to_dict().get("clientId")
    db.collection("configs").document(client_id).set(payload, merge=True)

    return {"status": "Configuração salva com sucesso"}

@router_protected.get(
    "/superadmin/collections",
    summary="Listar todas as collections no Qdrant",
    description="Endpoint restrito a superadmins para visualizar todas as coleções disponíveis no cluster Qdrant atual."
)
async def listar_collections(user=Depends(verify_token)):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Acesso negado — esta operação é restrita a superadministradores.")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    collections = client.get_collections()
    return collections.model_dump()

@router_protected.get(
    "/superadmin/collection-names",
    summary="Listar nomes de collections",
    description="Retorna apenas os nomes das collections disponíveis no cluster Qdrant. Útil para seleção em painéis administrativos."
)
async def listar_nomes_collections(user=Depends(verify_token)):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Acesso negado — esta operação é restrita a superadministradores.")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    collections = client.get_collections()
    return [c.name for c in collections.collections]

@router_protected.get(
    "/superadmin/collection-info/{collection_name}",
    summary="Detalhes de uma collection específica",
    description="Retorna informações técnicas de uma única collection: tamanho, vetores, payloads, configurações e status."
)
async def detalhes_collection(collection_name: str, user=Depends(verify_token)):
    if user.get("role") != "superadmin":
        raise HTTPException(status_code=403, detail="Acesso negado — esta operação é restrita a superadministradores.")

    client = QdrantClient(url=QDRANT_URL, api_key=QDRANT_API_KEY)
    info = client.get_collection(collection_name=collection_name)
    return info.model_dump()
