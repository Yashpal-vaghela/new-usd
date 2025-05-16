from django import forms
from account.models import *
class ContactForm(forms.ModelForm):
    class Meta:
        model = Contact
        fields= '__all__'
        
        
        
class UserSubmissionForm(forms.ModelForm):
    class Meta:
        model = UserSubmission
        fields = ['first_name', 'last_name', 'phone', 'email', 'agree_to_terms']
        widgets = {
            'first_name': forms.TextInput(attrs={'class': 'form-control ', 'placeholder': 'First Name'}),
            'last_name': forms.TextInput(attrs={'class': 'form-control ', 'placeholder': 'Last Name'}),
            'phone': forms.TextInput(attrs={'class': 'form-control ', 'placeholder': 'Phone'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'Email'}),
            'agree_to_terms': forms.CheckboxInput(attrs={'id': 'td33'}),
        }
