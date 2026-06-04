import logging
import uuid
from datetime import datetime, timezone, timedelta
from typing import Any, Dict, List, Optional, Tuple
from sqlalchemy.orm import Session

from backend.modules.incidents.models import Incident, OncallRotation, IncidentTimeline
from backend.modules.incidents.service import IncidentService

logger = logging.getLogger("qolyx.incidents.rotation")


class RotationService:
    """Service to manage on-call developer schedules, rotations, and incident assignment."""

    @staticmethod
    def get_current_oncall(rotation: OncallRotation) -> Optional[str]:
        """Returns the member currently on-call for the specified rotation schedule."""
        if not rotation or not rotation.members:
            return None
        
        # Guard index boundaries dynamically
        idx = int(rotation.current_index) % len(rotation.members)
        return rotation.members[idx]

    @staticmethod
    def get_current_oncall_for_incident(db: Session, incident: Incident) -> Optional[Tuple[str, str]]:
        """Determines the current on-call member and team for a given incident."""
        # Find rotation by assigned team if set, else fall back to first rotation
        query = db.query(OncallRotation)
        if incident.assigned_team:
            rotation = query.filter(OncallRotation.team_name == incident.assigned_team).first()
        else:
            rotation = query.first()

        if rotation and rotation.members:
            oncall_member = RotationService.get_current_oncall(rotation)
            if oncall_member:
                return oncall_member, rotation.team_name
        return None

    @staticmethod
    def rotate(db: Session, rotation_id: uuid.UUID) -> OncallRotation:
        """Manually rotates the current on-call member index to the next active developer."""
        rotation = db.query(OncallRotation).filter(OncallRotation.id == rotation_id).first()
        if not rotation:
            raise ValueError(f"OncallRotation with ID {rotation_id} does not exist.")

        if rotation.members:
            now = datetime.now(timezone.utc)
            old_oncall = RotationService.get_current_oncall(rotation)
            
            rotation.current_index = (rotation.current_index + 1) % len(rotation.members)
            rotation.last_rotated_at = now
            rotation.updated_at = now
            
            new_oncall = RotationService.get_current_oncall(rotation)
            logger.info(
                f"On-call rotation '{rotation.name}' rotated index.",
                extra={
                    "rotation_id": str(rotation_id),
                    "old_oncall": old_oncall,
                    "new_oncall": new_oncall,
                    "new_index": rotation.current_index
                }
            )
            
            # Commit the update
            try:
                db.commit()
                db.refresh(rotation)
            except Exception as exc:
                db.rollback()
                logger.error(f"Failed to save manual rotation step for ID: {rotation_id}", exc_info=True)
                raise
        
        return rotation

    @staticmethod
    def check_and_rotate(db: Session) -> int:
        """Evaluates all rotation schedules and automatically rotates them if their duration is due."""
        rotations = db.query(OncallRotation).all()
        rotated_count = 0
        now = datetime.now(timezone.utc)

        for rotation in rotations:
            if not rotation.members:
                continue

            due = False
            if not rotation.last_rotated_at:
                due = True
            else:
                last = rotation.last_rotated_at
                if last.tzinfo is None:
                    last = last.replace(tzinfo=timezone.utc)
                elapsed = now - last

                r_type = rotation.rotation_type.upper()
                if r_type == "HOURLY" and elapsed >= timedelta(hours=1):
                    due = True
                elif r_type == "DAILY" and elapsed >= timedelta(days=1):
                    due = True
                elif r_type == "WEEKLY" and elapsed >= timedelta(weeks=1):
                    due = True

            if due:
                old_oncall = RotationService.get_current_oncall(rotation)
                rotation.current_index = (rotation.current_index + 1) % len(rotation.members)
                rotation.last_rotated_at = now
                rotation.updated_at = now
                new_oncall = RotationService.get_current_oncall(rotation)
                
                rotated_count += 1
                logger.info(
                    f"Scheduled rotation triggered auto-rotate for '{rotation.name}'",
                    extra={
                        "rotation_id": str(rotation.id),
                        "old_oncall": old_oncall,
                        "new_oncall": new_oncall,
                        "rotation_type": rotation.rotation_type
                    }
                )

        if rotated_count > 0:
            try:
                db.commit()
            except Exception as exc:
                db.rollback()
                logger.error("Failed to commit auto-rotations", exc_info=True)
                raise

        return rotated_count

    @staticmethod
    def assign_incident_to_oncall(db: Session, incident_id: uuid.UUID) -> Optional[Incident]:
        """Automatically assigns the incident to the developer currently on-call."""
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            return None

        oncall_info = RotationService.get_current_oncall_for_incident(db, incident)
        if not oncall_info:
            logger.warning(
                "No active on-call developer matched the incident team configurations.",
                extra={"incident_id": str(incident_id), "assigned_team": incident.assigned_team}
            )
            return incident

        oncall_member, team_name = oncall_info
        logger.info(
            "Auto-assigning incident to on-call developer",
            extra={
                "incident_id": str(incident_id),
                "oncall_member": oncall_member,
                "team_name": team_name
            }
        )

        return IncidentService.assign(
            db=db,
            incident_id=incident_id,
            assigned_to=oncall_member,
            assigned_team=team_name,
            updated_by="system"
        )
