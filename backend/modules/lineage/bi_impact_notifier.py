import logging
import smtplib
import uuid
from datetime import datetime, timezone
from email.mime.text import MIMEText
from typing import Any, Dict, List, Optional
import httpx
from sqlalchemy.orm import Session

from backend.core.config import settings
from backend.modules.incidents.models import Incident, AlertConfig, IncidentTimeline
from backend.modules.lineage.models import LineageNode
from backend.modules.lineage.anomaly_suppression import get_downstream_nodes
from backend.utils.ntfy_topic import get_or_create_ntfy_topic

logger = logging.getLogger("qolyx.lineage.bi_impact_notifier")


def notify_dashboard_impact(db: Session, incident: Incident) -> List[str]:
    """Traces all downstream visual dashboards affected by an incident on a table,

    and sends structured alert warnings to all active notification channels.
    """
    logger.info(f"Checking downstream BI impact for table incident: {incident.table_name}")
    
    # 1. Trace downstream nodes recursively
    source_node_id = f"model.qolyx.{incident.table_name}"
    # Also support other node formats if present
    node_in_db = db.query(LineageNode).filter(
        (LineageNode.node_id == source_node_id) | 
        (LineageNode.node_id.like(f"%.{incident.table_name}"))
    ).first()
    
    if not node_in_db:
        logger.warning(f"Could not find matching lineage node for table: {incident.table_name}")
        return []

    downstream_ids = get_downstream_nodes(db, node_in_db.node_id)
    if not downstream_ids:
        logger.info(f"No downstream nodes found for table: {incident.table_name}")
        return []

    # Filter for dashboard nodes
    dashboard_nodes = db.query(LineageNode).filter(
        LineageNode.node_id.in_(downstream_ids),
        LineageNode.type == "dashboard"
    ).all()

    if not dashboard_nodes:
        logger.info(f"No downstream BI dashboards affected by table: {incident.table_name}")
        return []

    logger.info(f"Discovered {len(dashboard_nodes)} affected downstream BI dashboards.")

    # 2. Format payloads
    payload = format_impact_alert(incident, dashboard_nodes)
    successful_channels = []

    # Get active configs
    active_configs = db.query(AlertConfig).filter(AlertConfig.is_active == True).all()
    has_db_ntfy = any(c.channel_type.lower() == "ntfy" for c in active_configs)

    # 3. Default Ntfy alert
    if settings.NTFY_ENABLED and not has_db_ntfy:
        try:
            if send_ntfy_impact(incident, dashboard_nodes, None):
                successful_channels.append("ntfy (default)")
        except Exception as exc:
            logger.error("Failed to send default Ntfy BI impact alert", exc_info=True)

    # 4. Dispatch to active database configurations
    for config in active_configs:
        chan_type = config.channel_type.lower()
        success = False
        try:
            if chan_type == "slack":
                success = send_slack_impact(config, payload)
            elif chan_type == "discord":
                success = send_discord_impact(config, payload)
            elif chan_type == "teams":
                success = send_teams_impact(config, payload)
            elif chan_type == "telegram":
                success = send_telegram_impact(config, payload)
            elif chan_type in ("email", "smtp"):
                success = send_email_impact(config, payload)
            elif chan_type == "ntfy":
                success = send_ntfy_impact(incident, dashboard_nodes, config)
            else:
                logger.warning(f"Unsupported BI impact alert channel type: {config.channel_type}")
        except Exception as e:
            logger.error(f"Error dispatching BI impact alert via {chan_type}: {e}", exc_info=True)

        if success:
            successful_channels.append(config.channel_type)
            logger.info(f"Successfully dispatched BI impact alert to: {config.name} ({config.channel_type})")

    # 5. Log dispatch in incident timeline
    if successful_channels:
        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="BI_IMPACT_ALERT_DISPATCHED",
            event_data={"affected_dashboards": [d.name for d in dashboard_nodes], "channels": successful_channels},
            created_by="system",
            created_at=datetime.now(timezone.utc)
        )
        db.add(timeline_entry)
        try:
            db.commit()
        except Exception as exc:
            db.rollback()
            logger.error("Failed to commit BI impact timeline entry", exc_info=True)

    return successful_channels


def format_impact_alert(incident: Incident, dashboards: List[LineageNode]) -> Dict[str, Any]:
    """Generates formatted BI dashboard impact warning payloads for all active communication integrations."""
    dashboards_list_str = "\n".join([f"• *{d.name}* (Workspace: {d.schema}, Model: {d.database})" for d in dashboards])
    plain_text_dashboards = "\n".join([f" - {d.name} (Workspace: {d.schema}, Dataset: {d.database})" for d in dashboards])

    title = f"⚠️ Downstream BI Impact Warning"
    summary = (
        f"Incident '{incident.title}' on upstream table '{incident.table_name}' "
        f"has affected {len(dashboards)} downstream BI dashboards/reports. "
        f"Stakeholders should be advised that reports may display stale or invalid data."
    )

    # 1. Plain text representation
    plain_text = (
        f"{title}\n\n"
        f"Upstream Table Failure: {incident.table_name}\n"
        f"Incident Severity: {incident.severity}\n"
        f"Impact Summary: {summary}\n\n"
        f"Affected BI Dashboards:\n{plain_text_dashboards}\n\n"
        f"Lineage Graph Action URL: http://localhost:{settings.FRONTEND_PORT}/lineage"
    )

    # 2. Slack Block Kit payload
    slack_blocks = [
        {
            "type": "header",
            "text": {"type": "plain_text", "text": f"⚠️ Downstream BI Impact Alert"}
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": (
                    f"An incident of severity *{incident.severity}* has occurred on upstream table `{incident.table_name}`.\n"
                    f"*Impact Summary:* {summary}"
                )
            }
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": f"*Affected Downstream BI Dashboards:*\n{dashboards_list_str}"
            }
        },
        {
            "type": "actions",
            "elements": [
                {
                    "type": "button",
                    "text": {"type": "plain_text", "text": "Inspect Lineage Graph 📊"},
                    "url": f"http://localhost:{settings.FRONTEND_PORT}/lineage",
                    "style": "primary"
                }
            ]
        }
    ]

    # 3. Discord Embed structure
    discord_embed = {
        "title": f"⚠️ Downstream BI Impact Alert",
        "description": summary,
        "color": 16753920,  # Orange
        "fields": [
            {"name": "Upstream Table", "value": f"`{incident.table_name}`", "inline": True},
            {"name": "Severity", "value": f"`{incident.severity}`", "inline": True},
            {"name": "Affected Dashboards Count", "value": str(len(dashboards)), "inline": True},
            {"name": "Affected Reports", "value": plain_text_dashboards[:1024]}
        ],
        "timestamp": datetime.now(timezone.utc).isoformat()
    }

    # 4. Email HTML template
    email_rows = "".join([
        f"<tr>"
        f"<td style='padding: 10px; border-bottom: 1px solid #edf2f7; font-weight: bold;'>{d.name}</td>"
        f"<td style='padding: 10px; border-bottom: 1px solid #edf2f7;'>{d.schema}</td>"
        f"<td style='padding: 10px; border-bottom: 1px solid #edf2f7; font-family: monospace;'>{d.database}</td>"
        f"</tr>"
        for d in dashboards
    ])

    email_subject = f"⚠️ [Qolyx Impact Warning] {len(dashboards)} Downstream BI Dashboards Affected by {incident.table_name}"
    email_body = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <style>
    body {{
      font-family: 'Inter', -apple-system, sans-serif;
      background-color: #f7fafc;
      color: #2d3748;
      padding: 20px;
    }}
    .container {{
      max-width: 600px;
      background: #ffffff;
      border-radius: 12px;
      box-shadow: 0 4px 15px rgba(0, 0, 0, 0.05);
      border: 1px solid #e2e8f0;
      margin: 0 auto;
      overflow: hidden;
    }}
    .header {{
      background-color: #dd6b20;
      color: #ffffff;
      padding: 20px;
      text-align: center;
    }}
    .content {{
      padding: 24px;
    }}
    .table-container {{
      margin-top: 16px;
      border: 1px solid #edf2f7;
      border-radius: 8px;
      overflow: hidden;
    }}
    table {{
      width: 100%;
      border-collapse: collapse;
    }}
    th {{
      background-color: #f8fafc;
      color: #718096;
      font-weight: 600;
      padding: 10px;
      text-align: left;
      border-bottom: 1px solid #edf2f7;
    }}
    .button {{
      display: inline-block;
      background-color: #dd6b20;
      color: #ffffff;
      padding: 12px 24px;
      border-radius: 6px;
      text-decoration: none;
      font-weight: 700;
      margin-top: 20px;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="container">
    <div class="header">
      <h2>⚠️ Downstream BI Dashboard Impact warning</h2>
    </div>
    <div class="content">
      <p>An incident has been detected upstream that degrades the data reliability of visual dashboard assets.</p>
      <hr style="border: 0; border-top: 1px solid #edf2f7; margin: 16px 0;" />
      <p><strong>Failed Upstream Table:</strong> <code>{incident.table_name}</code></p>
      <p><strong>Impact Severity:</strong> {incident.severity}</p>
      <p><strong>Summary:</strong> {summary}</p>
      
      <div class="table-container">
        <table>
          <thead>
            <tr>
              <th>Dashboard Name</th>
              <th>BI Workspace</th>
              <th>Underlying Model</th>
            </tr>
          </thead>
          <tbody>
            {email_rows}
          </tbody>
        </table>
      </div>
      
      <div style="text-align: center;">
        <a href="http://localhost:{settings.FRONTEND_PORT}/lineage" class="button" style="color: #ffffff;">Open Lineage Workspace</a>
      </div>
    </div>
  </div>
</body>
</html>
"""

    return {
        "title": title,
        "summary": summary,
        "severity": incident.severity,
        "table_name": incident.table_name,
        "text": plain_text,
        "blocks": slack_blocks,
        "embeds": [discord_embed],
        "email_subject": email_subject,
        "email_body": email_body
    }


def send_slack_impact(config: AlertConfig, payload: Dict[str, Any]) -> bool:
    if not config.webhook_url:
        return False
    slack_payload = {"text": payload["text"], "blocks": payload["blocks"]}
    try:
        response = httpx.post(config.webhook_url, json=slack_payload, timeout=5.0)
        return response.status_code < 400
    except Exception:
        logger.error("Failed to send Slack BI impact alert", exc_info=True)
        return False


def send_discord_impact(config: AlertConfig, payload: Dict[str, Any]) -> bool:
    if not config.webhook_url:
        return False
    discord_payload = {
        "content": "⚠️ **Downstream BI Dashboard Impact Warning**",
        "embeds": payload["embeds"]
    }
    try:
        response = httpx.post(config.webhook_url, json=discord_payload, timeout=5.0)
        return response.status_code < 400
    except Exception:
        logger.error("Failed to send Discord BI impact alert", exc_info=True)
        return False


def send_teams_impact(config: AlertConfig, payload: Dict[str, Any]) -> bool:
    if not config.webhook_url:
        return False
    teams_payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "D97706",
        "summary": payload["title"],
        "title": payload["title"],
        "sections": [
            {
                "activityTitle": f"Failed Upstream: {payload['table_name']}",
                "activitySubtitle": payload["summary"],
                "markdown": True
            }
        ]
    }
    try:
        response = httpx.post(config.webhook_url, json=teams_payload, timeout=5.0)
        return response.status_code < 400
    except Exception:
        logger.error("Failed to send Teams BI impact alert", exc_info=True)
        return False


def send_telegram_impact(config: AlertConfig, payload: Dict[str, Any]) -> bool:
    if not config.telegram_bot_token or not config.telegram_chat_id:
        return False
    text_content = (
        f"<b>⚠️ Downstream BI Impact Warning</b>\n\n"
        f"An incident was declared on upstream table: <code>{payload['table_name']}</code>\n"
        f"<b>Severity:</b> {payload['severity']}\n\n"
        f"{payload['summary']}"
    )
    url = f"https://api.telegram.org/bot{config.telegram_bot_token}/sendMessage"
    try:
        response = httpx.post(url, json={
            "chat_id": config.telegram_chat_id,
            "text": text_content,
            "parse_mode": "HTML"
        }, timeout=5.0)
        return response.status_code < 400
    except Exception:
        logger.error("Failed to send Telegram BI impact alert", exc_info=True)
        return False


def send_email_impact(config: AlertConfig, payload: Dict[str, Any]) -> bool:
    email_config = config.email_config or {}
    if settings.SMTP_HOST and settings.SMTP_HOST.strip():
        smtp_server = settings.SMTP_HOST
        smtp_port = int(settings.SMTP_PORT or 587)
        smtp_user = settings.SMTP_USER
        smtp_password = settings.SMTP_PASSWORD
        from_address = settings.ALERT_EMAIL_FROM or settings.ALERT_EMAIL_SENDER or "alerts@qolyx.io"
        to_addresses_str = settings.ALERT_EMAIL_TO or "oncall@qolyx.io"
        to_addresses = [addr.strip() for addr in to_addresses_str.split(",")]
    else:
        smtp_server = email_config.get("smtp_server") or settings.SMTP_SERVER or "qolyx-mail"
        smtp_port = int(email_config.get("smtp_port") or settings.MAIL_SMTP_PORT or 1025)
        smtp_user = email_config.get("smtp_user")
        smtp_password = email_config.get("smtp_password")
        from_address = email_config.get("from_address") or "alerts@qolyx.io"
        to_addresses = email_config.get("to_addresses") or ["oncall@qolyx.io"]
        if isinstance(to_addresses, str):
            to_addresses = [addr.strip() for addr in to_addresses.split(",")]

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
    except Exception:
        logger.error("Failed to send SMTP email BI impact alert", exc_info=True)
        return False


def send_ntfy_impact(incident: Incident, dashboards: List[LineageNode], config: Optional[AlertConfig] = None) -> bool:
    if config:
        if not config.is_active:
            return False
        ntfy_url = config.webhook_url or f"{settings.NTFY_HOST}/{get_or_create_ntfy_topic()}"
    else:
        topic = get_or_create_ntfy_topic()
        ntfy_url = f"{settings.NTFY_HOST}/{topic}"

    try:
        message = (
            f"Downstream BI Impact Warning!\n"
            f"An incident on upstream table '{incident.table_name}' has affected {len(dashboards)} downstream dashboards.\n"
            f"Affected Dashboards:\n" + "\n".join([f"- {d.name}" for d in dashboards])
        )
        headers = {
            "Title": f"⚠️ Downstream BI Impact Alert",
            "Priority": "4",
            "Tags": "warning,bar_chart",
            "Click": f"http://localhost:{settings.FRONTEND_PORT}/lineage"
        }
        response = httpx.post(ntfy_url, content=message.encode("utf-8"), headers=headers, timeout=5.0)
        return response.status_code == 200
    except Exception:
        logger.error("Failed to send Ntfy BI impact alert", exc_info=True)
        return False
