from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, 
    BigInteger, ForeignKey, Index, Text, CheckConstraint
)
from sqlalchemy.sql import func
from app.database import Base 

class LedgerEntry(Base):
    __tablename__ = "ledger_entries"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id = Column(String(100), ForeignKey("transactions.transaction_id"), nullable=False, index=True)
    
    wallet_id = Column(BigInteger, ForeignKey("wallets.id"), nullable=False, index=True)

    entry_type = Column(String(50), nullable=False) # 'DEBIT' or 'CREDIT'
    
    #Amount in transaction
    amount = Column(Numeric(precision=20, scale=8), nullable=False)
    
    balance_before = Column(Numeric(precision=20, scale=8), nullable=False)
    balance_after = Column(Numeric(precision=20, scale=8), nullable=False)

    description = Column(String(255), nullable=True)
    created_at = Column(DateTime, server_default=func.now(), index=True)

    __table_args__ = (
        CheckConstraint("entry_type IN ('DEBIT', 'CREDIT')", name='chk_entry_type_valid'),
        Index("idx_ledger_trans_wallet","transaction_id", "wallet_id", "created_at"),
        {"mysql_engine": "InnoDB"},
    )