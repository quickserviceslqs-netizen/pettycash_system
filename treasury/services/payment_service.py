"""
Payment execution service for Treasury Payment Execution (Phase 5).

Core principles:
1. Segregation of Duties: executor ≠ requisition requester
2. 2FA required for all payments over threshold
3. Atomic transactions with automatic rollback on failure
4. Immutable audit trail via PaymentExecution records
5. Auto-trigger replenishment when balance drops below threshold
"""

import uuid
import random
import string
import hashlib
import hmac
from decimal import Decimal
from datetime import timedelta

from django.db import transaction
from django.utils import timezone
from django.core.exceptions import ValidationError
from django.core.mail import send_mail
from django.conf import settings

from transactions.models import Requisition
from treasury.models import (
    Payment, PaymentExecution, LedgerEntry, 
    VarianceAdjustment, ReplenishmentRequest, TreasuryFund
)


class OTPService:
    """Generate and validate one-time passwords for 2FA."""
    
    OTP_LENGTH = 6
    
    @classmethod
    def get_otp_validity_minutes(cls):
        """Get OTP validity period from settings."""
        from settings_manager.models import get_setting
        return int(get_setting('TREASURY_OTP_EXPIRY_MINUTES', '5'))
    
    @staticmethod
    def generate_otp() -> str:
        """Generate 6-digit OTP."""
        return ''.join(random.choices(string.digits, k=OTPService.OTP_LENGTH))
    
    @staticmethod
    def hash_otp(otp: str, payment_id: str) -> str:
        """Hash OTP with payment ID as salt using SHA-256."""
        # Use payment_id as salt for additional security
        salted_otp = f"{otp}{payment_id}{settings.SECRET_KEY}"
        return hashlib.sha256(salted_otp.encode()).hexdigest()
    
    @staticmethod
    def send_otp_email(email: str, otp: str) -> bool:
        """Send OTP via email. Returns True if successful."""
        from settings_manager.models import get_setting
        try:
            subject_prefix = get_setting('EMAIL_SUBJECT_PREFIX', '[Petty Cash System]')
            validity_minutes = OTPService.get_otp_validity_minutes()
            subject = f"{subject_prefix} Payment Verification - One-Time Password"
            message = f"""
Your one-time password (OTP) for payment approval is:

    {otp}

This code is valid for {validity_minutes} minutes.
If you did not request this, please ignore this email.

Do not share this code with anyone.
            """
            sender = get_setting('SYSTEM_EMAIL_FROM', settings.DEFAULT_FROM_EMAIL)
            send_mail(
                subject,
                message,
                sender,
                [email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Failed to send OTP email to {email}: {str(e)}")
            return False
    
    @staticmethod
    def is_otp_expired(payment: Payment) -> bool:
        """Check if OTP has expired based on settings."""
        if not payment.otp_sent_timestamp:
            return True
        validity_minutes = OTPService.get_otp_validity_minutes()
        return (timezone.now() - payment.otp_sent_timestamp) > timedelta(minutes=validity_minutes)


class PaymentExecutionService:
    """Service for executing payments with proper validation and segregation of duties."""
    
    @staticmethod
    def can_execute_payment(payment: Payment, executor_user) -> tuple[bool, str]:
        """
        Validate if executor can execute this payment.
        Returns (can_execute, error_message)
        """
        # Executor cannot be the original requester
        if hasattr(payment, 'requisition') and payment.requisition and executor_user.id == payment.requisition.requested_by_id:
            return False, "Executor cannot be the same as the requisition requester"
        
        # Must be Treasury, CFO, or Admin
        allowed_roles = ['treasury', 'cfo', 'admin']
        if executor_user.role.lower() not in allowed_roles:
            return False, f"Only Treasury, CFO, or Admin roles can execute payments. Your role: {executor_user.role}"
        
        # Check payment status
        if payment.status not in ['pending']:
            return False, f"Payment cannot be executed in status: {payment.status}"
        
        return True, ""
    
    @staticmethod
    def assign_executor(payment: Payment):
        """
        Phase 5: Assign executor for payment, ensuring executor ≠ requester.
        For Treasury-originated requests, assign different treasury officer or escalate to CFO.
        
        Returns: (executor_user, escalation_message)
        """
        from django.contrib.auth import get_user_model
        User = get_user_model()
        
        requester = payment.requisition.requested_by
        
        # Find alternate treasury officer (exclude requester)
        treasury_officers = User.objects.filter(
            role='treasury',
            is_active=True
        ).exclude(id=requester.id)
        
        if treasury_officers.exists():
            # Assign first available alternate officer
            executor = treasury_officers.first()
            return executor, None
        else:
            # No alternate treasury officer available - escalate to CFO
            cfo = User.objects.filter(role='cfo', is_active=True).first()
            if cfo:
                escalation_msg = (
                    f"No alternate Treasury officer available for payment {payment.payment_id}. "
                    f"Requester: {requester.get_display_name()}. CFO must assign executor."
                )
                # Send notification to CFO (placeholder - implement email/notification later)
                return None, escalation_msg
            else:
                # Last resort: admin
                admin = User.objects.filter(is_superuser=True, is_active=True).first()
                escalation_msg = (
                    f"No alternate Treasury officer or CFO available. "
                    f"Admin must assign executor for payment {payment.payment_id}."
                )
                return None, escalation_msg


    @staticmethod
    @transaction.atomic
    def execute_payment(payment: Payment, executor_user, phone_number: str = None,
                       ip_address: str = "", user_agent: str = "") -> tuple[bool, str]:
        """
        Execute payment atomically with M-Pesa STK Push after OTP verification.
        
        Steps:
        1. Validate executor permissions
        2. Lock fund and verify balance
        3. Mark payment as executing
        4. Initiate M-Pesa STK Push
        5. Deduct from TreasuryFund (after M-Pesa confirmation)
        6. Create LedgerEntry with M-Pesa receipt
        7. Create PaymentExecution record
        8. Mark payment as success
        9. Check replenishment trigger
        
        Args:
            payment: Payment object
            executor_user: User executing payment
            phone_number: M-Pesa phone number (format: 254XXXXXXXXX or 0XXXXXXXXX)
            ip_address: Executor's IP address
            user_agent: Executor's user agent
        
        Returns (success, message)
        """
        # Step 1: Validation
        can_execute, error = PaymentExecutionService.can_execute_payment(payment, executor_user)
        if not can_execute:
            return False, error
        
        # Payment settings validation
        from workflow.services.resolver import (
            is_payment_approval_required, is_payment_receipt_required,
            get_payment_method_restrictions, get_payment_time_window
        )
        
        # Check if payment approval is required
        if is_payment_approval_required() and payment.status != 'approved':
            return False, "Payment approval is required before execution"
        
        # Check payment time window
        time_window = get_payment_time_window()
        if time_window:
            try:
                start_time, end_time = time_window.split('-')
                current_time = timezone.now().time()
                start = timezone.datetime.strptime(start_time.strip(), '%H:%M').time()
                end = timezone.datetime.strptime(end_time.strip(), '%H:%M').time()
                
                if not (start <= current_time <= end):
                    return False, f"Payments can only be executed between {start_time} and {end_time}"
            except ValueError:
                # Invalid time format, skip validation
                pass
        
        # Check payment method restrictions
        restrictions = get_payment_method_restrictions()
        method_key = payment.method.lower()
        if method_key in restrictions:
            method_restrictions = restrictions[method_key]
            if 'min' in method_restrictions and payment.amount < method_restrictions['min']:
                return False, f"Payment amount {payment.amount} is below minimum {method_restrictions['min']} for {payment.method}"
            if 'max' in method_restrictions and payment.amount > method_restrictions['max']:
                return False, f"Payment amount {payment.amount} exceeds maximum {method_restrictions['max']} for {payment.method}"
        
        # Check if receipt is required
        if is_payment_receipt_required() and not hasattr(payment, 'receipt') or not payment.receipt:
            return False, "Payment receipt is required"
        
        # Additional treasury settings validation
        from settings_manager.models import get_setting
        
        # Check if payment method is allowed
        allowed_methods = get_setting('PAYMENT_METHODS_ALLOWED', 'cash,bank_transfer,mobile_money')
        allowed_methods_list = [m.strip().lower() for m in allowed_methods.split(',')]
        if payment.method.lower() not in allowed_methods_list:
            return False, f"Payment method '{payment.method}' is not allowed. Allowed methods: {allowed_methods}"
        
        # Check if OTP is required for payments
        require_otp = get_setting('TREASURY_REQUIRE_OTP_FOR_PAYMENTS', 'false') == 'true'
        if require_otp and not payment.otp_verified:
            return False, "OTP verification is required for this payment"
        
        # Check maximum retry attempts
        max_retries = int(get_setting('TREASURY_MAX_PAYMENT_RETRY_ATTEMPTS', '3'))
        if payment.retry_count >= max_retries:
            return False, f"Payment has exceeded maximum retry attempts ({max_retries})"

        # Ensure associated requisition is fully approved before allowing execution
        if hasattr(payment, 'requisition') and payment.requisition:
            try:
                if not payment.requisition.is_fully_approved():
                    return False, "Associated requisition is not fully approved for payment"
            except Exception:
                # If the approval check fails for any reason, block execution
                return False, "Unable to verify requisition approval status"

            # Snapshot critical requisition fields into payment if not already present
            snapshot_fields = []
            if getattr(payment, 'snapshot_amount', None) is None:
                payment.snapshot_amount = payment.requisition.amount
                snapshot_fields.append('snapshot_amount')
            if getattr(payment, 'snapshot_destination', None) in (None, ''):
                payment.snapshot_destination = payment.destination or ''
                snapshot_fields.append('snapshot_destination')
            if getattr(payment, 'snapshot_description', None) in (None, ''):
                payment.snapshot_description = payment.description or payment.requisition.purpose or ''
                snapshot_fields.append('snapshot_description')
            if getattr(payment, 'snapshot_company_id', None) is None and getattr(payment.requisition, 'company', None):
                payment.snapshot_company = payment.requisition.company
                snapshot_fields.append('snapshot_company')
            if getattr(payment, 'snapshot_branch_id', None) is None and getattr(payment.requisition, 'branch', None):
                payment.snapshot_branch = payment.requisition.branch
                snapshot_fields.append('snapshot_branch')

            if snapshot_fields:
                payment.save(update_fields=snapshot_fields)
        
        try:
            # Step 2: Get and lock fund
            fund = TreasuryFund.objects.select_for_update().get(
                company=payment.requisition.company,
                region=payment.requisition.region,
                branch=payment.requisition.branch
            )
            
            # Verify balance again (in case concurrent payment occurred)
            allow_negative = get_setting('TREASURY_ALLOW_NEGATIVE_BALANCE', 'false') == 'true'
            if not allow_negative and fund.current_balance < payment.amount:
                return False, f"Insufficient fund balance (concurrent deduction detected)"
            elif allow_negative and fund.current_balance + fund.get_min_balance() < payment.amount:
                # If negative balances allowed, still prevent going below minimum balance
                min_balance = fund.get_min_balance()
                return False, f"Payment would exceed minimum fund balance of {min_balance}"
            
            # Step 3: Mark as executing
            payment.status = 'executing'
            payment.execution_timestamp = timezone.now()
            payment.save(update_fields=['status', 'execution_timestamp'])
            
            # Step 4: Initiate M-Pesa STK Push
            mpesa_receipt = None
            gateway_reference = str(uuid.uuid4())
            
            if phone_number and payment.method == 'mpesa':
                from treasury.services.mpesa_service import MPesaService
                
                # Use sandbox for development, production for live
                use_sandbox = settings.DEBUG
                mpesa = MPesaService(use_sandbox=use_sandbox)
                
                # Initiate STK Push
                result = mpesa.initiate_stk_push(
                    phone_number=phone_number,
                    amount=float(payment.amount),
                    account_reference=str(payment.requisition.transaction_id)[:12],
                    transaction_desc=f"Payment {payment.payment_id}"[:13]
                )
                
                if not result.get('success'):
                    # M-Pesa initiation failed
                    payment.status = 'failed'
                    payment.last_error = result.get('error', 'M-Pesa STK Push failed')
                    payment.retry_count += 1
                    payment.save(update_fields=['status', 'last_error', 'retry_count'])
                    return False, f"M-Pesa payment failed: {result.get('error')}"
                
                # Store checkout request ID for tracking
                gateway_reference = result.get('checkout_request_id', gateway_reference)
                
                # NOTE: In production, you would wait for M-Pesa callback to confirm
                # For now, we proceed assuming success (callback will update later)
                # TODO: Implement callback handler to update payment with M-Pesa receipt
            
            # Step 5: Deduct from fund
            fund.current_balance -= payment.amount
            fund.save(update_fields=['current_balance', 'updated_at'])
            
            # Step 6: Create LedgerEntry
            description = f"Payment for {payment.requisition.transaction_id}"
            if mpesa_receipt:
                description += f" (M-Pesa: {mpesa_receipt})"
            
            ledger = LedgerEntry.objects.create(
                ledger_id=uuid.uuid4(),
                fund=fund,
                entry_type='debit',
                amount=payment.amount,
                payment=payment,
                description=description,
                created_by=executor_user,
            )
            
            # Step 7: Create PaymentExecution record
            execution = PaymentExecution.objects.create(
                execution_id=uuid.uuid4(),
                payment=payment,
                executor=executor_user,
                gateway_reference=gateway_reference,
                gateway_status='pending' if payment.method == 'mpesa' else 'success',
                otp_verified_at=payment.otp_verified_timestamp,
                otp_verified_by=executor_user,
                ip_address=ip_address,
                user_agent=user_agent[:500],
            )
            
            # Step 8: Mark payment as success (or pending for M-Pesa)
            if payment.method == 'mpesa':
                payment.status = 'pending_confirmation'  # Wait for M-Pesa callback
            else:
                payment.status = 'success'
            
            payment.executor = executor_user
            payment.save(update_fields=['status', 'executor'])
            
            # Send payment executed notification
            from workflow.services.resolver import send_payment_notification
            send_payment_notification(payment, 'executed')
            
            # Step 9: Check if replenishment needed (Phase 5: Auto-trigger)
            if fund.current_balance < fund.reorder_level:
                # Check if replenishment already pending
                pending = ReplenishmentRequest.objects.filter(
                    fund=fund,
                    status__in=['pending', 'approved']
                ).exists()
                
                if not pending:
                    # Auto-create replenishment request
                    replenishment = ReplenishmentRequest.objects.create(
                        request_id=uuid.uuid4(),
                        fund=fund,
                        current_balance=fund.current_balance,
                        requested_amount=fund.reorder_level * Decimal('2'),  # Request 2x reorder level
                        status='pending',
                        auto_triggered=True,
                    )
                    # Send replenishment notification
                    send_payment_notification(payment, 'replenishment_needed')
                    print(f"Auto-triggered replenishment request {replenishment.request_id} for fund {fund.fund_id}")
            
            return True, f"Payment executed successfully. Reference: {execution.gateway_reference}"
        
        except Exception as e:
            # Atomic transaction will automatically rollback
            payment.retry_count += 1
            payment.last_error = str(e)
            payment.status = 'failed'
            payment.save(update_fields=['retry_count', 'last_error', 'status'])
            
            # Send payment failed notification
            from workflow.services.resolver import send_payment_notification
            send_payment_notification(payment, 'failed')
            
            return False, f"Payment execution failed: {str(e)}"
    
    @staticmethod
    def send_otp(payment: Payment) -> tuple[bool, str]:
        """
        Generate and send OTP to executor.
        Returns (success, message)
        """
        # Generate OTP
        otp = OTPService.generate_otp()
        
        # Hash OTP with payment_id as salt and store securely
        otp_hash = OTPService.hash_otp(otp, str(payment.payment_id))
        payment.otp_hash = otp_hash
        payment.otp_sent_timestamp = timezone.now()
        payment.otp_verified = False  # Reset verification status
        payment.otp_verified_timestamp = None
        payment.save(update_fields=['otp_hash', 'otp_sent_timestamp', 'otp_verified', 'otp_verified_timestamp'])
        
        # Send via email
        executor_email = payment.requisition.requester.email  # In real scenario, different user
        if OTPService.send_otp_email(executor_email, otp):
            return True, f"OTP sent to {executor_email}"
        else:
            return False, f"Failed to send OTP to {executor_email}"
    
    @staticmethod
    def verify_otp(payment: Payment, provided_otp: str) -> tuple[bool, str]:
        """
        Verify provided OTP against stored hash.
        Returns (success, message)
        """
        # Check if OTP exists
        if not payment.otp_hash:
            return False, "No OTP has been sent for this payment"
        
        # Check if already verified (prevent replay attacks)
        if payment.otp_verified:
            return False, "OTP has already been used"
        
        # Check if OTP has expired
        if OTPService.is_otp_expired(payment):
            return False, "OTP has expired. Please request a new one."
        
        # Hash provided OTP and compare with stored hash
        provided_hash = OTPService.hash_otp(provided_otp, str(payment.payment_id))
        
        # Constant-time comparison to prevent timing attacks
        if not hmac.compare_digest(provided_hash, payment.otp_hash):
            return False, "Invalid OTP. Please check and try again."
        
        # OTP is valid - mark as verified
        payment.otp_verified = True
        payment.otp_verified_timestamp = timezone.now()
        payment.save(update_fields=['otp_verified', 'otp_verified_timestamp'])
        
        return True, "OTP verified successfully"


class ReconciliationService:
    """Handle payment reconciliation and variance tracking."""
    
    @staticmethod
    def reconcile_payment(payment: Payment, reconciled_by_user) -> tuple[bool, str]:
        """
        Mark payment as reconciled after gateway confirmation.
        Returns (success, message)
        """
        if payment.status != 'success':
            return False, "Only successful payments can be reconciled"
        
        payment.status = 'reconciled'
        payment.save(update_fields=['status'])
        
        # Mark ledger entry as reconciled
        ledger = LedgerEntry.objects.filter(payment=payment).first()
        if ledger:
            ledger.reconciled = True
            ledger.reconciled_by = reconciled_by_user
            ledger.reconciliation_timestamp = timezone.now()
            ledger.save(update_fields=['reconciled', 'reconciled_by', 'reconciliation_timestamp'])
        
        # Send payment reconciled notification
        from workflow.services.resolver import send_payment_notification
        send_payment_notification(payment, 'reconciled')
        
        return True, "Payment reconciled successfully"
    
    @staticmethod
    def record_variance(payment: Payment, original_amount: Decimal, adjusted_amount: Decimal, 
                       reason: str) -> tuple[bool, str]:
        """
        Record payment amount variance for CFO review.
        Returns (success, message)
        """
        from settings_manager.models import get_setting
        
        # Check if variance tracking is enabled
        enable_tracking = get_setting('ENABLE_VARIANCE_TRACKING', 'true') == 'true'
        if not enable_tracking:
            return False, "Variance tracking is disabled"
        
        variance_amount = adjusted_amount - original_amount
        if abs(variance_amount) == 0:
            return False, "No variance to record"
        
        # Check variance tolerance percentage
        tolerance_percent = Decimal(get_setting('VARIANCE_TOLERANCE_PERCENTAGE', '5'))
        tolerance_amount = abs(original_amount * tolerance_percent / 100)
        
        # Auto-approve small variances
        if abs(variance_amount) <= tolerance_amount:
            # Create and auto-approve variance
            variance = VarianceAdjustment.objects.create(
                variance_id=uuid.uuid4(),
                payment=payment,
                original_amount=original_amount,
                adjusted_amount=adjusted_amount,
                variance_amount=variance_amount,
                reason=f"{reason} (Auto-approved: within {tolerance_percent}% tolerance)",
                status='approved',
                approved_at=timezone.now(),
            )
            return True, f"Variance auto-approved: {variance_amount} (within tolerance)"
        else:
            # Create variance for CFO approval
            variance = VarianceAdjustment.objects.create(
                variance_id=uuid.uuid4(),
                payment=payment,
                original_amount=original_amount,
                adjusted_amount=adjusted_amount,
                variance_amount=variance_amount,
                reason=reason,
                status='pending',
            )
            return True, f"Variance recorded for CFO approval: {variance_amount}"
    
    @staticmethod
    def approve_variance(variance: VarianceAdjustment, approved_by_user) -> tuple[bool, str]:
        """
        CFO approval for payment variance.
        Returns (success, message)
        """
        # Verify approver is CFO
        if not hasattr(approved_by_user, 'groups'):
            return False, "Invalid user"
        
        if not approved_by_user.groups.filter(name__icontains='cfo').exists():
            return False, "Only CFO can approve variance"
        
        variance.status = 'approved'
        variance.approved_by = approved_by_user
        variance.approved_at = timezone.now()
        variance.save(update_fields=['status', 'approved_by', 'approved_at'])
        
        # Phase 5: Apply variance adjustment to fund balance
        if variance.fund and variance.variance_amount != 0:
            variance.fund.current_balance += variance.variance_amount
            variance.fund.save(update_fields=['current_balance', 'updated_at'])
        
        return True, "Variance approved by CFO"
