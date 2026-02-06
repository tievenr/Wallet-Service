from fastapi import Request, status
from fastapi.responses import JSONResponse
from fastapi.exceptions import RequestValidationError
from sqlalchemy.exc import SQLAlchemyError
from decimal import Decimal
from app.utils.exceptions import (
    InsufficientFundsError,
    WalletNotFoundError,
    DuplicateTransactionError
)
from decimal import Decimal

async def validation_exception_handler(request: Request, exc: RequestValidationError):
    """Handle Pydantic validation errors"""
    # Convert Decimal objects to strings for JSON serialization
    errors = exc.errors()
    for error in errors:
        if 'ctx' in error and isinstance(error['ctx'].get('gt'), Decimal):
            error['ctx']['gt'] = str(error['ctx']['gt'])
        if 'ctx' in error and isinstance(error['ctx'].get('lt'), Decimal):
            error['ctx']['lt'] = str(error['ctx']['lt'])
        if isinstance(error.get('input'), Decimal):
            error['input'] = str(error['input'])
    
    return JSONResponse(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        content={
            "error": "validation_error",
            "message": "Invalid request data",
            "details": errors
        }
    )

async def insufficient_funds_handler(request: Request, exc: InsufficientFundsError):
    """Handle insufficient funds errors"""
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "error": "insufficient_funds",
            "message": str(exc),
            "details": {}
        }
    )

async def wallet_not_found_handler(request: Request, exc: WalletNotFoundError):
    """Handle wallet not found errors"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={
            "error": "wallet_not_found",
            "message": str(exc),
            "details": {}
        }
    )

async def duplicate_transaction_handler(request: Request, exc: DuplicateTransactionError):
    """Handle duplicate transaction errors"""
    return JSONResponse(
        status_code=status.HTTP_409_CONFLICT,
        content={
            "error": "duplicate_transaction",
            "message": str(exc),
            "details": {}
        }
    )

async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    """Handle database errors"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "database_error",
            "message": "A database error occurred",
            "details": {}
        }
    )

async def generic_exception_handler(request: Request, exc: Exception):
    """Handle all other exceptions"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "internal_server_error",
            "message": "An unexpected error occurred",
            "details": {}
        }
    )