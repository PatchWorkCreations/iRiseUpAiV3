from django.shortcuts import render

def index(request):
    return render(request, 'myApp/index.html')


from django.shortcuts import render, redirect
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('form-name')
        email = request.POST.get('form-email')
        subject = request.POST.get('form-subject')
        message = request.POST.get('form-message')

        # Handle form submission logic, e.g., sending email
        send_mail(
            subject,
            f'Message from {name} ({email}):\n\n{message}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_TO_EMAIL],
            fail_silently=False,
        )
        return redirect(reverse('index'))

    return render(request, 'index.html')


from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from django.conf import settings
from django.utils import timezone
from datetime import timedelta
from square.client import Client
from .models import SquareCustomer, User, UserAccess, Transaction

import json
import uuid
import logging

logger = logging.getLogger(__name__)

# Initialize Square client
square_client = Client(
    access_token=settings.SQUARE_ACCESS_TOKEN,
    environment='production'  # Change to 'sandbox' if testing
)

@csrf_exempt
def process_payment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    try:
        data = json.loads(request.body)
        card_token = data.get('source_id')
        selected_plan = data.get('plan')
        verification_token = data.get('verification_token')
        user_email = request.session.get('email')

        # Enhanced validation checks
        if not user_email:
            return JsonResponse({"error": "Email is missing from session."}, status=400)
        if not card_token or not selected_plan:
            return JsonResponse({"error": "Missing payment or plan details."}, status=400)

        # Determine the amount from selected plan
        amount = determine_amount_based_on_plan(selected_plan)
        if amount <= 0:
            return JsonResponse({"error": "Invalid or unsupported plan selected."}, status=400)

        # Retrieve or create the customer in Square
        customer_id = get_or_create_square_customer(data, user_email)
        if not customer_id:
            return JsonResponse({"error": "Failed to create or retrieve customer profile."}, status=400)

        # Process payment and store card if successful
        payment_result = process_square_payment(card_token, amount, verification_token, customer_id)
        if payment_result.get("error"):
            return JsonResponse({"error": payment_result["error"]}, status=400)

        # Retrieve or create the user in the Django app
        user = get_or_create_user(user_email, data)

        # Set plan expiration and billing dates
        expiration_date, next_billing_date = get_billing_dates(selected_plan)

        # Update or create UserAccess and store customer and card IDs
        store_user_course_access(user, selected_plan, expiration_date)
        save_square_customer_info(user, customer_id, payment_result["card_id"])

        # Create a transaction record
        Transaction.objects.create(
            user=user,
            amount=amount,
            subscription_type=selected_plan,
            status='success',
            recurring=selected_plan in ['1-week', '4-week', '12-week'],
            next_billing_date=next_billing_date
        )

        return JsonResponse({"success": True})

    except Exception as e:
        logger.error("Unexpected error: %s", str(e), exc_info=True)
        return JsonResponse({"error": "An unexpected error occurred."}, status=500)


# Helper Functions
def determine_amount_based_on_plan(plan):
    # Pricing dictionary aligns with front-end data
    plan_amounts = {
        '1-week': 1287,
        '4-week': 3795,
        '12-week': 9700,
        'lifetime': 29700,
    }
    return plan_amounts.get(plan, 0)

def get_or_create_square_customer(data, email):
    try:
        customer_result = square_client.customers.create_customer(
            body={
                "given_name": data.get('givenName'),
                "family_name": data.get('familyName'),
                "email_address": email,
            }
        )
        if customer_result.is_success():
            return customer_result.body['customer']['id']
    except Exception as e:
        logger.error("Error creating customer: %s", e)
    return None

def process_square_payment(card_token, amount, verification_token, customer_id):
    try:
        payment_result = square_client.payments.create_payment(
            body={
                "source_id": card_token,
                "idempotency_key": str(uuid.uuid4()),
                "amount_money": {"amount": amount, "currency": "USD"},
                "verification_token": verification_token,
                "autocomplete": True,
                "customer_id": customer_id,
            }
        )
        if payment_result.is_success():
            return {"card_id": payment_result.body['payment']['card_details']['card']['id']}
    except Exception as e:
        logger.error("Payment error: %s", e)
    return {"error": "Payment failed. Please try again."}

def get_or_create_user(email, data):
    user, created = User.objects.get_or_create(
        username=email,
        defaults={'email': email}
    )
    if created:
        random_password = get_random_string(8)
        user.set_password(random_password)
        user.save()
        send_welcomepassword_email(email, random_password)
    return user

def get_billing_dates(plan):
    duration = {
        '1-week': timedelta(weeks=1),
        '4-week': timedelta(weeks=4),
        '12-week': timedelta(weeks=12),
    }.get(plan, None)

    expiration_date = timezone.now() + duration if duration else None
    next_billing_date = expiration_date if expiration_date else None
    return expiration_date, next_billing_date

def store_user_course_access(user, plan, expiration_date):
    UserAccess.objects.update_or_create(
        user=user,
        defaults={'expiration_date': expiration_date, 'selected_plan': plan}
    )

def save_square_customer_info(user, customer_id, card_id):
    SquareCustomer.objects.update_or_create(
        user=user,
        defaults={'customer_id': customer_id, 'card_id': card_id}
    )
