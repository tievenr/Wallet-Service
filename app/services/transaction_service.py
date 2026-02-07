from sqlalchemy.orm import Session
from sqlalchemy.exc import IntegrityError
from decimal import Decimal
from datetime import datetime
import uuid

from app.models.transaction import Transaction
from app.models.wallet import Wallet
from app.models.asset_types import AssetType
from app.repositories import wallet_repo, transaction_repo, ledger_repo
from app.utils.exceptions import InsufficientFundsError, DuplicateTransactionError
from app.utils.constants import SYSTEM_USER_IDS
from app.schemas.transaction import TopupRequest,BonusRequest, SpendRequest



def process_topup(db: Session, request: TopupRequest) -> Transaction:
    """
    Process a TOPUP transaction (user purchases coins).
    Money flows: Treasury -> User
    """
    try:
        # Step 1:Check idempotency
        existing = transaction_repo.get_by_idempotency_key(db, request.idempotency_key)
        if existing:
            return existing
        
        # Step 2: Get asset type
        asset_type = db.query(AssetType).filter(AssetType.code == request.asset_type).first()
        if not asset_type:
            raise ValueError(f"Asset type {request.asset_type} not found")
        
        # Step 3: Lock wallets in order (ascending wallet_id to prevent deadlocks)
        treasury_wallet = wallet_repo.get_wallet_with_lock(db, SYSTEM_USER_IDS["TREASURY"], asset_type.id)
        user_wallet = wallet_repo.get_wallet_with_lock(db, request.user_id, asset_type.id)
        
        if not treasury_wallet:
            raise ValueError(f"Treasury wallet not found for asset {request.asset_type}")
        
        # Create user wallet if doesn't exist
        if not user_wallet:
            user_wallet = wallet_repo.create_wallet(db, request.user_id, asset_type.id)
            db.flush()  # Get the wallet ID
            # Re-lock the newly created wallet
            user_wallet = wallet_repo.get_wallet_with_lock(db, request.user_id, asset_type.id)
        
        # Step 4: Create transaction record (PENDING)
        transaction_id = str(uuid.uuid4())
        transaction = transaction_repo.create_transaction(
            db=db,
            transaction_id=transaction_id,
            idempotency_key=request.idempotency_key,
            transaction_type="TOPUP",
            user_id=request.user_id,
            asset_type_id=asset_type.id,
            amount=request.amount,
            metadata=request.metadata
        )
        db.flush()
        
        # Step 5: Update balances
        treasury_balance_before = treasury_wallet.balance
        user_balance_before = user_wallet.balance
        
        # Calculate new balances
        treasury_balance_after = treasury_balance_before - request.amount
        user_balance_after = user_balance_before + request.amount
        
        # Update wallet balances
        wallet_repo.update_wallet_balance(db, treasury_wallet, treasury_balance_after)
        wallet_repo.update_wallet_balance(db, user_wallet, user_balance_after)
        
        # Step 6: Create ledger entries (double-entry)
        # Debit from treasury (negative amount)
        ledger_repo.create_ledger_entry(
            db=db,
            transaction_id=transaction_id,
            wallet_id=treasury_wallet.id,
            entry_type="DEBIT",
            amount=-request.amount,
            balance_before=treasury_balance_before,
            balance_after=treasury_balance_after,
            description=f"User {request.user_id} purchased {request.amount} {request.asset_type}"
        )
        
        # Credit to user
        ledger_repo.create_ledger_entry(
            db=db,
            transaction_id=transaction_id,
            wallet_id=user_wallet.id,
            entry_type="CREDIT",
            amount=request.amount,
            balance_before=user_balance_before,
            balance_after=user_balance_after,
            description=f"Purchased {request.amount} {request.asset_type}"
        )
        
        # Step 7: Mark transaction as completed
        transaction_repo.update_transaction_status(
            db=db,
            transaction_id=transaction_id,
            status="COMPLETED"
        )
        
        # Step 8: Commit
        db.commit()
        db.refresh(transaction)
        
        return transaction
        
    except IntegrityError as e:
        db.rollback()
        # Check if it's duplicate idempotency key
        existing = transaction_repo.get_by_idempotency_key(db, request.idempotency_key)
        if existing:
            return existing
        raise DuplicateTransactionError(f"Transaction with key {request.idempotency_key} already exists")
    
    except Exception as e:
        db.rollback()
        # Try to mark transaction as failed if it was created
        try:
            transaction_repo.update_transaction_status(
                db=db,
                transaction_id=transaction_id if 'transaction_id' in locals() else None,
                status="FAILED",
                error_message=str(e)
            )
            db.commit()
        except:
            pass
        raise



def process_bonus(db: Session, request: BonusRequest) -> Transaction:
    """
    Process a BONUS transaction (marketing gives bonus coins).
    Money flows: Marketing -> User
    """
    try:
        # Step 1: Check idempotency
        existing = transaction_repo.get_by_idempotency_key(db, request.idempotency_key)
        if existing:
            return existing
        
        # Step 2: Get asset type
        asset_type = db.query(AssetType).filter(AssetType.code == request.asset_type).first()
        if not asset_type:
            raise ValueError(f"Asset type {request.asset_type} not found")
        
        # Step 3: Lock wallets in order (ascending wallet_id to prevent deadlocks)
        marketing_wallet = wallet_repo.get_wallet_with_lock(db, SYSTEM_USER_IDS["MARKETING"], asset_type.id)
        user_wallet = wallet_repo.get_wallet_with_lock(db, request.user_id, asset_type.id)
        
        if not marketing_wallet:
            raise ValueError(f"Marketing wallet not found for asset {request.asset_type}")
        
        # Create user wallet if doesn't exist
        if not user_wallet:
            user_wallet = wallet_repo.create_wallet(db, request.user_id, asset_type.id)
            db.flush()  # Get the wallet ID
            # Re-lock the newly created wallet
            user_wallet = wallet_repo.get_wallet_with_lock(db, request.user_id, asset_type.id)
        
        # Step 4: Validate marketing wallet has sufficient funds
        if marketing_wallet.balance < request.amount:
            raise InsufficientFundsError(
                f"Marketing wallet has insufficient funds. Balance: {marketing_wallet.balance}, Required: {request.amount}"
            )
        
        # Step 5: Create transaction record (PENDING)
        transaction_id = str(uuid.uuid4())
        transaction = transaction_repo.create_transaction(
            db=db,
            transaction_id=transaction_id,
            idempotency_key=request.idempotency_key,
            transaction_type="BONUS",
            user_id=request.user_id,
            asset_type_id=asset_type.id,
            amount=request.amount,
            metadata=request.metadata
        )
        db.flush()
        
        # Step 6: Update balances
        marketing_balance_before = marketing_wallet.balance
        user_balance_before = user_wallet.balance
        
        # Calculate new balances
        marketing_balance_after = marketing_balance_before - request.amount
        user_balance_after = user_balance_before + request.amount
        
        # Update wallet balances
        wallet_repo.update_wallet_balance(db, marketing_wallet, marketing_balance_after)
        wallet_repo.update_wallet_balance(db, user_wallet, user_balance_after)
        
        # Step 7: Create ledger entries (double-entry)
        # Debit from marketing (negative amount)
        ledger_repo.create_ledger_entry(
            db=db,
            transaction_id=transaction_id,
            wallet_id=marketing_wallet.id,
            entry_type="DEBIT",
            amount=-request.amount,
            balance_before=marketing_balance_before,
            balance_after=marketing_balance_after,
            description=f"Bonus granted to user {request.user_id}"
        )
        
        # Credit to user
        ledger_repo.create_ledger_entry(
            db=db,
            transaction_id=transaction_id,
            wallet_id=user_wallet.id,
            entry_type="CREDIT",
            amount=request.amount,
            balance_before=user_balance_before,
            balance_after=user_balance_after,
            description=f"Received {request.amount} {request.asset_type} bonus"
        )
        
        # Step 8: Mark transaction as completed
        transaction_repo.update_transaction_status(
            db=db,
            transaction_id=transaction_id,
            status="COMPLETED"
        )
        
        # Step 9: Commit
        db.commit()
        db.refresh(transaction)
        
        return transaction
        
    except IntegrityError as e:
        db.rollback()
        # Check if it's duplicate idempotency key
        existing = transaction_repo.get_by_idempotency_key(db, request.idempotency_key)
        if existing:
            return existing
        raise DuplicateTransactionError(f"Transaction with key {request.idempotency_key} already exists")
    
    except Exception as e:
        db.rollback()
        # Try to mark transaction as failed if it was created
        try:
            transaction_repo.update_transaction_status(
                db=db,
                transaction_id=transaction_id if 'transaction_id' in locals() else None,
                status="FAILED",
                error_message=str(e)
            )
            db.commit()
        except:
            pass
        raise



def process_spend(db: Session, request: SpendRequest) -> Transaction:
    """
    Process a SPEND transaction (user spends coins).
    Money flows: User -> Revenue
    """
    try:
        # Step 1: Check idempotency
        existing = transaction_repo.get_by_idempotency_key(db, request.idempotency_key)
        if existing:
            return existing
        
        # Step 2: Get asset type
        asset_type = db.query(AssetType).filter(AssetType.code == request.asset_type).first()
        if not asset_type:
            raise ValueError(f"Asset type {request.asset_type} not found")
        
        # Step 3: Lock wallets in order (ascending wallet_id to prevent deadlocks)
        # Lock revenue wallet first (system wallet), then user wallet
        revenue_wallet = wallet_repo.get_wallet_with_lock(db, SYSTEM_USER_IDS["REVENUE"], asset_type.id)
        user_wallet = wallet_repo.get_wallet_with_lock(db, request.user_id, asset_type.id)
        
        if not revenue_wallet:
            raise ValueError(f"Revenue wallet not found for asset {request.asset_type}")
        
        # Step 4: Check if user wallet exists
        if not user_wallet:
            # Create user wallet with 0 balance, then fail validation
            user_wallet = wallet_repo.create_wallet(db, request.user_id, asset_type.id)
            db.flush()
            # Re-lock the newly created wallet
            user_wallet = wallet_repo.get_wallet_with_lock(db, request.user_id, asset_type.id)
        
        # Step 5: CRITICAL - Validate user has sufficient funds
        if user_wallet.balance < request.amount:
            raise InsufficientFundsError(
                f"User wallet has insufficient funds. Balance: {user_wallet.balance}, Required: {request.amount}"
            )
        
        # Step 6: Create transaction record (PENDING)
        transaction_id = str(uuid.uuid4())
        transaction = transaction_repo.create_transaction(
            db=db,
            transaction_id=transaction_id,
            idempotency_key=request.idempotency_key,
            transaction_type="SPEND",
            user_id=request.user_id,
            asset_type_id=asset_type.id,
            amount=request.amount,
            metadata=request.metadata
        )
        db.flush()
        
        # Step 7: Update balances
        user_balance_before = user_wallet.balance
        revenue_balance_before = revenue_wallet.balance
        
        # Calculate new balances
        user_balance_after = user_balance_before - request.amount
        revenue_balance_after = revenue_balance_before + request.amount
        
        # Update wallet balances
        wallet_repo.update_wallet_balance(db, user_wallet, user_balance_after)
        wallet_repo.update_wallet_balance(db, revenue_wallet, revenue_balance_after)
        
        # Step 8: Create ledger entries (double-entry)
        # Debit from user (negative amount)
        ledger_repo.create_ledger_entry(
            db=db,
            transaction_id=transaction_id,
            wallet_id=user_wallet.id,
            entry_type="DEBIT",
            amount=-request.amount,
            balance_before=user_balance_before,
            balance_after=user_balance_after,
            description=f"User {request.user_id} spent {request.amount} {request.asset_type}"
        )
        
        # Credit to revenue
        ledger_repo.create_ledger_entry(
            db=db,
            transaction_id=transaction_id,
            wallet_id=revenue_wallet.id,
            entry_type="CREDIT",
            amount=request.amount,
            balance_before=revenue_balance_before,
            balance_after=revenue_balance_after,
            description=f"Revenue from user {request.user_id} spend"
        )
        
        # Step 9: Mark transaction as completed
        transaction_repo.update_transaction_status(
            db=db,
            transaction_id=transaction_id,
            status="COMPLETED"
        )
        
        # Step 10: Commit
        db.commit()
        db.refresh(transaction)
        
        return transaction
        
    except IntegrityError as e:
        db.rollback()
        # Check if it's duplicate idempotency key
        existing = transaction_repo.get_by_idempotency_key(db, request.idempotency_key)
        if existing:
            return existing
        raise DuplicateTransactionError(f"Transaction with key {request.idempotency_key} already exists")
    
    except Exception as e:
        db.rollback()
        # Try to mark transaction as failed if it was created
        try:
            transaction_repo.update_transaction_status(
                db=db,
                transaction_id=transaction_id if 'transaction_id' in locals() else None,
                status="FAILED",
                error_message=str(e)
            )
            db.commit()
        except:
            pass
        raise