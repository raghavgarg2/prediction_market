from django.db import models
from django.contrib.auth.models import User


class Wallet(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="wallet")
    available_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    locked_balance = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet"


class WalletTransaction(models.Model):

    class TransactionType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAW = "WITHDRAW", "Withdraw"
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"
        LOCK = "LOCK", "Lock Funds"
        UNLOCK = "UNLOCK", "Unlock Funds"
        SPLIT = "SPLIT", "Split"
        MERGE = "MERGE", "Merge"
        SETTLEMENT = "SETTLEMENT", "Settlement"
        REFUND = "REFUND", "Refund"

    wallet = models.ForeignKey(Wallet, on_delete=models.CASCADE,related_name="transactions")
    transaction_type = models.CharField(max_length=20, choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    description = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return (
            f"{self.wallet.user.username} | "
            f"{self.transaction_type} | "
            f"₹{self.amount}"
        )






