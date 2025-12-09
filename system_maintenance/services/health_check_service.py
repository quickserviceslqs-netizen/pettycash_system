"""
System health check service for identifying critical issues.
"""

import os
from datetime import timedelta
from pathlib import Path

import psutil
from django.apps import apps
from django.conf import settings
from django.db import connection
from django.utils import timezone

from system_maintenance.models import BackupRecord, SystemHealthCheck


class HealthCheckService:
    """
    Comprehensive system health monitoring service.
    """

    def __init__(self):
        self.checks_performed = {}
        self.critical_issues = []
        self.warnings = []
        self.recommendations = []

    def perform_health_check(self, user=None):
        """
        Perform comprehensive system health check.

        Returns:
            SystemHealthCheck instance
        """
        import time

        start_time = time.time()

        check_id = (
            f"health_{timezone.now().strftime('%Y%m%d_%H%M%S')}_{os.urandom(3).hex()}"
        )

        # Perform all checks
        self._check_database_connectivity()
        self._check_disk_space()
        self._check_memory_usage()
        self._check_backup_status()
        self._check_data_integrity()
        self._check_orphaned_records()
        self._check_missing_files()
        self._check_critical_models()

        # Calculate health score
        health_score = self._calculate_health_score()
        overall_status = self._determine_overall_status(health_score)

        duration = time.time() - start_time

        # Get system metrics
        disk_usage = psutil.disk_usage(settings.BASE_DIR)
        memory = psutil.virtual_memory()

        # Calculate backup age
        backup_age_days = self._get_latest_backup_age()

        # Create health check record
        health_check = SystemHealthCheck.objects.create(
            check_id=check_id,
            performed_by=user,
            overall_status=overall_status,
            health_score=health_score,
            checks_performed=self.checks_performed,
            critical_issues=self.critical_issues,
            warnings=self.warnings,
            recommendations=self.recommendations,
            disk_usage_percent=disk_usage.percent,
            memory_usage_percent=memory.percent,
            backup_age_days=backup_age_days,
            orphaned_records_count=len(
                self.checks_performed.get("orphaned_records", {}).get(
                    "orphaned_items", []
                )
            ),
            missing_files_count=self.checks_performed.get("missing_files", {}).get(
                "count", 0
            ),
            duration_seconds=duration,
        )

        return health_check

    def _check_database_connectivity(self):
        """Check database connection"""
        try:
            with connection.cursor() as cursor:
                cursor.execute("SELECT 1")
                result = cursor.fetchone()

                self.checks_performed["database_connectivity"] = {
                    "status": "success",
                    "message": "Database connection successful",
                }
        except Exception as e:
            self.critical_issues.append(
                {
                    "check": "database_connectivity",
                    "message": f"Database connection failed: {str(e)}",
                }
            )
            self.checks_performed["database_connectivity"] = {
                "status": "critical",
                "message": str(e),
            }

    def _check_disk_space(self):
        """Check available disk space"""
        try:
            disk_usage = psutil.disk_usage(settings.BASE_DIR)

            status = "success"
            if disk_usage.percent > 90:
                status = "critical"
                self.critical_issues.append(
                    {
                        "check": "disk_space",
                        "message": f"Disk usage critical: {disk_usage.percent}% used",
                    }
                )
            elif disk_usage.percent > 80:
                status = "warning"
                self.warnings.append(
                    {
                        "check": "disk_space",
                        "message": f"Disk usage high: {disk_usage.percent}% used",
                    }
                )
                self.recommendations.append(
                    "Consider cleaning up old files or expanding storage"
                )

            self.checks_performed["disk_space"] = {
                "status": status,
                "percent_used": disk_usage.percent,
                "total_gb": disk_usage.total / (1024**3),
                "used_gb": disk_usage.used / (1024**3),
                "free_gb": disk_usage.free / (1024**3),
            }
        except Exception as e:
            self.warnings.append(
                {
                    "check": "disk_space",
                    "message": f"Could not check disk space: {str(e)}",
                }
            )

    def _check_memory_usage(self):
        """Check system memory usage"""
        try:
            memory = psutil.virtual_memory()

            status = "success"
            if memory.percent > 90:
                status = "warning"
                self.warnings.append(
                    {
                        "check": "memory_usage",
                        "message": f"Memory usage high: {memory.percent}%",
                    }
                )

            self.checks_performed["memory_usage"] = {
                "status": status,
                "percent_used": memory.percent,
                "total_mb": memory.total / (1024**2),
                "available_mb": memory.available / (1024**2),
            }
        except Exception as e:
            self.warnings.append(
                {
                    "check": "memory_usage",
                    "message": f"Could not check memory: {str(e)}",
                }
            )

    def _check_backup_status(self):
        """Check backup health and age"""
        try:
            latest_backup = (
                BackupRecord.objects.filter(status="completed")
                .order_by("-created_at")
                .first()
            )

            if not latest_backup:
                self.critical_issues.append(
                    {"check": "backup_status", "message": "No successful backups found"}
                )
                self.checks_performed["backup_status"] = {
                    "status": "critical",
                    "message": "No backups available",
                }
                return

            # Check backup age
            backup_age = timezone.now() - latest_backup.created_at
            age_days = backup_age.days

            status = "success"
            if age_days > 7:
                status = "critical"
                self.critical_issues.append(
                    {
                        "check": "backup_status",
                        "message": f"Latest backup is {age_days} days old",
                    }
                )
            elif age_days > 3:
                status = "warning"
                self.warnings.append(
                    {
                        "check": "backup_status",
                        "message": f"Latest backup is {age_days} days old",
                    }
                )
                self.recommendations.append("Create a new backup soon")

            self.checks_performed["backup_status"] = {
                "status": status,
                "latest_backup_age_days": age_days,
                "latest_backup_id": latest_backup.backup_id,
                "latest_backup_date": latest_backup.created_at.isoformat(),
                "total_backups": BackupRecord.objects.filter(
                    status="completed"
                ).count(),
            }
        except Exception as e:
            self.warnings.append(
                {
                    "check": "backup_status",
                    "message": f"Could not check backup status: {str(e)}",
                }
            )

    def _check_data_integrity(self):
        """Check data integrity across models"""
        try:
            from django.contrib.auth import get_user_model

            from transactions.models import Requisition
            from treasury.models import Payment, TreasuryFund

            User = get_user_model()

            issues = []

            # Check for requisitions without requested_by
            orphaned_requisitions = Requisition.objects.filter(
                requested_by__isnull=True
            ).count()
            if orphaned_requisitions > 0:
                issues.append(f"{orphaned_requisitions} requisitions without requester")

            # Check for payments without requisitions
            orphaned_payments = Payment.objects.filter(requisition__isnull=True).count()
            if orphaned_payments > 0:
                issues.append(f"{orphaned_payments} payments without requisitions")

            # Check for users without companies
            users_without_company = User.objects.filter(
                company__isnull=True, is_superuser=False
            ).count()
            if users_without_company > 0:
                issues.append(
                    f"{users_without_company} non-superuser users without company"
                )

            status = "success" if len(issues) == 0 else "warning"

            if issues:
                self.warnings.extend(
                    [{"check": "data_integrity", "message": issue} for issue in issues]
                )

            self.checks_performed["data_integrity"] = {
                "status": status,
                "issues_found": len(issues),
                "details": issues,
            }
        except Exception as e:
            self.warnings.append(
                {
                    "check": "data_integrity",
                    "message": f"Could not check data integrity: {str(e)}",
                }
            )

    def _check_orphaned_records(self):
        """Check for orphaned records"""
        orphaned_items = []

        try:
            from transactions.models import ApprovalTrail, Requisition
            from treasury.models import Payment

            # Check for approval trails without requisitions
            orphaned_trails = ApprovalTrail.objects.filter(
                requisition__isnull=True
            ).count()

            if orphaned_trails > 0:
                orphaned_items.append(
                    {
                        "model": "ApprovalTrail",
                        "count": orphaned_trails,
                        "issue": "Trails without requisitions",
                    }
                )

            self.checks_performed["orphaned_records"] = {
                "status": "warning" if orphaned_items else "success",
                "orphaned_items": orphaned_items,
                "total_orphaned": sum(item["count"] for item in orphaned_items),
            }

            if orphaned_items:
                self.recommendations.append(
                    "Run data cleanup to remove orphaned records"
                )

        except Exception as e:
            self.checks_performed["orphaned_records"] = {
                "status": "error",
                "message": str(e),
            }

    def _check_missing_files(self):
        """Check for database records with missing files"""
        missing_count = 0

        try:
            from transactions.models import Requisition

            # Check requisition receipts
            requisitions_with_receipts = Requisition.objects.exclude(receipt="")

            for req in requisitions_with_receipts[:100]:  # Sample check
                if req.receipt and not req.receipt.storage.exists(req.receipt.name):
                    missing_count += 1

            status = "success" if missing_count == 0 else "warning"

            self.checks_performed["missing_files"] = {
                "status": status,
                "count": missing_count,
                "checked": min(requisitions_with_receipts.count(), 100),
            }

            if missing_count > 0:
                self.warnings.append(
                    {
                        "check": "missing_files",
                        "message": f"Found {missing_count} records with missing files",
                    }
                )
                self.recommendations.append(
                    "Review and clean up records with missing files"
                )

        except Exception as e:
            self.checks_performed["missing_files"] = {
                "status": "error",
                "message": str(e),
            }

    def _check_critical_models(self):
        """Check critical models have data"""
        try:
            from django.contrib.auth import get_user_model

            from organization.models import Company

            User = get_user_model()

            issues = []

            # Check for at least one superuser
            superuser_count = User.objects.filter(is_superuser=True).count()
            if superuser_count == 0:
                issues.append("No superuser accounts found")

            # Check for at least one company
            company_count = Company.objects.count()
            if company_count == 0:
                issues.append("No companies configured")

            status = "critical" if issues else "success"

            if issues:
                self.critical_issues.extend(
                    [{"check": "critical_models", "message": issue} for issue in issues]
                )

            self.checks_performed["critical_models"] = {
                "status": status,
                "superuser_count": superuser_count,
                "company_count": company_count,
                "issues": issues,
            }
        except Exception as e:
            self.checks_performed["critical_models"] = {
                "status": "error",
                "message": str(e),
            }

    def _calculate_health_score(self):
        """Calculate overall health score (0-100)"""
        total_checks = len(self.checks_performed)
        if total_checks == 0:
            return 0

        # Start with perfect score
        score = 100

        # Deduct points for each critical issue
        score -= len(self.critical_issues) * 15

        # Deduct points for warnings
        score -= len(self.warnings) * 5

        # Ensure score is between 0 and 100
        return max(0, min(100, score))

    def _determine_overall_status(self, health_score):
        """Determine overall health status based on score"""
        if health_score >= 90:
            return "success"
        elif health_score >= 70:
            return "info"
        elif health_score >= 50:
            return "warning"
        else:
            return "critical"

    def _get_latest_backup_age(self):
        """Get age of latest backup in days"""
        try:
            latest_backup = (
                BackupRecord.objects.filter(status="completed")
                .order_by("-created_at")
                .first()
            )

            if latest_backup:
                age = timezone.now() - latest_backup.created_at
                return age.days + (age.seconds / 86400)  # Include fractional days

            return 999  # No backup found
        except Exception:
            return 999
