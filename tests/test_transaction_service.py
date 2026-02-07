import pytest
from decimal import Decimal
from sqlalchemy.exc import IntegrityError
from app.services.transaction_service import process_topup,process_bonus,process_spend
from app.schemas.transaction import TopupRequest,BonusRequest,SpendRequest
from app.models.asset_types import AssetType
from app.models.wallet import Wallet
from app.models.transaction import Transaction
from app.models.ledger import LedgerEntry
from app.utils.constants import SYSTEM_USER_IDS
from app.utils.exceptions import DuplicateTransactionError,InsufficientFundsError


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



# BONUS TRANSACTION TESTS

def test_process_bonus_success(db_session):
    """Test successful bonus transaction"""
    # Arrange
    request = BonusRequest(
        idempotency_key="test-bonus-001",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00"),
        metadata={"campaign": "welcome_bonus"}
    )
    
    # Act
    result = process_bonus(db_session, request)
    
    # Assert
    assert result.transaction_type == "BONUS"
    assert result.status == "COMPLETED"
    assert result.amount == Decimal("100.00")
    assert result.user_id == 1
    
    # Verify user wallet balance increased
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == db_session.query(AssetType).filter(AssetType.code == "COINS").first().id
    ).first()
    assert user_wallet.balance == Decimal("100.00")
    
    # Verify marketing wallet balance decreased
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    marketing_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["MARKETING"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert marketing_wallet.balance == Decimal("999900.00")  # Started with 1M
    
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


def test_process_bonus_creates_user_wallet_if_missing(db_session):
    """Test that bonus creates user wallet if it doesn't exist"""
    # Arrange
    request = BonusRequest(
        idempotency_key="test-bonus-002",
        user_id=888,  # New user without wallet
        asset_type="COINS",
        amount=Decimal("50.00")
    )
    
    # Verify wallet doesn't exist before
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    wallet_before = db_session.query(Wallet).filter(
        Wallet.user_id == 888,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_before is None
    
    # Act
    result = process_bonus(db_session, request)
    
    # Assert
    assert result.status == "COMPLETED"
    
    # Verify wallet was created
    wallet_after = db_session.query(Wallet).filter(
        Wallet.user_id == 888,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_after is not None
    assert wallet_after.balance == Decimal("50.00")


def test_process_bonus_idempotency(db_session):
    """Test that duplicate idempotency key returns original transaction"""
    # Arrange
    request = BonusRequest(
        idempotency_key="test-bonus-idempotent",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    # Act - first call
    result1 = process_bonus(db_session, request)
    
    # Get balance after first bonus
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == asset_type.id
    ).first()
    balance_after_first = user_wallet.balance
    
    # Act - second call with same idempotency key
    result2 = process_bonus(db_session, request)
    
    # Assert
    assert result1.transaction_id == result2.transaction_id
    assert result1.amount == result2.amount
    
    # Verify balance didn't change (no double-bonus)
    db_session.refresh(user_wallet)
    assert user_wallet.balance == balance_after_first
    
    # Verify only 1 transaction was created
    transactions = db_session.query(Transaction).filter(
        Transaction.idempotency_key == "test-bonus-idempotent"
    ).all()
    assert len(transactions) == 1


def test_process_bonus_insufficient_funds(db_session):
    """Test that bonus with insufficient marketing funds raises error"""
    # Arrange - deplete marketing wallet
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    marketing_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["MARKETING"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    marketing_wallet.balance = Decimal("50.00")
    db_session.commit()
    
    request = BonusRequest(
        idempotency_key="test-bonus-insufficient",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00")  # More than available
    )
    
    # Act & Assert
    with pytest.raises(InsufficientFundsError, match="Marketing wallet has insufficient funds"):
        process_bonus(db_session, request)


def test_process_bonus_invalid_asset_type(db_session):
    """Test that invalid asset type raises ValueError"""
    # Arrange
    request = BonusRequest(
        idempotency_key="test-bonus-invalid",
        user_id=1,
        asset_type="INVALID_ASSET",
        amount=Decimal("100.00")
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Asset type INVALID_ASSET not found"):
        process_bonus(db_session, request)


def test_process_bonus_marketing_wallet_missing(db_session):
    """Test that missing marketing wallet raises ValueError"""
    # Arrange - delete marketing wallet
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    marketing_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["MARKETING"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    db_session.delete(marketing_wallet)
    db_session.commit()
    
    request = BonusRequest(
        idempotency_key="test-bonus-no-marketing",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Marketing wallet not found"):
        process_bonus(db_session, request)


def test_process_bonus_decimal_precision(db_session):
    """Test that decimal amounts are handled correctly"""
    # Arrange
    request = BonusRequest(
        idempotency_key="test-bonus-decimal",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("123.456789")
    )
    
    # Act
    result = process_bonus(db_session, request)
    
    # Assert
    assert result.amount == Decimal("123.456789")
    
    # Verify wallet balance has correct precision
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert user_wallet.balance == Decimal("123.456789")


def test_process_bonus_metadata_stored(db_session):
    """Test that metadata is stored in transaction"""
    # Arrange
    metadata = {"campaign": "summer_promo", "source": "email", "code": "SUMMER2026"}
    request = BonusRequest(
        idempotency_key="test-bonus-metadata",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00"),
        metadata=metadata
    )
    
    # Act
    result = process_bonus(db_session, request)
    
    # Assert
    assert result.transaction_metadata == metadata



# SPEND TRANSACTION TESTS

def test_process_spend_success(db_session):
    """Test successful spend transaction"""
    # Arrange - First give user some coins
    topup_request = TopupRequest(
        idempotency_key="test-topup-for-spend",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("500.00")
    )
    process_topup(db_session, topup_request)
    
    # Act - Now spend some coins
    spend_request = SpendRequest(
        idempotency_key="test-spend-001",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00"),
        metadata={"item": "sword"}
    )
    result = process_spend(db_session, spend_request)
    
    # Assert
    assert result.transaction_type == "SPEND"
    assert result.status == "COMPLETED"
    assert result.amount == Decimal("100.00")
    assert result.user_id == 1
    
    # Verify user wallet balance decreased
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert user_wallet.balance == Decimal("400.00")  # 500 - 100
    
    # Verify revenue wallet balance increased
    revenue_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["REVENUE"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert revenue_wallet.balance == Decimal("100.00")  # Started with 0
    
    # Verify ledger entries exist
    ledger_entries = db_session.query(LedgerEntry).filter(
        LedgerEntry.transaction_id == result.transaction_id
    ).all()
    assert len(ledger_entries) == 2
    
    # Verify double-entry: entries sum to zero
    total = sum(entry.amount for entry in ledger_entries)
    assert total == Decimal("0.00")
    
    # Verify DEBIT is negative (user), CREDIT is positive (revenue)
    debit_entry = next(e for e in ledger_entries if e.entry_type == "DEBIT")
    credit_entry = next(e for e in ledger_entries if e.entry_type == "CREDIT")
    assert debit_entry.amount == Decimal("-100.00")
    assert credit_entry.amount == Decimal("100.00")


def test_process_spend_insufficient_funds(db_session):
    """Test that spend with insufficient funds raises error"""
    # Arrange - Give user only 50 coins
    topup_request = TopupRequest(
        idempotency_key="test-topup-for-spend-insufficient",
        user_id=2,
        asset_type="COINS",
        amount=Decimal("50.00")
    )
    process_topup(db_session, topup_request)
    
    # Act & Assert - Try to spend 100 (more than available)
    spend_request = SpendRequest(
        idempotency_key="test-spend-insufficient",
        user_id=2,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    with pytest.raises(InsufficientFundsError, match="User wallet has insufficient funds"):
        process_spend(db_session, spend_request)


def test_process_spend_idempotency(db_session):
    """Test that duplicate idempotency key returns original transaction"""
    # Arrange - Give user coins
    topup_request = TopupRequest(
        idempotency_key="test-topup-for-spend-idempotent",
        user_id=3,
        asset_type="COINS",
        amount=Decimal("200.00")
    )
    process_topup(db_session, topup_request)
    
    spend_request = SpendRequest(
        idempotency_key="test-spend-idempotent",
        user_id=3,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    # Act - first call
    result1 = process_spend(db_session, spend_request)
    
    # Get balance after first spend
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 3,
        Wallet.asset_type_id == asset_type.id
    ).first()
    balance_after_first = user_wallet.balance
    
    # Act - second call with same idempotency key
    result2 = process_spend(db_session, spend_request)
    
    # Assert
    assert result1.transaction_id == result2.transaction_id
    assert result1.amount == result2.amount
    
    # Verify balance didn't change (no double-spend)
    db_session.refresh(user_wallet)
    assert user_wallet.balance == balance_after_first
    assert user_wallet.balance == Decimal("100.00")  # 200 - 100
    
    # Verify only 1 spend transaction was created
    transactions = db_session.query(Transaction).filter(
        Transaction.idempotency_key == "test-spend-idempotent"
    ).all()
    assert len(transactions) == 1


def test_process_spend_user_wallet_missing(db_session):
    """Test that spend without existing wallet creates wallet with 0, then fails"""
    # Arrange - User 777 has no wallet
    spend_request = SpendRequest(
        idempotency_key="test-spend-no-wallet",
        user_id=777,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    # Act & Assert - Should create wallet with 0, then fail insufficient funds
    with pytest.raises(InsufficientFundsError):
        process_spend(db_session, spend_request)


def test_process_spend_invalid_asset_type(db_session):
    """Test that invalid asset type raises ValueError"""
    # Arrange
    spend_request = SpendRequest(
        idempotency_key="test-spend-invalid",
        user_id=1,
        asset_type="INVALID_ASSET",
        amount=Decimal("100.00")
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Asset type INVALID_ASSET not found"):
        process_spend(db_session, spend_request)


def test_process_spend_revenue_wallet_missing(db_session):
    """Test that missing revenue wallet raises ValueError"""
    # Arrange - delete revenue wallet
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    revenue_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["REVENUE"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    db_session.delete(revenue_wallet)
    db_session.commit()
    
    spend_request = SpendRequest(
        idempotency_key="test-spend-no-revenue",
        user_id=1,
        asset_type="COINS",
        amount=Decimal("100.00")
    )
    
    # Act & Assert
    with pytest.raises(ValueError, match="Revenue wallet not found"):
        process_spend(db_session, spend_request)


def test_process_spend_decimal_precision(db_session):
    """Test that decimal amounts are handled correctly"""
    # Arrange - Give user coins
    topup_request = TopupRequest(
        idempotency_key="test-topup-for-spend-decimal",
        user_id=4,
        asset_type="COINS",
        amount=Decimal("500.123456")
    )
    process_topup(db_session, topup_request)
    
    spend_request = SpendRequest(
        idempotency_key="test-spend-decimal",
        user_id=4,
        asset_type="COINS",
        amount=Decimal("123.456789")
    )
    
    # Act
    result = process_spend(db_session, spend_request)
    
    # Assert
    assert result.amount == Decimal("123.456789")
    
    # Verify wallet balance has correct precision
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 4,
        Wallet.asset_type_id == asset_type.id
    ).first()
    expected_balance = Decimal("500.123456") - Decimal("123.456789")
    assert user_wallet.balance == expected_balance


def test_process_spend_metadata_stored(db_session):
    """Test that metadata is stored in transaction"""
    # Arrange - Give user coins
    topup_request = TopupRequest(
        idempotency_key="test-topup-for-spend-metadata",
        user_id=5,
        asset_type="COINS",
        amount=Decimal("200.00")
    )
    process_topup(db_session, topup_request)
    
    metadata = {"item": "magic_sword", "shop": "armory", "price": 100}
    spend_request = SpendRequest(
        idempotency_key="test-spend-metadata",
        user_id=5,
        asset_type="COINS",
        amount=Decimal("100.00"),
        metadata=metadata
    )
    
    # Act
    result = process_spend(db_session, spend_request)
    
    # Assert
    assert result.transaction_metadata == metadata