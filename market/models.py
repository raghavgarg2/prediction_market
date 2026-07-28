from django.db import models
from django.contrib.auth.models import User


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

    class OutcomeName(models.TextChoices):
            YES = "YES", "Yes"
            NO = "NO", "No"

    market = models.ForeignKey(Market, on_delete=models.CASCADE, related_name="outcomes")
    name = models.CharField(max_length=10, choices=OutcomeName.choices)
    is_winner = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

   

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["market", "name"], name="unique_outcome_per_market")
        ]

    def __str__(self):
        return f"{self.market.title} - {self.name}"


class Order(models.Model):

    class OrderType(models.TextChoices):
        BUY = "BUY", "Buy"
        SELL = "SELL", "Sell"

    class Status(models.TextChoices):
        OPEN = "OPEN", "Open"
        PARTIALLY_FILLED = "PARTIALLY_FILLED", "Partially Filled"
        FILLED = "FILLED", "Filled"
        CANCELLED = "CANCELLED", "Cancelled"

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="orders")
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, related_name="orders")
    order_type = models.CharField(max_length=4, choices=OrderType.choices)
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    remaining_quantity = models.PositiveIntegerField()
    status = models.CharField(max_length=30, choices=Status.choices, default=Status.OPEN)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.user.username} {self.order_type} {self.quantity}"





class Trade(models.Model):
    buy_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="buy_trades")
    sell_order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="sell_trades")
    price = models.DecimalField(max_digits=12, decimal_places=2)
    quantity = models.PositiveIntegerField()
    executed_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Trade #{self.id}"





class Position(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="positions")
    outcome = models.ForeignKey(Outcome, on_delete=models.CASCADE, related_name="positions")
    quantity = models.PositiveIntegerField()
    locked_quantity = models.PositiveIntegerField(default=0)
    average_price = models.DecimalField(max_digits=12, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["user", "outcome"], name="unique_position_per_outcome")
        ]

    def __str__(self):
        return f"{self.user.username} - {self.outcome.name}"

