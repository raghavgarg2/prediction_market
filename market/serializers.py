
from rest_framework import serializers
from .models import Market,Outcome,Position,Order,Trade
from core.models import WalletTransaction
from django.utils import timezone
from decimal import Decimal


class CreateMarketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Market
        fields = [
            "title",
            "description",
            "close_at"
        ]

    def validate_close_at(self, value):
        if value <= timezone.now():
            raise serializers.ValidationError(
                "Close time must be in the future."
            )
        return value



class MarketSerializer(serializers.ModelSerializer):

    class Meta:
        model = Market
        fields = [
            "id",
            "title",
            "description",
            "status",
            "close_at"
        ]
        read_only_fields = fields


class OutcomeSerializer(serializers.ModelSerializer):

    class Meta :
        model = Outcome
        fields = [
            "id",
            "name"
        ]


class MarketDetailSerializer(serializers.ModelSerializer):

    outcomes = OutcomeSerializer(many=True,read_only=True)

    class Meta:
        model = Market
        fields = [
            "id",
            "title",
            "description",
            "status",
            "close_at",
            "outcomes"
        ]



class SplitSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12,decimal_places=2,min_value=Decimal("0.01")
    )


class MergeSerializer(serializers.Serializer):
    quantity = serializers.PositiveIntegerField()


class ResolveMarketSerializer(serializers.Serializer):

    winner = serializers.ChoiceField(
        choices=["YES","NO"]
    )


class PortfolioSerializer(serializers.ModelSerializer):

    market = serializers.CharField(source="outcome.market.title")
    outcome = serializers.CharField(source="outcome.name")

    class Meta:
        model = Position
        fields = [
            "quantity",
            "average_price",
            "outcome",
            "market",
        ]


class TransactionSerializer(serializers.ModelSerializer):

    class Meta:
        model = WalletTransaction
        fields = [
            "transaction_type",
            "amount",
            "description",
            "created_at",
        ]


class MyOrdersSerializer(serializers.ModelSerializer):

    market = serializers.CharField(source = "outcome.market.title")
    outcome = serializers.CharField(source = "outcome.name")
    class Meta :
        model = Order
        fields = [
            "id",
            "market",
            "outcome",
            "order_type",
            "price",
            "quantity",
            "remaining_quantity",
            "status",
            "created_at"
        ]


class TradeSerializer(serializers.ModelSerializer):

    class Meta:
        model = Trade
        fields = [
            "price",
            "quantity",
            "executed_at",
        ]