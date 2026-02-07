"""
Load testing script for Wallet Service using Locust.

Run with:
    locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 60s

Parameters:
    -u: Number of concurrent users
    -r: Spawn rate (users per second)
    -t: Test duration
"""

from locust import HttpUser, task, between
import random
import uuid


class WalletServiceUser(HttpUser):
    """
    Simulates a user interacting with the wallet service.
    
    Task weights determine request distribution:
    - 60% balance checks (most frequent)
    - 20% topup transactions
    - 10% bonus transactions  
    - 10% spend transactions
    """
    
    # Wait 1-3 seconds between requests per user
    wait_time = between(1, 3)
    
    def on_start(self):
        """Initialize user with random ID on startup"""
        # Use high user IDs to avoid conflicts with seed data
        self.user_id = random.randint(10000, 99999)
        self.asset_types = ["COIN", "GEMS", "GOLD"]
        
        # Ensure user has some balance for spend tests
        # Do initial topup (not counted in stats)
        self.client.post(
            "/api/v1/transactions/topup",
            json={
                "idempotency_key": str(uuid.uuid4()),
                "user_id": self.user_id,
                "asset_type": "COIN",
                "amount": 10000.00
            },
            name="/api/v1/transactions/topup (setup)"
        )
    
    @task(60)
    def check_balance(self):
        """Check wallet balance (60% of requests)"""
        asset_type_id = random.randint(1, 3)  # 1=COIN, 2=GEMS, 3=GOLD
        
        self.client.get(
            f"/api/v1/wallets/{self.user_id}/balance?asset_type_id={asset_type_id}",
            name="/api/v1/wallets/:user_id/balance"
        )
    
    @task(20)
    def topup_transaction(self):
        """Create topup transaction (20% of requests)"""
        self.client.post(
            "/api/v1/transactions/topup",
            json={
                "idempotency_key": str(uuid.uuid4()),
                "user_id": self.user_id,
                "asset_type": random.choice(self.asset_types),
                "amount": random.uniform(10.0, 500.0)
            },
            name="/api/v1/transactions/topup"
        )
    
    @task(10)
    def bonus_transaction(self):
        """Create bonus transaction (10% of requests)"""
        self.client.post(
            "/api/v1/transactions/bonus",
            json={
                "idempotency_key": str(uuid.uuid4()),
                "user_id": self.user_id,
                "asset_type": random.choice(self.asset_types),
                "amount": random.uniform(5.0, 100.0)
            },
            name="/api/v1/transactions/bonus"
        )
    
    @task(10)
    def spend_transaction(self):
        """Create spend transaction (10% of requests)"""
        self.client.post(
            "/api/v1/transactions/spend",
            json={
                "idempotency_key": str(uuid.uuid4()),
                "user_id": self.user_id,
                "asset_type": "COIN",
                "amount": random.uniform(1.0, 50.0)
            },
            name="/api/v1/transactions/spend"
        )
    
    @task(5)
    def health_check(self):
        """Hit health endpoint (5% of requests)"""
        self.client.get("/health", name="/health")