import requests
from django.shortcuts import render, redirect
from django.http import HttpResponse
from home.forms import UserSubmissionForm  
from .models import NewsletterSubscriber
from django.contrib import messages 

# Create your views here.
def singup(request):
    context = {

    }
    return render(request, 'singup.html', context)

    
def dentistreq(request):
    if request.method == 'POST':
        form = UserSubmissionForm(request.POST)
        if form.is_valid():
            # Save the form data to the database
            user_submission = form.save()

            # Create a success message to display as a popup
            messages.success(request, f"Form submitted successfully! Thank you, {user_submission.first_name} {user_submission.last_name}.")

            # Redirect to the Thank You page
            return redirect('home:thankyou')  # Assuming 'home:thankyou' is the URL for the Thank You page
        else:
            # Handle form errors
            return render(request, 'doctorreq.html', {'form': form, 'error_message': 'Please correct the errors below.'})
    else:
        form = UserSubmissionForm()

    context = {
        'form': form,
    }
    return render(request, 'doctorreq.html', context)

def NewsletterSubscribe(request):
    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()

        if not email:
            messages.error(request, "Please provide a valid email address.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        if NewsletterSubscriber.objects.filter(email=email).exists():
            messages.info(request, "This email is already subscribed.")
            return redirect(request.META.get('HTTP_REFERER', '/'))

        # Save to database
        NewsletterSubscriber.objects.create(email=email)

        # -------- CALL BIK API WEBHOOK --------
        try:
            webhook_url = (
                "https://bikapi.bikayi.app/chatbot/webhook/"
                "N8eHI9BWzqVPK7RnXu2xs5qIQt23"
                "?flow=thankyousu7449"
            )

            payload = {
                "Email": email
            }

            headers = {
                "Content-Type": "application/json"
            }

            response = requests.post(
                webhook_url,
                json=payload,
                headers=headers,
                timeout=5
            )

            # Optional: log response for debugging
            # print(response.status_code, response.text)

        except Exception as e:
            # Webhook failure should NOT block subscription
            print("BIK webhook failed:", e)

        messages.success(
            request,
            "Thank you for subscribing to our newsletter!"
        )

    return redirect(request.META.get('HTTP_REFERER', '/'))


def customer(request):
    context = {

    }
    return render(request, 'customer.html', context)



def patient_review(request):
    context = {

    }
    return render(request, 'patient_review.html', context)

def patient_password(request):
    context = {

    }
    return render(request, 'patient_password.html', context)

def patient_profile(request):
    context = {

    }
    return render(request, 'patient_profile.html', context)