/**
 * Payment Execution - 5-step wizard with OTP 2FA
 * Handles fund selection, payment selection, OTP request/verification, confirmation
 */

const PaymentManager = {
    currentPaymentId: null,
    currentStep: 1,
    maxSteps: 6,
    otpTimer: null,
    otpCountdown: 300, // 5 minutes in seconds
    fundId: null,

    /**
     * Initialize payment execution UI
     */
    init() {
        this.setupStepNavigation();
        this.loadFunds();
    },

    /**
     * Setup step indicators and navigation
     */
    setupStepNavigation() {
        document.querySelectorAll('.step-indicator').forEach((step, index) => {
            step.classList.toggle('active', index + 1 === this.currentStep);
        });
    },

    /**
     * Load available funds
     */
    loadFunds() {
        fetch('/api/treasury/funds/', {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.populateFundSelect(data.results || data);
        })
        .catch(error => {
            console.error('Error loading funds:', error);
            this.showError('Failed to load funds');
        });
    },

    /**
     * Populate fund dropdown
     */
    populateFundSelect(funds) {
        const select = document.getElementById('fund-select');
        if (!select) return;

        select.innerHTML = '<option value="">-- Select Fund --</option>';
        funds.forEach(fund => {
            const balance = parseFloat(fund.current_balance || 0).toLocaleString('en-IN', {maximumFractionDigits: 2});
            const option = document.createElement('option');
            option.value = fund.fund_id;
            option.textContent = `${fund.name || fund.company} - ₹${balance}`;
            select.appendChild(option);
        });
    },

    /**
     * Handle fund selection and load payments
     */
    selectFund(fundId) {
        this.fundId = fundId;
        this.loadPaymentsForFund(fundId);
    },

    /**
     * Load pending payments for selected fund
     */
    loadPaymentsForFund(fundId) {
        fetch(`/api/treasury/dashboard/pending_payments/?fund_id=${fundId}`, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'Content-Type': 'application/json',
            }
        })
        .then(response => response.json())
        .then(data => {
            this.populatePaymentSelect(data.results || data);
        })
        .catch(error => {
            console.error('Error loading payments:', error);
            this.showError('Failed to load payments');
        });
    },

    /**
     * Populate payment dropdown
     */
    populatePaymentSelect(payments) {
        const select = document.getElementById('payment-select');
        if (!select) return;

        select.innerHTML = '<option value="">-- Select Payment --</option>';
        payments.forEach(payment => {
            const amount = parseFloat(payment.amount).toLocaleString('en-IN', {maximumFractionDigits: 2});
            const reqId = payment.requisition?.transaction_id || payment.requisition_id;
            const option = document.createElement('option');
            option.value = payment.payment_id;
            option.textContent = `${reqId} - ₹${amount}`;
            select.appendChild(option);
        });
    },

    /**
     * Handle payment selection
     */
    selectPayment(paymentId) {
        this.currentPaymentId = paymentId;
        this.currentStep = 3;
        this.updateStepUI();
    },

    /**
     * Request OTP for payment
     */
    requestOTP() {
        if (!this.currentPaymentId) {
            this.showError('Please select a payment');
            return;
        }

        fetch(`/api/treasury/payments/${this.currentPaymentId}/request_otp/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'X-CSRFToken': this.getToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ payment_id: this.currentPaymentId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success || data.otp_sent) {
                this.currentStep = 4;
                this.startOTPCountdown();
                this.showSuccess('OTP sent successfully');
                this.updateStepUI();
            } else {
                this.showError(data.error || 'Failed to send OTP');
            }
        })
        .catch(error => {
            console.error('Error requesting OTP:', error);
            this.showError('Failed to request OTP');
        });
    },

    /**
     * Start OTP countdown timer (5 minutes)
     */
    startOTPCountdown() {
        this.otpCountdown = 300; // Reset to 5 minutes
        const timerElement = document.getElementById('otp-timer');

        if (this.otpTimer) {
            clearInterval(this.otpTimer);
        }

        this.otpTimer = setInterval(() => {
            this.otpCountdown--;

            const minutes = Math.floor(this.otpCountdown / 60);
            const seconds = this.otpCountdown % 60;
            const timeStr = `${minutes}:${seconds.toString().padStart(2, '0')}`;

            if (timerElement) {
                timerElement.textContent = timeStr;
                timerElement.classList.toggle('text-danger', this.otpCountdown < 60);
            }

            if (this.otpCountdown <= 0) {
                clearInterval(this.otpTimer);
                this.showError('OTP expired. Please request a new one.');
                document.getElementById('otp-input').disabled = true;
                document.getElementById('verify-otp-btn').disabled = true;
            }
        }, 1000);

        this.updateStepUI();
    },

    /**
     * Verify OTP
     */
    verifyOTP() {
        const otpInput = document.getElementById('otp-input');
        const otp = otpInput.value.trim();

        if (!otp || otp.length !== 6) {
            this.showError('Please enter a valid 6-digit OTP');
            return;
        }

        fetch(`/api/treasury/payments/${this.currentPaymentId}/verify_otp/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'X-CSRFToken': this.getToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ otp: otp })
        })
        .then(response => response.json())
        .then(data => {
            if (data.verified || data.success) {
                this.currentStep = 5;
                clearInterval(this.otpTimer);
                this.showSuccess('OTP verified successfully');
                this.updateStepUI();
            } else {
                this.showError(data.error || 'Invalid OTP');
                otpInput.value = '';
                otpInput.focus();
            }
        })
        .catch(error => {
            console.error('Error verifying OTP:', error);
            this.showError('Failed to verify OTP');
        });
    },

    /**
     * Confirm payment execution
     */
    confirmPayment() {
        const confirmCheckbox = document.getElementById('confirm-checkbox');
        
        if (!confirmCheckbox.checked) {
            this.showError('Please confirm you want to execute this payment');
            return;
        }

        this.executePaymentConfirmed();
    },

    /**
     * Execute payment after all confirmations
     */
    executePaymentConfirmed() {
        fetch(`/api/treasury/payments/${this.currentPaymentId}/execute/`, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${this.getToken()}`,
                'X-CSRFToken': this.getToken(),
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ payment_id: this.currentPaymentId })
        })
        .then(response => response.json())
        .then(data => {
            if (data.success || data.status === 'success') {
                this.currentStep = 6;
                this.showPaymentSuccess(data);
                this.updateStepUI();
            } else {
                this.showError(data.error || 'Payment execution failed');
            }
        })
        .catch(error => {
            console.error('Error executing payment:', error);
            this.showError('Failed to execute payment');
        });
    },

    /**
     * Show payment success result
     */
    showPaymentSuccess(data) {
        const resultDiv = document.getElementById('payment-result');
        if (resultDiv) {
            resultDiv.innerHTML = `
                <div class="alert alert-success">
                    <h5 class="alert-heading">✓ Payment Executed Successfully</h5>
                    <p class="mb-0">Transaction ID: ${data.transaction_id || this.currentPaymentId}</p>
                    <p class="mb-0">Status: ${data.status || 'Completed'}</p>
                    <p class="mb-2">Gateway Reference: ${data.gateway_ref || 'N/A'}</p>
                    <button class="btn btn-primary btn-sm" onclick="location.reload()">Close</button>
                </div>
            `;
        }
    },

    /**
     * Update step UI
     */
    updateStepUI() {
        document.querySelectorAll('.step-indicator').forEach((step, index) => {
            const stepNum = index + 1;
            step.classList.toggle('active', stepNum === this.currentStep);
            step.classList.toggle('completed', stepNum < this.currentStep);
        });

        document.querySelectorAll('.step-content').forEach((content, index) => {
            content.classList.toggle('d-none', index + 1 !== this.currentStep);
        });
    },

    /**
     * Execute payment (called from dashboard)
     */
    executePayment(paymentId) {
        this.currentPaymentId = paymentId;
        this.currentStep = 3;
        this.requestOTP();
    },

    /**
     * Show error message
     */
    showError(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-danger alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container-fluid')?.insertAdjacentElement('afterbegin', alert);
    },

    /**
     * Show success message
     */
    showSuccess(message) {
        const alert = document.createElement('div');
        alert.className = 'alert alert-success alert-dismissible fade show';
        alert.innerHTML = `
            ${message}
            <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
        `;
        document.querySelector('.container-fluid')?.insertAdjacentElement('afterbegin', alert);
    },

    /**
     * Get authentication token
     */
    getToken() {
        return document.querySelector('[name=csrfmiddlewaretoken]')?.value || '';
    }
};

// Export for global access
window.PaymentManager = PaymentManager;
