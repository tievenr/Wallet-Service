from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from app.repositories import wallet_repo
from app.utils.exceptions import WalletNotFoundError
from app.models.wallet import Wallet
from typing import Optional

def get_wallet_balance(db: Session, user_id: int, asset_type_id: int) -> float:
    """
    Get the current balance for a specific asset.
    """
    wallet = wallet_repo.get_wallet_by_user_and_asset(db, user_id, asset_type_id)
    if not wallet:
        return 0.0
    return float(wallet.balance)

def get_or_create_wallet(
    db: Session, 
    user_id: int, 
    asset_type_id: int, 
    is_system: bool = False
) -> Wallet:
    """
    Fetch a wallet or create it if it doesn't exist.
    """
    wallet = wallet_repo.get_wallet_by_user_and_asset(db, user_id, asset_type_id)
    if wallet:
        return wallet

    # wallet not found -> create a new one by calling the method from repository
    try:
        return wallet_repo.create_wallet(
            db, 
            user_id=user_id, 
            asset_type_id=asset_type_id, 
            is_system_wallet=is_system
        )
    except IntegrityError:
        # 3. RACE CONDITION HIT! 
        """When two threads try to concurrently create wallets for example"""
        db.rollback() 
        return wallet_repo.get_wallet_by_user_and_asset(db, user_id, asset_type_id)