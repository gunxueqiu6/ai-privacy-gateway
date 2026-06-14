"""
Statistics reports system for Pro/Enterprise tiers.
Provides daily, weekly, monthly reports with CSV export.
"""
import csv
import io
import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, List

from database import db

logger = logging.getLogger(__name__)


def _parse_date(date_str: Optional[str], default_days_ago: int = 0) -> str:
    """Parse a date string or return a default."""
    if date_str:
        return date_str
    dt = datetime.now() - timedelta(days=default_days_ago)
    return dt.strftime("%Y-%m-%d")


def get_daily_report(team_id: Optional[str] = None, date: Optional[str] = None) -> Dict[str, Any]:
    """Get hourly breakdown for a specific date."""
    target_date = _parse_date(date)
    with db.get_conn() as conn:
        cursor = conn.cursor()
        query = "SELECT * FROM stats WHERE date = ?"
        params = [target_date]
        if team_id:
            query += " AND team_id = ?"
            params.append(team_id)
        cursor.execute(query, params)
        row = cursor.fetchone()
    if row:
        return dict(row)
    return {"date": target_date, "total_count": 0}


def get_weekly_report(team_id: Optional[str] = None, end_date: Optional[str] = None) -> List[Dict[str, Any]]:
    """Get daily breakdown for the past 7 days."""
    if end_date:
        end = datetime.strptime(end_date, "%Y-%m-%d")
    else:
        end = datetime.now()
    start = end - timedelta(days=7)

    results = []
    with db.get_conn() as conn:
        cursor = conn.cursor()
        for i in range(7):
            d = (start + timedelta(days=i)).strftime("%Y-%m-%d")
            query = "SELECT * FROM stats WHERE date = ?"
            params = [d]
            if team_id:
                query += " AND team_id = ?"
                params.append(team_id)
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                results.append(dict(row))
            else:
                results.append({"date": d, "total_count": 0})
    return results


def get_monthly_report(team_id: Optional[str] = None, year: Optional[int] = None, month: Optional[int] = None) -> List[Dict[str, Any]]:
    """Get weekly breakdown for a specific month."""
    now = datetime.now()
    y = year or now.year
    m = month or now.month

    from calendar import monthrange
    days_in_month = monthrange(y, m)[1]

    results = []
    with db.get_conn() as conn:
        cursor = conn.cursor()
        for day in range(1, days_in_month + 1):
            d = f"{y:04d}-{m:02d}-{day:02d}"
            query = "SELECT * FROM stats WHERE date = ?"
            params = [d]
            if team_id:
                query += " AND team_id = ?"
                params.append(team_id)
            cursor.execute(query, params)
            row = cursor.fetchone()
            if row:
                results.append(dict(row))
            else:
                results.append({"date": d, "total_count": 0})
    return results


def export_report_csv(
    team_id: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> str:
    """Export stats as CSV string."""
    if not start_date:
        start_date = (datetime.now() - timedelta(days=30)).strftime("%Y-%m-%d")
    if not end_date:
        end_date = datetime.now().strftime("%Y-%m-%d")

    stat_columns = [
        "phone_count", "email_count", "idcard_count", "bankcard_count",
        "custom_count", "person_count", "location_count", "org_count",
        "plate_count", "ip_count", "url_count", "date_count",
        "amount_count", "postcode_count", "total_count",
    ]

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["date"] + [c.replace("_count", "") for c in stat_columns])

    with db.get_conn() as conn:
        cursor = conn.cursor()
        query = "SELECT date, " + ", ".join(stat_columns) + " FROM stats WHERE date >= ? AND date <= ?"
        params = [start_date, end_date]
        if team_id:
            query += " AND team_id = ?"
            params.append(team_id)
        query += " ORDER BY date ASC"
        cursor.execute(query, params)
        for row in cursor.fetchall():
            writer.writerow([row["date"]] + [row[c] for c in stat_columns])

    return output.getvalue()


def get_summary_stats(team_id: Optional[str] = None, days: int = 30) -> Dict[str, Any]:
    """Get aggregated summary statistics for the last N days."""
    start_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")

    stat_columns = [
        "phone_count", "email_count", "idcard_count", "bankcard_count",
        "custom_count", "person_count", "location_count", "org_count",
        "plate_count", "ip_count", "url_count", "date_count",
        "amount_count", "postcode_count", "total_count",
    ]

    sum_expr = ", ".join(f"SUM({c}) as {c}" for c in stat_columns)

    with db.get_conn() as conn:
        cursor = conn.cursor()
        query = f"SELECT {sum_expr} FROM stats WHERE date >= ?"
        params = [start_date]
        if team_id:
            query += " AND team_id = ?"
            params.append(team_id)
        cursor.execute(query, params)
        row = cursor.fetchone()

    if row:
        result = dict(row)
        result["days"] = days
        return result
    return {"days": days, "total_count": 0}
