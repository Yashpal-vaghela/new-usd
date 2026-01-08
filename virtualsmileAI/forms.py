from django import forms
from account.models import  SmileDesignLead

class SmileDesignLeadForm(forms.ModelForm):
    class Meta:
        model = SmileDesignLead
        fields='__all__'