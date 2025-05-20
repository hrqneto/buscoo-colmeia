from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
import httpx
import os
from firebase_admin import firestore
from src.middleware.auth_middleware import verify_token

router_auth = APIRouter()
FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

class LoginRequest(BaseModel):
    email: str
    password: str

@router_auth.post(
    "/auth/login",
    summary="Login com Firebase",
    description="Autentica o usuário utilizando email e senha via Firebase Authentication. Retorna o token de acesso e dados do usuário."
)
async def login(request: LoginRequest):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": request.email,
        "password": request.password,
        "returnSecureToken": True
    }
    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)
    if response.status_code != 200:
        raise HTTPException(status_code=401, detail="Credenciais inválidas")
    return response.json()