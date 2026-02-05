import pytest
from app.repositories import wallet_repository
from app.models.wallet import Wallet

def test_get_wallet_by_id(db_session, sample_wallet):
    """Test fetching wallet by ID."""
    wallet = wallet_repository.get_wallet_by_id(db_session, sample_wallet.id)
    
    assert wallet is not None
    assert wallet.id == sample_wallet.id
    assert wallet.user_id == 1
    assert wallet.balance == 1000.00

def test_get_wallet_by_id_not_found(db_session):
    """Test fetching non-existent wallet returns None."""
    wallet = wallet_repository.get_wallet_by_id(db_session, 99999)
    assert wallet is None

def test_get_wallet_by_user_and_asset(db_session, sample_wallet, sample_asset_type):
    """Test fetching wallet by user_id and asset_type_id."""
    wallet = wallet_repository.get_wallet_by_user_and_asset(
        db_session, 
        user_id=1, 
        asset_type_id=sample_asset_type.id
    )
    
    assert wallet is not None
    assert wallet.user_id == 1
    assert wallet.asset_type_id == sample_asset_type.id

def test_create_wallet(db_session, sample_asset_type):
    """Test creating a new wallet."""
    wallet = wallet_repository.create_wallet(
        db_session,
        user_id=2,
        asset_type_id=sample_asset_type.id
    )
    
    assert wallet.id is not None
    assert wallet.user_id == 2
    assert wallet.balance == 0.00
    assert wallet.is_system_wallet == False

def test_create_system_wallet(db_session, sample_asset_type):
    """Test creating a system wallet."""
    wallet = wallet_repository.create_wallet(
        db_session,
        user_id=-1,
        asset_type_id=sample_asset_type.id,
        is_system_wallet=True,
        system_wallet_type="TREASURY"
    )
    
    assert wallet.user_id == -1
    assert wallet.is_system_wallet == True
    assert wallet.system_wallet_type == "TREASURY"

def test_get_wallet_with_lock(db_session, sample_wallet):
    """Test fetching wallet with lock."""
    wallet = wallet_repository.get_wallet_with_lock(db_session, sample_wallet.id)
    
    assert wallet is not None
    assert wallet.id == sample_wallet.id
    # Note: We can't easily test that the lock was actually acquired
    # without multi-threading, which we'll test in Phase 10

def test_update_wallet_balance(db_session, sample_wallet):
    """Test updating wallet balance."""
    wallet_repository.update_wallet_balance(
        db_session,
        wallet_id=sample_wallet.id,
        new_balance=500.00
    )
    
    # Fetch wallet again to verify
    updated_wallet = wallet_repository.get_wallet_by_id(db_session, sample_wallet.id)
    assert updated_wallet.balance == 500.00