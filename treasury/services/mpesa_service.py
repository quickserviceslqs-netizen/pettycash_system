"""
M-Pesa Daraja API Integration Service
Handles STK Push for payment execution after 2FA verification.
"""

import base64
from datetime import datetime

import requests
from django.conf import settings
from django.utils import timezone


class MPesaService:
    """
    Safaricom M-Pesa Daraja API integration.
    Processes payments via STK Push after OTP verification.
    """

    # Daraja API endpoints
    SANDBOX_BASE_URL = "https://sandbox.safaricom.co.ke"
    PRODUCTION_BASE_URL = "https://api.safaricom.co.ke"

    AUTH_URL = "/oauth/v1/generate?grant_type=client_credentials"
    STK_PUSH_URL = "/mpesa/stkpush/v1/processrequest"
    QUERY_URL = "/mpesa/stkpushquery/v1/query"

    def __init__(self, use_sandbox=True):
        """
        Initialize M-Pesa service.

        Args:
            use_sandbox: If True, use sandbox environment. False for production.
        """
        self.base_url = (
            self.SANDBOX_BASE_URL if use_sandbox else self.PRODUCTION_BASE_URL
        )

        # Get credentials from settings
        self.consumer_key = getattr(settings, "MPESA_CONSUMER_KEY", "")
        self.consumer_secret = getattr(settings, "MPESA_CONSUMER_SECRET", "")
        self.business_shortcode = getattr(settings, "MPESA_SHORTCODE", "")
        self.passkey = getattr(settings, "MPESA_PASSKEY", "")
        self.callback_url = getattr(settings, "MPESA_CALLBACK_URL", "")

        self.access_token = None
        self.token_expiry = None

    def get_access_token(self) -> str:
        """
        Get OAuth access token from Daraja API.
        Tokens are cached and reused until expiry.

        Returns:
            Access token string
        """
        # Return cached token if still valid
        if (
            self.access_token
            and self.token_expiry
            and timezone.now() < self.token_expiry
        ):
            return self.access_token

        # Generate new token
        auth_url = f"{self.base_url}{self.AUTH_URL}"

        # Base64 encode credentials
        credentials = f"{self.consumer_key}:{self.consumer_secret}"
        encoded_credentials = base64.b64encode(credentials.encode()).decode()

        headers = {"Authorization": f"Basic {encoded_credentials}"}

        try:
            response = requests.get(auth_url, headers=headers)
            response.raise_for_status()

            data = response.json()
            self.access_token = data["access_token"]

            # Set expiry (tokens valid for ~1 hour, we set 50 minutes to be safe)
            from datetime import timedelta

            self.token_expiry = timezone.now() + timedelta(minutes=50)

            return self.access_token

        except requests.exceptions.RequestException as e:
            raise Exception(f"Failed to get M-Pesa access token: {str(e)}")

    def generate_password(self) -> tuple[str, str]:
        """
        Generate password for STK Push request.

        Returns:
            Tuple of (password, timestamp)
        """
        timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
        data_to_encode = f"{self.business_shortcode}{self.passkey}{timestamp}"
        password = base64.b64encode(data_to_encode.encode()).decode()
        return password, timestamp

    def initiate_stk_push(
        self,
        phone_number: str,
        amount: float,
        account_reference: str,
        transaction_desc: str,
    ) -> dict:
        """
        Initiate STK Push to customer's phone.

        Args:
            phone_number: Customer phone in format 254XXXXXXXXX
            amount: Amount to charge (minimum 1 KES)
            account_reference: Reference for the transaction (e.g., requisition ID)
            transaction_desc: Description of transaction

        Returns:
            Dict with response data including CheckoutRequestID
        """
        # Get access token
        access_token = self.get_access_token()

        # Generate password and timestamp
        password, timestamp = self.generate_password()

        # Prepare request
        stk_url = f"{self.base_url}{self.STK_PUSH_URL}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        # Format phone number (remove leading 0 if present, add 254)
        if phone_number.startswith("0"):
            phone_number = "254" + phone_number[1:]
        elif not phone_number.startswith("254"):
            phone_number = "254" + phone_number

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "TransactionType": "CustomerPayBillOnline",  # or "CustomerBuyGoodsOnline" for till
            "Amount": int(amount),  # M-Pesa requires integer amount
            "PartyA": phone_number,  # Customer phone number
            "PartyB": self.business_shortcode,  # Your shortcode
            "PhoneNumber": phone_number,  # Phone to receive prompt
            "CallBackURL": self.callback_url,  # Your callback endpoint
            "AccountReference": account_reference[:12],  # Max 12 chars
            "TransactionDesc": transaction_desc[:13],  # Max 13 chars
        }

        try:
            response = requests.post(stk_url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()

            # Check response
            if result.get("ResponseCode") == "0":
                return {
                    "success": True,
                    "checkout_request_id": result.get("CheckoutRequestID"),
                    "merchant_request_id": result.get("MerchantRequestID"),
                    "response_code": result.get("ResponseCode"),
                    "response_description": result.get("ResponseDescription"),
                    "customer_message": result.get("CustomerMessage"),
                }
            else:
                return {
                    "success": False,
                    "error": result.get("errorMessage", "Unknown error"),
                    "response_code": result.get("ResponseCode"),
                }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"STK Push failed: {str(e)}"}

    def query_stk_status(self, checkout_request_id: str) -> dict:
        """
        Query the status of an STK Push transaction.

        Args:
            checkout_request_id: CheckoutRequestID from STK Push response

        Returns:
            Dict with transaction status
        """
        access_token = self.get_access_token()
        password, timestamp = self.generate_password()

        query_url = f"{self.base_url}{self.QUERY_URL}"

        headers = {
            "Authorization": f"Bearer {access_token}",
            "Content-Type": "application/json",
        }

        payload = {
            "BusinessShortCode": self.business_shortcode,
            "Password": password,
            "Timestamp": timestamp,
            "CheckoutRequestID": checkout_request_id,
        }

        try:
            response = requests.post(query_url, json=payload, headers=headers)
            response.raise_for_status()

            result = response.json()

            return {
                "success": True,
                "result_code": result.get("ResultCode"),
                "result_desc": result.get("ResultDesc"),
                "checkout_request_id": result.get("CheckoutRequestID"),
                "merchant_request_id": result.get("MerchantRequestID"),
            }

        except requests.exceptions.RequestException as e:
            return {"success": False, "error": f"Query failed: {str(e)}"}


def process_mpesa_callback(callback_data: dict) -> dict:
    """
    Process M-Pesa callback data after STK Push completion.

    Args:
        callback_data: JSON data from M-Pesa callback

    Returns:
        Dict with extracted transaction details including M-Pesa receipt
    """
    try:
        body = callback_data.get("Body", {}).get("stkCallback", {})

        result_code = body.get("ResultCode")
        result_desc = body.get("ResultDesc")
        merchant_request_id = body.get("MerchantRequestID")
        checkout_request_id = body.get("CheckoutRequestID")

        # Extract callback metadata
        callback_metadata = body.get("CallbackMetadata", {}).get("Item", [])

        # Parse metadata items
        metadata = {}
        for item in callback_metadata:
            name = item.get("Name")
            value = item.get("Value")
            metadata[name] = value

        # Extract key fields
        amount = metadata.get("Amount")
        mpesa_receipt = metadata.get(
            "MpesaReceiptNumber"
        )  # This is the confirmation code
        transaction_date = metadata.get("TransactionDate")
        phone_number = metadata.get("PhoneNumber")

        return {
            "success": result_code == 0,
            "result_code": result_code,
            "result_desc": result_desc,
            "merchant_request_id": merchant_request_id,
            "checkout_request_id": checkout_request_id,
            "amount": amount,
            "mpesa_receipt": mpesa_receipt,  # M-Pesa confirmation code (e.g., QGK12345678)
            "transaction_date": transaction_date,
            "phone_number": phone_number,
        }

    except Exception as e:
        return {"success": False, "error": f"Failed to process callback: {str(e)}"}
