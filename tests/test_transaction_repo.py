import pytest
from app.repositories import transaction_repository
from datetime import datetime

@pytest.fixture
def sample_transaction(db_session, sample_asset_type):
    """Create a sample transaction for testing."""
    transaction = transaction_repository.create_transaction(
        db_session,
        transaction_id="txn_test_123",
        idempotency_key="idem_test_123",
        transaction_type="TOPUP",
        user_id=1,
        asset_type_id=sample_asset_type.id,
        amount=100.00,
        metadata={"source": "test"}
    )
    return transaction

def test_create_transaction(db_session, sample_asset_type):
    """Test creating a transaction."""
    transaction = transaction_repository.create_transaction(
        db_session,
        transaction_id="txn_001",
        idempotency_key="idem_001",
        transaction_type="SPEND",
        user_id=1,
        asset_type_id=sample_asset_type.id,
        amount=50.00
    )
    
    assert transaction.id is not None
    assert transaction.transaction_id == "txn_001"
    assert transaction.status == "PENDING"
    assert transaction.amount == 50.00

def test_get_by_idempotency_key(db_session, sample_transaction):
    """Test fetching transaction by idempotency key."""
    transaction = transaction_repository.get_by_idempotency_key(
        db_session, 
        "idem_test_123"
    )
    
    assert transaction is not None
    assert transaction.transaction_id == "txn_test_123"

def test_get_by_idempotency_key_not_found(db_session):
    """Test fetching non-existent idempotency key returns None."""
    transaction = transaction_repository.get_by_idempotency_key(
        db_session, 
        "nonexistent"
    )
    assert transaction is None

def test_get_by_transaction_id(db_session, sample_transaction):
    """Test fetching transaction by transaction_id."""
    transaction = transaction_repository.get_by_transaction_id(
        db_session,
        "txn_test_123"
    )
    
    assert transaction is not None
    assert transaction.idempotency_key == "idem_test_123"

def test_update_transaction_status_completed(db_session, sample_transaction):
    """Test updating transaction status to COMPLETED."""
    transaction_repository.update_transaction_status(
        db_session,
        transaction_id="txn_test_123",
        status="COMPLETED"
    )
    
    # Verify update
    transaction = transaction_repository.get_by_transaction_id(
        db_session,
        "txn_test_123"
    )
    assert transaction.status == "COMPLETED"
    assert transaction.completed_at is not None

def test_update_transaction_status_failed(db_session, sample_transaction):
    """Test updating transaction status to FAILED with error message."""
    transaction_repository.update_transaction_status(
        db_session,
        transaction_id="txn_test_123",
        status="FAILED",
        error_message="Insufficient funds"
    )
    
    # Verify update
    transaction = transaction_repository.get_by_transaction_id(
        db_session,
        "txn_test_123"
    )
    assert transaction.status == "FAILED"
    assert transaction.error_message == "Insufficient funds"