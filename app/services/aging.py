from __future__ import annotations

from calendar import monthrange
from datetime import datetime
from typing import NamedTuple


class InvoiceAging(NamedTuple):
    invoice_id: int
    invoice_number: str
    customer_name: str
    total: float
    due_date: str
    days_overdue: int
    bucket: str


class AgingService:
    """Calculate receivables aging."""

    BUCKETS = [
        ("current", 0, 30),
        ("31-60", 31, 60),
        ("61-90", 61, 90),
        ("91-180", 91, 180),
        ("180+", 181, None),
    ]

    def __init__(self, db) -> None:
        self.db = db

    def get_invoices_for_month(self, business_id: int, month: str) -> list[InvoiceAging]:
        """
        Get all unpaid invoices as of end of month.

        Args:
            business_id: Business ID
            month: Target month in YYYY-MM format

        Returns:
            List of invoice aging tuples.

        Raises:
            ValueError: If month format is invalid.
        """
        month_end = self.month_end(month)
        with self.db() as conn:
            rows = conn.execute(
                """
                SELECT invoices.id, invoices.invoice_number, invoices.total, invoices.due_date, customers.name AS customer_name
                FROM invoices
                JOIN customers ON customers.id = invoices.customer_id
                WHERE invoices.business_id = ?
                  AND invoices.payment_status != 'paid'
                  AND invoices.created_at <= ?
                ORDER BY invoices.due_date ASC, invoices.id ASC
                """,
                (business_id, f"{month_end}T23:59:59"),
            ).fetchall()

        results: list[InvoiceAging] = []
        for row in rows:
            due_date = row["due_date"] or month_end
            days = self.days_overdue(due_date, month_end)
            bucket = self.assign_bucket(days)[0]
            results.append(
                InvoiceAging(
                    invoice_id=int(row["id"]),
                    invoice_number=row["invoice_number"],
                    customer_name=row["customer_name"],
                    total=float(row["total"]),
                    due_date=due_date,
                    days_overdue=days,
                    bucket=bucket,
                )
            )
        return results

    def bucket_invoices(self, invoices: list[InvoiceAging]) -> list[dict]:
        """
        Group invoices into aging buckets.

        Args:
            invoices: Invoice aging tuples.

        Returns:
            Bucket summaries without policy rates applied.
        """
        grouped = {
            name: {"bucket": name, "label": self.bucket_label(name), "count": 0, "amount": 0.0}
            for name, _, _ in self.BUCKETS
        }
        for invoice in invoices:
            grouped[invoice.bucket]["count"] += 1
            grouped[invoice.bucket]["amount"] += float(invoice.total)
        return [grouped[name] for name, _, _ in self.BUCKETS]

    def get_bucket_summary(self, business_id: int, month: str) -> list[dict]:
        """
        Get bucketed aging summary via SQL aggregation.

        Args:
            business_id: Business ID
            month: Target month in YYYY-MM format

        Returns:
            Bucket summaries with count and amount.
        """
        month_end = self.month_end(month)
        with self.db() as conn:
            rows = conn.execute(
                """
                SELECT
                    CASE
                        WHEN MAX(0, CAST(julianday(?) - julianday(COALESCE(invoices.due_date, ?)) AS INTEGER)) <= 30 THEN 'current'
                        WHEN MAX(0, CAST(julianday(?) - julianday(COALESCE(invoices.due_date, ?)) AS INTEGER)) <= 60 THEN '31-60'
                        WHEN MAX(0, CAST(julianday(?) - julianday(COALESCE(invoices.due_date, ?)) AS INTEGER)) <= 90 THEN '61-90'
                        WHEN MAX(0, CAST(julianday(?) - julianday(COALESCE(invoices.due_date, ?)) AS INTEGER)) <= 180 THEN '91-180'
                        ELSE '180+'
                    END AS bucket,
                    COUNT(*) AS count,
                    COALESCE(SUM(invoices.total), 0) AS amount
                FROM invoices
                WHERE invoices.business_id = ?
                  AND invoices.payment_status != 'paid'
                  AND invoices.created_at <= ?
                GROUP BY bucket
                """,
                (
                    month_end,
                    month_end,
                    month_end,
                    month_end,
                    month_end,
                    month_end,
                    month_end,
                    month_end,
                    business_id,
                    f"{month_end}T23:59:59",
                ),
            ).fetchall()
        raw = {
            row["bucket"]: {"bucket": row["bucket"], "label": self.bucket_label(row["bucket"]), "count": int(row["count"]), "amount": float(row["amount"])}
            for row in rows
        }
        return [
            raw.get(name, {"bucket": name, "label": self.bucket_label(name), "count": 0, "amount": 0.0})
            for name, _, _ in self.BUCKETS
        ]

    @staticmethod
    def days_overdue(invoice_due_date: str, month_end: str) -> int:
        """
        Calculate days overdue as of month end.

        Args:
            invoice_due_date: Invoice due date in YYYY-MM-DD format.
            month_end: Month end in YYYY-MM-DD format.

        Returns:
            Non-negative days overdue.
        """
        due = datetime.strptime(invoice_due_date, "%Y-%m-%d")
        end = datetime.strptime(month_end, "%Y-%m-%d")
        return max(0, (end - due).days)

    @classmethod
    def assign_bucket(cls, days: int) -> tuple[str, int, int | None]:
        """Assign invoice to an aging bucket."""
        for bucket_name, days_min, days_max in cls.BUCKETS:
            if days_max is None and days >= days_min:
                return bucket_name, days_min, days_max
            if days_min <= days <= int(days_max):
                return bucket_name, days_min, days_max
        return "current", 0, 30

    @staticmethod
    def month_end(month: str) -> str:
        """Return the last date of a YYYY-MM month."""
        try:
            parsed = datetime.strptime(month, "%Y-%m")
        except ValueError as exc:
            raise ValueError("Invalid month format. Expected YYYY-MM") from exc
        last_day = monthrange(parsed.year, parsed.month)[1]
        return parsed.replace(day=last_day).strftime("%Y-%m-%d")

    @classmethod
    def bucket_label(cls, bucket: str) -> str:
        """Return the human label for a bucket."""
        mapping = {
            "current": "0-30 days",
            "31-60": "31-60 days",
            "61-90": "61-90 days",
            "91-180": "91-180 days",
            "180+": "180+ days",
        }
        return mapping[bucket]
