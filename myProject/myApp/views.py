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