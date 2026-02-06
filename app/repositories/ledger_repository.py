from sqlalchemy.orm import Session
from app.models.ledger import LedgerEntry
from typing import List

def create_ledger_entry(
    db: Session,transaction_id: str,wallet_id: int,entry_type: str,amount: float,balance_before: float,balance_after: float,description: str = None
) -> LedgerEntry:
    """Create a ledger entry (DEBIT or CREDIT)."""
    ledger_entry=LedgerEntry(
        transaction_id=transaction_id,
        wallet_id=wallet_id,
        entry_type=entry_type,
        amount=amount,
        balance_before=balance_before,
        balance_after=balance_after,
        description=description
        )
    db.add(ledger_entry)
    db.flush()
    return ledger_entry

def get_entries_by_transaction(db: Session, transaction_id: str) -> List[LedgerEntry]:
    """Get all ledger entries for a transaction (should be 2: DEBIT + CREDIT)."""
    return db.query(LedgerEntry).filter(LedgerEntry.transaction_id==transaction_id).all()
    