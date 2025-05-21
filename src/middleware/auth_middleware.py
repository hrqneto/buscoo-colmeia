# src/middleware/auth_middleware.py
from fastapi import Request, HTTPException, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from firebase_admin import firestore
from src.firebase.firebase_admin import firebase_auth

security = HTTPBearer()

async def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    token = credentials.credentials
    try:
        decoded_token = firebase_auth.verify_id_token(token)
        uid = decoded_token["uid"]

        # Consulta o Firestore para trazer mais dados
        db = firestore.client()
        user_doc = db.collection("users").document(uid).get()

        if user_doc.exists:
            decoded_token.update(user_doc.to_dict())

        return decoded_token
    except Exception as e:
        raise HTTPException(status_code=401, detail="Token inválido ou expirado")
