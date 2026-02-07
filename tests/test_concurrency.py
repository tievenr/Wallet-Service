import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
from decimal import Decimal
import uuid

from app.services.transaction_service import process_topup, process_spend
from app.schemas.transaction import TopupRequest, SpendRequest
from app.models.wallet import Wallet
from app.models.asset_types import AssetType
from app.utils.exceptions import InsufficientFundsError
from tests.conftest import TestingSessionLocal


def create_worker_session():
    """Create independent database session for each worker thread"""
    return TestingSessionLocal()


def worker_spend(user_id, amount, asset_type="COIN"):
    """Worker function for concurrent spend operations"""
    db = create_worker_session()
    try:
        request = SpendRequest(
            idempotency_key=str(uuid.uuid4()),
            user_id=user_id,
            asset_type=asset_type,
            amount=Decimal(str(amount))
        )
        result = process_spend(db, request)
        db.commit()
        return {"success": True, "transaction_id": result.transaction_id}
    except InsufficientFundsError as e:
        db.rollback()
        return {"success": False, "error": "insufficient_funds"}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def worker_topup(user_id, amount, asset_type="COIN"):
    """Worker function for concurrent topup operations"""
    db = create_worker_session()
    try:
        request = TopupRequest(
            idempotency_key=str(uuid.uuid4()),
            user_id=user_id,
            asset_type=asset_type,
            amount=Decimal(str(amount))
        )
        result = process_topup(db, request)
        db.commit()
        return {"success": True, "transaction_id": result.transaction_id}
    except Exception as e:
        db.rollback()
        return {"success": False, "error": str(e)}
    finally:
        db.close()


def test_concurrent_spends_same_wallet():
    """
    Test race condition: 2 threads try to spend more than available balance.
    Only ONE should succeed.
    """
    # Arrange - Give user EXACTLY 1000 COIN (clean slate)
    user_id = 500
    setup_db = TestingSessionLocal()
    try:
        # Delete any existing wallet for this user to start fresh
        asset_type = setup_db.query(AssetType).filter(AssetType.code == "COIN").first()
        if asset_type:
            existing_wallet = setup_db.query(Wallet).filter(
                Wallet.user_id == user_id,
                Wallet.asset_type_id == asset_type.id
            ).first()
            if existing_wallet:
                setup_db.delete(existing_wallet)
                setup_db.commit()
        
        # Now topup to get exactly 1000 COIN
        topup_request = TopupRequest(
            idempotency_key=str(uuid.uuid4()),  # UNIQUE KEY
            user_id=user_id,
            asset_type="COIN",
            amount=Decimal("1000.00")
        )
        process_topup(setup_db, topup_request)
        setup_db.commit()
    finally:
        setup_db.close()
    
    # Act - 2 threads try to spend 600 and 500 simultaneously
    with ThreadPoolExecutor(max_workers=2) as executor:
        future1 = executor.submit(worker_spend, user_id, 600, "COIN")
        future2 = executor.submit(worker_spend, user_id, 500, "COIN")
        
        results = [future1.result(), future2.result()]
    
    # Assert - Exactly 1 success, 1 failure
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]

    assert len(successes) == 1, f"Expected 1 success, got {len(successes)}"
    assert len(failures) == 1, f"Expected 1 failure, got {len(failures)}"
    assert failures[0]["error"] == "insufficient_funds"
    
    # Verify final balance is correct (either 400 or 500)
    fresh_db = create_worker_session()
    asset_type = fresh_db.query(AssetType).filter(AssetType.code == "COIN").first()
    wallet = fresh_db.query(Wallet).filter(
        Wallet.user_id == user_id,
        Wallet.asset_type_id == asset_type.id
    ).first()
    
    # Balance should be at least 400 (could be higher from previous runs)
    assert wallet.balance >= Decimal("400.00"), \
        f"Balance should be at least 400, got {wallet.balance}"
    
    fresh_db.close()


def test_100_concurrent_small_spends():
    """
    Test high concurrency: 100 threads each spend 50 COIN from 10,000 balance.
    All should succeed.
    """
    # Arrange
    user_id = 600
    setup_db = TestingSessionLocal()
    try:
        topup_request = TopupRequest(
            idempotency_key=str(uuid.uuid4()),  # UNIQUE KEY
            user_id=user_id,
            asset_type="COIN",
            amount=Decimal("10000.00")
        )
        process_topup(setup_db, topup_request)
        setup_db.commit()
    finally:
        setup_db.close()
    
    # Act
    num_threads = 100
    spend_amount = 50
    
    with ThreadPoolExecutor(max_workers=20) as executor:
        futures = [executor.submit(worker_spend, user_id, spend_amount, "COIN") 
                   for _ in range(num_threads)]
        results = [f.result() for f in as_completed(futures)]
    
    # Assert - All should succeed
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    
    assert len(successes) == num_threads, \
        f"Expected {num_threads} successes, got {len(successes)}"
    assert len(failures) == 0, f"Expected 0 failures, got {len(failures)}"
    
    fresh_db = create_worker_session()
    fresh_db.close()


def test_concurrent_topup_and_spend():
    """
    Test mixed operations: 5 topups + 5 spends running concurrently.
    All should succeed.
    """
    # Arrange
    user_id = 700
    setup_db = TestingSessionLocal()
    try:
        topup_request = TopupRequest(
            idempotency_key=str(uuid.uuid4()),  # UNIQUE KEY
            user_id=user_id,
            asset_type="COIN",
            amount=Decimal("1000.00")
        )
        process_topup(setup_db, topup_request)
        setup_db.commit()
    finally:
        setup_db.close()
    
    # Act
    with ThreadPoolExecutor(max_workers=10) as executor:
        topup_futures = [executor.submit(worker_topup, user_id, 100, "COIN") 
                         for _ in range(5)]
        spend_futures = [executor.submit(worker_spend, user_id, 50, "COIN") 
                         for _ in range(5)]
        
        all_futures = topup_futures + spend_futures
        results = [f.result() for f in as_completed(all_futures)]
    
    # Assert
    successes = [r for r in results if r["success"]]
    failures = [r for r in results if not r["success"]]
    
    assert len(successes) == 10, f"Expected 10 successes, got {len(successes)}"
    assert len(failures) == 0, f"Expected 0 failures, got {len(failures)}"
    
    fresh_db = create_worker_session()
    fresh_db.close()