import pytest
from decimal import Decimal
from app.models.asset_types import AssetType
from app.models.wallet import Wallet
from app.utils.constants import SYSTEM_USER_IDS
from decimal import Decimal

def test_topup_endpoint_success(client, db_session):
    """Test successful topup via API"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-001",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "100.00",
        "metadata": {"source": "api_test"}
    }
    
    # Act
    response = client.post("/api/v1/transactions/topup", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_type"] == "TOPUP"
    assert data["status"] == "COMPLETED"
    assert Decimal(data["amount"]) == Decimal("100.00")
    assert data["user_id"] == 1
    assert "transaction_id" in data
    assert data["transaction_metadata"] == {"source": "api_test"}


def test_topup_endpoint_idempotency(client, db_session):
    """Test that duplicate idempotency key returns same transaction"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-idempotent",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "100.00"
    }
    
    # Act - first request
    response1 = client.post("/api/v1/transactions/topup", json=payload)
    data1 = response1.json()
    
    # Act - second request with same idempotency key
    response2 = client.post("/api/v1/transactions/topup", json=payload)
    data2 = response2.json()
    
    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert data1["transaction_id"] == data2["transaction_id"]
    
    # Verify balance only increased once
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == asset_type.id
    ).first()
    # Balance should be 100, not 200
    assert user_wallet.balance == Decimal("100.00")


def test_topup_endpoint_validation_missing_fields(client, db_session):
    """Test validation errors for missing required fields"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-invalid",
        "user_id": 1
        # Missing asset_type and amount
    }
    
    # Act
    response = client.post("/api/v1/transactions/topup", json=payload)
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_topup_endpoint_validation_negative_amount(client, db_session):
    """Test validation errors for negative amount"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-negative",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "-50.00"
    }
    
    # Act
    response = client.post("/api/v1/transactions/topup", json=payload)
    
    # Assert
    assert response.status_code == 422


def test_topup_endpoint_validation_zero_amount(client, db_session):
    """Test validation errors for zero amount"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-zero",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "0.00"
    }
    
    # Act
    response = client.post("/api/v1/transactions/topup", json=payload)
    
    # Assert
    assert response.status_code == 422


def test_topup_endpoint_invalid_asset_type(client, db_session):
    """Test error handling for invalid asset type"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-invalid-asset",
        "user_id": 1,
        "asset_type": "INVALID_ASSET",
        "amount": "100.00"
    }
    
    # Act
    response = client.post("/api/v1/transactions/topup", json=payload)
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "Asset type INVALID_ASSET not found" in data["detail"]


def test_topup_endpoint_creates_new_user_wallet(client, db_session):
    """Test that topup creates wallet for new user"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-new-user",
        "user_id": 9999,  # New user
        "asset_type": "COINS",
        "amount": "50.00"
    }
    
    # Verify wallet doesn't exist
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    wallet_before = db_session.query(Wallet).filter(
        Wallet.user_id == 9999,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_before is None
    
    # Act
    response = client.post("/api/v1/transactions/topup", json=payload)
    
    # Assert
    assert response.status_code == 200
    
    # Verify wallet was created
    wallet_after = db_session.query(Wallet).filter(
        Wallet.user_id == 9999,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_after is not None
    assert wallet_after.balance == Decimal("50.00")


def test_topup_endpoint_multiple_asset_types(client, db_session):
    """Test topup with different asset types"""
    # Arrange - topup COINS
    payload_coins = {
        "idempotency_key": "api-test-coins",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "100.00"
    }
    
    # Arrange - topup GEMS
    payload_gems = {
        "idempotency_key": "api-test-gems",
        "user_id": 1,
        "asset_type": "GEMS",
        "amount": "50.00"
    }
    
    # Act
    response_coins = client.post("/api/v1/transactions/topup", json=payload_coins)
    response_gems = client.post("/api/v1/transactions/topup", json=payload_gems)
    
    # Assert
    assert response_coins.status_code == 200
    assert response_gems.status_code == 200
    
    # Verify both wallets have correct balances
    coins_asset = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    gems_asset = db_session.query(AssetType).filter(AssetType.code == "GEMS").first()
    
    coins_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == coins_asset.id
    ).first()
    gems_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == gems_asset.id
    ).first()
    
    assert coins_wallet.balance == Decimal("100.00")
    assert gems_wallet.balance == Decimal("50.00")


def test_topup_endpoint_large_amount(client, db_session):
    """Test topup with large amount"""
    # Arrange
    payload = {
        "idempotency_key": "api-test-large",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "999999.99"
    }
    
    # Act
    response = client.post("/api/v1/transactions/topup", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert Decimal(data["amount"]) == Decimal("999999.99")



# BONUS ENDPOINT TESTS

def test_bonus_endpoint_success(client, db_session):
    """Test successful bonus via API"""
    # Arrange
    payload = {
        "idempotency_key": "api-bonus-001",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "100.00",
        "metadata": {"campaign": "welcome_bonus"}
    }
    
    # Act
    response = client.post("/api/v1/transactions/bonus", json=payload)
    
    # Assert
    assert response.status_code == 200
    data = response.json()
    assert data["transaction_type"] == "BONUS"
    assert data["status"] == "COMPLETED"
    assert Decimal(data["amount"]) == Decimal("100.00")
    assert data["user_id"] == 1
    assert "transaction_id" in data
    assert data["transaction_metadata"] == {"campaign": "welcome_bonus"}


def test_bonus_endpoint_idempotency(client, db_session):
    """Test that duplicate idempotency key returns same transaction"""
    # Arrange
    payload = {
        "idempotency_key": "api-bonus-idempotent",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "100.00"
    }
    
    # Act - first request
    response1 = client.post("/api/v1/transactions/bonus", json=payload)
    data1 = response1.json()
    
    # Act - second request with same idempotency key
    response2 = client.post("/api/v1/transactions/bonus", json=payload)
    data2 = response2.json()
    
    # Assert
    assert response1.status_code == 200
    assert response2.status_code == 200
    assert data1["transaction_id"] == data2["transaction_id"]
    
    # Verify balance only increased once
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    user_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == 1,
        Wallet.asset_type_id == asset_type.id
    ).first()
    # Balance should be 100, not 200
    assert user_wallet.balance == Decimal("100.00")


def test_bonus_endpoint_invalid_asset_type(client, db_session):
    """Test error handling for invalid asset type"""
    # Arrange
    payload = {
        "idempotency_key": "api-bonus-invalid-asset",
        "user_id": 1,
        "asset_type": "INVALID_ASSET",
        "amount": "100.00"
    }
    
    # Act
    response = client.post("/api/v1/transactions/bonus", json=payload)
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "Asset type INVALID_ASSET not found" in data["detail"]


def test_bonus_endpoint_insufficient_funds(client, db_session):
    """Test error handling when marketing wallet has insufficient funds"""
    # Arrange - deplete marketing wallet
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    marketing_wallet = db_session.query(Wallet).filter(
        Wallet.user_id == SYSTEM_USER_IDS["MARKETING"],
        Wallet.asset_type_id == asset_type.id
    ).first()
    marketing_wallet.balance = Decimal("50.00")
    db_session.commit()
    
    payload = {
        "idempotency_key": "api-bonus-insufficient",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "100.00"  # More than available
    }
    
    # Act
    response = client.post("/api/v1/transactions/bonus", json=payload)
    
    # Assert
    assert response.status_code == 400
    data = response.json()
    assert "insufficient funds" in data["detail"].lower()


def test_bonus_endpoint_creates_new_user_wallet(client, db_session):
    """Test that bonus creates wallet for new user"""
    # Arrange
    payload = {
        "idempotency_key": "api-bonus-new-user",
        "user_id": 8888,  # New user
        "asset_type": "COINS",
        "amount": "50.00"
    }
    
    # Verify wallet doesn't exist
    asset_type = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    wallet_before = db_session.query(Wallet).filter(
        Wallet.user_id == 8888,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_before is None
    
    # Act
    response = client.post("/api/v1/transactions/bonus", json=payload)
    
    # Assert
    assert response.status_code == 200
    
    # Verify wallet was created
    wallet_after = db_session.query(Wallet).filter(
        Wallet.user_id == 8888,
        Wallet.asset_type_id == asset_type.id
    ).first()
    assert wallet_after is not None
    assert wallet_after.balance == Decimal("50.00")


def test_bonus_endpoint_validation_missing_fields(client, db_session):
    """Test validation errors for missing required fields"""
    # Arrange
    payload = {
        "idempotency_key": "api-bonus-invalid",
        "user_id": 1
        # Missing asset_type and amount
    }
    
    # Act
    response = client.post("/api/v1/transactions/bonus", json=payload)
    
    # Assert
    assert response.status_code == 422  # Validation error


def test_bonus_endpoint_validation_negative_amount(client, db_session):
    """Test validation errors for negative amount"""
    # Arrange
    payload = {
        "idempotency_key": "api-bonus-negative",
        "user_id": 1,
        "asset_type": "COINS",
        "amount": "-50.00"
    }
    
    # Act
    response = client.post("/api/v1/transactions/bonus", json=payload)
    
    # Assert
    assert response.status_code == 422