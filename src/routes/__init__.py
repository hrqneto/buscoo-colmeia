from fastapi import APIRouter
from .main_routes import router as router_main
from .auth_routes import router_auth
from .protected_routes import router_protected

router = APIRouter()
router.include_router(router_main)            # Rotas públicas da aplicação
router.include_router(router_auth)            # Login (Firebase Sign In)
router.include_router(router_protected)       # Rotas protegidas por token JWT (como /api/users/me)
