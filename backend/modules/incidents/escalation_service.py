import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Optional
from sqlalchemy.orm import Session

from backend.modules.incidents.models import Incident, EscalationPolicy, OncallRotation
from backend.modules.incidents.service import IncidentService
from backend.modules.incidents.rotation_service import RotationService

logger = logging.getLogger("qolyx.incidents.escalation")


class EscalationService:
    """Service to handle incident escalation checks, policies, and ownership transitions."""

    @staticmethod
    def get_escalation_policy_for_severity(db: Session, severity: str) -> Optional[EscalationPolicy]:
        """Retrieves the escalation policy configured for a specific incident severity."""
        return db.query(EscalationPolicy).filter(
            EscalationPolicy.severity == severity.upper()
        ).first()

    @staticmethod
    def escalate_incident(db: Session, incident_id: uuid.UUID) -> Optional[Incident]:
        """Escalates an incident to the target specified by the escalation policy for its severity."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            logger.warning(f"Incident with ID {incident_id} not found for escalation.")
            return None

        # Only open incidents should escalate
        if incident.state in ("RESOLVED", "CLOSED"):
            logger.info(f"Incident {incident_id} is already {incident.state}. Skipping escalation.")
            return incident

        policy = EscalationService.get_escalation_policy_for_severity(db, incident.severity)
        if not policy:
            logger.warning(f"No escalation policy found for severity {incident.severity}. Cannot escalate.")
            return incident

        assigned_to = incident.assigned_to
        assigned_team = incident.assigned_team

        target_type = policy.target_type.upper()
        target_id = policy.target_identifier

        if target_type == "MEMBER":
            assigned_to = target_id
        elif target_type == "TEAM":
            assigned_team = target_id
        elif target_type == "ROTATION":
            # Find rotation schedule by name or ID
            rotation = None
            try:
                rot_uuid = uuid.UUID(target_id)
                rotation = db.query(OncallRotation).filter(OncallRotation.id == rot_uuid).first()
            except ValueError:
                rotation = db.query(OncallRotation).filter(OncallRotation.name == target_id).first()

            if rotation:
                oncall_member = RotationService.get_current_oncall(rotation)
                if oncall_member:
                    assigned_to = oncall_member
                    assigned_team = rotation.team_name
                else:
                    logger.warning(f"Rotation {target_id} has no members to assign.")
            else:
                logger.warning(f"Rotation schedule {target_id} not found for escalation.")
        elif target_type == "SLACK_CHANNEL":
            # For Slack channels, we keep the assignee as is, but log and dispatch notification later
            logger.info(f"Escalation target is Slack channel: {target_id}. Assignee unchanged.")

        # Update assignment fields on the incident
        incident.assigned_to = assigned_to
        incident.assigned_team = assigned_team

        new_level = incident.escalation_level + 1

        # Use the base IncidentService.escalate to save to database, write timeline event and publish to event bus
        escalated_incident = IncidentService.escalate(
            db=db,
            incident_id=incident.id,
            escalation_level=new_level,
            escalated_by="system"
        )

        return escalated_incident

    @staticmethod
    def check_escalations(db: Session) -> int:
        """Evaluates all open, level-0 incidents and escalates them if their timeouts are exceeded."""
        incidents = db.query(Incident).filter(
            Incident.state == "OPEN",
            Incident.escalation_level == 0
        ).all()

        now = datetime.now(timezone.utc)
        escalated_count = 0

        for incident in incidents:
            policy = EscalationService.get_escalation_policy_for_severity(db, incident.severity)
            if not policy:
                continue

            created_at = incident.created_at
            if created_at.tzinfo is None:
                created_at = created_at.replace(tzinfo=timezone.utc)

            elapsed = now - created_at
            if elapsed >= timedelta(minutes=policy.timeout_minutes):
                logger.info(
                    f"Incident {incident.id} exceeded timeout ({policy.timeout_minutes}m). Escalating."
                )
                try:
                    EscalationService.escalate_incident(db, incident.id)
                    escalated_count += 1
                except Exception:
                    logger.error(f"Failed to escalate incident {incident.id}", exc_info=True)

        return escalated_count
