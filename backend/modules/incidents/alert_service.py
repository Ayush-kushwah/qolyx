import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.core.events import publish_with_retry
from backend.modules.incidents.models import Incident, IncidentRCA, IncidentTimeline, AlertConfig
from backend.utils.ntfy_topic import get_or_create_ntfy_topic

logger = logging.getLogger("qolyx.incidents.alert")

SEVERITY_LEVELS = {
    "LOW": 0,
    "MEDIUM": 1,
    "HIGH": 2,
    "CRITICAL": 3
}


class AlertService:
    """Service to handle formatting, constructing, and dispatching multi-channel alert notifications."""

    @staticmethod
    def create_slack_action_blocks(incident_id: uuid.UUID) -> List[Dict[str, Any]]:
        """Generates Slack Block Kit interactive action buttons for incident response management."""
        return [
            {
                "type": "actions",
                "elements": [
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Acknowledge 🟢"},
                        "style": "primary",
                        "action_id": f"acknowledge_incident_{incident_id}",
                        "value": str(incident_id)
                    },
                    {
                        "type": "button",
                        "text": {"type": "plain_text", "text": "Resolve 🔴"},
                        "style": "danger",
                        "action_id": f"resolve_incident_{incident_id}",
                        "value": str(incident_id)
                    }
                ]
            }
        ]

    @staticmethod
    def format_alert_message(incident: Incident, rca: Optional[IncidentRCA] = None, trust_score: Optional[Any] = None) -> Dict[str, Any]:
        """Formats multi-channel payload objects tailored for specific integration layouts."""
        rca_summary = rca.summary if rca else "No deterministic RCA generated yet."
        rca_cause = rca.root_cause if rca else "Review the data validation run to determine root cause."
        rca_rec = rca.recommendation if rca else "Check metrics baselines and profile drift."

        title = incident.title
        severity = incident.severity
        table_name = incident.table_name
        state = incident.state

        score_val = str(trust_score.trust_score) if trust_score else "N/A"
        score_status = str(trust_score.trust_score_status) if trust_score else "N/A"

        # Penalties formatting
        penalties_list = []
        if trust_score:
            if trust_score.contract_penalty:
                penalties_list.append(f"• Contract Penalty: -{trust_score.contract_penalty}")
            if trust_score.freshness_penalty:
                penalties_list.append(f"• Freshness Penalty: -{trust_score.freshness_penalty}")
            if trust_score.volume_penalty:
                penalties_list.append(f"• Volume Penalty: -{trust_score.volume_penalty}")
            if trust_score.anomaly_penalty:
                penalties_list.append(f"• Anomaly Penalty: -{trust_score.anomaly_penalty}")
            if trust_score.dbt_penalty:
                penalties_list.append(f"• DBT Penalty: -{trust_score.dbt_penalty}")

        penalties_str = "\n".join(penalties_list) if penalties_list else "• No penalties applied."

        # Plain text representation
        plain_text = (
            f"🚨 Qolyx Reliability Incident: {title}\n"
            f"Table: {table_name}\n"
            f"Severity: {severity}\n"
            f"State: {state}\n"
            f"Trust Score: {score_val} ({score_status})\n"
            f"Penalties:\n{penalties_str}\n"
            f"Root Cause: {rca_cause}\n"
            f"Recommendation: {rca_rec}"
        )

        # Slack Block Kit payload
        slack_blocks = [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🚨 Qolyx Incident: {title}"}
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*Table:* `{table_name}`"},
                    {"type": "mrkdwn", "text": f"*Severity:* `{severity}`"},
                    {"type": "mrkdwn", "text": f"*State:* `{state}`"},
                    {"type": "mrkdwn", "text": f"*Trust Score:* `{score_val} ({score_status})`"}
                ]
            }
        ]

        if penalties_list:
            slack_blocks.append({
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Penalty Breakdown:*\n{penalties_str}"}
            })

        slack_blocks.extend([
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Summary:*\n{rca_summary}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Root Cause:*\n{rca_cause}"}
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"*Recommendation:*\n{rca_rec}"}
            }
        ])
        slack_blocks.extend(AlertService.create_slack_action_blocks(incident.id))

        # Discord Embed structure
        discord_embed = {
            "title": f"🚨 Qolyx Incident: {title}",
            "description": rca_summary,
            "color": 16711680 if severity == "CRITICAL" else (16753920 if severity == "HIGH" else 16776960),  # Red, Orange, Yellow
            "fields": [
                {"name": "Table", "value": f"`{table_name}`", "inline": True},
                {"name": "Severity", "value": f"`{severity}`", "inline": True},
                {"name": "State", "value": f"`{state}`", "inline": True},
                {"name": "Trust Score", "value": f"`{score_val} ({score_status})`", "inline": True}
            ],
            "timestamp": incident.created_at.isoformat() if incident.created_at else None
        }

        if penalties_list:
            discord_embed["fields"].append({"name": "Penalty Breakdown", "value": penalties_str})

        discord_embed["fields"].extend([
            {"name": "Root Cause", "value": rca_cause},
            {"name": "Recommendation", "value": rca_rec}
        ])

        # Email details
        email_subject = f"🚨 [Qolyx Alert] {severity} Incident on {table_name}: {title}"
        severity_color = "#e53e3e" if severity == "CRITICAL" else ("#dd6b20" if severity == "HIGH" else ("#d69e2e" if severity == "MEDIUM" else "#3182ce"))
        
        email_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: 'Inter', -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
      background-color: #f7fafc;
      margin: 0;
      padding: 20px;
      color: #2d3748;
    }}
    .container {{
      max-width: 600px;
      background-color: #ffffff;
      border-radius: 12px;
      overflow: hidden;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
      border: 1px solid #e2e8f0;
      margin: 0 auto;
    }}
    .header {{
      background-color: {severity_color};
      padding: 24px;
      text-align: center;
      color: #ffffff;
    }}
    .header h1 {{
      margin: 0;
      font-size: 20px;
      font-weight: 700;
      letter-spacing: -0.5px;
    }}
    .content {{
      padding: 32px 24px;
    }}
    .grid {{
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 16px;
      margin-bottom: 24px;
    }}
    .field-card {{
      background-color: #f8fafc;
      padding: 12px 16px;
      border-radius: 8px;
      border: 1px solid #edf2f7;
    }}
    .field-label {{
      font-size: 11px;
      text-transform: uppercase;
      color: #718096;
      font-weight: 600;
      margin-bottom: 4px;
    }}
    .field-value {{
      font-size: 14px;
      font-weight: 700;
      color: #1a202c;
    }}
    .section-title {{
      font-size: 14px;
      font-weight: 700;
      color: #4a5568;
      border-bottom: 2px solid #edf2f7;
      padding-bottom: 8px;
      margin-top: 28px;
      margin-bottom: 12px;
      text-transform: uppercase;
      letter-spacing: 0.5px;
    }}
    .text-block {{
      font-size: 14px;
      line-height: 1.6;
      color: #4a5568;
      background-color: #f7fafc;
      padding: 16px;
      border-radius: 8px;
      border-left: 4px solid #cbd5e0;
      margin-bottom: 16px;
    }}
    .table-container {{
      margin-top: 12px;
      border: 1px solid #edf2f7;
      border-radius: 8px;
      overflow: hidden;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th, td {{
      padding: 10px 14px;
      text-align: left;
      font-size: 13px;
    }}
    th {{
      background-color: #f7fafc;
      color: #718096;
      font-weight: 600;
      border-bottom: 1px solid #edf2f7;
    }}
    td {{
      border-bottom: 1px solid #edf2f7;
    }}
    tr:last-child td {{
      border-bottom: none;
    }}
    .badge {{
      display: inline-block;
      padding: 2px 8px;
      border-radius: 4px;
      font-size: 12px;
      font-weight: 700;
      text-transform: uppercase;
    }}
    .badge-severity {{
      background-color: {severity_color}20;
      color: {severity_color};
    }}
    .badge-score {{
      background-color: #e2e8f0;
      color: #4a5568;
    }}
    .footer {{
      background-color: #f7fafc;
      padding: 20px;
      text-align: center;
      font-size: 11px;
      color: #a0aec0;
      border-top: 1px solid #edf2f7;
    }}
    .button {{
      display: inline-block;
      background-color: {severity_color};
      color: #ffffff;
      padding: 12px 24px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 700;
      font-size: 14px;
      margin-top: 16px;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h1>🚨 Qolyx Reliability Incident</h1>
    </div>
    <div class="content">
      <div style="font-size: 16px; font-weight: 700; margin-bottom: 16px; color: #1a202c;">
        {title}
      </div>
      
      <div class="grid">
        <div class="field-card">
          <div class="field-label">Table</div>
          <div class="field-value"><code>{table_name}</code></div>
        </div>
        <div class="field-card">
          <div class="field-label">Severity</div>
          <div class="field-value"><span class="badge badge-severity">{severity}</span></div>
        </div>
        <div class="field-card">
          <div class="field-label">State</div>
          <div class="field-value"><span class="badge badge-score">{state}</span></div>
        </div>
        <div class="field-card">
          <div class="field-label">Trust Score</div>
          <div class="field-value">{score_val} ({score_status})</div>
        </div>
      </div>

      {"<div class='section-title'>Penalty Breakdown</div>" if trust_score else ""}
      {"<div class='table-container'><table><thead><tr><th>Metric Penalty</th><th>Value</th></tr></thead><tbody>" if trust_score else ""}
      {f"<tr><td>Contract Penalty</td><td style='color: #e53e3e; font-weight: bold;'>-{trust_score.contract_penalty}</td></tr>" if trust_score and trust_score.contract_penalty else ""}
      {f"<tr><td>Freshness Penalty</td><td style='color: #e53e3e; font-weight: bold;'>-{trust_score.freshness_penalty}</td></tr>" if trust_score and trust_score.freshness_penalty else ""}
      {f"<tr><td>Volume Penalty</td><td style='color: #e53e3e; font-weight: bold;'>-{trust_score.volume_penalty}</td></tr>" if trust_score and trust_score.volume_penalty else ""}
      {f"<tr><td>Anomaly Penalty</td><td style='color: #e53e3e; font-weight: bold;'>-{trust_score.anomaly_penalty}</td></tr>" if trust_score and trust_score.anomaly_penalty else ""}
      {f"<tr><td>DBT Penalty</td><td style='color: #e53e3e; font-weight: bold;'>-{trust_score.dbt_penalty}</td></tr>" if trust_score and trust_score.dbt_penalty else ""}
      {"</tbody></table></div>" if trust_score else ""}

      <div class="section-title">Root Cause Analysis (RCA)</div>
      <div style="font-size: 13px; font-weight: 600; color: #718096; margin-bottom: 6px;">Summary</div>
      <div class="text-block" style="border-left-color: #3182ce;">{rca_summary}</div>
      
      <div style="font-size: 13px; font-weight: 600; color: #718096; margin-bottom: 6px;">Root Cause</div>
      <div class="text-block" style="border-left-color: #e53e3e;">{rca_cause}</div>
      
      <div style="font-size: 13px; font-weight: 600; color: #718096; margin-bottom: 6px;">Recommendation</div>
      <div class="text-block" style="border-left-color: #38a169;">{rca_rec}</div>

      <div style="text-align: center;">
        <a href="http://localhost:5173/incidents/{incident.id}" class="button" style="color: #ffffff;">View Incident Dashboard</a>
      </div>
    </div>
    <div class="footer">
      This alert was generated automatically by the Qolyx Reliability Engine.<br/>
      Run ID: <code>{incident.pipeline_run_id}</code>
    </div>
  </div>
</body>
</html>
"""

        return {
            "title": title,
            "severity": severity,
            "table_name": table_name,
            "state": state,
            "score_val": score_val,
            "score_status": score_status,
            "penalties_str": penalties_str,
            "rca_cause": rca_cause,
            "rca_rec": rca_rec,
            "text": plain_text,
            "blocks": slack_blocks,
            "embeds": [discord_embed],
            "email_subject": email_subject,
            "email_body": email_body
        }

    @staticmethod
    def _send_slack(config: AlertConfig, payload: Dict[str, Any]) -> bool:
        """Sends the incident Slack Block Kit payload to the configured webhook."""
        if not config.webhook_url:
            logger.error(f"Slack webhook URL is missing for config: {config.id}")
            return False

        slack_payload = {
            "text": payload["text"],
            "blocks": payload["blocks"]
        }
        try:
            response = httpx.post(config.webhook_url, json=slack_payload, timeout=5.0)
            if response.status_code >= 400:
                logger.error(
                    "Slack webhook responded with an error",
                    extra={"status_code": response.status_code, "body": response.text}
                )
                return False
            return True
        except Exception as exc:
            logger.error("Failed to dispatch Slack webhook alert", exc_info=True)
            return False

    @staticmethod
    def _send_discord(config: AlertConfig, payload: Dict[str, Any]) -> bool:
        """Sends the incident Discord Embed payload to the configured webhook."""
        if not config.webhook_url:
            logger.error(f"Discord webhook URL is missing for config: {config.id}")
            return False

        discord_payload = {
            "content": f"🚨 **Qolyx Incident Alert**\n{payload['text'][:200]}...",
            "embeds": payload["embeds"]
        }
        try:
            response = httpx.post(config.webhook_url, json=discord_payload, timeout=5.0)
            if response.status_code >= 400:
                logger.error(
                    "Discord webhook responded with an error",
                    extra={"status_code": response.status_code, "body": response.text}
                )
                return False
            return True
        except Exception as exc:
            logger.error("Failed to dispatch Discord webhook alert", exc_info=True)
            return False

    @staticmethod
    def _send_teams(config: AlertConfig, payload: Dict[str, Any]) -> bool:
        """Sends the incident Adaptive Card message payload to the configured Teams webhook."""
        if not config.webhook_url:
            logger.error(f"Teams webhook URL is missing for config: {config.id}")
            return False

        # Teams O365 MessageCard structure
        teams_payload = {
            "@type": "MessageCard",
            "@context": "http://schema.org/extensions",
            "themeColor": "FF0000" if payload["severity"] == "CRITICAL" else "FFFF00",
            "summary": payload["title"],
            "title": f"🚨 Qolyx Incident: {payload['title']}",
            "sections": [
                {
                    "activityTitle": f"Table: {payload['table_name']} ({payload['severity']})",
                    "activitySubtitle": f"State: {payload['state']}",
                    "facts": [
                        {"name": "Root Cause", "value": payload["rca_cause"]},
                        {"name": "Recommendation", "value": payload["rca_rec"]}
                    ],
                    "markdown": True
                }
            ]
        }
        try:
            response = httpx.post(config.webhook_url, json=teams_payload, timeout=5.0)
            if response.status_code >= 400:
                logger.error(
                    "Teams webhook responded with an error",
                    extra={"status_code": response.status_code, "body": response.text}
                )
                return False
            return True
        except Exception as exc:
            logger.error("Failed to dispatch Teams webhook alert", exc_info=True)
            return False

    @staticmethod
    def _send_telegram(config: AlertConfig, payload: Dict[str, Any]) -> bool:
        """Dispatches the alert message using the Telegram Bot API."""
        if not config.telegram_bot_token or not config.telegram_chat_id:
            logger.error(f"Telegram bot token or chat ID missing for config: {config.id}")
            return False

        title = payload.get("title", "N/A")
        table_name = payload.get("table_name", "N/A")
        severity = payload.get("severity", "N/A")
        state = payload.get("state", "N/A")
        score_val = payload.get("score_val", "N/A")
        score_status = payload.get("score_status", "N/A")
        penalties_str = payload.get("penalties_str", "• None")
        rca_cause = payload.get("rca_cause", "N/A")
        rca_rec = payload.get("rca_rec", "N/A")

        telegram_payload = {
            "chat_id": config.telegram_chat_id,
            "text": f"<b>🚨 Qolyx Incident Alert</b>\n\n"
                    f"<b>Title:</b> {title}\n"
                    f"<b>Table:</b> {table_name}\n"
                    f"<b>Severity:</b> {severity}\n"
                    f"<b>State:</b> {state}\n"
                    f"<b>Trust Score:</b> {score_val} ({score_status})\n\n"
                    f"<b>Penalties:</b>\n{penalties_str}\n\n"
                    f"<b>Root Cause:</b>\n{rca_cause}\n\n"
                    f"<b>Recommendation:</b>\n{rca_rec}",
            "parse_mode": "HTML"
        }
        url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
        try:
            response = httpx.post(url, json=telegram_payload, timeout=5.0)
            if response.status_code >= 400:
                logger.error(
                    "Telegram Bot API responded with an error",
                    extra={"status_code": response.status_code, "body": response.text}
                )
                return False
            return True
        except Exception as exc:
            logger.error("Failed to dispatch Telegram Bot API alert", exc_info=True)
            return False

    @staticmethod
    def _send_email(config: AlertConfig, payload: Dict[str, Any]) -> bool:
        """Sends the HTML formatted email via the configured SMTP server."""
        from backend.core.config import settings

        email_config = config.email_config or {}

        # Prioritize real SMTP host settings in .env if configured
        if settings.SMTP_HOST and settings.SMTP_HOST.strip():
            smtp_server = settings.SMTP_HOST
            smtp_port_val = settings.SMTP_PORT or 587
            smtp_user = settings.SMTP_USER
            smtp_password = settings.SMTP_PASSWORD
            from_address = settings.ALERT_EMAIL_FROM or settings.ALERT_EMAIL_SENDER or "alerts@qolyx.io"
            to_addresses_str = settings.ALERT_EMAIL_TO or "oncall@qolyx.io"
            to_addresses = [addr.strip() for addr in to_addresses_str.split(",")]
        else:
            smtp_server = email_config.get("smtp_server") or settings.SMTP_SERVER or "qolyx-mail"
            smtp_port_val = email_config.get("smtp_port") or settings.MAIL_SMTP_PORT or 1025
            smtp_user = email_config.get("smtp_user")
            smtp_password = email_config.get("smtp_password")
            from_address = email_config.get("from_address") or "alerts@qolyx.io"
            to_addresses = email_config.get("to_addresses")
            if not to_addresses:
                to_addresses = ["oncall@qolyx.io"]
            elif isinstance(to_addresses, str):
                to_addresses = [addr.strip() for addr in to_addresses.split(",")]

        smtp_port = int(smtp_port_val)

        msg = MIMEText(payload["email_body"], "html", "utf-8")
        msg["Subject"] = payload["email_subject"]
        msg["From"] = from_address
        msg["To"] = ", ".join(to_addresses)

        try:
            if smtp_port == 465:
                server = smtplib.SMTP_SSL(smtp_server, smtp_port, timeout=5.0)
            else:
                server = smtplib.SMTP(smtp_server, smtp_port, timeout=5.0)
                if smtp_port == 587 or smtp_server == "smtp.gmail.com":
                    server.ehlo()
                    server.starttls()
                    server.ehlo()
            
            with server:
                if smtp_user and smtp_password:
                    server.login(smtp_user, smtp_password)
                server.sendmail(from_address, to_addresses, msg.as_string())
            return True
        except Exception as exc:
            logger.error("Failed to send SMTP email alert", exc_info=True)
            return False

    @staticmethod
    def _send_ntfy(incident: Incident, rca: Optional[IncidentRCA] = None, config: Optional[AlertConfig] = None, trust_score: Optional[Any] = None) -> bool:
        """Sends structured alert notifications via the default or custom Ntfy push channel."""
        from backend.core.config import settings
        # Graceful configuration check
        if config:
            if not config.is_active:
                return False
            ntfy_url = config.webhook_url or f"{settings.NTFY_HOST}/{get_or_create_ntfy_topic()}"
        else:
            if not settings.NTFY_ENABLED:
                logger.info("Ntfy alert integration is disabled; skipping.")
                return True
            topic = get_or_create_ntfy_topic()
            ntfy_url = f"{settings.NTFY_HOST}/{topic}"

        try:
            priority_map = {
                "CRITICAL": "5",
                "HIGH": "4",
                "MEDIUM": "3",
                "LOW": "2"
            }
            priority = priority_map.get(incident.severity.upper(), "3")

            rca_cause = f"\nRoot Cause: {rca.root_cause}" if rca and rca.root_cause else ""
            rca_rec = f"\nRecommendation: {rca.recommendation}" if rca and rca.recommendation else ""

            score_details = ""
            if trust_score:
                score_details = f"\nTrust Score: {trust_score.trust_score} ({trust_score.trust_score_status})"
                penalties = []
                if trust_score.contract_penalty:
                    penalties.append(f"Contract: -{trust_score.contract_penalty}")
                if trust_score.freshness_penalty:
                    penalties.append(f"Freshness: -{trust_score.freshness_penalty}")
                if trust_score.volume_penalty:
                    penalties.append(f"Volume: -{trust_score.volume_penalty}")
                if trust_score.anomaly_penalty:
                    penalties.append(f"Anomaly: -{trust_score.anomaly_penalty}")
                if trust_score.dbt_penalty:
                    penalties.append(f"DBT: -{trust_score.dbt_penalty}")
                if penalties:
                    score_details += f"\nPenalties: {', '.join(penalties)}"

            message = (
                f"Incident: {incident.title}\n"
                f"Table: {incident.table_name}\n"
                f"Severity: {incident.severity}\n"
                f"State: {incident.state}"
                f"{score_details}"
                f"{rca_cause}"
                f"{rca_rec}"
            )

            headers = {
                "Title": f"[Qolyx Alert] {incident.title}",
                "Priority": priority,
                "Tags": "warning,rotating_light",
                "Click": f"http://localhost:{settings.FRONTEND_PORT}/incidents/{incident.id}"
            }

            logger.info(f"Dispatching Ntfy push notification to {ntfy_url}")
            response = httpx.post(
                ntfy_url,
                content=message.encode("utf-8"),
                headers=headers,
                timeout=5.0
            )

            if response.status_code == 200:
                logger.info(f"Successfully sent Ntfy notification for incident {incident.id}")
                return True
            else:
                logger.error(
                    f"Failed to send Ntfy notification. Status: {response.status_code}, Response: {response.text}"
                )
                return False
        except Exception as exc:
            logger.error("Uncaught exception dispatching Ntfy push notification", exc_info=True)
            return False

    @staticmethod
    def send_alert(db: Session, incident: Incident) -> None:
        """Sends structured alerts to all active channels matching the severity thresholds."""
        logger.info(f"Checking alert routing rules for incident: {incident.id}")

        # Fetch the latest RCA details if available
        rca = db.query(IncidentRCA).filter(
            IncidentRCA.incident_id == incident.id
        ).order_by(desc(IncidentRCA.version)).first()

        # Fetch the trust score details if available
        from backend.modules.trust_score.models import TrustScore
        trust_score = db.query(TrustScore).filter(
            TrustScore.id == incident.trust_score_id
        ).first() if incident.trust_score_id else None

        payload = AlertService.format_alert_message(incident, rca, trust_score)
        successful_channels = []

        active_configs = db.query(AlertConfig).filter(AlertConfig.is_active == True).all()

        # Check if there is an active database config for ntfy
        has_db_ntfy = any(c.channel_type.lower() == "ntfy" for c in active_configs)

        # Default Ntfy push alert (only if enabled and not already configured in DB)
        from backend.core.config import settings
        if settings.NTFY_ENABLED and not has_db_ntfy:
            try:
                if AlertService._send_ntfy(incident, rca, None, trust_score):
                    successful_channels.append("ntfy")
            except Exception as exc:
                logger.error("Failed to send default Ntfy alert", exc_info=True)

        if active_configs:
            incident_severity_rank = SEVERITY_LEVELS.get(incident.severity.upper(), 1)
            for config in active_configs:
                config_threshold_rank = SEVERITY_LEVELS.get(config.severity_threshold.upper(), 1)

                # Filter by severity threshold
                if incident_severity_rank < config_threshold_rank:
                    logger.info(
                        f"Skipping alert config {config.name} (type: {config.channel_type}); incident severity {incident.severity} is below threshold {config.severity_threshold}."
                    )
                    continue

                # Graceful degradation logic
                success = False
                chan_type = config.channel_type.lower()
                try:
                    if chan_type == "slack":
                        success = AlertService._send_slack(config, payload)
                    elif chan_type == "discord":
                        success = AlertService._send_discord(config, payload)
                    elif chan_type == "teams":
                        success = AlertService._send_teams(config, payload)
                    elif chan_type == "telegram":
                        success = AlertService._send_telegram(config, payload)
                    elif chan_type in ("email", "smtp"):
                        success = AlertService._send_email(config, payload)
                    elif chan_type == "ntfy":
                        success = AlertService._send_ntfy(incident, rca, config, trust_score)
                    else:
                        logger.warning(f"Unsupported alert channel type configured: {config.channel_type}")
                except Exception as e:
                    logger.error(f"Uncaught exception dispatching alert via {chan_type}: {e}", exc_info=True)

                if success:
                    successful_channels.append(config.channel_type)
                    logger.info(f"Successfully dispatched alert to channel: {config.name} ({config.channel_type})")
                else:
                    logger.error(f"Failed to dispatch alert to channel: {config.name} ({config.channel_type})")
        else:
            logger.info("No active optional alert configurations found in database.")

        # Register event on timeline if any alerts succeeded
        if successful_channels:
            timeline_entry = IncidentTimeline(
                id=uuid.uuid4(),
                incident_id=incident.id,
                event_type="ALERT_DISPATCHED",
                event_data={"channels": successful_channels},
                created_by="system",
                created_at=datetime.now(timezone.utc)
            )
            db.add(timeline_entry)
            try:
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.error("Failed to commit alert dispatch timeline entry", exc_info=True)

    @staticmethod
    def test_alert(db: Session, config_id: uuid.UUID, message: str) -> bool:
        """Sends a manual test alert message using the specified alert configuration."""
        config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
        if not config:
            raise ValueError(f"Alert configuration with ID {config_id} does not exist.")

        # Construct generic test payload
        payload = {
            "title": "Qolyx Test Notification",
            "severity": "MEDIUM",
            "table_name": "test_table",
            "state": "OPEN",
            "score_val": "95",
            "score_status": "GOOD",
            "penalties_str": "• None (Manual Test Alert)",
            "rca_cause": "N/A - This is a manual test verification.",
            "rca_rec": "N/A - This is a manual test verification.",
            "text": f"🚨 Manual Test Alert: {message}",
            "blocks": [
                {
                    "type": "header",
                    "text": {"type": "plain_text", "text": "🚨 Qolyx Alert System Verification"}
                },
                {
                    "type": "section",
                    "text": {"type": "mrkdwn", "text": f"*Message:*\n{message}"}
                }
            ],
            "embeds": [
                {
                    "title": "🚨 Qolyx Test Alert",
                    "description": message,
                    "color": 16776960
                }
            ],
            "email_subject": f"🚨 [Qolyx Test Alert] Channel Verification: {config.name}",
            "email_body": f"<h3>Qolyx Alert Channel Verification</h3><hr/><p>{message}</p><hr/>"
        }

        chan_type = config.channel_type.lower()
        logger.info(f"Testing alert channel {config.name} (type: {chan_type})")

        try:
            if chan_type == "slack":
                return AlertService._send_slack(config, payload)
            elif chan_type == "discord":
                return AlertService._send_discord(config, payload)
            elif chan_type == "teams":
                return AlertService._send_teams(config, payload)
            elif chan_type == "telegram":
                return AlertService._send_telegram(config, payload)
            elif chan_type in ("email", "smtp"):
                return AlertService._send_email(config, payload)
            elif chan_type == "ntfy":
                dummy_incident = Incident(
                    id=uuid.uuid4(),
                    title=payload["title"],
                    severity=payload["severity"],
                    table_name=payload["table_name"],
                    state=payload["state"],
                    pipeline_run_id=uuid.uuid4(),
                    created_at=datetime.now(timezone.utc)
                )
                return AlertService._send_ntfy(dummy_incident, None, config, None)
            else:
                logger.warning(f"Unsupported alert channel type for test: {config.channel_type}")
                return False
        except Exception as exc:
            logger.error(f"Failed to test alert channel: {config.name}", exc_info=True)
            return False
