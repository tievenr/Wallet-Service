# Testing Guide

Complete testing documentation for the Wallet Service, including unit tests, integration tests, concurrency tests, and load testing.

## Running Tests

### Run All Tests

```bash
# From host machine (MySQL must be running)
docker-compose up -d db  # Start database
pytest tests/ -v         # Run all 69 tests

# Expected: 69 passed tests
```

## Test Categories

### Unit Tests (Repository Layer)

Tests for data access layer functions including wallet CRUD operations and locking.

```bash
pytest tests/test_wallet_repo.py -v
pytest tests/test_transaction_repo.py -v
pytest tests/test_ledger_repo.py -v
```

**Coverage:**
- Wallet creation and retrieval
- Wallet locking (`SELECT FOR UPDATE`)
- Balance updates
- Transaction CRUD operations
- Idempotency key lookups
- Ledger entry creation

### Unit Tests (Service Layer)

Tests for business logic in transaction processing.

```bash
pytest tests/test_transaction_service.py -v
```

**24 tests covering:**
- Success paths for TOPUP, BONUS, SPEND transactions
- Idempotency handling (duplicate request detection)
- Insufficient funds validation
- Wallet auto-creation for new users
- Decimal precision (20 digits, 8 decimal places)
- Metadata storage and retrieval

### Integration Tests (API Layer)

End-to-end tests hitting the REST API endpoints.

```bash
pytest tests/test_transaction_api.py -v
```

**21 tests covering:**
- Complete API workflows (request → response)
- HTTP status codes (200, 400, 409, 422)
- Request validation (Pydantic)
- Error response formats
- All three transaction types via API

### Concurrency Tests

Critical tests verifying race condition prevention and data integrity under concurrent load.

```bash
# Important: For clean test results, restart containers between runs
docker-compose restart

pytest tests/test_concurrency.py -v
```

**3 tests:**

1. **test_concurrent_spends_same_wallet**: 
   - Scenario: 2 threads try to spend more than available balance
   - Expected: Exactly 1 succeeds, 1 fails with insufficient_funds
   - Validates: Pessimistic locking prevents negative balances

2. **test_100_concurrent_small_spends**:
   - Scenario: 100 threads each spend 50 from 10,000 balance
   - Expected: All 100 succeed, final balance = 5,000
   - Validates: High contention handling without deadlocks

3. **test_concurrent_topup_and_spend**:
   - Scenario: 5 topups and 5 spends running simultaneously
   - Expected: All 10 transactions complete successfully
   - Validates: Mixed operation types don't interfere

**Note on Concurrency Tests**: These tests use random user IDs to avoid stale data from previous runs. If you encounter unexpected failures, restart the Docker containers to ensure a clean database state.

## Test Coverage

The test suite provides comprehensive coverage of:

- **Idempotency**: Duplicate requests return cached results
- **Edge Cases**: 
  - Negative amounts (rejected)
  - Zero amounts (rejected)
  - Invalid asset types (rejected)
  - Non-existent wallets (created automatically or rejected based on context)
- **Concurrency**: Race conditions properly prevented
- **Precision**: Decimal amounts handled accurately (8 decimal places)
- **Wallet Creation**: New user wallets created on-demand
- **Error Handling**: Proper exceptions and HTTP status codes

## Load Testing

Performance testing using Locust to simulate realistic concurrent users.

### Setup

```bash
# Install Locust (if not already installed)
pip install locust

# Ensure services are running
docker-compose up -d
```

### Run Load Test

```bash
locust -f locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 -t 60s
```

**Parameters:**
- `-u 100`: 100 concurrent users
- `-r 10`: Spawn 10 users per second
- `-t 60s`: Run for 60 seconds
- `--headless`: Run without web UI (CLI only)

### Test Configuration

**Workload Distribution:**
- 60% balance checks (`GET /wallets/:id/balance`)
- 20% topup transactions (`POST /transactions/topup`)
- 10% bonus transactions (`POST /transactions/bonus`)
- 10% spend transactions (`POST /transactions/spend`)
- 5% health checks (`GET /health`)

This distribution simulates realistic application usage where balance checks are frequent but transactions are less common.

### Performance Results

Results from load test with 100 concurrent users over 60 seconds:

| Endpoint | Median Response Time | P95 Response Time | P99 Response Time | Throughput |
|----------|---------------------|-------------------|-------------------|------------|
| Balance Check | 8ms | 19ms | 31ms | 26.5 req/s |
| Topup Transaction | 25ms | 59ms | 140ms | 8.9 req/s |
| Bonus Transaction | 23ms | 47ms | 130ms | 4.5 req/s |
| Spend Transaction | 36ms | 130ms | 240ms | 4.4 req/s |
| Health Check | 3ms | 5ms | 9ms | 2.1 req/s |
| **Aggregate** | **8ms** | **70ms** | **260ms** | **~48 req/s** |

### Key Observations

**Performance:**
- System maintains sub-40ms median response times under load
- 95% of requests complete in under 70ms
- P99 latency of 260ms is acceptable for financial operations

**Reliability:**
- Zero deadlocks detected
- Zero race conditions detected
- No data corruption or negative balances
- Spend transactions (most critical path) handled reliably with proper balance validation

**Error Rates:**
- Expected 404 errors for non-existent wallets (43%) are application-level checks, not system failures
- All validation errors (400s) are expected behavior for invalid requests
- No 500 Internal Server Errors under normal load

### Load Testing Tips

1. **Warm-up Period**: The first few seconds show higher latency as connection pools initialize
2. **Database Connections**: The system uses connection pooling (pool_size=10, max_overflow=20)
3. **Realistic Scenarios**: Modify `locustfile.py` to match your expected production traffic patterns
4. **Monitoring**: Watch MySQL processlist during load tests to verify lock contention is minimal

## Debugging Failed Tests

### Common Issues

**Database Connection Errors:**
```bash
# Ensure MySQL is running
docker-compose ps

# Check database logs
docker-compose logs db
```

**Port Conflicts:**
```bash
# Check if port 3306 or 8000 is already in use
lsof -i :3306
lsof -i :8000
```

**Stale Data in Concurrency Tests:**
```bash
# Restart containers for clean slate
docker-compose restart

# Or completely reset database
docker-compose down -v
docker-compose up -d
```

**Import Errors:**
```bash
# Ensure you're in the project root
cd /path/to/wallet-service

# Run tests with proper Python path
pytest tests/ -v
```

## Running Tests in CI/CD

Example GitHub Actions workflow:

```yaml
name: Tests
on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: rootpassword
          MYSQL_DATABASE: wallet_db
        ports:
          - 3306:3306
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-python@v4
        with:
          python-version: '3.11'
      - run: pip install -r requirements.txt
      - run: pytest tests/ -v
```

## Test Data

The test suite uses:
- **System wallets**: Pre-seeded Treasury, Marketing, Revenue accounts
- **Asset types**: COIN, GEM, GOLD
- **Test users**: Random user IDs (10000-99999) to avoid conflicts
- **Idempotency keys**: UUID v4 for uniqueness

## Writing New Tests

When adding new functionality, follow the existing test patterns:

1. **Repository tests**: Test SQL operations and database constraints
2. **Service tests**: Test business logic and error handling
3. **API tests**: Test HTTP endpoints and response formats
4. **Concurrency tests**: Test race conditions if touching wallet balances

Always include:
- Success path tests
- Idempotency tests (for transactions)
- Error handling tests
- Edge case tests
