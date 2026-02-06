from pydantic import BaseModel, Field
from decimal import Decimal
from typing import Optional, Dict, Any
from datetime import datetime

class TopupRequest(BaseModel):
    idempotency_key: str = Field(..., min_length=1, max_length=100)
    user_id: int = Field(..., gt=0)
    asset_type: str = Field(..., min_length=1, max_length=50)
    amount: Decimal = Field(..., gt=0)
    metadata: Optional[Dict[str, Any]] = None

class TransactionResponse(BaseModel):
    transaction_id: str
    idempotency_key: str
    transaction_type: str
    user_id: int
    asset_type_id: int
    amount: Decimal
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None
    
    class Config:
        from_attributes = True