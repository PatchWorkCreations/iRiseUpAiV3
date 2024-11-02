# Standard Library Imports
import json
import uuid
import logging
from datetime import timedelta

# Django Imports
from django.conf import settings
from django.contrib.auth.models import User
from django.contrib.auth.tokens import default_token_generator
from django.core.exceptions import ValidationError
from django.core.mail import EmailMultiAlternatives, send_mail
from django.http import JsonResponse
from django.shortcuts import render, redirect
from django.urls import reverse, reverse_lazy
from django.utils.crypto import get_random_string
from django.utils.encoding import force_bytes, force_str
from django.utils.http import urlsafe_base64_encode, urlsafe_base64_decode
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.generic import TemplateView
from django.contrib.auth.views import (
    PasswordResetView, PasswordResetDoneView, PasswordResetConfirmView,
    PasswordResetCompleteView, PasswordChangeView, PasswordChangeDoneView
)

# App Models and Forms
from .models import SquareCustomer, UserAccess, Transaction
from .forms import CustomPasswordChangeForm

# Third-party Imports
from square.client import Client

# Initialize Logger
logger = logging.getLogger(__name__)

# Initialize Square Client
square_client = Client(
    access_token=settings.SQUARE_ACCESS_TOKEN,
    environment='production'
)

# Basic Views
def index(request):
    return render(request, 'myApp/index.html')

def contact(request):
    if request.method == 'POST':
        name = request.POST.get('form-name')
        email = request.POST.get('form-email')
        subject = request.POST.get('form-subject')
        message = request.POST.get('form-message')

        # Send email
        send_mail(
            subject,
            f'Message from {name} ({email}):\n\n{message}',
            settings.DEFAULT_FROM_EMAIL,
            [settings.DEFAULT_TO_EMAIL],
            fail_silently=False,
        )
        return redirect(reverse('index'))
    return render(request, 'index.html')

# Initialize logger and Square client
logger = logging.getLogger(__name__)
square_client = Client(
    access_token=settings.SQUARE_ACCESS_TOKEN,
    environment='production'  # Ensure this is set to 'production' for live payments
)

# Payment Processing Endpoint
# Square Payment Processing
@csrf_exempt
def process_payment(request):
    if request.method != "POST":
        return JsonResponse({"error": "Invalid request method."}, status=405)

    try:
        data = json.loads(request.body)
        card_token = data.get('source_id')
        selected_plan = data.get('plan')
        user_email = request.session.get('email')
        discount_code = data.get('discount_code')

        if not user_email or not card_token or not selected_plan:
            return JsonResponse({"error": "Missing required details."}, status=400)

        # Determine payment amount
        amount = determine_amount_based_on_plan(selected_plan)
        if discount_code == 'TESTDISCOUNT':
            amount = 100  # Apply discount

        # Retrieve or create Square customer
        customer_id = get_or_create_square_customer(data, user_email)
        if not customer_id:
            return JsonResponse({"error": "Failed to retrieve customer profile."}, status=400)

        # Process payment and return detailed error messages if applicable
        payment_result = process_square_payment(card_token, amount, customer_id)
        if payment_result.get("error"):
            logger.error("Payment error details: %s", payment_result["error"])  # Log error details
            return JsonResponse({"error": payment_result["error"]}, status=400)

        # Handle successful payment and user access logic
        user = get_or_create_user(user_email, data)
        expiration_date, next_billing_date = get_billing_dates(selected_plan)
        store_user_course_access(user, selected_plan, expiration_date)
        save_square_customer_info(user, customer_id, payment_result["card_id"])

        # Record transaction
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
        # Log unexpected errors
        logger.error("Unexpected error during payment processing: %s", str(e), exc_info=True)
        return JsonResponse({"error": "An unexpected error occurred. Please try again later."}, status=500)

# Helper Functions
def determine_amount_based_on_plan(plan):
    plan_amounts = {'1-week': 1287, '4-week': 3795, '12-week': 9700, 'lifetime': 29700}
    return plan_amounts.get(plan, 0)

def get_or_create_square_customer(data, email):
    try:
        result = square_client.customers.create_customer(
            body={
                "given_name": data.get('givenName'),
                "family_name": data.get('familyName'),
                "email_address": email
            }
        )
        if result.is_success():
            return result.body['customer']['id']
        else:
            logger.error("Square API error (create_customer): %s", result.errors)
    except Exception as e:
        logger.error("Error creating Square customer: %s", e)
    return None

def process_square_payment(card_token, amount, customer_id):
    try:
        result = square_client.payments.create_payment(
            body={
                "source_id": card_token,
                "idempotency_key": str(uuid.uuid4()),
                "amount_money": {"amount": amount, "currency": "USD"},
                "customer_id": customer_id,
            }
        )
        if result.is_success():
            return {"card_id": result.body['payment']['card_details']['card']['id']}
        else:
            # Capture detailed Square errors if the payment fails
            error_messages = [error['detail'] for error in result.errors]
            logger.error("Square Payment API error: %s", error_messages)
            return {"error": "Payment failed: " + "; ".join(error_messages)}
    except Exception as e:
        logger.error("Unexpected error in process_square_payment: %s", e, exc_info=True)
        return {"error": "An unexpected error occurred while processing payment."}

def get_or_create_user(email, data):
    user, created = User.objects.get_or_create(username=email, defaults={'email': email})
    if created:
        random_password = get_random_string(8)
        user.set_password(random_password)
        user.save()
        send_welcome_password_email(email, random_password)
    return user

def get_billing_dates(plan):
    duration = {'1-week': timedelta(weeks=1), '4-week': timedelta(weeks=4), '12-week': timedelta(weeks=12)}.get(plan)
    expiration_date = timezone.now() + duration if duration else None
    return expiration_date, expiration_date

def store_user_course_access(user, plan, expiration_date):
    UserAccess.objects.update_or_create(
        user=user, defaults={'expiration_date': expiration_date, 'selected_plan': plan}
    )

def save_square_customer_info(user, customer_id, card_id):
    SquareCustomer.objects.update_or_create(
        user=user, defaults={'customer_id': customer_id, 'card_id': card_id}
    )

def send_welcome_password_email(user_email, random_password):
    subject = 'Welcome to iRiseUp.Ai – Your Account is Ready!'
    from_email = 'hello@iriseupacademy.com'
    text_content = (
        f"Dear {user_email},\n\n"
        "Welcome to iRiseUp.Ai! Your account has been successfully created.\n"
        f"Here is your temporary password: {random_password}\n\n"
        "Please log in to update your password and start your learning journey.\n\n"
        "Best regards,\nThe iRiseUp.Ai Team"
    )
    html_content = f"""[...HTML email content...]"""  # Keep HTML content here
    email = EmailMultiAlternatives(subject, text_content, from_email, [user_email])
    email.attach_alternative(html_content, "text/html")
    email.send()

# Password Reset and Change Views
class CustomPasswordResetView(PasswordResetView):
    template_name = 'myApp/forgot_password.html'
    success_url = reverse_lazy('password_reset_done')

class CustomPasswordResetDoneView(PasswordResetDoneView):
    template_name = 'myApp/password_reset_done.html'

def custom_password_reset_confirm(request, uidb64=None, token=None):
    # Handle password reset confirmation
    pass  # Implement function logic here

class CustomPasswordResetCompleteView(PasswordResetCompleteView):
    template_name = 'myApp/password_reset_complete.html'

class CustomPasswordChangeView(PasswordChangeView):
    form_class = CustomPasswordChangeForm
    template_name = 'myApp/change_password.html'
    success_url = reverse_lazy('password_change_done')

class CustomPasswordChangeDoneView(PasswordChangeDoneView):
    template_name = 'myApp/password_change_done.html'

def password_reset_invalid_link(request, uidb64=None, token=None):
    # Handle invalid password reset link
    return render(request, 'myApp/password_reset_invalid.html')

from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login
from django.contrib import messages
from .forms import SignInForm  # Import the form
import logging
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

logger = logging.getLogger(__name__)

def sign_in(request):
    # Check if the user is already authenticated
    if request.user.is_authenticated:
        logger.debug(f"User {request.user.username} tried to access the login page while already logged in.")
        return redirect('coursemenu')  # Redirect to the course menu or appropriate page
    
    if request.method == 'POST':
        form = SignInForm(request.POST)

        if form.is_valid():
            login_identifier = form.cleaned_data.get('login_identifier')
            password = form.cleaned_data.get('password')
            logger.debug(f"Attempting login for identifier: {login_identifier}")

            # Authenticate using username or email
            user = authenticate(request, username=login_identifier, password=password)

            if user is None:
                try:
                    user = User.objects.get(email=login_identifier)
                    user = authenticate(request, username=user.username, password=password)
                except User.DoesNotExist:
                    user = None

            if user is not None:
                # Check if the user has logged in before
                if user.last_login is None:
                    logger.debug(f"First login detected for user: {user.username}")
                    login(request, user)
                    messages.info(request, 'Please change your password to continue.')
                    return redirect('password_change')
                else:
                    login(request, user)
                    logger.debug(f"Redirecting to course menu for user: {user.username}")
                    messages.success(request, f'Welcome back, {user.username}!')
                    return redirect('coursemenu')
            else:
                logger.error(f"Authentication failed for identifier: {login_identifier}")
                messages.error(request, 'Invalid username/email or password. Please try again.')
                return redirect('sign_in')

    else:
        form = SignInForm()

    return render(request, 'myApp/sign_in.html', {'form': form})


def sign_out(request):
    logout(request)  # This logs the user out
    return redirect('sign_in')  # Redirect to the sign-in page after logging out

