import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.services.transaction_service import process_topup
from app.schemas.transaction import TopupRequest
from app.models.asset_types import AssetType
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.ledger import LedgerEntry
from app.utils.constants import SYSTEM_USER_IDS
from app.utils.exceptions import DuplicateTransactionError


def test_process_topup_success(db_session):
    """Test successful topup transaction"""
    # Arrange
    request = TopupRequest(
        idempotency_key="test-topup-001",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00"),
        metadata={"source": "test"}
    )
    
    # Act
    result = process_topup(db_session, request)
    
    # Assert
    assert result.transaction_type == "TOPUP"
    assert result.status == "COMPLETED"
    assert result.amount == Decimal("100.00")
    assert result.user_id == 1
    
    # Verify user wallet balance increased
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == db_session.query(AssetType).filter(AssetType.code == "COINS").first().id
    ).first()
    assert user_wallet.balance == Decimal("100.00")
    
    # Verify treasury wallet balance decreased
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    treasury_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["TREASURY"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert treasury_wallet.balance == Decimal("999900.00")  # Started with 1M
    
    # Verify ledger entries exist
    ledger_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.transaction_id == result.transaction_id
    ).all()
    assert len(ledger_entries) == 2
    
    # Verify double-entry: entries sum to zero
    total = sum(entry.amount for entry in ledger_entries)
    assert total == Decimal("0.00")
    
    # Verify DEBIT is negative, CREDIT is positive
    debit_entry = next(e for e in ledger_entries if e.entry_type == "DEBIT")
    credit_entry = next(e for e in ledger_entries if e.entry_type == "CREDIT")
    assert debit_entry.amount == Decimal("-100.00")
    assert credit_entry.amount == Decimal("100.00")


def test_process_topup_creates_user_wallet_if_missing(db_session):
    """Test that topup creates user wallet if it doesn't exist"""
    # Arrange
    request = TopupRequest(
        idempotency_key="test-topup-002",
        user_id=999,  # New user without wallet
        asset_type="COINS",
        amount=Decimal("50.00")
    )
    
    # Verify wallet doesn't exist before
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    wallet_before = db_session.query(Wallet).filter(
        Wallet.user_id == 999,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_before is None
    
    # Act
    result = process_topup(db_session, request)
    
    # Assert
    assert result.status == "COMPLETED"
    
    # Verify wallet was created
    wallet_after = db_session.query(Wallet).filter(
        Wallet.user_id == 999,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_after is not None
    assert wallet_after.balance == Decimal("50.00")


def test_process_topup_idempotency(db_session):
    """Test that duplicate idempotency key returns original transaction"""
    # Arrange
    request = TopupRequest(
        idempotency_key="test-topup-idempotent",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    # Act - first call
    result1 = process_topup(db_session, request)
    
    # Get balance after first topup
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == asset_type.id
    ).first()
    balance_after_first = user_wallet.balance
    
    # Act - second call with same idempotency key
    result2 = process_topup(db_session, request)
    
    # Assert
    assert result1.transaction_id == result2.transaction_id
    assert result1.amount == result2.amount
    
    # Verify balance didn't change (no double-topup)
    db_session.refresh(user_wallet)
    assert user_wallet.balance == balance_after_first
    
    # Verify only 1 transaction was created
    transactions = db_session.query(Transaction).filter(
        Transaction.idempotency_key == "test-topup-idempotent"
    ).all()
    assert len(transactions) == 1


def test_process_topup_invalid_asset_type(db_session):
    """Test that invalid asset type raises ValueError"""
    # Arrange
    request = TopupRequest(
        idempotency_key="test-topup-invalid",
        user_id=1,
        asset_type="INVALID_ASSET",
        amount=Decimal("100.00")
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Asset type INVALID_ASSET not found"):
        process_topup(db_session, request)


def test_process_topup_treasury_wallet_missing(db_session):
    """Test that missing treasury wallet raises ValueError"""
    # Arrange - delete treasury wallet
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    treasury_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["TREASURY"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    db_session.delete(treasury_wallet)
    db_session.commit()
    
    request = TopupRequest(
        idempotency_key="test-topup-no-treasury",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Treasury wallet not found"):
        process_topup(db_session, request)


def test_process_topup_decimal_precision(db_session):
    """Test that decimal amounts are handled correctly"""
    # Arrange
    request = TopupRequest(
        idempotency_key="test-topup-decimal",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("123.456789")
    )
    
    # Act
    result = process_topup(db_session, request)
    
    # Assert
    assert result.amount == Decimal("123.456789")
    
    # Verify wallet balance has correct precision
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert user_wallet.balance == Decimal("123.456789")


def test_process_topup_metadata_stored(db_session):
    """Test that metadata is stored in transaction"""
    # Arrange
    metadata = {"source": "web", "campaign": "new_user", "ip": "192.168.1.1"}
    request = TopupRequest(
        idempotency_key="test-topup-metadata",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00"),
        metadata=metadata
    )
    
    # Act
    result = process_topup(db_session, request)
    
    # Assert
    assert result.transaction_metadata == metadata