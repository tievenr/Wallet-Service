from sqlalchemy import Column, Integer, String, DateTime, Boolean,Index
from sqlalchemy.sql import func
#TOD0 : Import base from app/database.py

class AssetType(Base):
    __tablename__ = "asset_types"
    id = Column(Integer, primary_key=True, autoincrement=True)
    
    # Internal name - e.g : "COIN", "GEM", "GOLD"
    code= Column(String(50), unique=True, nullable=False)
    
    # Display name - e.g : "Gold Coins"
    display_name = Column(String(100), nullable=False)
    is_active = Column(Boolean, nullable=False, server_default="1")
    
    created_at = Column(DateTime, server_default=func.now())
    updated_at = Column(DateTime, server_default=func.now(), onupdate=func.now())
    
    __table_args__ = (
        Index("idx_asset_types_active", "is_active"),
        {"mysql_engine": "InnoDB"},
    )