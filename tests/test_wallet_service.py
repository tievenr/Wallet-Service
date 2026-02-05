import pytest
from app.services import wallet_service
from app.utils.exceptions import WalletNotFoundError

def test_get_wallet_balance_existing_wallet(db_session, sample_wallet):
    """Test getting balance for existing wallet."""
    balance = wallet_service.get_wallet_balance(
        db_session,
        user_id=1,
        asset_type_id=sample_wallet.asset_type_id
    )
    
    assert balance == 1000.00

def test_get_wallet_balance_nonexistent_wallet(db_session, sample_asset_type):
    """Test getting balance for non-existent wallet returns 0."""
    balance = wallet_service.get_wallet_balance(
        db_session,
        user_id=999,
        asset_type_id=sample_asset_type.id
    )
    
    assert balance == 0.0

def test_get_or_create_wallet_existing(db_session, sample_wallet, sample_asset_type):
    """Test get_or_create returns existing wallet."""
    wallet = wallet_service.get_or_create_wallet(
        db_session,
        user_id=1,
        asset_type_id=sample_asset_type.id
    )
    
    assert wallet.id == sample_wallet.id
    assert wallet.user_id == 1

def test_get_or_create_wallet_new(db_session, sample_asset_type):
    """Test get_or_create creates new wallet when none exists."""
    wallet = wallet_service.get_or_create_wallet(
        db_session,
        user_id=999,
        asset_type_id=sample_asset_type.id
    )
    
    assert wallet.id is not None
    assert wallet.user_id == 999
    assert wallet.balance == 0.0
    assert wallet.is_system_wallet == False

def test_get_or_create_system_wallet(db_session, sample_asset_type):
    """Test creating system wallet."""
    wallet = wallet_service.get_or_create_wallet(
        db_session,
        user_id=-1,
        asset_type_id=sample_asset_type.id,
        is_system=True,
        system_wallet_type="TREASURY"
    )
    
    assert wallet.user_id == -1
    assert wallet.is_system_wallet == True
    assert wallet.system_wallet_type == "TREASURY"