import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from fastapi.testclient import TestClient
from decimal import Decimal
import os

from app.database import Base, get_db
from app.main import app
from app.models.asset_types import AssetType
from app.models.wallet import Wallet
from app.utils.constants import SYSTEM_USER_IDS

# Use TEST_DATABASE_URL from environment
TEST_DATABASE_URL = os.getenv(
    "TEST_DATABASE_URL", 
        "mysql+pymysql://wallet_user:wallet_pass@localhost:3306/wallet_db"
)

# Create test engine
engine = create_engine(TEST_DATABASE_URL, pool_pre_ping=True)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base.metadata.create_all(bind=engine)


@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test with transaction rollback.
    
    This uses nested transactions to ensure test isolation without 
    dropping/recreating tables every time.
    """
    connection = engine.connect()
    transaction = connection.begin()
    session = Session(bind=connection)
    
    # Seed minimal test data
    _seed_test_data(session)
    
    yield session
    
    session.close()
    transaction.rollback()
    connection.close()


def _seed_test_data(db: Session):
    """Seed essential test data if it doesn't exist."""
    
    # Check if asset types exist, if not create them
    coins = db.query(AssetType).filter(AssetType.code == "COINS").first()
    if not coins:
        coins = AssetType(code="COINS", display_name="Coins", is_active=True)
        db.add(coins)
        db.flush()
    
    gems = db.query(AssetType).filter(AssetType.code == "GEMS").first()
    if not gems:
        gems = AssetType(code="GEMS", display_name="Gems" , is_active=True)
        db.add(gems)
        db.flush()
    
    tickets = db.query(AssetType).filter(AssetType.code == "TICKETS").first()
    if not tickets:
        tickets = AssetType(code="TICKETS", display_name="Event Tickets", is_active=True)
        db.add(tickets)
        db.flush()
    
    # Create system wallets if they don't exist
    for asset in [coins, gems, tickets]:
        # Treasury wallet
        treasury = db.query(Wallet).filter(
            Wallet.user_id == SYSTEM_USER_IDS["TREASURY"],
            Wallet.asset_type_id == asset.id
        ).first()
        if not treasury:
            treasury = Wallet(
                user_id=SYSTEM_USER_IDS["TREASURY"],
                asset_type_id=asset.id,
                balance=Decimal("1000000.00"),
                is_system_wallet=True,
                system_wallet_type="TREASURY"
            )
            db.add(treasury)
        
        # Marketing wallet
        marketing = db.query(Wallet).filter(
            Wallet.user_id == SYSTEM_USER_IDS["MARKETING"],
            Wallet.asset_type_id == asset.id
        ).first()
        if not marketing:
            marketing = Wallet(
                user_id=SYSTEM_USER_IDS["MARKETING"],
                asset_type_id=asset.id,
                balance=Decimal("1000000.00"),
                is_system_wallet=True,
                system_wallet_type="MARKETING"
            )
            db.add(marketing)
        
        # Revenue wallet
        revenue = db.query(Wallet).filter(
            Wallet.user_id == SYSTEM_USER_IDS["REVENUE"],
            Wallet.asset_type_id == asset.id
        ).first()
        if not revenue:
            revenue = Wallet(
                user_id=SYSTEM_USER_IDS["REVENUE"],
                asset_type_id=asset.id,
                balance=Decimal("0.00"),
                is_system_wallet=True,
                system_wallet_type="REVENUE"
            )
            db.add(revenue)
    
    db.flush()


@pytest.fixture
def client(db_session):
    """
    Create a TestClient that uses the test database session.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass  # Don't close, conftest handles it
    
    app.dependency_overrides[get_db] = override_get_db
    
    with TestClient(app) as test_client:
        yield test_client
    
    app.dependency_overrides.clear()


@pytest.fixture
def sample_asset_type(db_session):
    """Get or create a sample asset type for testing."""
    asset = db_session.query(AssetType).filter(AssetType.code == "COINS").first()
    if not asset:
        asset = AssetType(code="COINS", display_name="Test Coins", is_active=True)
        db_session.add(asset)
        db_session.flush()
    return asset


@pytest.fixture
def sample_wallet(db_session, sample_asset_type):
    """Create a sample wallet for testing."""
    wallet = Wallet(
        user_id=1,
        asset_type_id=sample_asset_type.id,
        balance=Decimal("1000.00")
    )
    db_session.add(wallet)
    db_session.flush()
    return wallet


@pytest.fixture
def sample_transaction(db_session, sample_asset_type):
    """Create a sample transaction for testing."""
    from app.models.transaction import Transaction
    
    transaction = Transaction(
        transaction_id="txn_test_123",
        idempotency_key="idem_test_123",
        transaction_type="TOPUP",
        user_id=1,
        asset_type_id=sample_asset_type.id,
        amount=Decimal("100.00"),
        status="PENDING"
    )
    db_session.add(transaction)
    db_session.flush()
    return transaction