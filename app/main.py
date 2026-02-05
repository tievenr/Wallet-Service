from fastapi import FastAPI
from app.config import settings
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from app.api.v1 import api_router
from app.middleware.error_handler import (
    validation_exception_handler,
    insufficient_funds_handler,
    wallet_not_found_handler,
    duplicate_transaction_handler,
    database_exception_handler,
    generic_exception_handler
)
from app.utils.exceptions import (
    InsufficientFundsError,
    WalletNotFoundError,
    DuplicateTransactionError
)

app = FastAPI(
    title=settings.PROJECT_NAME,
    openapi_url=f"{settings.API_V1_PREFIX}/openapi.json"
)

@app.get("/health")
def health_check():
    return {"status": "healthy"}

# Register exception handlers
app.add_exception_handler(RequestValidationError, validation_exception_handler)
app.add_exception_handler(InsufficientFundsError, insufficient_funds_handler)
app.add_exception_handler(WalletNotFoundError, wallet_not_found_handler)
app.add_exception_handler(DuplicateTransactionError, duplicate_transaction_handler)
app.add_exception_handler(SQLAlchemyError, database_exception_handler)
app.add_exception_handler(Exception, generic_exception_handler)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)