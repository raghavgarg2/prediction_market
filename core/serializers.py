from rest_framework import serializers
from django.contrib.auth.models import User
from .models import Wallet
from django.contrib.auth.password_validation import validate_password
from rest_framework.validators import UniqueValidator


class RegisterSerializer(serializers.ModelSerializer):

    password = serializers.CharField(
        write_only=True,
    )

    email = serializers.EmailField(
        validators=[
            UniqueValidator(
                queryset=User.objects.all(),
                message="Email already exists.",
            )
        ],
    )

    class Meta:

        model = User

        fields = [
            "id",
            "username",
            "email",
            "password",
        ]

    def validate_email(self, value):

        return value.lower()

    def validate_password(self, value):

        validate_password(value)

        return value

    def create(self, validated_data):

        return User.objects.create_user(
            **validated_data,
        )
    

class LoginSerializer(serializers.Serializer):

    username = serializers.CharField()
    password = serializers.CharField(
        write_only = True
    )


class DepositSerializer(serializers.Serializer):
    amount = serializers.DecimalField(max_digits=12,decimal_places=2,min_value=0.01)



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


