import os
import firebase_admin
from firebase_admin import credentials, auth

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CREDENTIAL_PATH = os.path.join(BASE_DIR, "secrets", "firebase-admin.json")

print(f"🔐 Carregando credencial Firebase de: {CREDENTIAL_PATH}")

if not os.path.exists(CREDENTIAL_PATH):
    raise FileNotFoundError(f"❌ Firebase credential not found at {CREDENTIAL_PATH}")

if not firebase_admin._apps:
    cred = credentials.Certificate(CREDENTIAL_PATH)
    firebase_admin.initialize_app(cred)

firebase_auth = auth
