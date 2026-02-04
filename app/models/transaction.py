from sqlalchemy import (
    Column, Integer, String, DateTime, Numeric, 
    BigInteger, ForeignKey, Index, Text, JSON,CheckConstraint
)
from sqlalchemy.sql import func

from app.database import Base 

class Transaction(Base):
    __tablename__ = "transactions"
    
    id = Column(BigInteger, primary_key=True, autoincrement=True)
    transaction_id = Column(String(100), unique=True, nullable=False, index=True) 
    idempotency_key = Column(String(100), unique=True, nullable=False, index=True)
    
    # Standardize types: 'TOPUP', 'SPEND', 'BONUS'
    transaction_type = Column(String(50), nullable=False, index=True) 

    user_id = Column(BigInteger, nullable=False, index=True) #This is the dude doing the transaction
    asset_type_id = Column(Integer, ForeignKey("asset_types.id"), nullable=False, index=True)#Currency the trade is mediated through

    amount = Column(Numeric(precision=20, scale=8), nullable=False)
    
    # Status: PENDING, COMPLETED, FAILED
    status = Column(String(50), nullable=False, server_default="PENDING", index=True) 

    #More info regarding the transaction
    transaction_metadata = Column(JSON, nullable=True)

    # Error message if status is 'FAILED'
    error_message = Column(Text, nullable=True)

    # Audit for transactions
    created_at = Column(DateTime, server_default=func.now(), index=True)
    completed_at = Column(DateTime, nullable=True)
    
    

    __table_args__ = (
        CheckConstraint("status IN ('PENDING', 'COMPLETED', 'FAILED')", name='chk_status_valid'),
        Index("idx_user_asset_status", "user_id", "asset_type_id", "status"),
        {"mysql_engine": "InnoDB"},
    )