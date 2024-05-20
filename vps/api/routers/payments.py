import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, Request, Form, Depends
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette import status

from api import pydantic_models as models
from api.exceptions import subscriptionNotExist_exception, notSub_exception, alreadySub_exception
from api.actions.users import get_current_user
from db.dals.users import UserDAL
from db.dals.subscriptions import SubscriptionDAL
from db.dals.statistics import StatsDAL
from db.session import get_db
from core.config import Config
from core.status import StatusEnum, SubscriptionTypeEnum, StatEventTypeEnum

router = APIRouter()
logger = logging.getLogger("routers")

stripe.api_key = Config.STRIPE_SECRET_KEY


@router.post(path="/webhook", tags=["Payments"])
async def webhook_received(
    request: Request,
    session: AsyncSession = Depends(get_db),
):
    logger.info(f"Stripe webhook received!")
    request_data = await request.json()

    payload = await request.body()
    sig_header = request.headers["stripe-signature"]

    if Config.STRIPE_WEBHOOK_SECRET:
        try:
            event = stripe.Webhook.construct_event(
                payload=payload,
                sig_header=sig_header,
                secret=Config.STRIPE_WEBHOOK_SECRET,
            )
            data = event["data"]
        except Exception as e:
            logger.info(f"Stripe webhook exception {e}")
            return e
        # Get the type of webhook event sent - used to check the status of PaymentIntents.
        event_type = event["type"]
    else:
        data = request_data["data"]
        event_type = request_data["type"]

    data_object = data["object"]

    logger.info(f"{event_type}:data\n{data_object}")

    if event_type == "checkout.session.completed":
        # Payment is successful and the subscription is created.
        # You should provision the subscription and save the customer ID to your database.
        logger.info(f"Stripe webhook receive checkout.session.completed")

        mode = data_object["mode"]
        user_id = data_object["client_reference_id"]
        quantity = data_object["metadata"]["quantity"]

        if mode == "payment" and data_object["payment_status"] == "paid":
            async with session.begin():
                await UserDAL(session).update_balance(user_id, int(quantity))
                await StatsDAL(session).create(user_id, 
                    StatEventTypeEnum.bought_minutes,
                    {"amount": quantity}
                )

            logger.info(
                f"User({user_id}) has bought {quantity} minutes"
            )

    elif event_type == "invoice.paid":
        # Continue to provision the subscription as payments continue to be made.
        # Store the status in your database and check when a user accesses your service.
        # This approach helps you avoid hitting rate limits.
        logger.info(f"Stripe webhook receive invoice.paid")
        logger.info(f'{data_object["customer_email"]}')
        logger.info(f'{data_object["amount_paid"]}')

        user_email = data_object["customer_email"]
        amount_cents = data_object["amount_paid"]
        stripe_sub_id = data_object["lines"]["data"][0]["subscription"]
        sub_id = data_object["metadata"]["sub_id"]
        logger.info(f"SUB ID {sub_id}")

        logger.info(f"User {user_email} has bought sub({sub_id}) for {amount_cents} cents")

        async with session.begin():
            user_dal = UserDAL(session)
            sub_dal = SubscriptionDAL(session)
            user = await user_dal.get_by_email(user_email)
            await sub_dal.create_user_sub(user.id, sub_id, stripe_sub_id)

    elif event_type == "invoice.payment_failed":
        # The payment failed or the customer does not have a valid payment method.
        # The subscription becomes past_due. Notify your customer and send them to the
        # customer portal to update their payment information.
        logger.info(f"Stripe webhook receive invoice.payment_failed")
        logger.info(f'{data_object["customer_email"]}')
        logger.info(f'{data_object["lines"]["data"]["plan"]["id"]}')
    else:
        logger.info("Unhandled event type {}".format(event_type))

    return JSONResponse({"status": "success"})


@router.get(path="/minutes", tags=["Payments"])
async def checkout_minutes(
    request: Request,
    minutes: int,
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.email} is checking out {minutes} minutes")

    price_id = Config.STRIPE_MINUTE_PRICE_ID
    async with session.begin():
        sub_dal = SubscriptionDAL(session)
        user_sub = await sub_dal.get_user_sub(current_user.id)
        if user_sub:
            sub = await sub_dal.get_sub(user_sub.subscription_id)
            if sub.type == SubscriptionTypeEnum.Lower_price:
                price_id = sub.meta["min_price_id"]

    try:
        checkout_session = stripe.checkout.Session.create(
            success_url=Config.FRONTEND_URL + "successful_payment",
            cancel_url=Config.FRONTEND_URL + "payment_cancellation",
            payment_method_types=["card"],
            mode="payment",
            line_items=[
                {
                    "price": price_id,
                    "quantity": minutes,
                }
            ],
            customer_email=current_user.email,
            client_reference_id=current_user.id,
            metadata={"quantity": minutes}
        )

        return {"stripe_url": checkout_session.url}
    except Exception as e:
        raise Exception(f"Wrong sticks payment: {e}")
    

@router.get(path="/subscription", tags=["Payments"])
async def list_subscriptions(
    request: Request,
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    async with session.begin():
        sub_dal = SubscriptionDAL(session)
        subs = await sub_dal.get_list_subs()
    
    subs_list = []

    for sub in subs:
        subs_list.append(models.SubscriptionInfo(
            id=sub.id,
            duration=sub.duration.days,
            type=sub.type,
            price_in_cents=sub.meta["display_price"],
            currency=sub.meta["display_currency"]
        ))

    return models.SubscriptionsList(subscriptions=subs_list)


@router.post(path="/subscription", tags=["Payments"])
async def checkout_subscription(
    request: Request,
    sub_id: uuid.UUID = Form(...),
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    async with session.begin():
        sub_dal = SubscriptionDAL(session)
        sub = await sub_dal.get_sub(sub_id)
        if not sub:
            raise subscriptionNotExist_exception
        user_sub = await sub_dal.get_user_sub(current_user.id)
        if user_sub:
            raise alreadySub_exception

    logger.info(f"User {current_user.email} is checking out monthly subscription")

    try:
        checkout_session = stripe.checkout.Session.create(
            success_url=Config.FRONTEND_URL + "successful_subscribe",
            cancel_url=Config.FRONTEND_URL + "payment_cancellation",
            payment_method_types=["card"],
            mode="subscription",
            line_items=[
                {
                    "price": sub.meta["price_id"],
                    "quantity": 1,
                }
            ],
            client_reference_id=current_user.id,
            customer_email=current_user.email,
            metadata={"sub_id": sub.id}
        )

        return {"stripe_url": checkout_session.url}
    except Exception as e:
        raise Exception(f"Wrong sub payment: {e}")


@router.delete(path="/subscription", tags=["Payments"])
async def cancel_subscription(
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.email} is cancelling monthly subscription")

    async with session.begin():
        sub_dal = SubscriptionDAL(session)
        user_sub = await sub_dal.get_user_sub(current_user.id)
        if not user_sub:
            raise notSub_exception

        stripe.Subscription.modify(user_sub.stripe_sub_id, cancel_at_period_end=True)
        await sub_dal.disable_user_sub(user_sub.id)

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"{current_user.email} subscription was canceled",
    )


@router.patch(path="/reveal_subscription", tags=["Payments"])
async def reveal_subscription(
    current_user: models.UserInfo = Depends(get_current_user),
    session: AsyncSession = Depends(get_db),
):
    logger.info(f"User {current_user.email} is revealing monthly subscription")

    async with session.begin():
        sub_dal = SubscriptionDAL(session)
        user_sub = await sub_dal.get_user_sub(current_user.id)
        if not user_sub:
            raise notSub_exception
        if user_sub.status == StatusEnum.created:
            raise alreadySub_exception

        try:
            db_sub = await sub_dal.get_sub(user_sub.subscription_id)
            subscription = stripe.Subscription.retrieve(user_sub.stripe_sub_id)

            stripe.Subscription.modify(
                subscription.id,
                cancel_at_period_end=False,
                proration_behavior="create_prorations",
                items=[
                    {
                        "id": subscription["items"]["data"][0].id,
                        "price": db_sub.meta["price_id"],
                    }
                ],
            )

            await sub_dal.reactivate_user_sub(current_user.id)
        except Exception as e:
            logger.error(f"FATAL ERROR:\n{e.__str__()}")

    return JSONResponse(
        status_code=status.HTTP_200_OK,
        content=f"{current_user.email} subscription was revealed",
    )
