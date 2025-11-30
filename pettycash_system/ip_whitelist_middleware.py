"""
IP Whitelist Middleware for Security
Restricts access based on IP addresses when enabled
"""
from django.http import HttpResponseForbidden
from django.conf import settings
from django.urls import reverse
from ipaddress import ip_address, ip_network
from settings_manager.models import get_setting


class IPWhitelistMiddleware:
    """
    Middleware to restrict access based on IP whitelist.
    
    When ENABLE_IP_WHITELIST is True, only IPs in ALLOWED_IP_ADDRESSES
    can access the system (except login page and static files).
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
        
        # URLs that should always be accessible (even when IP blocked)
        self.exempt_urls = [
            '/accounts/login/',
            '/static/',
            '/media/',
            '/admin/login/',
        ]
    
    def __call__(self, request):
        # Check if IP whitelisting is enabled (dynamic)
        ip_whitelist_enabled = get_setting('ENABLE_IP_WHITELIST', 'false') == 'true'
        allowed_ips = get_setting('ALLOWED_IP_ADDRESSES', '').split(',')

        if ip_whitelist_enabled:
            client_ip = self.get_client_ip(request)
            if not self.is_exempt_url(request.path):
                if client_ip not in allowed_ips or not client_ip:
                    return HttpResponseForbidden(
                        f"""
                        <html>
                        <head><title>Access Denied</title></head>
                        <body style=\"font-family: Arial; text-align: center; margin-top: 100px;\">
                            <h1>🚫 Access Denied</h1>
                            <p>Your IP address ({client_ip}) is not authorized to access this system.</p>
                            <p>Please contact your system administrator.</p>
                            <hr>
                            <small>IP Whitelist Security Policy Enforced</small>
                        </body>
                        </html>
                        """
                    )
        response = self.get_response(request)
        return response
    
    def get_client_ip(self, request):
        """
        Extract client IP address from request.
        Handles proxy headers (X-Forwarded-For).
        """
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            # Get first IP (actual client) from proxy chain
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        
        return ip
    
    def is_exempt_url(self, path):
        """
        Check if URL should bypass IP whitelist.
        Allows login page and static files.
        """
        for exempt in self.exempt_urls:
            if path.startswith(exempt):
                return True
        return False
    
    def is_ip_allowed(self, client_ip):
        """
        Check if client IP is in the whitelist.
        Supports individual IPs and CIDR ranges.
        
        Examples:
            192.168.1.100 - Single IP
            192.168.1.0/24 - Entire subnet (192.168.1.1-254)
            10.0.0.0/8 - Large network
        """
        # Get allowed IPs from settings
        allowed_ips_str = get_setting('ALLOWED_IP_ADDRESSES', '')
        
        if not allowed_ips_str:
            # If no IPs configured, deny all (fail-secure)
            return False
        
        # Parse allowed IPs
        allowed_ips = [ip.strip() for ip in allowed_ips_str.split(',') if ip.strip()]
        
        try:
            client = ip_address(client_ip)
            
            for allowed in allowed_ips:
                try:
                    # Check if it's a network range (CIDR notation)
                    if '/' in allowed:
                        network = ip_network(allowed, strict=False)
                        if client in network:
                            return True
                    else:
                        # Single IP address
                        if client == ip_address(allowed):
                            return True
                except ValueError:
                    # Invalid IP/network format, skip
                    continue
            
            return False
            
        except ValueError:
            # Invalid client IP format
            return False


class SecurityLoggingMiddleware:
    """
    Middleware to log security-relevant events.
    Logs blocked IP attempts and suspicious activity.
    """
    
    def __init__(self, get_response):
        self.get_response = get_response
    
    def __call__(self, request):
        response = self.get_response(request)
        
        # Log blocked access attempts (403 responses)
        if response.status_code == 403:
            from settings_manager.views import log_activity
            
            client_ip = self.get_client_ip(request)
            path = request.path
            
            # Log the blocked attempt
            log_activity(
                user=request.user if request.user.is_authenticated else None,
                action='system',
                content_type='Security',
                description=f'Blocked access attempt to {path}',
                changes={'ip': client_ip, 'path': path, 'reason': 'IP not whitelisted'},
                success=False,
                error_message='IP address not in whitelist',
                request=request
            )
        
        return response
    
    def get_client_ip(self, request):
        """Extract client IP address from request."""
        x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
        if x_forwarded_for:
            ip = x_forwarded_for.split(',')[0].strip()
        else:
            ip = request.META.get('REMOTE_ADDR')
        return ip
