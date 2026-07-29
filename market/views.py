



from django.shortcuts import render
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db import transaction
from .models import Outcome,Market,Position,Order,Trade
from core.models import Wallet,WalletTransaction
from .serializers import MarketSerializer,CreateMarketSerializer,MarketDetailSerializer,SplitSerializer,MergeSerializer,ResolveMarketSerializer,PortfolioSerializer,MyOrdersSerializer,TransactionSerializer,TradeSerializer,PlaceOrderSerializer
from rest_framework.response import Response
from rest_framework import status
from decimal import Decimal
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Sum




class MarketAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request):

        serializer = CreateMarketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        with transaction.atomic():

            market = serializer.save()

            Outcome.objects.bulk_create([
                Outcome(
                    market=market,
                    name=Outcome.OutcomeName.YES
                ),
                Outcome(
                    market=market,
                    name=Outcome.OutcomeName.NO
                )
            ])

        return Response(
            {
                "message": "Market created successfully.",
                "market": MarketSerializer(market).data
            },
            status=status.HTTP_201_CREATED
        )


    def get(self, request):

        markets = Market.objects.filter(
            status=Market.Status.OPEN
        ).order_by("close_at")

        serializer = MarketSerializer(
               markets,
               many=True
        )

        return Response(serializer.data)  



class MarketDetailAPIView(APIView):

    def get(self, request, pk):

        market = get_object_or_404(
            Market.objects.prefetch_related("outcomes"),
            id=pk
        )

        return Response(
            MarketDetailSerializer(market).data
        )

class SplitAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        serializer = SplitSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        amount = serializer.validated_data["amount"]

        with transaction.atomic():

            market = get_object_or_404(
                Market.objects.select_for_update(),
                pk=pk,
            )

            if market.status != Market.Status.OPEN:
                return Response(
                    {"message": "Market is closed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            wallet = Wallet.objects.select_for_update().get(
                user=request.user
            )

            if wallet.available_balance < amount:
                return Response(
                    {"message": "Insufficient balance."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            yes_outcome = market.outcomes.get(
                name=Outcome.OutcomeName.YES
            )

            no_outcome = market.outcomes.get(
                name=Outcome.OutcomeName.NO
            )

            existing_positions = Position.objects.select_for_update().filter(
                user=request.user,
                outcome__in=[yes_outcome, no_outcome],
            )

            yes_position = None
            no_position = None

            for position in existing_positions:
                if position.outcome == yes_outcome:
                    yes_position = position
                elif position.outcome == no_outcome:
                    no_position = position

            wallet.available_balance -= amount
            wallet.save()

            WalletTransaction.objects.create(
                wallet=wallet,
                transaction_type=WalletTransaction.TransactionType.SPLIT,
                amount=amount,
                description="Split into prediction shares",
            )

            # ---------- YES POSITION ----------

            if yes_position is None:
                yes_position = Position(
                    user=request.user,
                    outcome=yes_outcome,
                    quantity=amount,
                    average_price=Decimal("1.00"),
                )
            else:
                total_quantity = yes_position.quantity + amount

                yes_position.average_price = (
                    (yes_position.average_price * yes_position.quantity)
                    + (Decimal("1.00") * amount)
                ) / total_quantity

                yes_position.quantity = total_quantity

            yes_position.save()

            # ---------- NO POSITION ----------

            if no_position is None:
                no_position = Position(
                    user=request.user,
                    outcome=no_outcome,
                    quantity=amount,
                    average_price=Decimal("1.00"),
                )
            else:
                total_quantity = no_position.quantity + amount

                no_position.average_price = (
                    (no_position.average_price * no_position.quantity)
                    + (Decimal("1.00") * amount)
                ) / total_quantity

                no_position.quantity = total_quantity

            no_position.save()

        return Response(
            {"message": "Split successful."},
            status=status.HTTP_200_OK,
        )


class MergeAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        serializer = MergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():

            market = get_object_or_404(
                Market.objects.select_for_update(),
                pk=pk,
            )

            if market.status != Market.Status.OPEN:
                return Response(
                    {"message": "Market is not open."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            wallet = Wallet.objects.select_for_update().get(
                user=request.user
            )

            positions = Position.objects.select_for_update().filter(
                user=request.user,
                outcome__market=market,
            )

            yes_position = None
            no_position = None

            for position in positions:
                if position.outcome.name == Outcome.OutcomeName.YES:
                    yes_position = position
                elif position.outcome.name == Outcome.OutcomeName.NO:
                    no_position = position

            if not yes_position or not no_position:
                return Response(
                    {
                        "message": "You must own both YES and NO shares to merge."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                yes_position.quantity < quantity
                or no_position.quantity < quantity
            ):
                return Response(
                    {"message": "Insufficient shares to merge."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
                transaction_type=WalletTransaction.TransactionType.MERGE,
                amount=quantity,
                description=f"Merged {quantity} YES-NO pairs in '{market.title}'",
            )

        return Response(
            {
                "message": "Shares merged successfully."
            },
            status=status.HTTP_200_OK,
        )

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        serializer = MergeSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        quantity = serializer.validated_data["quantity"]

        market = get_object_or_404(Market, pk=pk)

        if market.status != Market.Status.OPEN:
            return Response(
                {"message": "Market is not open."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        with transaction.atomic():

            wallet = Wallet.objects.select_for_update().get(
                user=request.user
            )

            positions = Position.objects.select_for_update().filter(
                user=request.user,
                outcome__market=market,
            )

            yes_position = None
            no_position = None

            for position in positions:
                if position.outcome.name == Outcome.OutcomeName.YES:
                    yes_position = position
                elif position.outcome.name == Outcome.OutcomeName.NO:
                    no_position = position

            if not yes_position or not no_position:
                return Response(
                    {
                        "message": "You must own both YES and NO shares to merge."
                    },
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if (
                yes_position.quantity < quantity
                or no_position.quantity < quantity
            ):
                return Response(
                    {"message": "Insufficient shares to merge."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

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
                transaction_type=WalletTransaction.TransactionType.MERGE,
                amount=quantity,
                description=f"Merged {quantity} YES-NO pairs in '{market.title}'",
            )

        return Response(
            {"message": "Shares merged successfully."},
            status=status.HTTP_200_OK,
        )




class ResolveMarketAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        serializer = ResolveMarketSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        winner = serializer.validated_data["winner"]

        with transaction.atomic():

            market = get_object_or_404(
                Market.objects.select_for_update(),
                pk=pk,
            )

            if market.status != Market.Status.CLOSED:
                return Response(
                    {"message": "Only closed markets can be resolved."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            market.status = Market.Status.RESOLVED
            market.resolved_at = timezone.now()
            market.save()

            outcome = market.outcomes.get(name=winner)
            outcome.is_winner = True
            outcome.save()

        return Response(
            {"message": "Market resolved successfully."},
            status=status.HTTP_200_OK,
        )


class SettlementAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        with transaction.atomic():

            market = get_object_or_404(
                Market.objects.select_for_update(),
                pk=pk,
            )

            if market.status != Market.Status.RESOLVED:
                return Response(
                    {"message": "Cannot settle because market is not resolved yet."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            positions = (
                Position.objects
                .select_related("user", "outcome")
                .filter(outcome__market=market)
            )

            for position in positions:

                if position.outcome.is_winner:

                    wallet = Wallet.objects.select_for_update().get(
                        user=position.user
                    )

                    wallet.available_balance += position.quantity
                    wallet.save(update_fields=["available_balance"])

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type=WalletTransaction.TransactionType.SETTLEMENT,
                        amount=position.quantity,
                        description=f"Settlement for '{market.title}'",
                    )

                position.delete()

        return Response(
            {"message": "Market settled successfully."},
            status=status.HTTP_200_OK,
        )


class PortfolioAPIView(APIView):

      permission_classes = [IsAuthenticated]

      def get(self, request):

        positions = (
            Position.objects
            .select_related("outcome__market")
            .filter(user=request.user)
            .order_by("outcome__market__title", "-quantity")
        )

        serializer = PortfolioSerializer(positions, many=True)

        return Response(
            {"positions": serializer.data},
            status=status.HTTP_200_OK,
        )



class WalletTransactionAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request):

        transactions = (
            WalletTransaction.objects
            .filter(wallet=request.user.wallet)
            .order_by("-created_at")
        )

        serializer = TransactionSerializer(
            transactions,
            many=True,
        )

        return Response(
            {"transactions": serializer.data},
            status=status.HTTP_200_OK,
        )


class MyOrdersAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self,request): 
       orders = Order.objects.select_related("outcome__market").filter(user = request.user).order_by("-created_at")
       serializer = MyOrdersSerializer(orders,many = True)

       return Response({
           "orders" : serializer.data
       },status=status.HTTP_200_OK)



class TradeHistoryAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def get(self, request, pk):

        get_object_or_404(Market, pk=pk)

        trades = (
            Trade.objects
            .filter(buy_order__outcome__market_id=pk)
            .order_by("-executed_at")
        )

        serializer = TradeSerializer(trades, many=True)

        return Response(
            {"trades": serializer.data},
            status=status.HTTP_200_OK,
        )


    
class PlaceOrderAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        serializer = PlaceOrderSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)

        outcome = serializer.validated_data["outcome"]
        order_type = serializer.validated_data["order_type"]
        price = serializer.validated_data["price"]
        quantity = serializer.validated_data["quantity"]

        with transaction.atomic():

            market = get_object_or_404(
                   Market.objects.select_for_update(),
                   id=pk,
            )

            if market.status != Market.Status.OPEN:
                return Response(
                    {"msg": "market is closed."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if outcome.market_id != market.id:
                return Response(
                    {"msg": "invalid outcome."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            wallet = (
                Wallet.objects
                .select_for_update()
                .get(user=request.user)
            )
            

            if order_type == Order.OrderType.BUY:

                total_amount = price * quantity

                if wallet.available_balance < total_amount:
                    return Response(
                        {"msg": "insufficient balance"},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                wallet.available_balance -= total_amount
                wallet.locked_balance += total_amount

                wallet.save(
                    update_fields=[
                        "available_balance",
                        "locked_balance",
                    ]
                )

                created_order = Order.objects.create(
                    user=request.user,
                    outcome=outcome,
                    order_type=Order.OrderType.BUY,
                    price=price,
                    quantity=quantity,
                    remaining_quantity=quantity,
                    status=Order.Status.OPEN,
                )

                matching_orders = (
                    Order.objects
                    .select_for_update()
                    .select_related("user")
                    .filter(
                        outcome=outcome,
                        order_type=Order.OrderType.SELL,
                        price__lte=price,
                        status__in=[
                            Order.Status.OPEN,
                            Order.Status.PARTIALLY_FILLED,
                        ],
                    )
                    .order_by(
                        "price",
                        "created_at",
                    )
                )

                remaining_quantity = quantity
                buyer_position = (
                    Position.objects
                    .select_for_update()
                    .filter(
                        user=request.user,
                        outcome=outcome,
                    )
                    .first()
                )

                for order in matching_orders:

                    if remaining_quantity == 0:
                        break

                    seller_position = (
                        Position.objects
                        .select_for_update()
                        .get(
                            user=order.user,
                            outcome=outcome,
                        )
                    )


                    if order.remaining_quantity >= remaining_quantity:

                        traded_quantity = remaining_quantity

                        created_order.remaining_quantity = 0
                        created_order.status = Order.Status.FILLED

                        order.remaining_quantity -= traded_quantity

                        if order.remaining_quantity == 0:
                            order.status = Order.Status.FILLED
                        else:
                            order.status = Order.Status.PARTIALLY_FILLED

                    else:

                        traded_quantity = order.remaining_quantity

                        created_order.remaining_quantity -= traded_quantity

                        created_order.status = (
                            Order.Status.PARTIALLY_FILLED
                        )

                        order.remaining_quantity = 0
                        order.status = Order.Status.FILLED

                    order.save(
                        update_fields=[
                            "remaining_quantity",
                            "status",
                        ]
                    )

                    created_order.save(
                        update_fields=[
                            "remaining_quantity",
                            "status",
                        ]
                    )

                    Trade.objects.create(
                        buy_order=created_order,
                        sell_order=order,
                        price=order.price,
                        quantity=traded_quantity,
                    )

                    if buyer_position is None:

                        buyer_position = Position.objects.create(
                            user=request.user,
                            outcome=outcome,
                            quantity=traded_quantity,
                            average_price=order.price,
                        )

                    else:

                        total_quantity = (
                            buyer_position.quantity + traded_quantity
                        )

                        buyer_position.average_price = (
                            (
                                buyer_position.average_price
                                * buyer_position.quantity
                            )
                            + (order.price * traded_quantity)
                        ) / total_quantity

                        buyer_position.quantity = total_quantity

                        buyer_position.save(
                            update_fields=[
                                "average_price",
                                "quantity",
                            ]
                        )

                    seller_position.quantity -= traded_quantity
                    seller_position.locked_quantity -= traded_quantity

                    if seller_position.quantity == 0:
                        seller_position.delete()
                    else:
                        seller_position.save(
                            update_fields = [
                                "quantity",
                                "locked_quantity"
                            ]
                        )


                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type=WalletTransaction.TransactionType.BUY,
                        amount=order.price * traded_quantity,
                        description=(
                            f"Bought {traded_quantity} shares of "
                            f"{outcome.name} at {order.price}"
                        ),
                    )

                    seller_wallet = (
                        Wallet.objects
                        .select_for_update()
                        .get(user=order.user)
                    )

                    WalletTransaction.objects.create(
                        wallet=seller_wallet,
                        transaction_type=WalletTransaction.TransactionType.SELL,
                        amount=order.price * traded_quantity,
                        description=(
                            f"Sold {traded_quantity} shares of "
                            f"{outcome.name} at {order.price}"
                        ),
                    )

                    reserved_price = created_order.price
                    trade_price = order.price

                    wallet.locked_balance -= (
                        reserved_price * traded_quantity
                    )

                    wallet.available_balance += (
                        (reserved_price - trade_price)
                        * traded_quantity
                    )

                    seller_wallet.available_balance += (
                        trade_price * traded_quantity
                    )

                    wallet.save(
                        update_fields=[
                            "available_balance",
                            "locked_balance",
                        ]
                    )

                    seller_wallet.save(
                        update_fields=[
                            "available_balance",
                        ]
                    )

                    remaining_quantity -= traded_quantity

                return Response(
                    {
                        "msg": "Order placed successfully.",
                        "order_id": created_order.id,
                    },
                    status=status.HTTP_201_CREATED,
                )

            # sell flow
            else:

                seller_position = (
                    Position.objects
                    .select_for_update()
                    .filter(
                        user=request.user,
                        outcome=outcome,
                    )
                    .first()
                )

                if seller_position is None:
                    return Response(
                        {"msg": "You don't own this outcome."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                available_quantity = (
                    seller_position.quantity
                    - seller_position.locked_quantity
                )

                if available_quantity < quantity:
                    return Response(
                        {"msg": "You don't have enough shares."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                seller_position.locked_quantity += quantity

                seller_position.save(
                    update_fields=[
                        "locked_quantity",
                    ]
                )

                wallet = (
                    Wallet.objects
                    .select_for_update()
                    .get(user=request.user)
                )

                created_order = Order.objects.create(
                    user=request.user,
                    outcome=outcome,
                    order_type=Order.OrderType.SELL,
                    price=price,
                    quantity=quantity,
                    remaining_quantity=quantity,
                    status=Order.Status.OPEN,
                )

                matching_orders = (
                    Order.objects
                    .select_for_update()
                    .select_related("user")
                    .filter(
                        outcome=outcome,
                        order_type=Order.OrderType.BUY,
                        price__gte=price,
                        status__in=[
                            Order.Status.OPEN,
                            Order.Status.PARTIALLY_FILLED,
                        ],
                    )
                    .order_by(
                        "-price",
                        "created_at",
                    )
                )

                remaining_quantity = quantity

                for order in matching_orders:

                    if remaining_quantity == 0:
                        break

                    buyer_position = (
                        Position.objects
                        .select_for_update()
                        .filter(
                            user=order.user,
                            outcome=outcome,
                        )
                        .first()
                    )

                    traded_quantity = min(
                        remaining_quantity,
                        order.remaining_quantity,
                    )

                    created_order.remaining_quantity -= traded_quantity
                    order.remaining_quantity -= traded_quantity

                    if created_order.remaining_quantity == 0:
                        created_order.status = Order.Status.FILLED
                    else:
                        created_order.status = (
                            Order.Status.PARTIALLY_FILLED
                        )

                    if order.remaining_quantity == 0:
                        order.status = Order.Status.FILLED
                    else:
                        order.status = (
                            Order.Status.PARTIALLY_FILLED
                        )

                    created_order.save(
                        update_fields=[
                            "remaining_quantity",
                            "status",
                        ]
                    )

                    order.save(
                        update_fields=[
                            "remaining_quantity",
                            "status",
                        ]
                    )

                    Trade.objects.create(
                        buy_order=order,
                        sell_order=created_order,
                        price=order.price,
                        quantity=traded_quantity,
                    )

                    if buyer_position is None:

                        buyer_position = Position.objects.create(
                            user=order.user,
                            outcome=outcome,
                            quantity=traded_quantity,
                            average_price=order.price,
                        )

                    else:

                        old_quantity = buyer_position.quantity
                        new_quantity = (
                            old_quantity + traded_quantity
                        )

                        buyer_position.average_price = (
                            (
                                buyer_position.average_price
                                * old_quantity
                            )
                            + (
                                order.price
                                * traded_quantity
                            )
                        ) / new_quantity

                        buyer_position.quantity = new_quantity

                        buyer_position.save(
                            update_fields=[
                                "average_price",
                                "quantity",
                            ]
                        )

                    seller_position.quantity -= traded_quantity
                    seller_position.locked_quantity -= traded_quantity

                    if seller_position.quantity == 0:
                        seller_position.delete()
                    else:
                        seller_position.save(
                            update_fields=[
                                "quantity",
                                "locked_quantity",
                            ]
                        )

                    buyer_wallet = (
                        Wallet.objects
                        .select_for_update()
                        .get(user=order.user)
                    )

                    reserved_price = order.price
                    trade_price = order.price

                    buyer_wallet.locked_balance -= (
                        reserved_price
                        * traded_quantity
                    )

                    buyer_wallet.available_balance += (
                        (
                            reserved_price
                            - trade_price
                        )
                        * traded_quantity
                    )

                    wallet.available_balance += (
                        trade_price
                        * traded_quantity
                    )

                    buyer_wallet.save(
                        update_fields=[
                            "available_balance",
                            "locked_balance",
                        ]
                    )

                    wallet.save(
                        update_fields=[
                            "available_balance",
                        ]
                    )

                    WalletTransaction.objects.create(
                        wallet=buyer_wallet,
                        transaction_type=WalletTransaction.TransactionType.BUY,
                        amount=trade_price * traded_quantity,
                        description=(
                            f"Bought {traded_quantity} shares of "
                            f"{outcome.name} at {trade_price}"
                        ),
                    )

                    WalletTransaction.objects.create(
                        wallet=wallet,
                        transaction_type=WalletTransaction.TransactionType.SELL,
                        amount=trade_price * traded_quantity,
                        description=(
                            f"Sold {traded_quantity} shares of "
                            f"{outcome.name} at {trade_price}"
                        ),
                    )

                    remaining_quantity -= traded_quantity

                return Response(
                    {
                        "msg": "Order placed successfully.",
                        "order_id": created_order.id,
                    },
                    status=status.HTTP_201_CREATED,
                )


class CancelOrderAPIView(APIView):

    permission_classes = [IsAuthenticated]

    def post(self, request, pk):

        with transaction.atomic():

            order = get_object_or_404(
                Order.objects.select_for_update(),
                id=pk,
                user=request.user,
            )

            if order.status not in [
                Order.Status.OPEN,
                Order.Status.PARTIALLY_FILLED,
            ]:
                return Response(
                    {"msg": "Cannot cancel order."},
                    status=status.HTTP_400_BAD_REQUEST,
                )

            if order.order_type == Order.OrderType.BUY:

                wallet = (
                    Wallet.objects
                    .select_for_update()
                    .get(user=request.user)
                )

                refund_amount = (
                    order.price
                    * order.remaining_quantity
                )

                wallet.locked_balance -= refund_amount
                wallet.available_balance += refund_amount

                wallet.save(
                    update_fields=[
                        "locked_balance",
                        "available_balance",
                    ]
                )

                WalletTransaction.objects.create(
                    wallet=wallet,
                    transaction_type=WalletTransaction.TransactionType.REFUND,
                    amount=refund_amount,
                    description="Order cancelled. Funds refunded.",
                )

            else:

                position = (
                    Position.objects
                    .select_for_update()
                    .get(
                        user=request.user,
                        outcome=order.outcome,
                    )
                )

                position.locked_quantity -= (
                    order.remaining_quantity
                )

                position.save(
                    update_fields=[
                        "locked_quantity",
                    ]
                )

            order.status = Order.Status.CANCELLED

            order.save(
                update_fields=[
                    "status",
                ]
            )

        return Response(
            {
                "msg": "Order cancelled successfully.",
            },
            status=status.HTTP_200_OK,
        )



class OrderBookAPIView(APIView):

    def get(self, request, pk):

        market = get_object_or_404(
            Market,
            id=pk,
        )

        data = {}

        for outcome in market.outcomes.all():

            buy_orders = (
                Order.objects
                .filter(
                    outcome=outcome,
                    order_type=Order.OrderType.BUY,
                    status__in=[
                        Order.Status.OPEN,
                        Order.Status.PARTIALLY_FILLED,
                    ],
                )
                .values("price")
                .annotate(
                    quantity=Sum("remaining_quantity"),
                )
                .order_by("-price")
            )

            sell_orders = (
                Order.objects
                .filter(
                    outcome=outcome,
                    order_type=Order.OrderType.SELL,
                    status__in=[
                        Order.Status.OPEN,
                        Order.Status.PARTIALLY_FILLED,
                    ],
                )
                .values("price")
                .annotate(
                    quantity=Sum("remaining_quantity"),
                )
                .order_by("price")
            )

            data[outcome.name] = {
                "BUY": buy_orders,
                "SELL": sell_orders,
            }

        return Response(data)