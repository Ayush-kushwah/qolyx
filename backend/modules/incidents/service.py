import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.core.events import publish_with_retry
from backend.modules.incidents.models import Incident, IncidentTimeline, IncidentComment
from backend.modules.incidents.schemas import IncidentCreate, IncidentCommentRequest

logger = logging.getLogger("qolyx.incidents")


class IncidentService:
    """Service to handle the full lifecycle, timeline events, and state transitions of data reliability incidents."""

    @staticmethod
    def _emit_incident_event(event_type: str, incident: Incident) -> None:
        """Helper method to construct and publish incident lifecycle events to the Redis event bus."""
        event_payload = {
            "event_type": event_type,
            "incident_id": str(incident.id),
            "pipeline_run_id": str(incident.pipeline_run_id),
            "table_name": incident.table_name,
            "incident_severity": incident.severity,
            "incident_status": incident.state,
            "assigned_to": incident.assigned_to,
            "assigned_team": incident.assigned_team,
            "updated_at": incident.updated_at.isoformat() if incident.updated_at else None
        }
        try:
            publish_with_retry(event_type, event_payload)
            logger.info(
                f"Successfully published incident event: {event_type}",
                extra={"incident_id": str(incident.id), "event_type": event_type}
            )
        except Exception as exc:
            logger.error(
                f"Failed to publish incident event: {event_type}",
                exc_info=True,
                extra={"incident_id": str(incident.id), "event_type": event_type}
            )

    @staticmethod
    def create_incident(db: Session, trust_score_record) -> Incident:
        """Helper to create an incident from a TrustScore record."""
        score = trust_score_record.trust_score
        if score < 40:
            severity = "CRITICAL"
        elif score < 60:
            severity = "HIGH"
        else:
            severity = "MEDIUM"

        title = f"Trust Score degraded to {score} on table {trust_score_record.table_name}"

        incident_data = IncidentCreate(
            trust_score_id=trust_score_record.id,
            pipeline_run_id=trust_score_record.pipeline_run_id,
            table_name=trust_score_record.table_name,
            severity=severity,
            title=title
        )
        return IncidentService.create(db, incident_data)

    @staticmethod
    def create(db: Session, incident_data: IncidentCreate) -> Incident:
        """Creates a new incident record in the database if one does not already exist for the pipeline run."""
        # Ensure idempotency by checking for an existing incident by pipeline_run_id
        existing = db.query(Incident).filter(
            Incident.pipeline_run_id == incident_data.pipeline_run_id
        ).first()

        if existing:
            logger.info(
                "Incident already exists for pipeline_run_id. Returning existing record.",
                extra={
                    "pipeline_run_id": str(incident_data.pipeline_run_id),
                    "incident_id": str(existing.id)
                }
            )
            return existing

        now = datetime.now(timezone.utc)
        db_incident = Incident(
            id=uuid.uuid4(),
            trust_score_id=incident_data.trust_score_id,
            pipeline_run_id=incident_data.pipeline_run_id,
            table_name=incident_data.table_name,
            severity=incident_data.severity.upper(),
            state="OPEN",
            assigned_to=incident_data.assigned_to,
            assigned_team=incident_data.assigned_team,
            title=incident_data.title,
            created_at=now,
            updated_at=now
        )
        db.add(db_incident)

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=db_incident.id,
            event_type="CREATED",
            event_data={"severity": db_incident.severity, "title": db_incident.title},
            created_by="system",
            created_at=now
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(db_incident)
            logger.info(
                "Created new incident record",
                extra={"incident_id": str(db_incident.id), "pipeline_run_id": str(db_incident.pipeline_run_id)}
            )
            
            # Auto-generate RCA for the new incident
            try:
                from backend.modules.incidents.rca_service import RCAService
                RCAService.generate_rca(db, db_incident.id)
            except Exception as rca_exc:
                logger.error(
                    f"Graceful degradation: failed to auto-generate RCA for incident {db_incident.id}",
                    exc_info=True
                )
            
            # Auto-dispatch alerts for the new incident
            try:
                from backend.modules.incidents.alert_service import AlertService
                AlertService.send_alert(db, db_incident)
            except Exception as alert_exc:
                logger.error(
                    f"Graceful degradation: failed to auto-dispatch alerts for incident {db_incident.id}",
                    exc_info=True
                )
                
            IncidentService._emit_incident_event("incident.created", db_incident)
            return db_incident
        except Exception as exc:
            db.rollback()
            logger.error(
                "Failed to create incident record",
                exc_info=True,
                extra={"pipeline_run_id": str(incident_data.pipeline_run_id)}
            )
            raise

    @staticmethod
    def get(db: Session, incident_id: uuid.UUID) -> Optional[Incident]:
        """Retrieves an incident by its unique ID with all relationships preloaded."""
        return db.query(Incident).options(
            joinedload(Incident.timeline),
            joinedload(Incident.comments),
            joinedload(Incident.rcas)
        ).filter(Incident.id == incident_id).first()

    @staticmethod
    def list(
        db: Session,
        table_name: Optional[str] = None,
        severity: Optional[str] = None,
        state: Optional[str] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Dict[str, Any]:
        """Retrieves a paginated and filtered list of incident records."""
        if page < 1:
            raise ValueError("Page number must be 1 or greater.")
        if page_size < 1 or page_size > 100:
            raise ValueError("Page size must be between 1 and 100.")

        query = db.query(Incident)
        if table_name:
            query = query.filter(Incident.table_name == table_name)
        if severity:
            query = query.filter(Incident.severity == severity.upper())
        if state:
            query = query.filter(Incident.state == state.upper())

        total = query.count()
        import math
        pages = math.ceil(total / page_size) if total > 0 else 1

        items = query.order_by(Incident.created_at.desc()).offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "pages": pages
        }

    @staticmethod
    def stats(db: Session, table_name: Optional[str] = None) -> Dict[str, Any]:
        """Calculates summary metrics and statistics for incidents in the system."""
        query = db.query(Incident)
        if table_name:
            query = query.filter(Incident.table_name == table_name)

        severity_counts = db.query(Incident.severity, func.count(Incident.id))
        state_counts = db.query(Incident.state, func.count(Incident.id))

        if table_name:
            severity_counts = severity_counts.filter(Incident.table_name == table_name)
            state_counts = state_counts.filter(Incident.table_name == table_name)

        severity_results = severity_counts.group_by(Incident.severity).all()
        state_results = state_counts.group_by(Incident.state).all()

        by_severity = {r[0]: r[1] for r in severity_results}
        by_state = {r[0]: r[1] for r in state_results}

        total_open = by_state.get("OPEN", 0)
        total_acknowledged = by_state.get("ACKNOWLEDGED", 0)
        total_resolved = by_state.get("RESOLVED", 0)
        total_closed = by_state.get("CLOSED", 0)

        return {
            "by_severity": by_severity,
            "by_state": by_state,
            "total_open": total_open,
            "total_acknowledged": total_acknowledged,
            "total_resolved": total_resolved,
            "total_closed": total_closed
        }

    @staticmethod
    def assign(
        db: Session,
        incident_id: uuid.UUID,
        assigned_to: Optional[str],
        assigned_team: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Incident]:
        """Assigns an incident to a specific developer and/or team, logging the event on the timeline."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        incident.assigned_to = assigned_to
        incident.assigned_team = assigned_team
        incident.updated_at = datetime.now(timezone.utc)

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="ASSIGNED",
            event_data={"assigned_to": assigned_to, "assigned_team": assigned_team},
            created_by=updated_by or "system",
            created_at=datetime.now(timezone.utc)
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(incident)
            logger.info("Assigned incident successfully", extra={"incident_id": str(incident.id)})
            IncidentService._emit_incident_event("incident.assigned", incident)
            return incident
        except Exception as exc:
            db.rollback()
            logger.error("Failed to assign incident", exc_info=True, extra={"incident_id": str(incident_id)})
            raise

    @staticmethod
    def acknowledge(
        db: Session,
        incident_id: uuid.UUID,
        acknowledged_by: Optional[str] = None
    ) -> Optional[Incident]:
        """Acknowledges an open incident, setting appropriate status and tracking fields."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        if incident.state == "ACKNOWLEDGED":
            return incident

        now = datetime.now(timezone.utc)
        incident.state = "ACKNOWLEDGED"
        incident.acknowledged_at = now
        incident.updated_at = now

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="ACKNOWLEDGED",
            event_data={"acknowledged_by": acknowledged_by},
            created_by=acknowledged_by or "system",
            created_at=now
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(incident)
            logger.info("Acknowledged incident successfully", extra={"incident_id": str(incident.id)})
            IncidentService._emit_incident_event("incident.acknowledged", incident)
            return incident
        except Exception as exc:
            db.rollback()
            logger.error("Failed to acknowledge incident", exc_info=True, extra={"incident_id": str(incident_id)})
            raise

    @staticmethod
    def resolve(
        db: Session,
        incident_id: uuid.UUID,
        resolution_notes: str,
        resolved_by: Optional[str] = None
    ) -> Optional[Incident]:
        """Resolves an incident, registering resolution notes and closing the timeline cycle."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        if incident.state == "RESOLVED":
            return incident

        now = datetime.now(timezone.utc)
        incident.state = "RESOLVED"
        incident.resolved_at = now
        incident.resolution_notes = resolution_notes
        incident.updated_at = now

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="RESOLVED",
            event_data={"resolved_by": resolved_by, "notes": resolution_notes},
            created_by=resolved_by or "system",
            created_at=now
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(incident)
            logger.info("Resolved incident successfully", extra={"incident_id": str(incident.id)})
            IncidentService._emit_incident_event("incident.resolved", incident)
            return incident
        except Exception as exc:
            db.rollback()
            logger.error("Failed to resolve incident", exc_info=True, extra={"incident_id": str(incident_id)})
            raise

    @staticmethod
    def close(
        db: Session,
        incident_id: uuid.UUID,
        closed_by: Optional[str] = None
    ) -> Optional[Incident]:
        """Closes a resolved incident, marking the record resolved and closed."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        if incident.state == "CLOSED":
            return incident

        now = datetime.now(timezone.utc)
        incident.state = "CLOSED"
        incident.closed_at = now
        incident.updated_at = now

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="CLOSED",
            event_data={"closed_by": closed_by},
            created_by=closed_by or "system",
            created_at=now
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(incident)
            logger.info("Closed incident successfully", extra={"incident_id": str(incident.id)})
            IncidentService._emit_incident_event("incident.closed", incident)
            return incident
        except Exception as exc:
            db.rollback()
            logger.error("Failed to close incident", exc_info=True, extra={"incident_id": str(incident_id)})
            raise

    @staticmethod
    def reopen(
        db: Session,
        incident_id: uuid.UUID,
        reopened_by: Optional[str] = None
    ) -> Optional[Incident]:
        """Reopens a previously resolved or closed incident, reverting status and clearing resolutions."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        if incident.state == "OPEN":
            return incident

        now = datetime.now(timezone.utc)
        incident.state = "OPEN"
        incident.resolved_at = None
        incident.closed_at = None
        incident.updated_at = now

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="REOPENED",
            event_data={"reopened_by": reopened_by},
            created_by=reopened_by or "system",
            created_at=now
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(incident)
            logger.info("Reopened incident successfully", extra={"incident_id": str(incident.id)})
            IncidentService._emit_incident_event("incident.reopened", incident)
            return incident
        except Exception as exc:
            db.rollback()
            logger.error("Failed to reopen incident", exc_info=True, extra={"incident_id": str(incident_id)})
            raise

    @staticmethod
    def add_comment(
        db: Session,
        incident_id: uuid.UUID,
        comment_data: IncidentCommentRequest
    ) -> IncidentComment:
        """Adds a comment to an active incident and publishes the comment addition to the timeline."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise ValueError(f"Incident with ID {incident_id} does not exist.")

        now = datetime.now(timezone.utc)
        db_comment = IncidentComment(
            id=uuid.uuid4(),
            incident_id=incident_id,
            comment=comment_data.comment,
            created_by=comment_data.created_by,
            created_at=now
        )
        db.add(db_comment)

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident_id,
            event_type="COMMENT_ADDED",
            event_data={"created_by": comment_data.created_by},
            created_by=comment_data.created_by,
            created_at=now
        )
        db.add(timeline_entry)

        incident.updated_at = now

        try:
            db.commit()
            db.refresh(db_comment)
            logger.info("Comment added successfully to incident", extra={"incident_id": str(incident_id)})
            
            # Emit comment added event
            event_payload = {
                "event_type": "incident.comment_added",
                "incident_id": str(incident_id),
                "comment_id": str(db_comment.id),
                "created_by": db_comment.created_by
            }
            publish_with_retry("incident.comment_added", event_payload)
            
            return db_comment
        except Exception as exc:
            db.rollback()
            logger.error("Failed to add comment to incident", exc_info=True, extra={"incident_id": str(incident_id)})
            raise

    @staticmethod
    def update_state(
        db: Session,
        incident_id: uuid.UUID,
        new_state: str,
        notes: Optional[str] = None,
        updated_by: Optional[str] = None
    ) -> Optional[Incident]:
        """Updates the state of an incident by routing to the specific transition method."""
        state_upper = new_state.upper()
        if state_upper == "OPEN":
            return IncidentService.reopen(db, incident_id, updated_by)
        elif state_upper == "ACKNOWLEDGED":
            return IncidentService.acknowledge(db, incident_id, updated_by)
        elif state_upper == "RESOLVED":
            return IncidentService.resolve(db, incident_id, notes or "", updated_by)
        elif state_upper == "CLOSED":
            return IncidentService.close(db, incident_id, updated_by)
        else:
            raise ValueError(f"Invalid state transition: {new_state}")

    @staticmethod
    def escalate(
        db: Session,
        incident_id: uuid.UUID,
        escalation_level: int,
        escalated_by: Optional[str] = None
    ) -> Optional[Incident]:
        """Escalates an incident to the next level of management or developer rotation."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        now = datetime.now(timezone.utc)
        incident.escalated_at = now
        incident.escalation_level = escalation_level
        incident.updated_at = now

        timeline_entry = IncidentTimeline(
            id=uuid.uuid4(),
            incident_id=incident.id,
            event_type="ESCALATED",
            event_data={"escalation_level": escalation_level, "escalated_by": escalated_by},
            created_by=escalated_by or "system",
            created_at=now
        )
        db.add(timeline_entry)

        try:
            db.commit()
            db.refresh(incident)
            logger.info(
                "Incident escalated successfully",
                extra={"incident_id": str(incident.id), "escalation_level": escalation_level}
            )
            IncidentService._emit_incident_event("incident.escalated", incident)
            return incident
        except Exception as exc:
            db.rollback()
            logger.error("Failed to escalate incident", exc_info=True, extra={"incident_id": str(incident_id)})
            raise
