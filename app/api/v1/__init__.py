from fastapi import APIRouter
from . import health, wallets,transaction

api_router = APIRouter()

# Include all v1 routes
api_router.include_router(health.router, tags=["health"])
api_router.include_router(wallets.router, prefix="/wallets", tags=["wallets"])
api_router.include_router(transaction.router, prefix="/transactions", tags=["transactions"])