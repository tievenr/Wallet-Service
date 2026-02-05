from pydantic import BaseModel
from decimal import Decimal

class WalletBalanceResponse(BaseModel):
    user_id: int
    asset_type_id: int
    asset_type_code: str
    balance: Decimal
    
    class Config:
        from_attributes = True

class WalletResponse(BaseModel):
    id: int
    user_id: int
    asset_type_id: int
    balance: Decimal
    is_system_wallet: bool
    
    class Config:
        from_attributes = True