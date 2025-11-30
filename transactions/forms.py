from django import forms
from .models import Requisition
from settings_manager.models import get_setting

class RequisitionForm(forms.ModelForm):
    # Add a hidden field to track if this is a draft save
    is_draft = forms.BooleanField(required=False, widget=forms.HiddenInput())
    
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
        is_draft = cleaned_data.get('is_draft', False)
        
        # Only validate urgency reason if not a draft and is_urgent is True
        if not is_draft and is_urgent and not urgency_reason:
            raise forms.ValidationError(
                "Urgency reason is required when marking a requisition as urgent."
            )
        
        # Requisition settings validation - only apply to non-drafts
        if not is_draft:
            amount = cleaned_data.get('amount')
            receipt = cleaned_data.get('receipt')
            
            # Check minimum requisition amount
            min_amount = get_setting('MINIMUM_REQUISITION_AMOUNT', default=0)
            if amount and amount < min_amount:
                raise forms.ValidationError(
                    f"Requisition amount must be at least {min_amount}."
                )
            
            # Check maximum requisition amount (from approval settings)
            max_amount = get_setting('MAX_REQUISITION_AMOUNT', default=1000000)
            if amount and amount > max_amount:
                raise forms.ValidationError(
                    f"Requisition amount cannot exceed {max_amount}."
                )
            
            # Check attachment file type and size if receipt is provided
            if receipt:
                # Check allowed attachment types
                allowed_types = get_setting('ALLOWED_ATTACHMENT_TYPES', default='image/*,.pdf')
                allowed_types_list = [t.strip().lower() for t in allowed_types.split(',')]
                
                # Get file extension and content_type (if provided by upload)
                file_name = receipt.name.lower()
                file_ext = file_name.split('.')[-1] if '.' in file_name else ''
                try:
                    content_type = getattr(receipt, 'content_type', None)
                except Exception:
                    content_type = None

                # Check if file type is allowed. If content_type is present, require a
                # content-type-based match. If content_type is not provided, fall back
                # to extension-based checks (legacy behavior).
                is_allowed = False
                if content_type:
                    ct = content_type.split(';')[0].strip().lower()
                    import mimetypes
                    for allowed_type in allowed_types_list:
                        t = allowed_type.strip().lower()
                        if t == 'image/*' and ct.startswith('image/'):
                            is_allowed = True
                            break
                        if '/' in t:
                            # Exact mime match (e.g., 'application/pdf')
                            if ct == t:
                                is_allowed = True
                                break
                        # If allowed type is declared as extension, guess mime and compare
                        normalized_ext = t.lstrip('.')
                        if normalized_ext:
                            guessed = mimetypes.guess_type(f'file.{normalized_ext}')[0]
                            if guessed and guessed.split(';')[0] == ct:
                                is_allowed = True
                                break
                else:
                    # No content_type available: fall back to extension matching
                    for allowed_type in allowed_types_list:
                        t = allowed_type.strip().lower()
                        if t == 'image/*' and file_ext in ['jpg', 'jpeg', 'png', 'gif', 'bmp']:
                            is_allowed = True
                            break
                        if '/' in t:
                            # Compare subtype to extension (e.g., 'application/pdf')
                            try:
                                maintype, subtype = t.split('/', 1)
                            except ValueError:
                                maintype, subtype = t, ''
                            if subtype == file_ext or subtype.lstrip('.') == file_ext:
                                is_allowed = True
                                break
                        normalized_ext = t.lstrip('.')
                        if normalized_ext == file_ext:
                            is_allowed = True
                            break
                
                if not is_allowed:
                    raise forms.ValidationError(
                        f"Attachment type not allowed. Allowed types: {allowed_types}"
                    )
                
                # Check attachment max size
                max_size_mb = get_setting('ATTACHMENT_MAX_SIZE_MB', default=10)
                max_size_bytes = max_size_mb * 1024 * 1024
                if receipt.size > max_size_bytes:
                    raise forms.ValidationError(
                        f"Attachment size exceeds maximum allowed size of {max_size_mb} MB."
                    )
        
        return cleaned_data
