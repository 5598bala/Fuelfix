# FuelFix online payments (Razorpay)

FuelFix uses Razorpay Standard Checkout for card and UPI payments. The server creates each order from the configured database fuel rate, verifies the checkout signature, confirms the amount/currency/order with Razorpay, and only then marks the request paid and assigns it to a provider.

## Configure fuel prices

1. Run the FuelFix database migrations.
2. Sign in to Django admin and open **Fuel rates**.
3. Add one active Petrol row and one active Diesel row. Set each price per litre and the optional delivery fee. The checkout total is `(price per litre × litres) + delivery fee`.
4. Rates are stored with the request total so later rate changes do not change an existing payment amount.

## Configure Razorpay keys

Add these to the ignored project-root `.env` file. Do not commit or send the secret values in chat.

```dotenv
RAZORPAY_KEY_ID=your_test_key_id
RAZORPAY_KEY_SECRET=your_test_key_secret
RAZORPAY_WEBHOOK_SECRET=your_webhook_secret
```

Start in Razorpay Test Mode with test API keys. Once the checkout flow works with Razorpay's supplied test payment details, use Live Mode keys to collect real money. Enable card and UPI methods for the merchant account. Availability can depend on Razorpay account activation and its payment-method settings.

## Webhook

In the Razorpay Dashboard, add the public HTTPS URL `https://your-domain/payments/razorpay/webhook/`, set the same webhook secret as `RAZORPAY_WEBHOOK_SECRET`, and subscribe to the `payment.captured` event. The signed checkout callback also verifies payment immediately; the webhook covers cases where the customer closes the browser after paying.

After changing `.env`, restart Django. Live payments require an activated Razorpay merchant account and Live Mode keys.