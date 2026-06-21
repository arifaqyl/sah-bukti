from __future__ import annotations

import csv
import io
import json
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, TypedDict

from app.db.store import get_db, utc_now
from app.services.aging import AgingService


class AgingBucket(TypedDict):
    bucket: str
    label: str
    count: int
    amount: float
    rate: float
    provision: float


class ProvisionResult(TypedDict):
    month: str
    total_outstanding: float
    provision_amount: float
    breakdown: list[AgingBucket]
    policy_used: dict
    journal_entry: dict
    justification: str
    calculated_at: str


@dataclass
class CacheEntry:
    expires_at: float
    value: ProvisionResult


class ProvisionEngine:
    """Core provision calculation engine."""

    DEFAULT_POLICY = {
        "current": 0.0,
        "31-60": 0.05,
        "61-90": 0.10,
        "91-180": 0.20,
        "180+": 1.0,
    }
    CACHE_TTL_SECONDS = 300
    _cache: dict[str, CacheEntry] = {}

    def __init__(self, db=get_db):
        self.db = db
        self.aging_service = AgingService(db)

    def get_aging(self, business_id: int, month: str, policy: Optional[dict] = None) -> list[AgingBucket]:
        """
        Get receivables aging report with provision amounts per bucket.

        Args:
            business_id: Business ID
            month: Target month in YYYY-MM format
            policy: Optional custom policy

        Returns:
            Aging buckets with rates and provision amounts.
        """
        resolved_policy = self._resolve_policy(business_id, policy)
        bucket_rows = self.aging_service.get_bucket_summary(business_id, month)
        breakdown: list[AgingBucket] = []
        for bucket in bucket_rows:
            rate = float(resolved_policy.get(bucket["bucket"], 0.0))
            amount = self._money(bucket["amount"])
            provision = self._money(amount * rate)
            breakdown.append(
                {
                    "bucket": bucket["bucket"],
                    "label": bucket["label"],
                    "count": int(bucket["count"]),
                    "amount": amount,
                    "rate": rate,
                    "provision": provision,
                }
            )
        return breakdown

    def calculate(self, business_id: int, month: str, policy: Optional[dict] = None) -> ProvisionResult:
        """
        Calculate provision for doubtful debts.

        Args:
            business_id: Business to calculate for
            month: Target month in YYYY-MM format
            policy: Optional custom provision policy

        Returns:
            Provision result with breakdown, journal entry, and justification.

        Raises:
            ValueError: If month or policy format is invalid.
            LookupError: If business not found or no unpaid invoices exist.
        """
        cache_key = self._cache_key(business_id, month, policy)
        cached = self._cache.get(cache_key)
        if cached and cached.expires_at > time.time():
            return cached.value

        self._validate_business_exists(business_id)
        breakdown = self.get_aging(business_id, month, policy)
        total_outstanding = self._money(sum(bucket["amount"] for bucket in breakdown))
        if total_outstanding == 0:
            raise LookupError("No unpaid invoices found for this business in this period")

        provision_amount = self._money(sum(bucket["provision"] for bucket in breakdown))
        policy_used = self._resolve_policy(business_id, policy)
        journal_entry = self.generate_journal_entry(provision_amount, month)
        invoice_count = sum(bucket["count"] for bucket in breakdown if bucket["count"] > 0)
        active_buckets = sum(1 for bucket in breakdown if bucket["count"] > 0)
        historical_rate = self._historical_write_off_rate(business_id)
        justification = (
            f"Based on {invoice_count} outstanding invoices across {active_buckets} age buckets. "
            f"Total outstanding: RM{total_outstanding:,.2f}. Historical write-off rate: {historical_rate:.1f}%. "
            "Provision calculated using standard MFRS 9 expected credit loss approach."
        )
        result: ProvisionResult = {
            "month": month,
            "total_outstanding": total_outstanding,
            "provision_amount": provision_amount,
            "breakdown": breakdown,
            "policy_used": policy_used,
            "journal_entry": journal_entry,
            "justification": justification,
            "calculated_at": datetime.now(timezone.utc).isoformat(),
        }
        self._store_snapshot(business_id, month, total_outstanding, provision_amount, policy_used, journal_entry)
        self._cache[cache_key] = CacheEntry(expires_at=time.time() + self.CACHE_TTL_SECONDS, value=result)
        return result

    def generate_journal_entry(self, provision_amount: float, month: str) -> dict:
        """
        Generate double-entry journal entry for provision.

        Args:
            provision_amount: Calculated provision amount.
            month: Target month in YYYY-MM format.

        Returns:
            Balanced journal entry dict.
        """
        month_end = self.aging_service.month_end(month)
        month_end_dt = datetime.strptime(month_end, "%Y-%m-%d")
        return {
            "date": month_end,
            "description": f"Provision for doubtful debts - {month_end_dt.strftime('%B %Y')}",
            "reference": f"PROV-{month}",
            "entries": [
                {
                    "account": "Provision for Doubtful Debts",
                    "account_code": "1400",
                    "debit": self._money(provision_amount),
                    "credit": 0.0,
                    "type": "expense",
                },
                {
                    "account": "Allowance for Doubtful Debts",
                    "account_code": "1410",
                    "debit": 0.0,
                    "credit": self._money(provision_amount),
                    "type": "contra_asset",
                },
            ],
            "balanced": True,
            "total_debit": self._money(provision_amount),
            "total_credit": self._money(provision_amount),
        }

    def export_csv(self, business_id: int, result: ProvisionResult) -> str:
        """
        Export provision calculation as CSV for accountant.

        Args:
            business_id: Business ID for labeling.
            result: Calculated provision result.

        Returns:
            CSV string with summary, journal entry, and justification.
        """
        business_name = self._get_business_name(business_id)
        output = io.StringIO()
        writer = csv.writer(output)
        month_label = datetime.strptime(result["month"], "%Y-%m").strftime("%B %Y")
        writer.writerow([f"Provision for Doubtful Debts - {month_label}"])
        writer.writerow([f"Generated: {datetime.now(timezone.utc).strftime('%Y-%m-%d')}"])
        writer.writerow([f"Business: {business_name}"])
        writer.writerow([])
        writer.writerow(["AGING SUMMARY"])
        writer.writerow(["Bucket", "Count", "Amount (RM)", "Rate (%)", "Provision (RM)"])
        total_count = 0
        for bucket in result["breakdown"]:
            total_count += int(bucket["count"])
            writer.writerow(
                [
                    bucket["label"].replace("0-30", "Current (0-30)") if bucket["bucket"] == "current" else bucket["label"],
                    bucket["count"],
                    f"{bucket['amount']:.2f}",
                    f"{bucket['rate'] * 100:.0f}%",
                    f"{bucket['provision']:.2f}",
                ]
            )
        writer.writerow(["TOTAL", total_count, f"{result['total_outstanding']:.2f}", "", f"{result['provision_amount']:.2f}"])
        writer.writerow([])
        writer.writerow(["JOURNAL ENTRY"])
        writer.writerow(["Date", "Account Code", "Account Name", "Debit (RM)", "Credit (RM)"])
        for entry in result["journal_entry"]["entries"]:
            writer.writerow(
                [
                    result["journal_entry"]["date"],
                    entry["account_code"],
                    entry["account"],
                    f"{entry['debit']:.2f}",
                    f"{entry['credit']:.2f}",
                ]
            )
        writer.writerow([])
        writer.writerow(["JUSTIFICATION"])
        writer.writerow([result["justification"]])
        return output.getvalue()

    def update_policy(self, business_id: int, policy: dict) -> dict[str, float]:
        """
        Update a business provision policy.

        Args:
            business_id: Business ID
            policy: Policy dict

        Returns:
            Normalized policy used for storage.
        """
        self._validate_business_exists(business_id)
        normalized = self._normalize_policy(policy)
        with self.db() as conn:
            conn.execute(
                """
                UPDATE businesses
                SET provision_policy = ?, updated_at = ?
                WHERE id = ?
                """,
                (json.dumps(normalized), utc_now(), business_id),
            )
        self._clear_business_cache(business_id)
        return normalized

    def _resolve_policy(self, business_id: int, policy: Optional[dict]) -> dict[str, float]:
        if policy is not None:
            return self._normalize_policy(policy)
        with self.db() as conn:
            row = conn.execute("SELECT provision_policy FROM businesses WHERE id = ?", (business_id,)).fetchone()
        if not row:
            raise LookupError("Business not found")
        raw_policy = row["provision_policy"]
        if not raw_policy:
            return dict(self.DEFAULT_POLICY)
        try:
            loaded = json.loads(raw_policy)
        except json.JSONDecodeError:
            return dict(self.DEFAULT_POLICY)
        return self._normalize_policy(loaded)

    def _normalize_policy(self, policy: dict) -> dict[str, float]:
        normalized = dict(self.DEFAULT_POLICY)
        details = []
        for key, value in policy.items():
            if key not in self.DEFAULT_POLICY:
                details.append({"field": f"policy.{key}", "message": "Unknown policy bucket", "code": "unknown_bucket"})
                continue
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                details.append({"field": f"policy.{key}", "message": "Rate must be numeric", "code": "invalid_type"})
                continue
            if numeric < 0 or numeric > 1:
                details.append({"field": f"policy.{key}", "message": "Rate must be between 0 and 1", "code": "out_of_range"})
                continue
            normalized[key] = numeric
        if details:
            raise ValueError(json.dumps(details))
        return normalized

    def _historical_write_off_rate(self, business_id: int) -> float:
        with self.db() as conn:
            row = conn.execute(
                """
                SELECT
                    COALESCE(SUM(CASE WHEN payment_status = 'paid' THEN total ELSE 0 END), 0) AS paid_total,
                    COALESCE(SUM(CASE WHEN payment_status != 'paid' THEN total ELSE 0 END), 0) AS unpaid_total
                FROM invoices
                WHERE business_id = ?
                """,
                (business_id,),
            ).fetchone()
        paid_total = float(row["paid_total"])
        unpaid_total = float(row["unpaid_total"])
        total = paid_total + unpaid_total
        if total <= 0:
            return 0.0
        return round((unpaid_total / total) * 100, 1)

    def _store_snapshot(
        self,
        business_id: int,
        month: str,
        total_outstanding: float,
        provision_amount: float,
        policy_used: dict[str, float],
        journal_entry: dict,
    ) -> None:
        with self.db() as conn:
            existing = conn.execute(
                "SELECT id FROM provision_snapshots WHERE business_id = ? AND month = ? ORDER BY id DESC LIMIT 1",
                (business_id, month),
            ).fetchone()
            if existing:
                conn.execute(
                    """
                    UPDATE provision_snapshots
                    SET total_outstanding = ?, provision_amount = ?, policy_used = ?, journal_entry = ?, created_at = ?
                    WHERE id = ?
                    """,
                    (
                        total_outstanding,
                        provision_amount,
                        json.dumps(policy_used),
                        json.dumps(journal_entry),
                        utc_now(),
                        existing["id"],
                    ),
                )
            else:
                conn.execute(
                    """
                    INSERT INTO provision_snapshots (business_id, month, total_outstanding, provision_amount, policy_used, journal_entry, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        business_id,
                        month,
                        total_outstanding,
                        provision_amount,
                        json.dumps(policy_used),
                        json.dumps(journal_entry),
                        utc_now(),
                    ),
                )

    def _validate_business_exists(self, business_id: int) -> None:
        with self.db() as conn:
            row = conn.execute("SELECT id FROM businesses WHERE id = ?", (business_id,)).fetchone()
        if not row:
            raise LookupError("Business not found")

    def _get_business_name(self, business_id: int) -> str:
        with self.db() as conn:
            row = conn.execute("SELECT name FROM businesses WHERE id = ?", (business_id,)).fetchone()
        if not row:
            raise LookupError("Business not found")
        return row["name"]

    def _cache_key(self, business_id: int, month: str, policy: Optional[dict]) -> str:
        payload = json.dumps(policy or {}, sort_keys=True)
        return f"{business_id}:{month}:{payload}"

    def _clear_business_cache(self, business_id: int) -> None:
        for key in list(self._cache):
            if key.startswith(f"{business_id}:"):
                del self._cache[key]

    @staticmethod
    def _money(value: float) -> float:
        return float(Decimal(str(value)).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP))
