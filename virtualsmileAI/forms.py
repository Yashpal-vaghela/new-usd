from django import forms
from .models import SmileDesignLead 

class SmileDesignLeadForm(forms.ModelForm):
    class Meta:
        model = SmileDesignLead
        fields = ["name", "phone", "city", "message"]
