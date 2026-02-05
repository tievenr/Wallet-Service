from sqlalchemy import (
    Column, Integer, String, DateTime, Boolean, Index, 
    BigInteger, Numeric, ForeignKey, CheckConstraint, UniqueConstraint
)
from sqlalchemy.sql import func
from app.database import Base 
from sqlalchemy.orm import relationship


class Wallet(Base):
    __tablename__="wallets"
    id = Column(BigInteger, primary_key=True, autoincrement=True)

    # user_id can be negative for system wallets
    user_id = Column(BigInteger,nullable=False,index=True)
    asset_type_id=Column(Integer,ForeignKey("asset_types.id"),nullable=False)

    balance = Column(Numeric(precision=20, scale=8), nullable=False, server_default="0.00000000")
    is_system_wallet = Column(Boolean, nullable=False, server_default="0")
    system_wallet_type = Column(String(50), nullable=True) 


    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    asset_type = relationship("AssetType", backref="wallets")

    # Constraints for data integrity
    __table_args__ = (
        # Prevent duplicate wallets for the same user/asset combo
        UniqueConstraint('user_id', 'asset_type_id', name='uq_user_asset'),
        
        # Safety rail: Balance can't be negative unless it's a system wallet
        CheckConstraint('balance >= 0 OR is_system_wallet = 1', name='chk_balance_not_negative'),
        
        # Index for fast system wallet lookups
        Index("idx_system_wallets", "is_system_wallet", "system_wallet_type"),
        
        {"mysql_engine": "InnoDB"},
    )