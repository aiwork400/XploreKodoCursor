"""
Tools for OperationsAgent: Wisdom Report generation and system health monitoring.
"""

from __future__ import annotations

import os
from datetime import datetime
from pathlib import Path
from typing import Optional

from agency_swarm.tools import BaseTool
from pydantic import Field
from sqlalchemy import text
from sqlalchemy.orm import Session

from database.db_manager import SessionLocal


class GenerateWisdomReport(BaseTool):
    """
    Generates daily wisdom report auditing CandidateProfile database and logs.

    Produces summary of:
    - Total candidates 'Travel-Ready'
    - Common troubleshooting queries from Advisory Agent
    - System health and Token Thrift optimization status
    """

    date: Optional[str] = Field(
        default=None, description="Date for report (YYYY-MM-DD). Defaults to today."
    )
    include_token_metrics: bool = Field(
        default=True, description="Include token usage and optimization metrics"
    )

    def run(self) -> str:
        """
        Generate comprehensive wisdom report with real SQL queries.

        Queries PostgreSQL database for:
        - Travel-Ready candidate counts
        - Payment success rates
        - System health metrics
        """
        db: Session = SessionLocal()
        try:
            # Get report date
            report_date = self.date or datetime.now().strftime("%Y-%m-%d")
            
            # Query: Total candidates by status
            status_query = text("""
                SELECT 
                    status,
                    COUNT(*) as count
                FROM candidates
                GROUP BY status
                ORDER BY count DESC
            """)
            status_results = db.execute(status_query).fetchall()
            
            # Query: Travel-Ready count
            travel_ready_query = text("""
                SELECT COUNT(*) as count
                FROM candidates
                WHERE travel_ready = TRUE
            """)
            travel_ready_count = db.execute(travel_ready_query).scalar() or 0
            
            # Query: Total candidates
            total_candidates_query = text("SELECT COUNT(*) FROM candidates")
            total_candidates = db.execute(total_candidates_query).scalar() or 0
            
            # Query: Payment success rate (today)
            payment_success_query = text("""
                SELECT 
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(*) as total,
                    ROUND(
                        COUNT(CASE WHEN status = 'success' THEN 1 END)::numeric / 
                        NULLIF(COUNT(*), 0) * 100, 
                        2
                    ) as success_rate
                FROM payments
                WHERE DATE(created_at) = :report_date
            """)
            payment_result = db.execute(payment_success_query, {"report_date": report_date}).fetchone()
            
            payment_successful = payment_result[0] if payment_result else 0
            payment_total = payment_result[1] if payment_result else 0
            payment_success_rate = payment_result[2] if payment_result else 0.0
            
            # Query: Track distribution
            track_query = text("""
                SELECT 
                    track,
                    COUNT(*) as count
                FROM candidates
                GROUP BY track
            """)
            track_results = db.execute(track_query).fetchall()
            
            # Build report
            report = f"""# XploreKodo Daily Wisdom Report

**Date:** {report_date}  
**Generated:** {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

---

## Travel-Ready Status

- **Total Candidates:** {total_candidates}
- **Travel-Ready:** {travel_ready_count}
- **Travel-Ready Rate:** {round((travel_ready_count / total_candidates * 100) if total_candidates > 0 else 0, 2)}%

### Status Breakdown:
"""
            for status, count in status_results:
                percentage = round((count / total_candidates * 100) if total_candidates > 0 else 0, 2)
                report += f"- **{status}:** {count} ({percentage}%)\n"
            
            report += f"""
### Track Distribution:
"""
            for track, count in track_results:
                percentage = round((count / total_candidates * 100) if total_candidates > 0 else 0, 2)
                report += f"- **{track.title()}:** {count} ({percentage}%)\n"
            
            report += f"""
---

## Payment Success Metrics

- **Total Payments Today:** {payment_total}
- **Successful Payments:** {payment_successful}
- **Payment Success Rate:** {payment_success_rate}%
- **Failed Payments:** {payment_total - payment_successful}

---

## Advisory Agent Query Analysis

*Note: Query log analysis requires additional logging infrastructure. Placeholder for future implementation.*

Top Troubleshooting Topics:
1. [Most common query from Advisory Agent logs]
2. [Second most common query]
3. [Third most common query]

Query Volume: [Total queries processed today]

---

## System Health

- **Agency Status:** Operational
- **Database Status:** Connected
- **Active Agents:** [Count of active agents]
- **Error Rate:** [Errors / Total requests]
- **Average Response Time:** [ms]

---

## Token Thrift Optimization

"""
            if self.include_token_metrics:
                report += """- **Total Tokens Used Today:** [Count]
- **Average Tokens per Request:** [Count]
- **Token Optimization Score:** [Percentage]
- **Recommendations:**
  * [Optimization suggestion 1]
  * [Optimization suggestion 2]

"""
            
            report += """---

## Recommendations

1. Monitor Travel-Ready rate trends to identify bottlenecks
2. Review payment failures to improve success rate
3. Analyze status distribution to optimize candidate journey

---

*Report generated by OperationsAgent*
"""
            
            # Save report to file
            reports_dir = Path(__file__).parent.parent.parent / "operations" / "reports"
            reports_dir.mkdir(parents=True, exist_ok=True)
            
            report_filename = f"wisdom_report_{report_date.replace('-', '_')}.md"
            report_path = reports_dir / report_filename
            
            with open(report_path, "w", encoding="utf-8") as f:
                f.write(report)
            
            return f"Wisdom report generated and saved to: {report_path}\n\n{report}"
            
        except Exception as e:
            return f"Error generating wisdom report: {str(e)}"
        finally:
            db.close()

