# src/routes/auth_routes.py ✅

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from src.admin.services.auth_service import firebase_login

router_auth = APIRouter()

class LoginRequest(BaseModel):
    email: str
    password: str

@router_auth.post("/auth/login")
async def login(request: LoginRequest):
    try:
        result = await firebase_login(request.email, request.password)
        return result
    except Exception as e:
        raise HTTPException(status_code=401, detail=str(e))
