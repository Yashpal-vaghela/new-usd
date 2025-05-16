from django.shortcuts import render, redirect
from django.http import HttpResponse
from home.forms import UserSubmissionForm  
from .models import UserSubmission
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