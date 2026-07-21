from django.db import models
from django.contrib.auth.models import User

class Wallet(models.Model):
    user = models.OneToOneField(User,on_delete=models.CASCADE,related_name="wallet")
    available_balance = models.DecimalField(max_digits=12,decimal_places=2, default=0)
    locked_balance = models.DecimalField(max_digits=12,decimal_places=2,default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username}'s Wallet"
    



class WalletTransaction(models.Model):
    class TransactionType(models.TextChoices):
        DEPOSIT = "DEPOSIT", "Deposit"
        WITHDRAW = "WITHDRAW", "Withdraw"
        LOCK = "LOCK", "Lock Funds"
        UNLOCK = "UNLOCK", "Unlock Funds"
        SETTLEMENT = "SETTLEMENT", "Settlement"
        REFUND = "REFUND", "Refund"
    
    wallet = models.ForeignKey(Wallet,on_delete=models.CASCADE,related_name="transactions")
    transaction_type = models.CharField(max_length=20,choices=TransactionType.choices)
    amount = models.DecimalField(max_digits=12,decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    description = models.CharField(max_length=255,blank=True)

    def __str__(self):
       return (
        f"{self.wallet.user.username} | "
        f"{self.transaction_type} | "
        f"₹{self.amount}"
    )

class Market(models.Model):

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        CLOSED = "CLOSED", "Closed"
        RESOLVED = "RESOLVED", "Resolved"

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.OPEN)
    close_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title
    
class Outcome(models.Model):
    market = models.ForeignKey(Market,on_delete=models.CASCADE,related_name="outcomes")
    name = models.CharField(max_length=255)
    is_winner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
      return f"{self.market.title} - {self.name}"

class Order(models.Model):
    class OrderType(models.TextChoices):
        BUY = "BUY","buy"
        SELL = "SELL","sell"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIALLY_FILLED = "PARTIALLY_FILLED", "Partially Filled"
        FILLED = "FILLED", "Filled"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="orders")
    outcome = models.ForeignKey(Outcome,on_delete=models.CASCADE,related_name="orders")
    order_type = models.CharField(max_length=4,choices=OrderType.choices)
    price = models.DecimalField(max_digits=12,decimal_places=2)
    quantity = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=30,choices=Status.choices,default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
      return f"{self.user.username} {self.order_type} {self.quantity}"



class Trade(models.Model):
    buy_order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name="buy_trades")
    sell_order = models.ForeignKey(Order,on_delete=models.CASCADE,related_name="sell_trades")
    price = models.DecimalField(max_digits=12,decimal_places=2)
    quantity = models.PositiveIntegerField()
    executed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
      return f"Trade #{self.id}"



class Position(models.Model):
    user = models.ForeignKey(User,on_delete=models.CASCADE,related_name="positions")
    outcome = models.ForeignKey(Outcome,on_delete=models.CASCADE,related_name="positions")
    quantity = models.PositiveIntegerField()
    average_price = models.DecimalField(max_digits=12,decimal_places=2)
    updated_at = models.DateTimeField(auto_now=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
      return f"{self.user.username} - {self.outcome.name}"

