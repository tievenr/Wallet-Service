from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import wallet_service
from app.schemas.wallet import WalletBalanceResponse
from app.repositories import wallet_repo

router = APIRouter()

@router.get("/{user_id}/balance", response_model=WalletBalanceResponse)
def get_wallet_balance(
    user_id: int,
    asset_type_id: int = Query(..., description="Asset type ID"),
    db: Session = Depends(get_db)
):
    """
    Get wallet balance for a specific user and asset type.
    """
    wallet = wallet_repo.get_wallet_by_user_and_asset(db, user_id, asset_type_id)
    
    if not wallet:
        raise HTTPException(
            status_code=404,
            detail=f"Wallet not found for user {user_id} and asset_type {asset_type_id}"
        )
    
    # Get asset type code
    asset_type_code = wallet.asset_type.code if wallet.asset_type else "UNKNOWN"
    
    return WalletBalanceResponse(
        user_id=wallet.user_id,
        asset_type_id=wallet.asset_type_id,
        asset_type_code=asset_type_code,
        balance=wallet.balance
    )