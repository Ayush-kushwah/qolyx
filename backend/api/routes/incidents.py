import logging
import uuid
import qrcode
import base64
from io import BytesIO
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc
from sqlalchemy.orm import Session

from backend.utils.ntfy_topic import get_or_create_ntfy_topic

from backend.core.database import get_db
from backend.modules.incidents.models import (
    Incident,
    IncidentTimeline,
    IncidentComment,
    IncidentRCA,
    AlertConfig,
    OncallRotation,
    EscalationPolicy,
)
from backend.modules.incidents.schemas import (
    IncidentCreate,
    IncidentResponse,
    IncidentUpdate,
    IncidentListResponse,
    IncidentStatsResponse,
    IncidentTimelineResponse,
    IncidentCommentRequest,
    IncidentCommentResponse,
    IncidentRCAResponse,
    AlertConfigCreate,
    AlertConfigResponse,
    AlertConfigUpdate,
    AlertTestRequest,
    OncallRotationCreate,
    OncallRotationResponse,
    EscalationPolicyCreate,
    EscalationPolicyResponse,
)
from backend.modules.incidents.service import IncidentService
from backend.modules.incidents.rca_service import RCAService
from backend.modules.incidents.alert_service import AlertService
from backend.modules.incidents.rotation_service import RotationService
from backend.modules.incidents.escalation_service import EscalationService

logger = logging.getLogger("qolyx.api.routes.incidents")

router = APIRouter(prefix="/incidents", tags=["Incidents"])


# --- INCIDENT ENDPOINTS (1-9) ---

@router.post("", response_model=IncidentResponse, status_code=status.HTTP_201_CREATED)
def create_incident(payload: IncidentCreate, db: Session = Depends(get_db)) -> IncidentResponse:
    """Create a new incident record in the database if one does not already exist."""
    try:
        incident = IncidentService.create(db, payload)
        return incident
    except Exception as exc:
        logger.error("Failed to create incident via API", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while creating the incident."
        )


@router.get("", response_model=IncidentListResponse)
def list_incidents(
    table_name: Optional[str] = None,
    severity: Optional[str] = None,
    state: Optional[str] = None,
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(20, ge=1, le=100, description="Items per page"),
    db: Session = Depends(get_db)
) -> IncidentListResponse:
    """Retrieve a paginated and filtered list of incident records."""
    try:
        result = IncidentService.list(
            db=db,
            table_name=table_name,
            severity=severity,
            state=state,
            page=page,
            page_size=page_size
        )
        return IncidentListResponse.model_validate(result)
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to list incidents", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while retrieving incidents."
        )


@router.get("/stats", response_model=IncidentStatsResponse)
def get_incident_stats(
    table_name: Optional[str] = None,
    db: Session = Depends(get_db)
) -> IncidentStatsResponse:
    """Calculate summary statistics and metrics for incidents."""
    try:
        stats = IncidentService.stats(db, table_name)
        return IncidentStatsResponse(**stats)
    except Exception as exc:
        logger.error("Failed to calculate incident stats", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while calculating statistics."
        )


@router.get("/{incident_id:uuid}", response_model=IncidentResponse)
def get_incident(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> IncidentResponse:
    """Retrieve details of a single incident by its unique ID."""
    incident = IncidentService.get(db, incident_id)
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    return incident


@router.patch("/{incident_id:uuid}", response_model=IncidentResponse)
def update_incident(
    incident_id: uuid.UUID,
    payload: IncidentUpdate,
    db: Session = Depends(get_db)
) -> IncidentResponse:
    """Update incident status and assignment parameters."""
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )

    try:
        # Update state if provided
        if payload.state is not None:
            IncidentService.update_state(
                db=db,
                incident_id=incident_id,
                new_state=payload.state,
                notes=payload.resolution_notes,
                updated_by="operator"
            )

        # Update assignment if provided
        if payload.assigned_to is not None or payload.assigned_team is not None:
            IncidentService.assign(
                db=db,
                incident_id=incident_id,
                assigned_to=payload.assigned_to if payload.assigned_to is not None else incident.assigned_to,
                assigned_team=payload.assigned_team if payload.assigned_team is not None else incident.assigned_team,
                updated_by="operator"
            )

        db.refresh(incident)
        # Fetch updated details preloading relationships
        updated_incident = IncidentService.get(db, incident_id)
        return updated_incident
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to update incident", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the incident."
        )


@router.post("/{incident_id:uuid}/acknowledge", response_model=IncidentResponse)
def acknowledge_incident(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> IncidentResponse:
    """Acknowledge an open incident, setting the state to ACKNOWLEDGED."""
    incident = IncidentService.acknowledge(db, incident_id, acknowledged_by="operator")
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    return incident


@router.post("/{incident_id:uuid}/resolve", response_model=IncidentResponse)
def resolve_incident(
    incident_id: uuid.UUID,
    resolution_notes: str = Query(..., min_length=1, description="Notes summarizing the resolution"),
    db: Session = Depends(get_db)
) -> IncidentResponse:
    """Resolve an incident, adding resolution notes."""
    incident = IncidentService.resolve(db, incident_id, resolution_notes, resolved_by="operator")
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    return incident


@router.post("/{incident_id:uuid}/close", response_model=IncidentResponse)
def close_incident(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> IncidentResponse:
    """Mark a resolved incident as CLOSED."""
    incident = IncidentService.close(db, incident_id, closed_by="operator")
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    return incident


@router.post("/{incident_id:uuid}/reopen", response_model=IncidentResponse)
def reopen_incident(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> IncidentResponse:
    """Reopen a resolved or closed incident."""
    incident = IncidentService.reopen(db, incident_id, reopened_by="operator")
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    return incident


# --- TIMELINE & COMMENTS ENDPOINTS (10-12) ---

@router.get("/{incident_id:uuid}/timeline", response_model=List[IncidentTimelineResponse])
def get_incident_timeline(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> List[IncidentTimelineResponse]:
    """Retrieve the full event timeline for an incident."""
    # Ensure incident exists
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    timeline = db.query(IncidentTimeline).filter(
        IncidentTimeline.incident_id == incident_id
    ).order_by(desc(IncidentTimeline.created_at)).all()
    return timeline


@router.get("/{incident_id:uuid}/comments", response_model=List[IncidentCommentResponse])
def get_incident_comments(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> List[IncidentCommentResponse]:
    """Retrieve comments logged for a specific incident."""
    # Ensure incident exists
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Incident with ID {incident_id} not found."
        )
    comments = db.query(IncidentComment).filter(
        IncidentComment.incident_id == incident_id
    ).order_by(IncidentComment.created_at.asc()).all()
    return comments


@router.post("/{incident_id:uuid}/comments", response_model=IncidentCommentResponse, status_code=status.HTTP_201_CREATED)
def add_incident_comment(
    incident_id: uuid.UUID,
    payload: IncidentCommentRequest,
    db: Session = Depends(get_db)
) -> IncidentCommentResponse:
    """Add a new comment or note to an incident."""
    try:
        comment = IncidentService.add_comment(db, incident_id, payload)
        return comment
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to add comment via API", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while adding the comment."
        )


# --- ROOT CAUSE ANALYSIS (RCA) ENDPOINTS (13-15) ---

@router.get("/{incident_id:uuid}/rca", response_model=IncidentRCAResponse)
def get_latest_rca(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> IncidentRCAResponse:
    """Retrieve the latest Root Cause Analysis (RCA) version generated for an incident."""
    rca = db.query(IncidentRCA).filter(
        IncidentRCA.incident_id == incident_id
    ).order_by(desc(IncidentRCA.version)).first()

    if not rca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No Root Cause Analysis (RCA) found for incident {incident_id}."
        )
    return rca


@router.get("/{incident_id:uuid}/rca/version/{version}", response_model=IncidentRCAResponse)
def get_rca_by_version(
    incident_id: uuid.UUID,
    version: int,
    db: Session = Depends(get_db)
) -> IncidentRCAResponse:
    """Retrieve a specific version of Root Cause Analysis (RCA) for an incident."""
    rca = db.query(IncidentRCA).filter(
        IncidentRCA.incident_id == incident_id,
        IncidentRCA.version == version
    ).first()

    if not rca:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"RCA version {version} not found for incident {incident_id}."
        )
    return rca


@router.post("/{incident_id:uuid}/rca/regenerate", response_model=IncidentRCAResponse)
def regenerate_rca(incident_id: uuid.UUID, db: Session = Depends(get_db)) -> IncidentRCAResponse:
    """Trigger manual regeneration of the Root Cause Analysis (RCA) metrics."""
    try:
        rca = RCAService.generate_rca(db, incident_id)
        return rca
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed to regenerate RCA", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the Root Cause Analysis."
        )


# --- ALERT CONFIGURATIONS ENDPOINTS (16-21) ---

@router.post("/alerts/configs", response_model=AlertConfigResponse, status_code=status.HTTP_201_CREATED)
def create_alert_config(payload: AlertConfigCreate, db: Session = Depends(get_db)) -> AlertConfigResponse:
    """Create a new alert notification configuration channel."""
    db_config = AlertConfig(
        id=uuid.uuid4(),
        name=payload.name,
        channel_type=payload.channel_type,
        webhook_url=payload.webhook_url,
        email_config=payload.email_config,
        telegram_bot_token=payload.telegram_bot_token,
        telegram_chat_id=payload.telegram_chat_id,
        severity_threshold=payload.severity_threshold,
        is_active=payload.is_active
    )
    try:
        db.add(db_config)
        db.commit()
        db.refresh(db_config)
        return db_config
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create alert configuration", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the alert configuration."
        )


@router.get("/alerts/configs", response_model=List[AlertConfigResponse])
def list_alert_configs(db: Session = Depends(get_db)) -> List[AlertConfigResponse]:
    """Retrieve all alert configurations."""
    return db.query(AlertConfig).all()


@router.get("/alerts/configs/{config_id}", response_model=AlertConfigResponse)
def get_alert_config(config_id: uuid.UUID, db: Session = Depends(get_db)) -> AlertConfigResponse:
    """Retrieve details of a single alert configuration."""
    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert configuration with ID {config_id} not found."
        )
    return config


@router.put("/alerts/configs/{config_id}", response_model=AlertConfigResponse)
def update_alert_config(
    config_id: uuid.UUID,
    payload: AlertConfigUpdate,
    db: Session = Depends(get_db)
) -> AlertConfigResponse:
    """Update an existing alert notification channel config."""
    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert configuration with ID {config_id} not found."
        )

    for key, val in payload.model_dump(exclude_unset=True).items():
        setattr(config, key, val)

    try:
        config.updated_at = datetime.now(timezone.utc)
        db.commit()
        db.refresh(config)
        return config
    except Exception as exc:
        db.rollback()
        logger.error("Failed to update alert configuration", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while updating the configuration."
        )


@router.delete("/alerts/configs/{config_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_alert_config(config_id: uuid.UUID, db: Session = Depends(get_db)) -> None:
    """Delete an alert configuration channel from the database."""
    config = db.query(AlertConfig).filter(AlertConfig.id == config_id).first()
    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Alert configuration with ID {config_id} not found."
        )

    try:
        db.delete(config)
        db.commit()
        return None
    except Exception as exc:
        db.rollback()
        logger.error("Failed to delete alert configuration", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while deleting the configuration."
        )


@router.post("/alerts/configs/test", status_code=status.HTTP_200_OK)
def test_alert_channel(payload: AlertTestRequest, db: Session = Depends(get_db)) -> dict:
    """Send a manual test alert message using the first active config matching the channel type."""
    config = db.query(AlertConfig).filter(
        AlertConfig.channel_type == payload.channel_type,
        AlertConfig.is_active == True
    ).first()

    if not config:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No active alert configuration found for channel type '{payload.channel_type}'."
        )

    success = AlertService.test_alert(db, config.id, payload.message)
    return {"status": "success" if success else "failed", "sent": success}


# --- ON-CALL ROTATIONS ENDPOINTS (22-24) ---

@router.post("/rotations", response_model=OncallRotationResponse, status_code=status.HTTP_201_CREATED)
def create_oncall_rotation(payload: OncallRotationCreate, db: Session = Depends(get_db)) -> OncallRotationResponse:
    """Create a new developer on-call rotation schedule."""
    db_rot = OncallRotation(
        id=uuid.uuid4(),
        name=payload.name,
        team_name=payload.team_name,
        members=payload.members,
        rotation_type=payload.rotation_type,
        current_index=0,
        last_rotated_at=None
    )
    try:
        db.add(db_rot)
        db.commit()
        db.refresh(db_rot)
        return db_rot
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create on-call rotation", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the rotation schedule."
        )


@router.get("/rotations", response_model=List[OncallRotationResponse])
def list_oncall_rotations(db: Session = Depends(get_db)) -> List[OncallRotationResponse]:
    """Retrieve all on-call rotation schedules."""
    return db.query(OncallRotation).all()


@router.post("/rotations/{rotation_id}/rotate", response_model=OncallRotationResponse)
def trigger_manual_rotation(rotation_id: uuid.UUID, db: Session = Depends(get_db)) -> OncallRotationResponse:
    """Manually rotate the on-call schedule to the next active developer."""
    try:
        rotation = RotationService.rotate(db, rotation_id)
        return rotation
    except ValueError as exc:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(exc))
    except Exception as exc:
        logger.error("Failed manual on-call rotation trigger", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred during rotation execution."
        )


# --- ESCALATION POLICY ENDPOINTS (25-27) ---

@router.post("/escalation-policies", response_model=EscalationPolicyResponse, status_code=status.HTTP_201_CREATED)
def create_escalation_policy(payload: EscalationPolicyCreate, db: Session = Depends(get_db)) -> EscalationPolicyResponse:
    """Create a new escalation routing policy for unresolved incidents."""
    # Ensure severity uniqueness checks
    existing = db.query(EscalationPolicy).filter(
        EscalationPolicy.severity == payload.severity.upper()
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An escalation policy for severity '{payload.severity}' already exists."
        )

    db_policy = EscalationPolicy(
        id=uuid.uuid4(),
        name=payload.name,
        severity=payload.severity.upper(),
        timeout_minutes=payload.timeout_minutes,
        target_type=payload.target_type,
        target_identifier=payload.target_identifier
    )
    try:
        db.add(db_policy)
        db.commit()
        db.refresh(db_policy)
        return db_policy
    except Exception as exc:
        db.rollback()
        logger.error("Failed to create escalation policy", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while saving the escalation policy."
        )


@router.get("/escalation-policies", response_model=List[EscalationPolicyResponse])
def list_escalation_policies(db: Session = Depends(get_db)) -> List[EscalationPolicyResponse]:
    """Retrieve all configured escalation policies."""
    return db.query(EscalationPolicy).all()


@router.post("/escalation-policies/check", status_code=status.HTTP_200_OK)
def trigger_escalation_checks(db: Session = Depends(get_db)) -> dict:
    """Manually evaluate all active open incidents for escalation timeouts."""
    try:
        count = EscalationService.check_escalations(db)
        return {"status": "success", "escalated_count": count}
    except Exception as exc:
        logger.error("Failed to run manual escalation policy checks", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while executing the escalation checks."
        )


@router.get("/ntfy/topic", status_code=status.HTTP_200_OK)
def get_ntfy_topic() -> dict:
    """Retrieve the generated default Ntfy alert topic and public subscribe URL."""
    try:
        topic = get_or_create_ntfy_topic()
        return {"topic": topic, "url": f"https://ntfy.sh/{topic}"}
    except Exception as exc:
        logger.error("Failed to retrieve Ntfy topic via API", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while fetching the Ntfy topic."
        )


@router.get("/ntfy/qrcode", status_code=status.HTTP_200_OK)
def get_ntfy_qrcode() -> dict:
    """Generate a QR code image pointing to the default Ntfy topic subscribe URL."""
    try:
        topic = get_or_create_ntfy_topic()
        ntfy_url = f"https://ntfy.sh/{topic}"

        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(ntfy_url)
        qr.make(fit=True)
        img = qr.make_image(fill_color="black", back_color="white")

        buffered = BytesIO()
        img.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")

        return {
            "qr_code": f"data:image/png;base64,{img_str}",
            "topic": topic,
            "url": ntfy_url
        }
    except Exception as exc:
        logger.error("Failed to generate Ntfy QR code via API", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="An error occurred while generating the Ntfy QR code."
        )
