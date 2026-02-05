from fastapi import APIRouter
from app.api.v1 import health, wallets

api_router = APIRouter()

# Include all v1 routes
api_router.include_router(health.router, tags=["health"])
api_router.include_router(wallets.router, prefix="/wallets", tags=["wallets"])