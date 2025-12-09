"""
Report Service - Generates treasury reports, forecasts, and exports.
"""

import csv
from datetime import datetime, timedelta
from decimal import Decimal
from io import BytesIO, StringIO

from django.core.files.base import ContentFile
from django.db.models import Avg, Count, Q, Sum
from django.utils import timezone

from treasury.models import (
    DashboardMetric,
    FundForecast,
    LedgerEntry,
    Payment,
    ReplenishmentRequest,
    TreasuryFund,
    VarianceAdjustment,
)


class ReportService:
    """
    Service for generating treasury reports and forecasts.
    """

    @staticmethod
    def generate_payment_summary(
        company_id, start_date, end_date, region_id=None, branch_id=None
    ):
        """
        Generate payment summary report for date range.
        """
        # Payments linked via requisition (company/region/branch)
        query = Payment.objects.current_company().filter(
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
            status__in=["success", "failed"],
        )

        if region_id:
            query = query.filter(requisition__region_id=region_id)
        if branch_id:
            query = query.filter(requisition__branch_id=branch_id)

        total_payments = query.count()
        total_amount = query.aggregate(Sum("amount"))["amount__sum"] or Decimal("0.00")

        # By status
        by_status = {}
        for status in ["success", "failed", "pending"]:
            status_query = query.filter(status=status)
            by_status[status] = {
                "count": status_query.count(),
                "amount": status_query.aggregate(Sum("amount"))["amount__sum"]
                or Decimal("0.00"),
            }

        # By payment method
        by_method = {}
        methods = query.values("method").distinct()
        for method_dict in methods:
            method = method_dict["method"]
            method_query = query.filter(method=method)
            by_method[method] = {
                "count": method_query.count(),
                "amount": method_query.aggregate(Sum("amount"))["amount__sum"]
                or Decimal("0.00"),
            }

        # By requisition origin
        by_origin = {}
        origins = query.values("requisition__origin_type").distinct()
        for origin_dict in origins:
            origin = origin_dict["requisition__origin_type"]
            origin_query = query.filter(requisition__origin_type=origin)
            by_origin[origin] = {
                "count": origin_query.count(),
                "amount": origin_query.aggregate(Sum("amount"))["amount__sum"]
                or Decimal("0.00"),
            }

        return {
            "period": f"{start_date} to {end_date}",
            "total_payments": total_payments,
            "total_amount": float(total_amount),
            "by_status": by_status,
            "by_method": by_method,
            "by_origin": by_origin,
            "success_rate": (
                (by_status["success"]["count"] / total_payments * 100)
                if total_payments > 0
                else 0
            ),
        }

    @staticmethod
    def generate_fund_health_report(company_id, region_id=None, branch_id=None):
        """
        Generate comprehensive fund health report.
        """
        query = TreasuryFund.objects.filter(company_id=company_id)

        if region_id:
            query = query.filter(region_id=region_id)
        if branch_id:
            query = query.filter(branch_id=branch_id)

        funds = list(query)
        total_capacity = sum(f.reorder_level for f in funds)
        total_balance = sum(f.current_balance for f in funds)

        fund_details = []
        for fund in funds:
            utilization = (
                (fund.current_balance / fund.reorder_level * 100)
                if fund.reorder_level > 0
                else 0
            )

            # Determine status
            if fund.current_balance < fund.reorder_level:
                if fund.current_balance < (fund.reorder_level * Decimal("0.8")):
                    status = "CRITICAL"
                else:
                    status = "WARNING"
            else:
                status = "OK"

            fund_details.append(
                {
                    "fund_name": str(fund),
                    "company": fund.company.name,
                    "region": fund.region.name if fund.region else None,
                    "branch": fund.branch.name if fund.branch else None,
                    "balance": float(fund.current_balance),
                    "reorder_level": float(fund.reorder_level),
                    "utilization_pct": float(utilization),
                    "status": status,
                    "last_replenished": fund.last_replenished,
                }
            )

        return {
            "report_date": timezone.now().isoformat(),
            "total_funds": len(funds),
            "total_balance": float(total_balance),
            "total_capacity": float(total_capacity),
            "avg_utilization_pct": float(
                (total_balance / total_capacity * 100) if total_capacity > 0 else 0
            ),
            "funds_critical": sum(1 for f in fund_details if f["status"] == "CRITICAL"),
            "funds_warning": sum(1 for f in fund_details if f["status"] == "WARNING"),
            "fund_details": fund_details,
        }

    @staticmethod
    def generate_variance_analysis(company_id, start_date, end_date):
        """
        Generate variance analysis report.
        """
        query = VarianceAdjustment.objects.filter(
            treasury_fund__company_id=company_id,
            created_at__date__gte=start_date,
            created_at__date__lte=end_date,
        )

        total_variances = query.count()
        total_variance_amount = query.aggregate(Sum("variance_amount"))[
            "variance_amount__sum"
        ] or Decimal("0.00")

        positive_variances = query.filter(variance_amount__gt=0)
        positive_count = positive_variances.count()
        positive_amount = positive_variances.aggregate(Sum("variance_amount"))[
            "variance_amount__sum"
        ] or Decimal("0.00")

        negative_variances = query.filter(variance_amount__lt=0)
        negative_count = negative_variances.count()
        negative_amount = negative_variances.aggregate(Sum("variance_amount"))[
            "variance_amount__sum"
        ] or Decimal("0.00")

        # Pending approvals
        pending = query.filter(status="pending")
        pending_count = pending.count()
        pending_amount = pending.aggregate(Sum("variance_amount"))[
            "variance_amount__sum"
        ] or Decimal("0.00")

        # Approved
        approved = query.filter(status="approved")
        approved_count = approved.count()

        # Avg approval time
        approved_with_timestamp = approved.filter(approved_at__isnull=False)
        if approved_with_timestamp.exists():
            time_diffs = [
                (v.approved_at - v.created_at).total_seconds() / 3600
                for v in approved_with_timestamp
            ]
            avg_approval_hours = sum(time_diffs) / len(time_diffs)
        else:
            avg_approval_hours = 0

        return {
            "period": f"{start_date} to {end_date}",
            "total_variances": total_variances,
            "total_variance_amount": float(total_variance_amount),
            "positive_variances": {
                "count": positive_count,
                "amount": float(positive_amount),
            },
            "negative_variances": {
                "count": negative_count,
                "amount": float(negative_amount),
            },
            "pending_approval": {
                "count": pending_count,
                "amount": float(pending_amount),
            },
            "approved": {
                "count": approved_count,
            },
            "avg_approval_time_hours": avg_approval_hours,
        }

    @staticmethod
    def generate_replenishment_forecast(fund, horizon_days=None):
        """
        Generate replenishment forecast for a fund.
        Predicts when fund will reach reorder level based on spending patterns.
        """
        from settings_manager.models import SystemSetting

        if horizon_days is None:
            horizon_days = SystemSetting.get_setting(
                "TREASURY_FORECAST_HORIZON_DAYS", 30
            )

        today = timezone.now().date()
        forecast_date = today + timedelta(days=horizon_days)

        # Calculate average daily expense (configured lookback period)
        lookback_days = SystemSetting.get_setting("TREASURY_HISTORY_LOOKBACK_DAYS", 30)
        lookback_date = today - timedelta(days=lookback_days)
        ledger_entries = LedgerEntry.objects.filter(
            treasury_fund=fund,
            created_at__date__gte=lookback_date,
            created_at__date__lte=today,
            entry_type="debit",
        )

        total_expense = ledger_entries.aggregate(Sum("amount"))[
            "amount__sum"
        ] or Decimal("0.00")
        days_with_data = lookback_days
        daily_average = (
            total_expense / Decimal(days_with_data)
            if days_with_data > 0
            else Decimal("0.00")
        )

        # Predict balance at forecast date
        predicted_balance = fund.current_balance - (
            daily_average * Decimal(horizon_days)
        )
        predicted_balance = max(predicted_balance, Decimal("0.00"))

        # Calculate utilization
        predicted_utilization = (
            (predicted_balance / fund.reorder_level * 100)
            if fund.reorder_level > 0
            else 0
        )
        predicted_utilization = min(predicted_utilization, 100)

        # Calculate days until reorder needed
        if daily_average > 0:
            days_until_reorder = int(
                (fund.current_balance - fund.reorder_level) / daily_average
            )
            days_until_reorder = max(days_until_reorder, 0)
        else:
            days_until_reorder = 999  # If no spending, no reorder needed

        # Determine if replenishment needed
        needs_replenishment = predicted_balance < fund.reorder_level

        # Calculate confidence (0-100%)
        if days_with_data >= 30:
            confidence = Decimal("95")
        elif days_with_data >= 14:
            confidence = Decimal("85")
        else:
            confidence = Decimal("70")

        # Recommended amount (bring to 150% of reorder level)
        recommended_amount = Decimal("0.00")
        if needs_replenishment:
            recommended_amount = (
                fund.reorder_level * Decimal("1.5")
            ) - predicted_balance

        # Create or update forecast
        forecast, created = FundForecast.objects.update_or_create(
            fund=fund,
            forecast_date=forecast_date,
            defaults={
                "predicted_balance": predicted_balance,
                "predicted_utilization_pct": predicted_utilization,
                "predicted_daily_expense": daily_average,
                "days_until_reorder": days_until_reorder,
                "needs_replenishment": needs_replenishment,
                "recommended_replenishment_amount": recommended_amount,
                "confidence_level": confidence,
                "calculated_at": timezone.now(),
                "forecast_horizon_days": horizon_days,
            },
        )

        return forecast

    @staticmethod
    def export_report_to_csv(report_data, report_type="payment_summary"):
        """
        Export report data to CSV format.
        """
        output = StringIO()
        writer = csv.writer(output)

        if report_type == "payment_summary":
            writer.writerow(["Payment Summary Report"])
            writer.writerow(["Period", report_data["period"]])
            writer.writerow(["Total Payments", report_data["total_payments"]])
            writer.writerow(["Total Amount", report_data["total_amount"]])
            writer.writerow(["Success Rate", f"{report_data['success_rate']:.2f}%"])
            writer.writerow([])

            writer.writerow(["By Status"])
            writer.writerow(["Status", "Count", "Amount"])
            for status, data in report_data["by_status"].items():
                writer.writerow([status, data["count"], data["amount"]])
            writer.writerow([])

            writer.writerow(["By Method"])
            writer.writerow(["Method", "Count", "Amount"])
            for method, data in report_data["by_method"].items():
                writer.writerow([method, data["count"], data["amount"]])

        elif report_type == "fund_health":
            writer.writerow(["Fund Health Report"])
            writer.writerow(["Report Date", report_data["report_date"]])
            writer.writerow([])

            writer.writerow(["Fund Details"])
            writer.writerow(
                [
                    "Fund Name",
                    "Region",
                    "Branch",
                    "Balance",
                    "Reorder Level",
                    "Utilization %",
                    "Status",
                ]
            )
            for fund in report_data["fund_details"]:
                writer.writerow(
                    [
                        fund["fund_name"],
                        fund["region"],
                        fund["branch"],
                        fund["balance"],
                        fund["reorder_level"],
                        f"{fund['utilization_pct']:.2f}%",
                        fund["status"],
                    ]
                )

        elif report_type == "variance_analysis":
            writer.writerow(["Variance Analysis Report"])
            writer.writerow(["Period", report_data["period"]])
            writer.writerow(["Total Variances", report_data["total_variances"]])
            writer.writerow(
                ["Total Variance Amount", report_data["total_variance_amount"]]
            )
            writer.writerow(
                [
                    "Avg Approval Time (hours)",
                    f"{report_data['avg_approval_time_hours']:.2f}",
                ]
            )
            writer.writerow([])

            writer.writerow(["Variance Summary"])
            writer.writerow(["Category", "Count", "Amount"])
            writer.writerow(
                [
                    "Positive",
                    report_data["positive_variances"]["count"],
                    report_data["positive_variances"]["amount"],
                ]
            )
            writer.writerow(
                [
                    "Negative",
                    report_data["negative_variances"]["count"],
                    report_data["negative_variances"]["amount"],
                ]
            )
            writer.writerow(
                [
                    "Pending",
                    report_data["pending_approval"]["count"],
                    report_data["pending_approval"]["amount"],
                ]
            )

        return output.getvalue()

    @staticmethod
    def export_report_to_pdf(report_data, report_type="payment_summary"):
        """
        Export report to PDF format.
        Uses ReportLab library.
        """
        try:
            from reportlab.lib import colors
            from reportlab.lib.pagesizes import A4, letter
            from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
            from reportlab.lib.units import inch
            from reportlab.platypus import (
                Paragraph,
                SimpleDocTemplate,
                Spacer,
                Table,
                TableStyle,
            )

            buffer = BytesIO()
            doc = SimpleDocTemplate(buffer, pagesize=A4)
            elements = []
            styles = getSampleStyleSheet()

            # Title
            title_style = ParagraphStyle(
                "Title",
                parent=styles["Heading1"],
                fontSize=16,
                textColor=colors.HexColor("#1f4788"),
                spaceAfter=12,
            )

            if report_type == "payment_summary":
                title = Paragraph("Payment Summary Report", title_style)
            elif report_type == "fund_health":
                title = Paragraph("Fund Health Report", title_style)
            else:
                title = Paragraph("Variance Analysis Report", title_style)

            elements.append(title)
            elements.append(Spacer(1, 0.3 * inch))

            # Summary data
            summary_data = [["Metric", "Value"]]
            if report_type == "payment_summary":
                summary_data.extend(
                    [
                        ["Period", report_data["period"]],
                        ["Total Payments", str(report_data["total_payments"])],
                        ["Total Amount", f"₹{report_data['total_amount']:,.2f}"],
                        ["Success Rate", f"{report_data['success_rate']:.2f}%"],
                    ]
                )

            summary_table = Table(summary_data, colWidths=[2.5 * inch, 2.5 * inch])
            summary_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4788")),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, 0), 11),
                        ("BOTTOMPADDING", (0, 0), (-1, 0), 12),
                        ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                    ]
                )
            )

            elements.append(summary_table)
            elements.append(Spacer(1, 0.3 * inch))

            # Build PDF
            doc.build(elements)
            buffer.seek(0)
            return buffer.getvalue()

        except ImportError:
            return None  # ReportLab not installed
