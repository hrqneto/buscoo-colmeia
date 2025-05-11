import httpx
import os

FIREBASE_API_KEY = os.getenv("FIREBASE_API_KEY")

async def firebase_login(email: str, password: str):
    url = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_API_KEY}"
    payload = {
        "email": email,
        "password": password,
        "returnSecureToken": True
    }

    async with httpx.AsyncClient() as client:
        response = await client.post(url, json=payload)

    if response.status_code != 200:
        raise Exception(response.json().get("error", {}).get("message", "Erro desconhecido"))

    return response.json()  # Contém idToken, refreshToken, localId...
