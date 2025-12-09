"""
Multi-Tenancy Managers for Company-Level Data Isolation

These managers automatically filter querysets by company to ensure
data isolation between different companies.
"""

from django.db import models
from pettycash_system.middleware import get_current_company


class CompanyQuerySet(models.QuerySet):
    """QuerySet that automatically filters by current company."""

    def for_company(self, company):
        """Explicitly filter by a specific company."""
        if company:
            return self.filter(company=company)
        return self.none()

    def current_company(self):
        """Filter by the current request's company (from middleware)."""
        company = get_current_company()
        if company:
            return self.filter(company=company)
        return self  # If no company context, return all (for superusers)


class CompanyManager(models.Manager):
    """Manager that provides company-scoped querysets."""

    def get_queryset(self):
        """Return a CompanyQuerySet."""
        return CompanyQuerySet(self.model, using=self._db)

    def for_company(self, company):
        """Get objects for a specific company."""
        return self.get_queryset().for_company(company)

    def current_company(self):
        """Get objects for the current request's company."""
        return self.get_queryset().current_company()


class RequisitionQuerySet(models.QuerySet):
    """QuerySet for Requisitions with company-based filtering."""

    def for_company(self, company):
        """Filter requisitions by company through requested_by user."""
        if company:
            return self.filter(requested_by__company=company)
        return self.none()

    def current_company(self):
        """Filter by current request's company."""
        company = get_current_company()
        if company:
            return self.filter(requested_by__company=company)
        return self  # Superuser sees all


class RequisitionManager(models.Manager):
    """Manager for Requisition model with company isolation."""

    def get_queryset(self):
        """Return a RequisitionQuerySet."""
        return RequisitionQuerySet(self.model, using=self._db)

    def for_company(self, company):
        """Get requisitions for a specific company."""
        return self.get_queryset().for_company(company)

    def current_company(self):
        """Get requisitions for the current request's company."""
        return self.get_queryset().current_company()


class PaymentQuerySet(models.QuerySet):
    """QuerySet for Payments with company-based filtering via requisition."""

    def for_company(self, company):
        """Filter payments by company through requisition's requester."""
        if company:
            return self.filter(requisition__requested_by__company=company)
        return self.none()

    def current_company(self):
        """Filter by current request's company."""
        company = get_current_company()
        if company:
            return self.filter(requisition__requested_by__company=company)
        return self  # Superuser sees all


class PaymentManager(models.Manager):
    """Manager for Payment model with company isolation via requisition."""

    def get_queryset(self):
        """Return a PaymentQuerySet."""
        return PaymentQuerySet(self.model, using=self._db)

    def for_company(self, company):
        """Get payments for a specific company."""
        return self.get_queryset().for_company(company)

    def current_company(self):
        """Get payments for the current request's company."""
        return self.get_queryset().current_company()
