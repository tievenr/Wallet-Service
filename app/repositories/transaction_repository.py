from sqlalchemy.orm import Session
from app.models.transaction import Transaction
from typing import Optional
from datetime import datetime

def create_transaction(
    db: Session,
    transaction_id: str,
    idempotency_key: str,
    transaction_type: str,
    user_id: int,
    asset_type_id: int,
    amount: float,
    metadata: dict = None
) -> Transaction:
    """
    Create a new transaction record.
    
    Status defaults to PENDING.
    
    Args:
        db: Database session
        transaction_id: Unique transaction identifier
        idempotency_key: Unique key to prevent duplicates
        transaction_type: 'TOPUP', 'SPEND', or 'BONUS'
        user_id: User making the transaction
        asset_type_id: Asset being transacted
        amount: Transaction amount
        metadata: Optional additional data
    """
    transaction =Transaction(
        transaction_id=transaction_id,
        idempotency_key=idempotency_key,
        transaction_type=transaction_type,
        user_id=user_id,
        asset_type_id=asset_type_id,
        amount=amount,
        metadata=metadata
        )
    db.add(transaction)
    db.commit()
    db.refresh(transaction)
    return transaction


def get_by_idempotency_key(db: Session, idempotency_key: str) -> Optional[Transaction]:
    """
    Find a transaction by its idempotency key.
    """
    
    return db.query(Transaction).filter(Transaction.idempotency_key==idempotency_key).first()

def get_by_transaction_id(db: Session, transaction_id: str) -> Optional[Transaction]:
    """Fetch a transaction by its transaction_id."""
    return db.query(Transaction).filter(Transaction.transaction_id==transaction_id).first()


def update_transaction_status(
    db: Session,
    transaction_id: str,
    status: str,
    error_message: Optional[str] = None
) -> None:
    """
    Update transaction status to COMPLETED or FAILED.
    """
    transaction=get_by_transaction_id(db,transaction_id)
    if transaction:
        transaction.status=status
        if transaction.status=="COMPLETED":
            transaction.completed_at=datetime.now()
        if error_message:
            transaction.error_message=error_message
