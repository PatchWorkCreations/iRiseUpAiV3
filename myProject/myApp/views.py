
from django.conf import settings
from django.utils import timezone
from datetime import datetime, timedelta
from .models import AIUserAccess
from django.shortcuts import render, get_object_or_404, redirect
from .models import BotService, AIUserAccess
from django.contrib.auth.decorators import login_required
from square.client import Client


def personalized_plan(request):
    if request.method == 'POST':
        gender = request.POST.get('gender')
        special_goal = request.POST.get('special_goal')
        main_goal = request.POST.get('main_goal')
        
        # Store data in the session
        if gender:
            request.session['gender'] = gender
        if special_goal:
            request.session['special_goal'] = special_goal
        if main_goal:
            request.session['main_goal'] = main_goal
        
        return redirect('next_view_name')  # Replace 'next_view_name' with the actual view name you want to redirect to

    # If the request is GET, render the template with the current session data
    gender = request.session.get('gender', '')
    special_goal = request.session.get('special_goal', '')
    main_goal = request.session.get('main_goal', '')
    
    context = {
        'gender': gender,
        'special_goal': special_goal,
        'main_goal' : main_goal,
    }

    return render(request, 'myApp/personalized_plan.html', context)


# Initialize the Square Client
square_client = Client(
    access_token=settings.SQUARE_ACCESS_TOKEN,
    environment='production',
)

import json
import logging
from django.http import JsonResponse

logger = logging.getLogger(__name__)

def setSelectedPlanInSession(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            selected_plan = data.get('plan')
            logger.info(f"Selected plan received by backend: {selected_plan}")

            allowed_plans = ['1-week', '4-week', '12-week', 'lifetime']
            if selected_plan not in allowed_plans:
                logger.error(f"Invalid plan selected: {selected_plan}")
                return JsonResponse({'success': False, 'error': 'Invalid plan selected.'})

            request.session['selected_plan'] = selected_plan
            return JsonResponse({'success': True})
        except Exception as e:
            logger.error("Error in setSelectedPlanInSession:", exc_info=True)
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'error': 'Invalid request method.'}, status=405)



def determine_amount_based_on_plan(selected_plan):
    if selected_plan == '1-week':
        return 1287  # $12.87 in cents
    elif selected_plan == '4-week':
        return 3795  # $37.95 in cents
    elif selected_plan == '12-week':
        return 9700  # $97.00 in cents
    elif selected_plan == 'lifetime':
        return 29700  # $297.00 in cents
    else:
        return 0  # Default to 0 for unrecognized plans


def grant_BotService_access(user, selected_plan):
    """
    This function grants the user access to all BotServices and sets an expiration date based on the selected plan.
    """
    # Get all BotServices available in the BotService menu
    BotServices = BotService.objects.all()

    # Set a default expiration date (optional)
    expiration_date = None

    # Determine expiration date based on selected plan
    if selected_plan == '1-week':
        expiration_date = timezone.now() + timedelta(weeks=1)
    elif selected_plan == '4-week':
        expiration_date = timezone.now() + timedelta(weeks=4)
    elif selected_plan == '12-week':
        expiration_date = timezone.now() + timedelta(weeks=12)
    elif selected_plan == 'lifetime':
        expiration_date = None 
    else:
        # Handle the case where the selected plan is not recognized
        expiration_date = timezone.now() + timedelta(weeks=4)  # Default to 1 week if plan is unrecognized
        # Optionally, log a warning or handle this situation differently
        logger.warning(f"Unrecognized selected plan: {selected_plan}, defaulting to 4 week expiration.")

    # Grant access to all BotServices with the determined expiration date
    for BotService in BotServices:
        AIUserAccess.objects.create(user=user, BotService=BotService, progress=0.0, expiration_date=expiration_date)

    return True

from django.core.mail import EmailMultiAlternatives

def send_welcomepassword_email(user_email, random_password):
    """
    Sends a personalized welcome email with HTML design to new users.
    """
    subject = 'Welcome to iRiseUp Academy – Your Account is Ready!'
    from_email = 'hello@iriseupacademy.com'
    to_email = [user_email]

    # Plain text content for fallback
    text_content = (
        f"Dear {user_email},\n\n"
        "Welcome to iRiseUp Academy! Your account has been successfully created.\n"
        f"Here is your temporary password: {random_password}\n\n"
        "Please log in to update your password and start your learning journey.\n\n"
        "Best regards,\n"
        "The iRiseUp Academy Team"
    )

    # HTML content (you can use your email design)
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <title>Welcome to iRiseUp Academy</title>
        <style>
            body {{
                font-family: Arial, sans-serif;
                color: #333;
                line-height: 1.6;
                margin: 0;
                padding: 0;
                background-color: #f4f4f4;
            }}
            .container {{
                width: 100%;
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border-radius: 8px;
                box-shadow: 0 2px 8px rgba(0, 0, 0, 0.1);
                overflow: hidden;
            }}
            .header {{
                background-color: #5860F8;
                color: #ffffff;
                padding: 20px;
                text-align: center;
            }}
            .header img {{
                max-width: 120px;
                margin-bottom: 10px;
            }}
            .header h1 {{
                margin: 0;
                font-size: 28px;
                font-weight: bold;
            }}
            .content {{
                padding: 30px 20px;
                text-align: left;
                background-color: #ffffff;
            }}
            .content p {{
                font-size: 16px;
                margin-bottom: 20px;
            }}
            .button {{
                display: inline-block;
                padding: 12px 25px;
                color: #ffffff;
                background-color: #5860F8;
                text-decoration: none;
                border-radius: 5px;
                font-size: 16px;
                margin-top: 20px;
            }}
            .button:hover {{
                background-color: #4752c4;
            }}
            .footer {{
                text-align: center;
                padding: 20px;
                background-color: #f4f4f4;
                color: #888;
                font-size: 12px;
            }}
            .footer p {{
                margin: 0;
            }}
            .footer a {{
                color: #5860F8;
                text-decoration: none;
            }}
        </style>
    </head>
    <body>
        <div class="container">
            <!-- Email Header -->
            <div class="header">
                <img src="https://www.iriseupacademy.com/static/myapp/images/resource/author-6.png" alt="iRiseUp Academy Logo">
                <h1>Welcome to iRiseUp Academy, {user_email}!</h1>
            </div>

            <!-- Email Content -->
            <div class="content">
                <p>Hello {user_email},</p>
                <p>Your account has been successfully created. Below is your temporary password:</p>
                <p><strong>Temporary Password:</strong> {random_password}</p>
                <p>Please log in and update your password for security.</p>
                <a href="https://www.iriseupacademy.com/sign_in" class="button">Log In Now</a>
                <p>Best regards,<br><strong>The iRiseUp Academy Team</strong></p>
            </div>

            <!-- Email Footer -->
            <div class="footer">
                <p>iRiseUp Academy, Columbus, Ohio, USA | <a href="https://iriseupacademy.com/unsubscribe">Unsubscribe</a></p>
            </div>
        </div>
    </body>
    </html>
    """

    # Create the email message with plain text and HTML alternatives
    email = EmailMultiAlternatives(subject, text_content, from_email, to_email)
    email.attach_alternative(html_content, "text/html")
    email.send()

from django.utils import timezone
from datetime import timedelta
import logging
from .models import BotService, AIUserAccess

logger = logging.getLogger(__name__)

def grant_service_access(user, selected_plan):
    """
    Grants the user access to all bot services and sets an expiration date based on the selected plan.
    """
    # Get all bot services available
    services = BotService.objects.all()

    # Set a default expiration date (optional)
    expiration_date = None

    # Determine expiration date based on selected plan
    if selected_plan == '1-week':
        expiration_date = timezone.now() + timedelta(weeks=1)
    elif selected_plan == '4-week':
        expiration_date = timezone.now() + timedelta(weeks=4)
    elif selected_plan == '12-week':
        expiration_date = timezone.now() + timedelta(weeks=12)
    elif selected_plan == 'lifetime':
        expiration_date = None  # Lifetime access, no expiration
    else:
        # Handle unrecognized plans
        expiration_date = timezone.now() + timedelta(weeks=4)  # Default to 4 weeks if unrecognized
        logger.warning(f"Unrecognized selected plan: {selected_plan}, defaulting to 4-week expiration.")

    # Grant access to all bot services with the determined expiration date
    for service in services:
        AIUserAccess.objects.create(
            user=user,
            bot_service=service,
            expiration_date=expiration_date,
            progress=0.0
        )

    return True


# Get an instance of a logger
logger = logging.getLogger('myapp')

from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils.crypto import get_random_string
from django.core.mail import send_mail
import json
import uuid
import logging
from square.client import Client
from .models import User  # Adjust according to your user model
from django.contrib.auth.models import User  # For User model
from django.utils.crypto import get_random_string  # For generating random passwords
from django.core.mail import send_mail  # For sending emails
from .models import BotUserPaymentInfo, User, AIUserAccess

logger = logging.getLogger(__name__)

# Initialize Square client
client = Client(
    access_token=settings.SQUARE_ACCESS_TOKEN,
    environment='production',  # Change to 'production' when you're ready
)

from django.utils.crypto import get_random_string
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth.models import User
from django.utils import timezone
import json
import uuid
import logging
from datetime import timedelta
from .models import BotService, AIUserAccess, BotBotTransaction, BotUserPaymentInfo

logger = logging.getLogger(__name__)

@csrf_exempt
def process_payment(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            card_token = data.get('source_id')
            selected_plan = data.get('plan')
            verification_token = data.get('verification_token')

            # Ensure the correct email is being used from the user's current session
            user_email = data.get('email')
            if not user_email:
                logger.error("Email is missing from form data. Cannot proceed with payment.")
                return JsonResponse({"error": "Email is missing from session."}, status=400)

            # Ensure the amount is valid based on the selected plan
            amount = determine_amount_based_on_plan(selected_plan)
            if amount <= 0:
                return JsonResponse({"error": "Invalid plan selected."}, status=400)

            # Step 1: Create a new customer or retrieve the existing one
            customer_result = square_client.customers.create_customer(
                body={
                    "given_name": data.get('givenName'),
                    "family_name": data.get('familyName'),
                    "email_address": user_email,
                }
            )
            if customer_result.is_error():
                logger.error("Customer creation failed: %s", customer_result.errors)
                user = User.objects.get(email=user_email)
                BotBotTransaction.objects.create(
                    user=user,
                    amount=amount,
                    subscription_type=selected_plan,
                    status='error',
                    error_logs=str(customer_result.errors),
                    recurring=False
                )
                return JsonResponse({"error": "Failed to create customer profile."}, status=400)

            customer_id = customer_result.body['customer']['id']

            # Step 2: Make the payment request with the verification token and store the card on file
            payment_result = square_client.payments.create_payment(
                body={
                    "source_id": card_token,
                    "idempotency_key": str(uuid.uuid4()),
                    "amount_money": {
                        "amount": amount,
                        "currency": "USD"
                    },
                    "verification_token": verification_token,
                    "autocomplete": True,
                    "customer_id": customer_id,
                }
            )
            logger.info("Square API Payment Response: %s", payment_result)

            if payment_result.is_error():
                error_codes = [error['code'] for error in payment_result.errors]
                logger.error("Payment Error: %s", error_codes)

                # Handle various error codes with specific messages
                error_messages = {
                    'CARD_DECLINED': "Your card was declined. Please try another payment method.",
                    'INSUFFICIENT_FUNDS': "Insufficient funds. Please check your account balance.",
                    'INVALID_CARD': "Invalid card details. Please check and try again.",
                    'EXPIRED_CARD': "Your card has expired. Please use another card.",
                    'NETWORK_ERROR': "Network issue encountered. Please try again later.",
                    'FRAUD_REJECTED': "Payment rejected due to suspected fraud. Please contact your bank.",
                    'AUTHENTICATION_REQUIRED': "Additional authentication required. Please complete the verification."
                }
                for code in error_codes:
                    if code in error_messages:
                        return JsonResponse({"error": error_messages[code]}, status=400)
                return JsonResponse({"error": "Payment failed. Please try again."}, status=400)

            payment_id = payment_result.body['payment']['id']

            # Step 3: Store the card on file for the customer
            card_result = square_client.cards.create_card(
                body={
                    "idempotency_key": str(uuid.uuid4()),
                    "source_id": payment_id,
                    "verification_token": verification_token,
                    "card": {
                        "cardholder_name": f"{data.get('givenName')} {data.get('familyName')}",
                        "customer_id": customer_id,
                    }
                }
            )
            if card_result.is_error():
                logger.error("Card storage failed: %s", card_result.errors)
                BotBotTransaction.objects.create(
                    user=user,
                    amount=amount,
                    subscription_type=selected_plan,
                    status='error',
                    error_logs=str(card_result.errors),
                    recurring=False
                )
                return JsonResponse({"error": "Failed to store card on file."}, status=400)

            card_id = card_result.body['card']['id']

            # Step 4: Create or retrieve the user in the Django application
            user, created = User.objects.get_or_create(
                username=user_email,
                defaults={'email': user_email}
            )

            if created:
                random_password = get_random_string(8)
                user.set_password(random_password)
                user.save()

                # Send the welcome email
                send_welcomepassword_email(user_email, random_password)

            logger.info(f"User {user_email} processed for payment.") 

            # Step 6: Store the customer_id and card_id in the database
            BotUserPaymentInfo.objects.update_or_create(
                user=user,
                defaults={'customer_id': customer_id, 'card_id': card_id}
            )

            # Step 7: Set expiration and billing dates based on the selected plan
            expiration_date = None
            next_billing_date = None
            if selected_plan == '1-week':
                expiration_date = timezone.now() + timedelta(weeks=1)
                next_billing_date = expiration_date
            elif selected_plan == '4-week':
                expiration_date = timezone.now() + timedelta(weeks=4)
                next_billing_date = expiration_date
            elif selected_plan == '12-week':
                expiration_date = timezone.now() + timedelta(weeks=12)
                next_billing_date = expiration_date
            elif selected_plan == 'lifetime':
                expiration_date = None
                next_billing_date = None

            # Update or create AIUserAccess for the plan
            AIUserAccess.objects.update_or_create(
                user=user,
                defaults={
                    'expiration_date': expiration_date,
                    'selected_plan': selected_plan
                }
            )

            # Step 9: Create a BotBotTransaction with a success status and recurring info
            BotBotTransaction.objects.create(
                user=user,
                amount=amount,
                subscription_type=selected_plan,
                status='success',
                recurring=selected_plan in ['1-week', '4-week', '12-week'],
                next_billing_date=next_billing_date
            )

            return JsonResponse({"success": True})

        except Exception as e:
            logger.error("Unexpected error occurred: %s", str(e), exc_info=True)
            user = User.objects.get(email=user_email) if 'user_email' in locals() else None
            if user:
                BotBotTransaction.objects.create(
                    user=user,
                    amount=amount,
                    subscription_type=selected_plan,
                    status='error',
                    error_logs=str(e),
                    recurring=False
                )
            return JsonResponse({"error": f"An unexpected error occurred: {str(e)}"}, status=500)

    return JsonResponse({"error": "Invalid request method."}, status=405)


from django.shortcuts import render
from .models import BotService, AIUserAccess
from django.core.paginator import Paginator

def coursemenu(request):
    if request.user.is_authenticated:
        # Get the current page number from the request
        page_number = request.GET.get('page', 1)

        # Fetch all bot services
        all_services = BotService.objects.filter(is_active=True)

        # Separate saved and favorite bot services for the user
        saved_services = AIUserAccess.objects.filter(user=request.user, is_saved=True)
        favorite_services = AIUserAccess.objects.filter(user=request.user, is_favorite=True)

        # Pagination for all services (recommended bot services)
        paginator = Paginator(all_services, 8)  # 8 bot services per page
        recommended_services_page = paginator.get_page(page_number)

        context = {
            'saved_services': saved_services,
            'favorite_services': favorite_services,
            'recommended_services_page': recommended_services_page,  # Include paginated page
        }

        return render(request, 'myapp/coursemenu.html', context)

    return render(request, 'myapp/coursemenu.html')

