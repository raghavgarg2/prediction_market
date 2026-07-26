from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Wallet,Market,Outcome,Position,WalletTransaction,Order,Trade



class RegisterSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only = True)
    class Meta :
        model = User
        fields = [
            "id",
            "username",
            "email",
            "password"
        ]
    
    def create(self,validated_data):
        return User.objects.create_user(**validated_data)
    

class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()
    password = serializers.CharField(
        write_only = True
    )


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12,decimal_places=2, default=0,min_value=0.01)



    # def validate_amount(self, value):
    #     if value <= 0:
    #         raise serializers.ValidationError(
    #             "Amount must be greater than 0."
    #         )

    #     return value



class WalletSerializer(serializers.ModelSerializer):

    class Meta :
        model = Wallet
        fields = [
            "available_balance",
            "locked_balance"
        ]


class MarketSerializer(serializers.ModelSerializer):
    class Meta : 
        model = Market
        fields = [
            "title",
            "description",
            "close_at"
        ]


class MarketOutputSerializer(serializers.ModelSerializer):
    class Meta : 
        model = Market
        fields = [
            "id",
            "title",
            "description",
            "status",
            "close_at"
        ]


class OutcomeSerializer(serializers.ModelSerializer):

    class Meta :
        model = Outcome
        fields = [
            "id",
            "name"
        ]

class MarketDetailSerializer(serializers.ModelSerializer):
    outcomes = OutcomeSerializer(many = True,read_only = True)

    class Meta :
        model = Market
        fields = [
            "id",
            "title",
            "description",
            "status",
            "close_at",
            "outcomes"

        ]


class PlaceOrderSerializer(serializers.ModelSerializer):
    pass


class MergeSerializer(serializers.Serializer):

    quantity = serializers.PositiveIntegerField()



class ResolveMarketSerializer(serializers.Serializer):

    winner = serializers.ChoiceField(
        choices=["YES","NO"]
    )


class PortfolioSerializer(serializers.ModelSerializer):
    market = serializers.CharField(source = "outcome.market.title")
    outcome = serializers.CharField(source = "outcome.name")
    class Meta : 
        model = Position
        fields = [
            "quantity",
            "average_price",
            "outcome",
            "market"
        ]



class TransactionSerializer(serializers.ModelSerializer):

    class Meta :
        model = WalletTransaction
        fields = [
            "transaction_type",
            "amount",
            "description",
            "created_at"
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
            "executed_at"
        ]