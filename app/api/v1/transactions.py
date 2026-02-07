from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from app.database import get_db
from app.services import transaction_service
from app.schemas.transaction import TopupRequest, TransactionResponse,BonusRequest
from app.utils.exceptions import DuplicateTransactionError, InsufficientFundsError

router = APIRouter()

@router.post("/topup", response_model=TransactionResponse)
def topup(request: TopupRequest, db: Session = Depends(get_db)):
    """
    Process a TOPUP transaction.
    User purchases coins from the treasury.
    """
    try:
        transaction = transaction_service.process_topup(db, request)
        return transaction
    except DuplicateTransactionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")

@router.post("/bonus", response_model=TransactionResponse)
def bonus(request: BonusRequest, db: Session = Depends(get_db)):
    """
    Process a BONUS transaction.
    Marketing wallet grants bonus coins to a user.
    """
    try:
        transaction = transaction_service.process_bonus(db, request)
        return transaction
    except DuplicateTransactionError as e:
        raise HTTPException(status_code=409, detail=str(e))
    except InsufficientFundsError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Internal error: {str(e)}")