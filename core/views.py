from django.shortcuts import render
from rest_framework.views import APIView
from .serializers import RegisterSerializer,LoginSerializer,DepositSerializer,WalletSerializer
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




class WalletAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self,request):
        serializer = DepositSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)

        wallet = Wallet.objects.get(user = request.user)

        with transaction.atomic():
           wallet.available_balance = wallet.available_balance + serializer.validated_data["amount"]
           wallet.save()

           WalletTransaction.objects.create(
              wallet = wallet,
              transaction_type = "DEPOSIT",
              amount = serializer.validated_data["amount"]
        )

        return Response({
            "msg" : "money deposited successfully",
            "wallet" : WalletSerializer(wallet).data
        },
        status = status.HTTP_200_OK)

    def post(self,request):

       serializer = DepositSerializer(data = request.data)
       serializer.is_valid(raise_exception=True)
       wallet = Wallet.objects.get(user = request.user)
       if(wallet.available_balance < serializer.validated_data["amount"]):
           return Response({
               "msg" : "Insufficient balance"
           },status=status.HTTP_400_BAD_REQUEST)

       with transaction.atomic():
            wallet.available_balance -= serializer.validated_data["amount"]
            wallet.save()
            WalletTransaction.objects.create(
               wallet = wallet,
               transaction_type = "WITHDRAW",
               amount = serializer.validated_data["amount"]
       )

       return Response({
           "msg" : "money withdrawn successfully",
           "wallet" : WalletSerializer(wallet).data
       },status=status.HTTP_200_OK)






# class PlaceOrderAPI(APIView):

#     def post(self,request,pk):

#         serializer = PlaceOrderSerializer(
#             data = request.data
#         )

#         serializer.is_valid(raise_exception=True)

#         market = get_object_or_404(Market,id = pk)

#         if(market.status != market.Status.OPEN):
#             return Response({
#                 "msg" : "market is closed."
#         })

#         outcome = serializer.validated_data["outcome"]
#         order_type = serializer.validated_data["order_type"]
#         price = serializer.validated_data["price"]
#         quantity = serializer.validated_data["quantity"]

#         with transaction.atomic():
#                 wallet = Wallet.objects.get(user = request.user)
#                 if(order_type == Order.OrderType.BUY):
#                     if(price * quantity > wallet.available_balance):
#                         return Response({
#                              "msg" : "insufficient balance"
#                         })
                    
#                     wallet.available_balance -= price * quantity
#                     wallet.locked_balance += price * quantity
#                     wallet.save(update_fields=["available_balance","locked_balance"])

#                     createdOrder = Order.objects.create(
#                         user = request.user,
#                         outcome = outcome,
#                         order_type = order_type,
#                         price = price,
#                         quantity = quantity,
#                         remaining_quantity = quantity,
#                         status = Order.Status.OPEN
#                     )

#                     matchingOrders = Order.objects.filter(
#                         order_type = Order.OrderType.SELL,
#                         price__lte = price,
#                         outcome = outcome,
#                         status__in = [Order.Status.OPEN,Order.Status.PARTIALLY_FILLED]
#                     ).order_by("price","created_at")

#                     remaining_quantity = quantity
#                     quantityToBeTraded = 0
#                     for order in matchingOrders:

#                         if order.remaining_quantity > remaining_quantity:
#                             quantityToBeTraded = remaining_quantity

#                         # update the status and remaining_quantity of order and createdOrder in Order
#                             createdOrder.status = Order.Status.FILLED
#                             createdOrder.remaining_quantity = 0

#                             order.status = Order.Status.PARTIALLY_FILLED
#                             order.remaining_quantity = order.remaining_quantity -     quantityToBeTraded
    
#                         elif order.remaining_quantity < remaining_quantity :

#                             quantityToBeTraded = order.remaining_quantity

#                             createdOrder.status = Order.Status.PARTIALLY_FILLED
#                             createdOrder.remaining_quantity = createdOrder.remaining_quantity -     quantityToBeTraded

#                             order.status = Order.Status.FILLED
#                             order.remaining_quantity = 0

#                         else:

#                             quantityToBeTraded = remaining_quantity
#                             createdOrder.status = Order.Status.FILLED
#                             createdOrder.remaining_quantity = 0

#                             order.status = Order.Status.FILLED
#                             order.remaining_quantity = 0

#                         order.save(update_fields=["status","remaining_quantity"])
#                         createdOrder.save(update_fields=["status","remaining_quantity"])



#                          #entry in trades table
#                         Trade.objects.create(
#                             buy_order = createdOrder,
#                             sell_order = order,
#                             price = order.price,
#                             quantity = quantityToBeTraded
#                         )

#                          # update the positions table of order and createdOrder
                    
#                         buyOrderPosition ,created= Position.objects.get_or_create(
#                                 user = request.user,
#                                 outcome = outcome,
#                                 defaults={"quantity" : quantityToBeTraded , "average_price" : order.price}
                    
#                         )
#                         if not created :
#                             buyOrderPosition.average_price = (buyOrderPosition.average_price *     buyOrderPosition.quantity + order.price * quantityToBeTraded)/    (buyOrderPosition.quantity + quantityToBeTraded)
                    
#                             buyOrderPosition.quantity = buyOrderPosition.quantity +     quantityToBeTraded
                    
#                             buyOrderPosition.save(update_fields=["average_price","quantity"])
                    
#                         sellOrderPosition = Position.objects.get(
#                                     user = order.user,
#                                     outcome = outcome
#                                 )
                    
#                         sellOrderPosition.quantity -= quantityToBeTraded
#                         if(sellOrderPosition.quantity == 0):
#                             sellOrderPosition.delete()
#                         else:
#                             sellOrderPosition.save(update_fields=["quantity"])

#                         orderWallet = Wallet.objects.get(user = order.user)
#                         # wallettransactions of both order and createdOrder
#                         WalletTransaction.objects.create(
#                                 wallet = wallet,
#                                 transaction_type = WalletTransaction.TransactionType.BUY,
#                                 amount = order.price * quantityToBeTraded,
#                                 description = f"bought {quantityToBeTraded} shares of ${outcome}     at price {order.price}"
#                             )
                        
#                         WalletTransaction.objects.create(
#                             wallet = orderWallet,
#                             transaction_type = WalletTransaction.TransactionType.SELL,
#                             amount = order.price * quantityToBeTraded,
#                             description = f"sold {quantityToBeTraded} shares of ${outcome} at price {order.price}"
                        
#                     )

#                     # update the wallets
#                         buyer_price = createdOrder.price
#                         trade_price = order.price
#                         qty = quantityToBeTraded

#                         # Remove the full amount that was reserved for these shares
#                         wallet.locked_balance -= buyer_price * qty

#                         # Refund the price improvement to the buyer
#                         wallet.available_balance += (buyer_price - trade_price) * qty

#                         # Pay the seller
#                         orderWallet.available_balance += trade_price * qty
#                         wallet.save(update_fields=["locked_balance", "available_balance"])
#                         orderWallet.save(update_fields=["available_balance"])

#                         remaining_quantity = remaining_quantity - quantityToBeTraded
#                         if remaining_quantity == 0:
#                           break
                       

#                 else:
#                     position = get_object_or_404(Position,outcome = outcome,user = request.user)

#                     if(position.quantity < quantity):
#                         return Response({
#                             "msg" : "you don't have enough shares."
#                         })

#                     createdOrder = Order.objects.create(
#                         user = request.user,
#                         outcome = outcome,
#                         order_type = order_type,
#                         price = price,
#                         quantity = quantity,
#                         remaining_quantity = quantity,
#                         status = Order.Status.OPEN
#                     )

#                     matchingOrders = Order.objects.filter(
#                         order_type = Order.OrderType.BUY,
#                         price__gte = price,
#                         outcome = outcome,
#                         status__in = [Order.Status.OPEN,Order.Status.PARTIALLY_FILLED]
#                     ).order_by("price","created_at")

#                     remaining_quantity = quantity
#                     quantityToBeTraded = 0

#                     for order in matchingOrders:

#                         if order.remaining_quantity > remaining_quantity:
#                             quantityToBeTraded = remaining_quantity

#                              # update the status and remaining_quantity of order and createdOrder in Order
#                             createdOrder.status = Order.Status.FILLED
#                             createdOrder.remaining_quantity = 0
                        
#                             order.status = Order.Status.PARTIALLY_FILLED
#                             order.remaining_quantity = order.remaining_quantity -     quantityToBeTraded
                            
                        
#                         elif order.remaining_quantity < remaining_quantity :
                        
#                             quantityToBeTraded = order.remaining_quantity
#                             createdOrder.status = Order.Status.PARTIALLY_FILLED
#                             createdOrder.remaining_quantity = createdOrder.remaining_quantity -     quantityToBeTraded
                        
#                             order.status = Order.Status.FILLED
#                             order.remaining_quantity = 0
                        
                            
#                         else:
                        
#                             quantityToBeTraded = remaining_quantity
#                             createdOrder.status = Order.Status.FILLED
#                             createdOrder.remaining_quantity = 0
                        
#                             order.status = Order.Status.FILLED
#                             order.remaining_quantity = 0
                        
#                         order.save(update_fields=["status","remaining_quantity"])
#                         createdOrder.save(update_fields=["status","remaining_quantity"])


#                          #entry in trades table
#                         Trade.objects.create(
#                                 buy_order = order,
#                                 sell_order = createdOrder,
#                                 price = createdOrder.price,
#                                 quantity = quantityToBeTraded
#                         )


#                         # update the positions table of order and createdOrder

#                         buyOrderPosition ,created= Position.objects.get_or_create(
#                                 user = order.user,
#                                 outcome = outcome,
#                                 defaults={"quantity" : quantityToBeTraded , "average_price" : order.price}
                                            
#                             )
#                         if not created :
#                                 buyOrderPosition.average_price = (buyOrderPosition.average_price *     buyOrderPosition.quantity + order.price * quantityToBeTraded)/    (buyOrderPosition.quantity + quantityToBeTraded)
                                            
#                                 buyOrderPosition.quantity = buyOrderPosition.quantity +     quantityToBeTraded
                                            
#                                 buyOrderPosition.save(update_fields=["average_price","quantity"])
                                            
#                         sellOrderPosition = Position.objects.get(
#                                 user = request.user,
#                                 outcome = outcome
#                         )
                                            
#                         sellOrderPosition.quantity -= quantityToBeTraded
#                         if(sellOrderPosition.quantity == 0):
#                             sellOrderPosition.delete()
#                         else:
#                             sellOrderPosition.save(update_fields=["quantity"])


#                         orderWallet = Wallet.objects.get(user = order.user)
#                         # wallettransactions of both order and createdOrder
#                         WalletTransaction.objects.create(
#                                 wallet = orderWallet,
#                                 transaction_type = WalletTransaction.TransactionType.BUY,
#                                 amount = order.price * quantityToBeTraded,
#                                 description = f"bought {quantityToBeTraded} shares of ${outcome}     atprice {order.price}"
#                             )
                                                
#                         WalletTransaction.objects.create(
#                                 wallet = wallet,
#                                 transaction_type = WalletTransaction.TransactionType.SELL,
#                                 amount = order.price * quantityToBeTraded,
#                                 description = f"sold {quantityToBeTraded} shares of ${outcome} at price {order.price}"
                                                
#                         )

#                         # update the wallets
#                         buyer_price = order.price
#                         trade_price = createdOrder.price
#                         qty = quantityToBeTraded
                        
#                         # Remove the full amount that was reserved for these shares
#                         orderWallet.locked_balance -= buyer_price * qty

#                         # Refund the price improvement to the buyer
#                         orderWallet.available_balance += (buyer_price - trade_price) * qty
                        
#                         # Pay the seller
#                         wallet.available_balance += trade_price * qty
#                         orderWallet.save(update_fields=["locked_balance", "available_balance"])
#                         wallet.save(update_fields=["available_balance"])
                        
#                         remaining_quantity = remaining_quantity - quantityToBeTraded
#                         if remaining_quantity == 0:
#                             break
                        





# class CancelOrderAPI(APIView):

    def post(self,request,pk):

        order = get_object_or_404(Order,id = pk,user = request.user)
        if(order.status not in [Order.Status.OPEN , Order.Status.PARTIALLY_FILLED] ):
            return Response({
                "msg" : "cannot cancel order"
        })

        with transaction.atomic():

            # update the status of order
            order.status = Order.Status.CANCELLED
            order.save(update_fields=["status"])

             # unlock money
            wallet = Wallet.objects.get(user = request.user)

            wallet.locked_balance -= order.price * order.remaining_quantity
            wallet.available_balance += order.price * order.remaining_quantity
            wallet.save(update_fields=["locked_balance","available_balance"])

            #make wallet transactions

            WalletTransaction.objects.create(
                wallet = wallet,
                transaction_type = WalletTransaction.TransactionType.REFUND,
                amount = order.price * order.remaining_quantity,
                description = "order cancel refund"
            )

        return Response({
            "msg" : "order cancelled successfully"
        })













      
       
        







                    


                    










        

        









       



        

    


        

