class WalletException(Exception):
    """Base exception for all wallet-related errors"""
    def __init__(self, message: str, code: str = "WALLET_ERROR"):
        self.message = message
        self.code = code
        super().__init__(self.message)

class InsufficientFundsError(WalletException):
    def __init__(self, message: str = "Insufficient funds to complete transaction"):
        super().__init__(message, code="INSUFFICIENT_FUNDS")

class WalletNotFoundError(WalletException):
    def __init__(self, message: str = "The requested wallet was not found"):
        super().__init__(message, code="WALLET_NOT_FOUND")

class DuplicateTransactionError(WalletException):
    def __init__(self, message: str = "Transaction with this idempotency key already exists"):
        super().__init__(message, code="DUPLICATE_TRANSACTION")