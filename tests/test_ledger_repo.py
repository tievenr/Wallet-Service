import pytest
from app.repositories import ledger_repository, transaction_repository, wallet_repository

@pytest.fixture
def sample_transaction(db_session, sample_asset_type):
    """Create a transaction for ledger entries to reference."""
    return transaction_repository.create_transaction(
        db_session,
        transaction_id="txn_ledger_test",
        idempotency_key="idem_ledger_test",
        transaction_type="TOPUP",
        user_id=1,
        asset_type_id=sample_asset_type.id,
        amount=100.00
    )

@pytest.fixture
def sample_ledger_entry(db_session, sample_wallet, sample_transaction):
    """Create a sample ledger entry for testing."""
    entry = ledger_repository.create_ledger_entry(
        db_session,
        transaction_id=sample_transaction.transaction_id,
        wallet_id=sample_wallet.id,
        entry_type="CREDIT",
        amount=100.00,
        balance_before=1000.00,
        balance_after=1100.00,
        description="Test credit"
    )
    return entry

def test_create_ledger_entry(db_session, sample_wallet, sample_asset_type):
    """Test creating a ledger entry."""
    # First create a transaction
    transaction = transaction_repository.create_transaction(
        db_session,
        transaction_id="txn_001",
        idempotency_key="idem_001",
        transaction_type="SPEND",
        user_id=1,
        asset_type_id=sample_asset_type.id,
        amount=50.00
    )
    
    # Now create ledger entry that references it
    entry = ledger_repository.create_ledger_entry(
        db_session,
        transaction_id=transaction.transaction_id,
        wallet_id=sample_wallet.id,
        entry_type="DEBIT",
        amount=-50.00,
        balance_before=1000.00,
        balance_after=950.00
    )
    
    assert entry.id is not None
    assert entry.amount == -50.00
    assert entry.entry_type == "DEBIT"
    assert entry.balance_after == 950.00

def test_get_entries_by_transaction(db_session, sample_wallet, sample_asset_type):
    """Test fetching all ledger entries for a transaction."""
    # Create a SECOND wallet for the test
    second_wallet = wallet_repository.create_wallet(
        db_session,
        user_id=2,
        asset_type_id=sample_asset_type.id
    )
    
    # Create transaction first
    transaction = transaction_repository.create_transaction(
        db_session,
        transaction_id="txn_double",
        idempotency_key="idem_double",
        transaction_type="SPEND",
        user_id=1,
        asset_type_id=sample_asset_type.id,
        amount=100.00
    )
    
    # Create two entries for same transaction (different wallets)
    ledger_repository.create_ledger_entry(
        db_session,
        transaction_id=transaction.transaction_id,
        wallet_id=sample_wallet.id,
        entry_type="DEBIT",
        amount=-100.00,
        balance_before=1000.00,
        balance_after=900.00
    )
    
    ledger_repository.create_ledger_entry(
        db_session,
        transaction_id=transaction.transaction_id,
        wallet_id=second_wallet.id,  # Use the wallet we just created!
        entry_type="CREDIT",
        amount=100.00,
        balance_before=0.00,
        balance_after=100.00
    )
    
    # Fetch both entries
    entries = ledger_repository.get_entries_by_transaction(
        db_session,
        transaction.transaction_id
    )
    
    assert len(entries) == 2
    assert entries[0].transaction_id == transaction.transaction_id
    assert entries[1].transaction_id == transaction.transaction_id
    
    # Verify double-entry: sum should be 0
    total = sum(entry.amount for entry in entries)
    assert total == 0.00