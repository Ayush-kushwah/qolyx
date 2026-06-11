import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field, ConfigDict

class AnomalyDetectionRequest(BaseModel):
    """Schema representing a request to analyze a run for anomalies."""
    model_config = ConfigDict(frozen=True)

    pipeline_run_id: uuid.UUID = Field(
        ...,
        description="The unique identifier for the pipeline run."
    )
    table_name: str = Field(
        ...,
        description="The physical database table name checked."
    )
    feature_values: Dict[str, Any] = Field(
        ...,
        description="Key-value metrics collected for the run to be analyzed."
    )


class AnomalyDetectionResponse(BaseModel):
    """Schema representing the details of a detected anomaly."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID) of the anomaly detection record."
    )
    pipeline_run_id: uuid.UUID = Field(
        ...,
        description="The unique identifier of the pipeline run that triggered the detection."
    )
    table_name: str = Field(
        ...,
        description="The physical database table name where anomaly was detected."
    )
    anomaly_type: str = Field(
        ...,
        description="The classified type of the anomaly (e.g., volume_spike, volume_drop)."
    )
    anomaly_score: float = Field(
        ...,
        description="The calculated anomaly score (0 to 1)."
    )
    anomaly_penalty: int = Field(
        ...,
        description="The trust score penalty deducted for this anomaly (0 to 20)."
    )
    feature_values: Optional[Dict[str, Any]] = Field(
        None,
        description="The values of features analyzed during detection."
    )
    explanation: Optional[str] = Field(
        None,
        description="A human-readable explanation of why this run was flagged."
    )
    is_acknowledged: bool = Field(
        ...,
        description="Whether the anomaly alert has been acknowledged by a human user."
    )
    is_false_positive: bool = Field(
        ...,
        description="Flag indicating if this alert was marked as a false positive."
    )
    last_alerted_at: Optional[datetime] = Field(
        None,
        description="Timestamp when the notification was last dispatched."
    )
    created_at: datetime = Field(
        ...,
        description="The UTC timestamp when this detection was recorded."
    )
    updated_at: datetime = Field(
        ...,
        description="The UTC timestamp when this detection was last updated."
    )


class BaselineTrainingRequest(BaseModel):
    """Schema representing a request to train baseline metrics for a table."""
    model_config = ConfigDict(frozen=True)

    table_name: str = Field(
        ...,
        description="The physical database table to train the baseline statistics for."
    )
    force_retrain: bool = Field(
        False,
        description="Flag to force retraining even if baseline already exists."
    )


class BaselineTrainingResponse(BaseModel):
    """Schema representing the response summary of baseline training."""
    model_config = ConfigDict(from_attributes=True)

    table_name: str = Field(
        ...,
        description="The physical database table name."
    )
    features_count: int = Field(
        ...,
        description="Number of feature metrics trained in the baseline."
    )
    training_run_count: int = Field(
        ...,
        description="Total number of pipeline runs used as historical samples for training."
    )
    training_completed: bool = Field(
        ...,
        description="True if the training run finished successfully, False otherwise."
    )


class AnomalyFeedbackRequest(BaseModel):
    """Schema representing user feedback submitted for a detection."""
    model_config = ConfigDict(frozen=True)

    feedback_type: str = Field(
        ...,
        description="Feedback category (e.g. 'false_positive', 'correct', 'needs_investigation')."
    )
    user_notes: Optional[str] = Field(
        None,
        description="Optional detailed text comments from the operator."
    )
    created_by: str = Field(
        ...,
        description="User identifier submitting the feedback."
    )


class AnomalyFeedbackResponse(BaseModel):
    """Schema representing the recorded feedback details."""
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID = Field(
        ...,
        description="Unique identifier (UUID) of the feedback record."
    )
    anomaly_detection_id: uuid.UUID = Field(
        ...,
        description="Reference to the anomaly detection record."
    )
    feedback_type: str = Field(
        ...,
        description="Feedback category."
    )
    user_notes: Optional[str] = Field(
        None,
        description="Optional detailed text comments from the operator."
    )
    created_by: str = Field(
        ...,
        description="User identifier who created the feedback."
    )
    created_at: datetime = Field(
        ...,
        description="The UTC timestamp when this feedback was recorded."
    )


class AnomalyListResponse(BaseModel):
    """Schema representing a paginated list of anomaly detections."""
    model_config = ConfigDict(from_attributes=True)

    detections: List[AnomalyDetectionResponse] = Field(
        ...,
        description="The list of anomaly detections on the current page."
    )
    total: int = Field(
        ...,
        description="The total count of detections matching filters."
    )
    page: int = Field(
        ...,
        description="The current page index (1-based)."
    )
    page_size: int = Field(
        ...,
        description="The limit of items returned per page."
    )


class BaselineProgress(BaseModel):
    """Schema representing baseline training progress for a table."""
    runs_completed: int = Field(
        ...,
        description="The actual count of pipeline runs completed for this table."
    )
    runs_needed: int = Field(
        7,
        description="The target number of pipeline runs needed to establish the baseline."
    )
    is_ready: bool = Field(
        ...,
        description="Whether the baseline is ready (runs_completed >= runs_needed)."
    )
    estimated_minutes_remaining: Optional[int] = Field(
        None,
        description="The estimated number of minutes remaining for baseline training."
    )


class BaselineProgressResponse(BaseModel):
    """Schema representing baseline training progress for all tables."""
    bronze_financial_candles: BaselineProgress = Field(
        ...,
        description="Baseline training progress for the Financial Candles table."
    )
    bronze_fda_events: BaselineProgress = Field(
        ...,
        description="Baseline training progress for the FDA Events table."
    )
    bronze_github_events: BaselineProgress = Field(
        ...,
        description="Baseline training progress for the GitHub Events table."
    )

