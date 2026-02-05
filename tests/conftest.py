import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.database import Base
from app.config import settings
import os

# Use TEST_DATABASE_URL from .env
TEST_DATABASE_URL = os.getenv("TEST_DATABASE_URL", "mysql+pymysql://wallet_user:wallet_pass@localhost:3306/test_db")

# Create test engine
engine = create_engine(TEST_DATABASE_URL)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(scope="function")
def db_session():
    """
    Create a fresh database session for each test.
    
    This fixture:
    1. Creates all tables
    2. Yields a session for the test
    3. Rolls back any changes after the test
    4. Drops all tables
    
    This ensures each test starts with a clean database.
    """
    # Create all tables
    Base.metadata.create_all(bind=engine)
    
    # Create session
    session = TestingSessionLocal()
    
    try:
        yield session
    finally:
        session.rollback()
        session.close()
        # Drop all tables after test
        Base.metadata.drop_all(bind=engine)

@pytest.fixture
def sample_asset_type(db_session):
    """Create a sample asset type for testing."""
    from app.models.asset_types import AssetType
    
    asset = AssetType(
        code="COIN",
        display_name="Test Coins",
        is_active=True
    )
    db_session.add(asset)
    db_session.commit()
    db_session.refresh(asset)
    return asset

@pytest.fixture
def sample_wallet(db_session, sample_asset_type):
    """Create a sample wallet for testing."""
    from app.models.wallet import Wallet
    
    wallet = Wallet(
        user_id=1,
        asset_type_id=sample_asset_type.id,
        balance=1000.00
    )
    db_session.add(wallet)
    db_session.commit()
    db_session.refresh(wallet)
    return wallet