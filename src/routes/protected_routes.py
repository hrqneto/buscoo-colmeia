# src/routes/protected_routes.py
from fastapi import APIRouter, Depends
from src.middleware.auth_middleware import verify_token
from firebase_admin import firestore

router_protected = APIRouter()


@router_protected.get("/users/me")
async def get_profile(user=Depends(verify_token)):
    return {
        "uid": user["uid"],
        "email": user.get("email")
    }


@router_protected.get("/admin/configs")
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


@router_protected.post("/admin/save-configs")
async def save_admin_configs(payload: dict, user=Depends(verify_token)):
    db = firestore.client()

    uid = user["uid"]
    user_doc = db.collection("users").document(uid).get()

    if not user_doc.exists:
        return {"error": "Usuário não encontrado"}

    client_id = user_doc.to_dict().get("clientId")
    db.collection("configs").document(client_id).set(payload, merge=True)

    return {"status": "Configuração salva com sucesso"}
