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

    def post(self,request):
        serializer = RegisterSerializer(
            data = request.data
        )
        serializer.is_valid(raise_exception=True)

        serializer.save()

        return Response({
            "msg" : "User created successfully",
            "user" : serializer.data
        },status = status.HTTP_201_CREATED)



        
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




class MarketAPIView(APIView):

    def post(self,request):

        serializer = MarketSerializer(data = request.data)
        serializer.is_valid(raise_exception=True)
        with transaction.atomic():
           market =  Market.objects.create(
               **serializer.validated_data
           )

           Outcome.objects.create(
              market = market,
              name = "YES"
          )
           Outcome.objects.create(
              market = market,
              name = "NO"
           )
             
        return Response({
            "msg" : "market created successfully"
        },status=status.HTTP_201_CREATED)


    def get(self,request):

        markets = Market.objects.filter(status = "OPEN")

        serializer = MarketOutputSerializer(markets,many = True)

        return Response(
            serializer.data
        )

    def get(self,request,pk):

       market =  get_object_or_404(Market,id = pk)
    
       return Response(
          MarketDetailSerializer(market).data
        
       )

    def post(self, request, pk):

        serializer = DepositSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data["amount"]

        market = get_object_or_404(Market, id=pk)

        if market.status != "OPEN":
            return Response(
                {"msg": "Market is closed"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        wallet = Wallet.objects.get(user=request.user)

        if wallet.available_balance < amount:
            return Response(
                {"msg": "Insufficient balance"},
                status=status.HTTP_400_BAD_REQUEST,
            )

        yes_outcome = market.outcomes.get(name="YES")
        no_outcome = market.outcomes.get(name="NO")

        with transaction.atomic():

            # Deduct wallet balance
            wallet.available_balance -= amount
            wallet.save()

            # Wallet transaction
            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="SPLIT",
                amount=amount,
                description="Split into prediction shares",
            )

            # ---------- YES POSITION ----------

            yes_position, created = Position.objects.get_or_create(
                user=request.user,
                outcome=yes_outcome,
                defaults={
                    "quantity": Decimal("0"),
                    "average_price": Decimal("0.00"),
                },
            )

            if created:
                yes_position.quantity = amount
                yes_position.average_price = Decimal("1.00")
            else:
                total_quantity = yes_position.quantity + amount

                yes_position.average_price = (
                    (yes_position.average_price * yes_position.quantity)
                    + (Decimal("1.00") * amount)
                ) / total_quantity

                yes_position.quantity = total_quantity

            yes_position.save()

            # ---------- NO POSITION ----------

            no_position, created = Position.objects.get_or_create(
                user=request.user,
                outcome=no_outcome,
                defaults={
                    "quantity": Decimal("0"),
                    "average_price": Decimal("0.00"),
                },
            )

            if created:
                no_position.quantity = amount
                no_position.average_price = Decimal("1.00")
            else:
                total_quantity = no_position.quantity + amount

                no_position.average_price = (
                    (no_position.average_price * no_position.quantity)
                    + (Decimal("1.00") * amount)
                ) / total_quantity

                no_position.quantity = total_quantity

            no_position.save()

        return Response(
            {
                "message": "Split successful"
            },
            status=status.HTTP_200_OK,
        )


# {
#     "outcome": "YES",
#     "order_type": "BUY",
#     "price": "7.50",
#     "quantity": 20
# }

# class PlaceOrderAPIView(APIView):

#     def post(self,request,pk):

#         market = get_object_or_404(Market,id = pk)
#         if(market.status != "OPEN"):
#             return Response({
#                 "msg" : "market is closed"
#             })

#         serializer = PlaceOrderSerializer(data = request.data)

#         serializer.is_valid(raise_exception=True)

#         price = serializer.validated_data["price"]
#         quantity = serializer.validated_data["quantity"]
#         orderType = serializer.validated_data["order_type"]
#         outcome = serializer.validated_data["outcome"]

#         wallet = Wallet.objects.get(user = request.user)

#         with transaction.atomic():
#             createdOrder = Order.objects.create(
#                 user = request.user,
#                 outcome = outcome,
#                 order_type = orderType,
#                 price = price,
#                 quantity = quantity,
#                 remaining_quantity = quantity,
#                 status = Order.Status.OPEN
#                 )

#             if orderType == "BUY":

#               if(wallet.available_balance < price * quantity ):
#                 return Response({
#                     "msg" : "insufficient balance"
#                 })

#             matching_orders = (
#                 Order.objects.filter(
#                 outcome = outcome,
#                 order_type = Order.OrderType.SELL,
#                 status = Order.Status.OPEN,
#                 price__lte = price
#                 )
#             .order_by("price","created_at")
#         )
#             for order in matching_orders:

#                if order.quantity > quantity:
#                   order.remaining_quantity = order.quantity - quantity
#                   order.status = Order.Status.PARTIALLY_FILLED
#                   order.save()

#                   createdOrder.status = Order.Status.FILLED
#                   createdOrder.remaining_quantity = 0
#                   createdOrder.save()

#                   Trade.objects.create(
#                     buy_order = createdOrder,
#                     sell_order = order,
#                     price = order.price,
#                     quantity = quantity
#                 )

#                   position,created = Position.objects.get_or_create(
#                     user = request.user,
#                     outcome = outcome,
#                     defaults={"average_price" : order.price,"quantity" : quantity}

#                 )
#                   if not created :
        
#                     position.average_price = position.average_price * position.quantity + createdOrder.quantity / (createdOrder.quantity + position.quantity)
#                     position.quantity = createdOrder.quantity + position.quantity
#                break

#              elif order.quantity == quantity:
#                  order.remaining_quantity = 0
#                 order.status = Order.Status.FILLED
#                 order.save()

                
#                 createdOrder.status = Order.Status.FILLED
#                 createdOrder.remaining_quantity = 0
#                 createdOrder.save()

#                 Trade.objects.create(
#                     buy_order = createdOrder,
#                     sell_order = order,
#                     price = order.price,
#                     quantity = quantity
#                 )
#                 position,created = Position.objects.get_or_create(
#                     user = request.user,
#                     outcome = outcome,
#                     defaults={"average_price" : order.price,"quantity" : quantity}
#                 )
#                 if not created :
#                     position.average_price = position.average_price * position.quantity + createdOrder.quantity / (createdOrder.quantity + position.quantity)
#                     position.quantity = createdOrder.quantity + position.quantity

#                 break

#             else:
#                 order.remaining_quantity = 0
#                 order.status = Order.Status.FILLED
#                 order.save()
                
#                 createdOrder.status = Order.Status.PARTIALLY_FILLED
#                 createdOrder.remaining_quantity = quantity - order.quantity
#                 createdOrder.save()

#                 Trade.objects.create(
#                     buy_order = createdOrder,
#                     sell_order = order,
#                     price = order.price,
#                     quantity = quantity
#                 )
#                 position,created = Position.objects.get_or_create(
#                     user = request.user,
#                     outcome = outcome,
#                     defaults={"average_price" : order.price,"quantity" : quantity}
#                     )
#                 if not created :
#                     position.average_price = position.average_price * position.quantity + createdOrder.quantity / (createdOrder.quantity + position.quantity)
#                     position.quantity = createdOrder.quantity + position.quantity
                




#         with transaction.atomic():

#             wallet = Wallet.objects.get(user = request.user)

#             wallet.locked_balance += price * quantity
#             wallet.available_balance -= price * quantity

#             wallet.save()

#             WalletTransaction.objects.create(
#                 wallet = wallet,
#                 transaction_type = "LOCK",
#                 amount = price * quantity
#             )
#             for order in matching_orders:
#                 pass





class MergeAPIView(APIView):

  def post(self, request, pk):

        serializer = MergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]

        market = get_object_or_404(Market, pk=pk)

        if market.status != market.status.OPEN:
            return Response(
                {"msg": "Market is not open."},
                status=status.HTTP_400_BAD_REQUEST
            )

        positions = Position.objects.filter(
            user=request.user,
            outcome__market=market
        )

        yes_position = None
        no_position = None

        for position in positions:
            if position.outcome.name == "YES":
                yes_position = position
            elif position.outcome.name == "NO":
                no_position = position

        if not yes_position or not no_position:
            return Response(
                {"msg": "You must own both YES and NO shares to merge."},
                status=status.HTTP_400_BAD_REQUEST
            )

        if (
            yes_position.quantity < quantity or
            no_position.quantity < quantity
        ):
            return Response(
                {"msg": "Insufficient shares to merge."},
                status=status.HTTP_400_BAD_REQUEST
            )

        wallet = get_object_or_404(Wallet, user=request.user)

        with transaction.atomic():

            yes_position.quantity -= quantity
            no_position.quantity -= quantity

            if yes_position.quantity == 0:
                yes_position.delete()
            else:
                yes_position.save()

            if no_position.quantity == 0:
                no_position.delete()
            else:
                no_position.save()

            wallet.available_balance += quantity
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type="MERGE",
                amount=quantity,
                description=f"Merged {quantity} YES-NO pairs in '{market.title}'"
            )

        return Response(
            {
                "message": "Shares merged successfully."
            },
            status=status.HTTP_200_OK
        )
            
            



class ResolveMarketAPIView(APIView):

    def post(self,request,pk):

        serializer = ResolveMarketSerializer(
            data = request.data
        )

        serializer.is_valid(raise_exception=True)

        winner = serializer.validated_data["winner"]

        market = get_object_or_404(Market,id = pk)


        if(market.status != market.Status.CLOSED):
            return Response({
                "msg" : "only closed markets can be resolved."
            })

        with transaction.atomic():

            market.status = market.Status.RESOLVED
            market.resolved_at = timezone.now()
            market.save()

            outcome = market.outcomes.get(name = winner)
            outcome.is_winner = True
            outcome.save()


        return Response({
            "msg" : "market resolved successfully"
        },status=status.HTTP_200_OK)



class SettlementAPIView(APIView):

    # def post(self,request,pk):

    #     market = get_object_or_404(Market,id = pk)

    #     if market.status != market.Status.RESOLVED:
    #         return Response({
    #             "msg" : "cannot settle because market is not resolved yet"
    #         })

    #     positions = Position.objects.filter(outcome__market = market)

    #     for position in positions:
            
    #         if position.outcome.is_winner:
    #             wallet = Wallet.objects.get(user = position.user)
    #             wallet.available_balance +=  position.quantity
    #             wallet.save()

    #             WalletTransaction.objects.create(
    #                 wallet = wallet,
    #                 transaction_type = WalletTransaction.TransactionType.SETTLEMENT,
    #                 amount =  position.quantity,
    #                 description = "Settlement"
    #             )

    #         position.delete()

    #     return Response({
    #         "msg" : "market settled successfully"
    #     })

    def post(self,request,pk):

        market = get_object_or_404(Market,id = pk)

        if market.status != market.Status.RESOLVED:
            return Response({
                "msg" : "cannot settle because market is not resolved yet"
            })

        positions = Position.objects.select_related("user","outcome").filter(outcome__market = market)

        with transaction.atomic():
            for position in positions:
            
                if position.outcome.is_winner:
                    wallet = Wallet.objects.get(user = position.user)
                    wallet.available_balance +=  position.quantity
                    wallet.save()

                    WalletTransaction.objects.create(
                       wallet = wallet,
                       transaction_type = WalletTransaction.TransactionType.SETTLEMENT,
                       amount =  position.quantity,
                       description=f"Settlement for '{market.title}'"
                    )
                position.delete()

        return Response({
            "msg" : "market settled successfully"
        })

       

class PortfolioAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):
        positions = Position.objects.select_related("outcome__market").filter(
           user = request.user
        )

        serializer = PortfolioSerializer(positions,many = True)

        return Response({
            "positions" : serializer.data
        })


class WalletTransactionAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request):

        transactions = WalletTransaction.objects.filter(
            wallet = request.user.wallet
        ).order_by("-created_at")

        serializer = TransactionSerializer(transactions,many = True)

        return Response({
            "transactions" : serializer.data
        })



class MyOrdersAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request): 
       orders = Order.objects.select_related("outcome__market").filter(user = request.user).order_by("-created_at")
       serializer = MyOrdersSerializer(orders,many = True)

       return Response({
           "orders" : serializer.data
       })



class TradeHistoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request,pk):

        get_object_or_404(Market,id = pk)
        

        trades = Trade.objects.filter(
            buy_order__outcome__market_id = pk
        ).order_by("-executed_at")

        serializer = TradeSerializer(trades,many = True)

        return Response({
            "trades" : serializer.data
        })




class PlaceOrderAPI(APIView):

    # {
#     "outcome": "YES",
#     "order_type": "BUY",
#     "price": "7.50",
#     "quantity": 20
# }

    def post(self,request,pk):

        serializer = PlaceOrderSerializer(
            data = request.data
        )

        serializer.is_valid(raise_exception=True)

        market = get_object_or_404(Market,id = pk)

        if(market.status != market.Status.OPEN):
            return Response({
                "msg" : "market is closed."
        })

        outcome = serializer.validated_data["outcome"]
        order_type = serializer.validated_data["order_type"]
        price = serializer.validated_data["price"]
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():
                wallet = Wallet.objects.get(user = request.user)
                if(order_type == Order.OrderType.BUY):
                    if(price * quantity > wallet.available_balance):
                        return Response({
                             "msg" : "insufficient balance"
                        })
                    
                    wallet.available_balance -= price * quantity
                    wallet.locked_balance += price * quantity
                    wallet.save(update_fields=["available_balance","locked_balance"])

                    createdOrder = Order.objects.create(
                        user = request.user,
                        outcome = outcome,
                        order_type = order_type,
                        price = price,
                        quantity = quantity,
                        remaining_quantity = quantity,
                        status = Order.Status.OPEN
                    )

                    matchingOrders = Order.objects.filter(
                        order_type = Order.OrderType.SELL,
                        price__lte = price,
                        outcome = outcome,
                        status__in = [Order.Status.OPEN,Order.Status.PARTIALLY_FILLED]
                    ).order_by("price","created_at")

                    remaining_quantity = quantity
                    quantityToBeTraded = 0
                    for order in matchingOrders:

                        if order.remaining_quantity > remaining_quantity:
                            quantityToBeTraded = remaining_quantity

                        # update the status and remaining_quantity of order and createdOrder in Order
                            createdOrder.status = Order.Status.FILLED
                            createdOrder.remaining_quantity = 0

                            order.status = Order.Status.PARTIALLY_FILLED
                            order.remaining_quantity = order.remaining_quantity -     quantityToBeTraded
    
                            order.save(update_fields=["status","remaining_quantity"])
                            createdOrder.save(update_fields=["status","remaining_quantity"])


                        elif order.remaining_quantity < remaining_quantity :

                            quantityToBeTraded = order.remaining_quantity

                            createdOrder.status = Order.Status.PARTIALLY_FILLED
                            createdOrder.remaining_quantity = createdOrder.remaining_quantity -     quantityToBeTraded

                            order.status = Order.Status.FILLED
                            order.remaining_quantity = 0

                            order.save(update_fields=["status","remaining_quantity"])
                            createdOrder.save(update_fields=["status","remaining_quantity"])
                        else:

                            quantityToBeTraded = remaining_quantity
                            createdOrder.status = Order.Status.FILLED
                            createdOrder.remaining_quantity = 0

                            order.status = Order.Status.FILLED
                            order.remaining_quantity = 0

                            order.save(update_fields=["status","remaining_quantity"])
                            createdOrder.save(update_fields=["status","remaining_quantity"])



                         #entry in trades table
                        Trade.objects.create(
                            buy_order = createdOrder,
                            sell_order = order,
                            price = order.price,
                            quantity = quantityToBeTraded
                        )

                         # update the positions table of order and createdOrder
                    
                        buyOrderPosition ,created= Position.objects.get_or_create(
                                user = request.user,
                                outcome = outcome,
                                defaults={"quantity" : quantityToBeTraded , "average_price" : order.price}
                    
                        )
                        if not created :
                            buyOrderPosition.average_price = (buyOrderPosition.average_price *     buyOrderPosition.quantity + order.price * quantityToBeTraded)/    (buyOrderPosition.quantity + quantityToBeTraded)
                    
                            buyOrderPosition.quantity = buyOrderPosition.quantity +     quantityToBeTraded
                    
                            buyOrderPosition.save(update_fields=["average_price","quantity"])
                    
                        sellOrderPosition = Position.objects.get(
                                    user = order.user,
                                    outcome = outcome
                                )
                    
                        sellOrderPosition.quantity -= quantityToBeTraded
                        if(sellOrderPosition.quantity == 0):
                            sellOrderPosition.delete()
                        else:
                            sellOrderPosition.save(update_fields=["quantity"])

                        orderWallet = Wallet.objects.get(user = order.user)
                        # wallettransactions of both order and createdOrder
                        WalletTransaction.objects.create(
                                wallet = wallet,
                                transaction_type = WalletTransaction.TransactionType.BUY,
                                amount = order.price * quantityToBeTraded,
                                description = f"bought {quantityToBeTraded} shares of ${outcome}     at price {order.price}"
                            )
                        
                        WalletTransaction.objects.create(
                            wallet = orderWallet,
                            transaction_type = WalletTransaction.TransactionType.SELL,
                            amount = order.price * quantityToBeTraded,
                            description = f"sold {quantityToBeTraded} shares of ${outcome} at price {order.price}"
                        
                    )

                    # update the wallets
                        buyer_price = createdOrder.price
                        trade_price = order.price
                        qty = quantityToBeTraded

                        # Remove the full amount that was reserved for these shares
                        wallet.locked_balance -= buyer_price * qty

                        # Refund the price improvement to the buyer
                        wallet.available_balance += (buyer_price - trade_price) * qty

                        # Pay the seller
                        orderWallet.available_balance += trade_price * qty
                        wallet.save(update_fields=["locked_balance", "available_balance"])
                        orderWallet.save(update_fields=["available_balance"])

                        remaining_quantity = remaining_quantity - quantityToBeTraded
                        if remaining_quantity == 0:
                          break
                       

                else:
                    position = get_object_or_404(Position,outcome = outcome,user = request.user)

                    if(position.quantity < quantity):
                        return Response({
                            "msg" : "you don't have enough shares."
                        })


                    










        

        









       



        

    


        

