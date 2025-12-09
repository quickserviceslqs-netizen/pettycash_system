"""
Smoke Tests for Petty Cash Management System
Quick validation tests to run after deployment
"""

import argparse
import sys
from datetime import datetime

import requests


class SmokeTestRunner:
    """Run smoke tests against deployed environment"""

    def __init__(self, base_url, timeout=10):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.passed = 0
        self.failed = 0
        self.results = []

    def test(self, name, url, expected_status=200, method="GET", data=None):
        """Execute a single smoke test"""
        full_url = f"{self.base_url}{url}"

        try:
            if method == "GET":
                response = requests.get(full_url, timeout=self.timeout)
            elif method == "POST":
                response = requests.post(full_url, json=data, timeout=self.timeout)
            else:
                raise ValueError(f"Unsupported method: {method}")

            if response.status_code == expected_status:
                self.passed += 1
                result = f"✅ PASS: {name}"
                print(result)
                self.results.append((True, name, response.status_code))
            else:
                self.failed += 1
                result = f"❌ FAIL: {name} (Expected {expected_status}, got {response.status_code})"
                print(result)
                self.results.append((False, name, response.status_code))

        except Exception as e:
            self.failed += 1
            result = f"❌ ERROR: {name} - {str(e)}"
            print(result)
            self.results.append((False, name, str(e)))

    def run_all(self):
        """Run all smoke tests"""
        print(f"\n{'='*60}")
        print(f"SMOKE TESTS - {self.base_url}")
        print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        # Health check
        self.test("Health Check", "/health/", 200)

        # Static files
        self.test("Static Files Available", "/static/css/styles.css", 200)

        # Authentication
        self.test("Login Page Loads", "/accounts/login/", 200)

        # API Endpoints
        self.test("API Root", "/api/", 200)
        self.test(
            "Requisitions API (unauthenticated)",
            "/api/requisitions/",
            expected_status=401,
        )
        self.test(
            "Treasury API (unauthenticated)",
            "/treasury/api/dashboard/metrics/",
            expected_status=401,
        )

        # Dashboard
        self.test(
            "Dashboard Redirect", "/dashboard/", expected_status=302
        )  # Redirects to login

        # Reports
        self.test(
            "Reports Page", "/reports/", expected_status=302
        )  # Redirects to login

        # Database connection (via API)
        self.test("Database Connection", "/api/health/db/", 200)

        # Media files
        self.test(
            "Media Directory", "/media/", expected_status=404
        )  # No files expected

        print(f"\n{'='*60}")
        print(f"RESULTS: {self.passed} passed, {self.failed} failed")
        print(f"Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")

        return self.failed == 0


def main():
    parser = argparse.ArgumentParser(description="Run smoke tests after deployment")
    parser.add_argument(
        "--env",
        choices=["local", "staging", "production"],
        required=True,
        help="Environment to test",
    )
    parser.add_argument("--url", help="Custom base URL (overrides environment)")
    parser.add_argument(
        "--timeout",
        type=int,
        default=10,
        help="Request timeout in seconds (default: 10)",
    )

    args = parser.parse_args()

    # Determine base URL
    if args.url:
        base_url = args.url
    elif args.env == "local":
        base_url = "http://localhost:8000"
    elif args.env == "staging":
        base_url = "https://staging.yourcompany.com"
    elif args.env == "production":
        base_url = "https://pettycash.yourcompany.com"

    # Run tests
    runner = SmokeTestRunner(base_url, timeout=args.timeout)
    success = runner.run_all()

    # Exit with appropriate code
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
