from sqlalchemy.orm import Session
from app.models.wallet import Wallet
from typing import Optional

def get_wallet_by_id(db: Session, wallet_id: int) -> Optional[Wallet]:
    """Fetch a wallet by its ID."""
    return db.query(Wallet).filter(Wallet.id == wallet_id).first()

def get_wallet_by_user_and_asset(
    db: Session, 
    user_id: int, 
    asset_type_id: int
) -> Optional[Wallet]:
    """
    Find a user's wallet for a specific asset type.
    
    Example: Get Alice's COIN wallet
    """
    return db.query(Wallet).filter(Wallet.user_id==user_id,Wallet.asset_type_id==asset_type_id).first()

def create_wallet(
    db: Session,
    user_id: int,
    asset_type_id: int,
    is_system_wallet: bool = False,
    system_wallet_type: Optional[str] = None
) -> Wallet:
    """
    Create a new wallet for a user.
    
    Example: Create Alice's first GEM wallet
    """
    wallet = Wallet(
        user_id=user_id,
        asset_type_id=asset_type_id,
        is_system_wallet=is_system_wallet,
        system_wallet_type=system_wallet_type
        # balance defaults to 0 from the model
    )
    db.add(wallet)
    db.commit()
    db.refresh(wallet)
    return wallet

def get_wallet_with_lock(db: Session, wallet_id: int) -> Optional[Wallet]:
    """
    Fetch wallet and LOCK it for the current transaction.
    
    Uses SELECT ... FOR UPDATE to prevent concurrent modifications.
    The lock is held until db.commit() or db.rollback().
    """
    return db.query(Wallet).filter(Wallet.id == wallet_id).with_for_update().first()


def update_wallet_balance(
    db: Session,
    wallet_id: int,
    new_balance: float
) -> None:
    """
    Update a wallet's balance.
    
    NOTE: This assumes you already locked the wallet!
    Always call get_wallet_with_lock() first.
    
    Args:
        db: Database session
        wallet_id: ID of the wallet to update
        new_balance: New balance value
    """
    
    wallet = db.query(Wallet).filter(Wallet.id == wallet_id).first()
    if wallet:
        wallet.balance = new_balance

    
