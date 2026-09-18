"""Email delivery: instant alerts + the daily digest.

Uses plain SMTP (Gmail) so it works from GitHub Actions with a stored App
Password. Credentials come from environment variables / repo secrets:
    SMTP_HOST      (default: smtp.gmail.com)
    SMTP_PORT      (default: 465, SSL)
    SMTP_USER      your gmail address
    SMTP_PASS      a Gmail App Password (NOT your normal password)
    DIGEST_TO      recipient (default: SMTP_USER)
"""

from __future__ import annotations

import html
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from models import Job


def _cfg() -> dict:
    user = os.environ.get("SMTP_USER", "")
    return {
        "host": os.environ.get("SMTP_HOST", "smtp.gmail.com"),
        "port": int(os.environ.get("SMTP_PORT", "465")),
        "user": user,
        "password": os.environ.get("SMTP_PASS", ""),
        "to": os.environ.get("DIGEST_TO", user),
    }


def _send(subject: str, html_body: str) -> None:
    c = _cfg()
    if not (c["user"] and c["password"] and c["to"]):
        raise RuntimeError(
            "Email not configured: set SMTP_USER, SMTP_PASS, and DIGEST_TO."
        )
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = c["user"]
    msg["To"] = c["to"]
    msg.attach(MIMEText("This email is best viewed as HTML.", "plain"))
    msg.attach(MIMEText(html_body, "html"))

    with smtplib.SMTP_SSL(c["host"], c["port"]) as server:
        server.login(c["user"], c["password"])
        server.sendmail(c["user"], [c["to"]], msg.as_string())


def _row(job: Job) -> str:
    loc = html.escape(job.location or "—")
    title = html.escape(job.title or "")
    company = html.escape(job.company or "")
    url = html.escape(job.url or "#", quote=True)
    tag = " 🔥" if job.priority >= 2 else ""
    return (
        f'<tr>'
        f'<td style="padding:6px 10px;font-weight:600">{company}{tag}</td>'
        f'<td style="padding:6px 10px"><a href="{url}">{title}</a></td>'
        f'<td style="padding:6px 10px;color:#555">{loc}</td>'
        f"</tr>"
    )


def _table(jobs: list[Job]) -> str:
    if not jobs:
        return "<p>No new matching postings.</p>"
    # Highest priority first, then company name.
    jobs = sorted(jobs, key=lambda j: (-j.priority, j.company.lower(), j.title.lower()))
    rows = "\n".join(_row(j) for j in jobs)
    return (
        '<table style="border-collapse:collapse;font-family:system-ui,Arial,sans-serif;font-size:14px">'
        '<thead><tr style="text-align:left;border-bottom:2px solid #222">'
        '<th style="padding:6px 10px">Company</th>'
        '<th style="padding:6px 10px">Position</th>'
        '<th style="padding:6px 10px">Location</th>'
        "</tr></thead><tbody>"
        f"{rows}"
        "</tbody></table>"
    )


def send_instant_alert(jobs: list[Job]) -> None:
    """Fire immediately when high-priority companies post something new."""
    if not jobs:
        return
    n = len(jobs)
    subject = f"🚨 {n} new job{'s' if n != 1 else ''} — apply now"
    body = (
        "<p><strong>New postings from your priority companies:</strong></p>"
        f"{_table(jobs)}"
        "<p style='color:#888;font-size:12px'>You're seeing this early — "
        "these went live within the last polling window.</p>"
    )
    _send(subject, body)


def send_digest(jobs: list[Job], hours: int = 24) -> None:
    """Once-a-day summary of everything new."""
    n = len(jobs)
    subject = f"📋 Daily job digest — {n} new in last {hours}h"
    body = (
        f"<p><strong>{n}</strong> new matching posting"
        f"{'s' if n != 1 else ''} in the last {hours} hours.</p>"
        f"{_table(jobs)}"
    )
    _send(subject, body)
