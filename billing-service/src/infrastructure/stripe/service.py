from decimal import Decimal
from uuid import UUID

import stripe
from pydantic import SecretStr


class StripeService:
    def __init__(self, secret_key: SecretStr, webhook_secret: SecretStr):
        self.secret_key = secret_key.get_secret_value()
        self.webhook_secret = webhook_secret.get_secret_value()
        stripe.api_key = self.secret_key

    async def create_payment_intent(
        self,
        order_id: UUID,
        amount: Decimal,
        currency: str = 'usd',
        metadata: dict | None = None,
    ) -> tuple[str, str]:
        amount_cents = int(amount * 100)

        intent_metadata = {
            'order_id': str(order_id),
        }
        if metadata:
            intent_metadata.update(metadata)

        try:
            intent = stripe.PaymentIntent.create(
                amount=amount_cents,
                currency=currency.lower(),
                metadata=intent_metadata,
                automatic_payment_methods={'enabled': True},
            )

            return intent.id, intent.client_secret

        except stripe.error.StripeError as e:
            raise Exception(f'Stripe error: {str(e)}')

    async def retrieve_payment_intent(self, payment_intent_id: str) -> dict:
        try:
            intent = stripe.PaymentIntent.retrieve(payment_intent_id)
            return {
                'id': intent.id,
                'status': intent.status,
                'amount': Decimal(intent.amount) / 100,
                'currency': intent.currency,
                'metadata': intent.metadata,
            }
        except stripe.error.StripeError as e:
            raise Exception(f'Stripe error: {str(e)}')

    async def cancel_payment_intent(self, payment_intent_id: str) -> None:
        try:
            stripe.PaymentIntent.cancel(payment_intent_id)
        except stripe.error.StripeError as e:
            raise Exception(f'Stripe error: {str(e)}')

    def construct_webhook_event(
        self,
        payload: bytes,
        sig_header: str,
    ) -> stripe.Event:
        try:
            event = stripe.Webhook.construct_event(
                payload, sig_header, self.webhook_secret
            )
            return event
        except stripe.error.SignatureVerificationError as e:
            raise Exception(f'Invalid webhook signature: {str(e)}')

    @staticmethod
    def extract_order_id_from_event(event: stripe.Event) -> UUID | None:
        try:
            if event.type.startswith('payment_intent.'):
                payment_intent = event.data.object
                order_id_str = payment_intent.get('metadata', {}).get('order_id')
                if order_id_str:
                    return UUID(order_id_str)

            elif event.type.startswith('charge.'):
                charge = event.data.object
                order_id_str = charge.get('metadata', {}).get('order_id')
                if order_id_str:
                    return UUID(order_id_str)

            return None
        except (ValueError, KeyError):
            return None
