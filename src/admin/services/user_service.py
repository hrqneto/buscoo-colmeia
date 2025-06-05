# src/services/user_service.py
from src.infra.firestore_client import db

def create_default_user_if_not_exists(user_data):
    doc_ref = db.collection("users").document(user_data["uid"])
    if not doc_ref.get().exists:
        doc_ref.set({
            "uid": user_data["uid"],
            "email": user_data.get("email"),
            "name": user_data.get("name", "Novo Usuário"),
            "company_name": "",
            "phone": "",
            "address": "",
            "photo_url": "",
            "client_id": user_data["uid"],  # cada usuário será dono da própria collection de produtos/configs
            "configs": {
                "layout": "grid",
                "placeholder": "Buscar produtos...",
            }
        })
