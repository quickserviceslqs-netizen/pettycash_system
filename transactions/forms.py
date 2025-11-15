from django import forms
from .models import Requisition

class RequisitionForm(forms.ModelForm):
    class Meta:
        model = Requisition
        fields = [
            'origin_type', 'company', 'region', 'branch',
            'department', 'amount', 'purpose', 'is_urgent', 'urgency_reason'
        ]
        widgets = {
            'origin_type': forms.Select(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'is_urgent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'urgency_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
