class TransactionType:
    TOPUP = "TOPUP"
    SPEND = "SPEND"
    BONUS = "BONUS"
    TRANSFER = "TRANSFER"

class SystemWalletType:
    TREASURY = "TREASURY"
    MARKETING = "MARKETING"
    REVENUE = "REVENUE"

class TransactionStatus:
    PENDING = "PENDING"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"

SYSTEM_USER_IDS = {
    "TREASURY": -1,
    "MARKETING": -2,
    "REVENUE": -3
}