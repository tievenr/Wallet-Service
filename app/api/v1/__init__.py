from fastapi import APIRouter
from . import health, wallets, transactions

api_router = APIRouter()

api_router.include_router(health.router, tags=["health"])
api_router.include_router(wallets.router, prefix="/wallets", tags=["wallets"])
api_router.include_router(transactions.router, prefix="/transactions", tags=["transactions"])