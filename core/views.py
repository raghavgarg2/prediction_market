from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import RegisterSerializer,LoginSerializer,DepositSerializer,WalletSerializer,MarketSerializer,MarketOutputSerializer,MarketDetailSerializer,PlaceOrderSerializer,MergeSerializer,ResolveMarketSerializer,PortfolioSerializer,TransactionSerializer,MyOrdersSerializer,TradeSerializer
from rest_framework.response import Response
from rest_framework import status
from django.contrib.auth import authenticate
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework.permissions import IsAuthenticated
from .models import Wallet,WalletTransaction,Market,Outcome,Position,Order,Trade
from django.db import transaction
from django.shortcuts import get_object_or_404
from decimal import Decimal
from django.utils import timezone
from django.contrib.auth.models import User




class RegisterAPIView(APIView):

    def post(self, request):
        serializer = RegisterSerializer(
            data=request.data
        )
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():
            user = serializer.save()

            Wallet.objects.create(
                user=user
            )

        return Response(
            {
                "msg": "User created successfully",
                "user": serializer.data
            },
            status=status.HTTP_201_CREATED
        )


        
class LoginAPIView(APIView):

    def post(self,request):
        serializer = LoginSerializer(
            data = request.data
            )
        
        serializer.is_valid(raise_exception=True)

        user = authenticate(
            **serializer.validated_data
        )

        if user is None:
            return Response({
                "msg" : "invalid credentials"
            },status=status.HTTP_401_UNAUTHORIZED)
        
        refresh = RefreshToken.for_user(user)

        refresh_token = str(refresh)
        access_token = str(refresh.access_token)

        return Response({
            "msg" : "logged in successfully",
            "refreshToken" : refresh_token,
            "accessToken" : access_token
        },
        status=status.HTTP_200_OK)




class DepositAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = DepositSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        amount = serializer.validated_data["amount"]

        with transaction.atomic():

            wallet = (
                Wallet.objects
                .select_for_update()
                .get(user=request.user)
            )

            wallet.available_balance += amount

            wallet.save(
                update_fields=[
                    "available_balance",
                ]
            )

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.DEPOSIT,
                amount=amount,
            )

        return Response(
            {
                "msg": "Money deposited successfully.",
                "wallet": WalletSerializer(wallet).data,
            },
            status=status.HTTP_200_OK,
        )





class WithdrawAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = DepositSerializer(
            data=request.data,
        )

        serializer.is_valid(
            raise_exception=True,
        )

        amount = serializer.validated_data["amount"]

        with transaction.atomic():

            wallet = (
                Wallet.objects
                .select_for_update()
                .get(user=request.user)
            )

            if wallet.available_balance < amount:

                return Response(
                    {
                        "msg": "Insufficient balance.",
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            wallet.available_balance -= amount

            wallet.save(
                update_fields=[
                    "available_balance",
                ]
            )

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.WITHDRAW,
                amount=amount,
            )

        return Response(
            {
                "msg": "Money withdrawn successfully.",
                "wallet": WalletSerializer(wallet).data,
            },
            status=status.HTTP_200_OK,
        )
       
        

class WalletAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        wallet = get_object_or_404(
            Wallet,
            user=request.user,
        )

        return Response(
            WalletSerializer(wallet).data,
            status=status.HTTP_200_OK,
        )





                    


                    










        

        









       



        

    


        

