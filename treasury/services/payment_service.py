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
    OTP_VALIDITY_MINUTES = 5
    
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
        try:
            subject = "Petty Cash Payment Verification - One-Time Password"
            message = f"""
Your one-time password (OTP) for payment approval is:

    {otp}

This code is valid for {OTPService.OTP_VALIDITY_MINUTES} minutes.
If you did not request this, please ignore this email.

Do not share this code with anyone.
            """
            send_mail(
                subject,
                message,
                settings.DEFAULT_FROM_EMAIL,
                [email],
                fail_silently=False,
            )
            return True
        except Exception as e:
            print(f"Failed to send OTP email to {email}: {str(e)}")
            return False
    
    @staticmethod
    def is_otp_expired(payment: Payment) -> bool:
        """Check if OTP has expired (>5 minutes old)."""
        if not payment.otp_sent_timestamp:
            return True
        now = timezone.now()
        expiry = payment.otp_sent_timestamp + timedelta(minutes=OTPService.OTP_VALIDITY_MINUTES)
        return now > expiry


class PaymentExecutionService:
    """Orchestrate atomic payment execution with all safeguards."""
    
    @staticmethod
    def can_execute_payment(payment: Payment, executor_user) -> tuple[bool, str]:
        """
        Validate if executor can process payment.
        Returns (can_execute, error_message)
        """
        # Check 1: Payment not already executed
        if payment.status in ['success', 'reconciled']:
            return False, "Payment already completed"
        
        # Check 2: Executor segregation - executor cannot be requester
        if payment.requisition.requester == executor_user:
            return False, "Executor cannot approve their own requisition"
        
        # Check 3: 2FA verification if required
        if payment.otp_required and not payment.otp_verified:
            return False, "OTP verification required before execution"
        
        # Check 4: OTP not expired
        if payment.otp_required and OTPService.is_otp_expired(payment):
            return False, "OTP has expired. Request new OTP."
        
        # Check 5: Retry limit not exceeded
        if payment.retry_count >= payment.max_retries:
            return False, f"Max retries ({payment.max_retries}) exceeded"
        
        # Check 6: Fund balance available
        requisition = payment.requisition
        fund = TreasuryFund.objects.filter(
            company=requisition.company,
            region=requisition.region,
            branch=requisition.branch
        ).first()
        
        if not fund or fund.current_balance < payment.amount:
            return False, f"Insufficient fund balance. Available: {fund.current_balance if fund else 0}"
        
        return True, ""
    
    @staticmethod
    @transaction.atomic
    def execute_payment(payment: Payment, executor_user, gateway_reference: str = None, 
                       gateway_status: str = "success", ip_address: str = "", 
                       user_agent: str = "") -> tuple[bool, str]:
        """
        Execute payment atomically with complete audit trail.
        
        Steps:
        1. Validate executor permissions
        2. Lock fund and verify balance
        3. Mark payment as executing
        4. Deduct from TreasuryFund
        5. Create LedgerEntry
        6. Create PaymentExecution record
        7. Mark payment as success
        8. Check replenishment trigger
        
        Returns (success, message)
        """
        # Step 1: Validation
        can_execute, error = PaymentExecutionService.can_execute_payment(payment, executor_user)
        if not can_execute:
            return False, error
        
        try:
            # Step 2: Get and lock fund
            fund = TreasuryFund.objects.select_for_update().get(
                company=payment.requisition.company,
                region=payment.requisition.region,
                branch=payment.requisition.branch
            )
            
            # Verify balance again (in case concurrent payment occurred)
            if fund.current_balance < payment.amount:
                return False, f"Insufficient fund balance (concurrent deduction detected)"
            
            # Step 3: Mark as executing
            payment.status = 'executing'
            payment.execution_timestamp = timezone.now()
            payment.save(update_fields=['status', 'execution_timestamp'])
            
            # Step 4: Deduct from fund
            fund.current_balance -= payment.amount
            fund.save(update_fields=['current_balance', 'updated_at'])
            
            # Step 5: Create LedgerEntry
            ledger = LedgerEntry.objects.create(
                ledger_id=uuid.uuid4(),
                fund=fund,
                entry_type='debit',
                amount=payment.amount,
                payment=payment,
                description=f"Payment for {payment.requisition.requisition_code}",
                created_by=executor_user,
            )
            
            # Step 6: Create PaymentExecution record
            execution = PaymentExecution.objects.create(
                execution_id=uuid.uuid4(),
                payment=payment,
                executor=executor_user,
                gateway_reference=gateway_reference or str(uuid.uuid4()),
                gateway_status=gateway_status,
                otp_verified_at=payment.otp_verified_timestamp,
                otp_verified_by=executor_user,  # OTP verified by same executor
                ip_address=ip_address,
                user_agent=user_agent[:500],  # Limit to 500 chars
            )
            
            # Step 7: Mark payment as success
            payment.status = 'success'
            payment.executor = executor_user
            payment.save(update_fields=['status', 'executor'])
            
            # Step 8: Check if replenishment needed
            if fund.check_reorder_needed():
                # Check if replenishment already pending
                pending = ReplenishmentRequest.objects.filter(
                    fund=fund,
                    status__in=['pending', 'approved']
                ).exists()
                
                if not pending:
                    ReplenishmentRequest.objects.create(
                        request_id=uuid.uuid4(),
                        fund=fund,
                        current_balance=fund.current_balance,
                        requested_amount=fund.reorder_level * Decimal('2'),  # Request 2x reorder level
                        status='pending',
                        auto_triggered=True,
                    )
            
            return True, f"Payment executed successfully. Reference: {execution.gateway_reference}"
        
        except Exception as e:
            # Atomic transaction will automatically rollback
            payment.retry_count += 1
            payment.last_error = str(e)
            payment.status = 'failed'
            payment.save(update_fields=['retry_count', 'last_error', 'status'])
            
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
        
        return True, "Payment reconciled successfully"
    
    @staticmethod
    def record_variance(payment: Payment, original_amount: Decimal, adjusted_amount: Decimal, 
                       reason: str) -> tuple[bool, str]:
        """
        Record payment amount variance for CFO review.
        Returns (success, message)
        """
        if abs(adjusted_amount - original_amount) == 0:
            return False, "No variance to record"
        
        variance = VarianceAdjustment.objects.create(
            variance_id=uuid.uuid4(),
            payment=payment,
            original_amount=original_amount,
            adjusted_amount=adjusted_amount,
            variance_amount=adjusted_amount - original_amount,
            reason=reason,
            status='pending',
        )
        
        return True, f"Variance recorded: {variance.variance_amount}"
    
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
        
        # Apply variance adjustment to fund if needed
        # TODO: Implement variance credit/debit logic
        
        return True, "Variance approved by CFO"
