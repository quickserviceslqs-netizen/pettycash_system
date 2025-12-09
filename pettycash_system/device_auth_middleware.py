"""
Device Authentication Middleware
Restricts login to whitelisted devices only
"""

from django.contrib import messages
from django.shortcuts import redirect
from django.urls import reverse

from accounts.models_device import DeviceAccessAttempt, WhitelistedDevice
from settings_manager.models import get_setting


def get_device_info(request):
    """Extract device information from request"""
    user_agent = request.META.get("HTTP_USER_AGENT", "")

    # Parse device name from user agent
    device_name = "Unknown Device"
    if "Windows" in user_agent:
        if "Windows NT 10" in user_agent or "Windows NT 11" in user_agent:
            device_name = "Windows 10/11"
        elif "Windows NT 6" in user_agent:
            device_name = "Windows 7/8"
        else:
            device_name = "Windows"
    elif "Macintosh" in user_agent or "Mac OS X" in user_agent:
        device_name = "macOS"
    elif "Linux" in user_agent:
        device_name = "Linux"
    elif "Android" in user_agent:
        device_name = "Android"
    elif "iPhone" in user_agent or "iPad" in user_agent:
        device_name = "iOS"

    # Add browser info
    if "Chrome" in user_agent and "Edg" not in user_agent:
        device_name += " - Chrome"
    elif "Edg" in user_agent:
        device_name += " - Edge"
    elif "Firefox" in user_agent:
        device_name += " - Firefox"
    elif "Safari" in user_agent and "Chrome" not in user_agent:
        device_name += " - Safari"

    return {"device_name": device_name, "user_agent": user_agent}


def get_client_ip(request):
    """Extract client IP from request"""
    x_forwarded_for = request.META.get("HTTP_X_FORWARDED_FOR")
    if x_forwarded_for:
        ip = x_forwarded_for.split(",")[0].strip()
    else:
        ip = request.META.get("REMOTE_ADDR")
    return ip


def get_location(ip_address):
    """Get location from IP address using geolocation API"""
    enable_geolocation = get_setting("ENABLE_ACTIVITY_GEOLOCATION", "true")

    if enable_geolocation != "true":
        return ""

    try:
        import requests

        response = requests.get(f"http://ip-api.com/json/{ip_address}", timeout=2)
        if response.status_code == 200:
            data = response.json()
            if data.get("status") == "success":
                city = data.get("city", "")
                region = data.get("regionName", "")
                country = data.get("country", "")
                return (
                    f"{city}, {region}, {country}" if city else f"{region}, {country}"
                )
    except:
        pass

    return ""


class DeviceAuthenticationMiddleware:
    """
    Middleware to restrict access to whitelisted devices only.
    Users can only login from registered devices.
    """

    def __init__(self, get_response):
        self.get_response = get_response

        # URLs that should always be accessible
        self.exempt_urls = [
            "/accounts/login/",
            "/accounts/logout/",
            "/accounts/signup/",
            "/accounts/device-blocked/",
            "/accounts/request-device/",
            "/static/",
            "/media/",
            "/admin/login/",
        ]

    def __call__(self, request):
        # Check if device whitelist enforcement is enabled
        enforce_device_whitelist = get_setting("ENFORCE_DEVICE_WHITELIST", "false")

        if enforce_device_whitelist == "true" and request.user.is_authenticated:
            # Skip exempt URLs
            if not self.is_exempt_url(request.path):
                # Check if device is whitelisted
                if not self.is_device_whitelisted(request):
                    # Log blocked attempt
                    self.log_blocked_attempt(request)

                    # Logout user and redirect to blocked page
                    from django.contrib.auth import logout

                    logout(request)
                    return redirect("device_blocked")

        response = self.get_response(request)
        return response

    def is_exempt_url(self, path):
        """Check if URL should bypass device check"""
        for exempt in self.exempt_urls:
            if path.startswith(exempt):
                return True
        return False

    def is_device_whitelisted(self, request):
        """Check if current device is whitelisted and active"""
        device_info = get_device_info(request)
        ip_address = get_client_ip(request)
        user_agent = device_info["user_agent"]

        # Check if exact device exists and is active
        device = WhitelistedDevice.objects.filter(
            user=request.user, user_agent=user_agent, is_active=True
        ).first()

        if device:
            # Update last used timestamp
            device.save()  # This triggers auto_now on last_used_at
            return True

        return False

    def log_blocked_attempt(self, request):
        """Log blocked device access attempt"""
        device_info = get_device_info(request)
        ip_address = get_client_ip(request)
        location = get_location(ip_address)

        DeviceAccessAttempt.objects.create(
            user=request.user,
            ip_address=ip_address,
            device_name=device_info["device_name"],
            user_agent=device_info["user_agent"],
            location=location,
            was_allowed=False,
            reason="Device not whitelisted",
            request_path=request.path,
        )
