from django import forms
from .models import Requisition

class RequisitionForm(forms.ModelForm):
    class Meta:
        model = Requisition
        fields = [
            'origin_type', 'company', 'region', 'branch',
            'department', 'cost_center', 'amount', 'purpose', 'receipt', 'is_urgent', 'urgency_reason'
        ]
        widgets = {
            'origin_type': forms.Select(attrs={'class': 'form-control'}),
            'company': forms.Select(attrs={'class': 'form-control'}),
            'region': forms.Select(attrs={'class': 'form-control'}),
            'branch': forms.Select(attrs={'class': 'form-control'}),
            'department': forms.Select(attrs={'class': 'form-control'}),
            'cost_center': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control', 'step': '0.01'}),
            'purpose': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
            'receipt': forms.FileInput(attrs={'class': 'form-control', 'accept': 'image/*,.pdf'}),
            'is_urgent': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
            'urgency_reason': forms.Textarea(attrs={'class': 'form-control', 'rows': 2}),
        }
    
    def clean(self):
        """Phase 3: Validate urgency_reason is required when is_urgent=True"""
        cleaned_data = super().clean()
        is_urgent = cleaned_data.get('is_urgent')
        urgency_reason = cleaned_data.get('urgency_reason')
        
        if is_urgent and not urgency_reason:
            raise forms.ValidationError(
                "Urgency reason is required when marking a requisition as urgent."
            )
        
        return cleaned_data
