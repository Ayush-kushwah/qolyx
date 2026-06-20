import logging
import uuid
from typing import List
from datetime import datetime, timezone
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from backend.core.database import get_db
from backend.core.config import settings
from backend.modules.users.models import User, LLMProvider
from backend.modules.users.settings_schemas import (
    LLMProviderRequest,
    LLMProviderResponse,
    LLMProviderTestRequest,
)
from backend.modules.users.utils import encrypt_config
from backend.api.routes.users import get_current_user
from backend.utils.llm_gateway import execute_llm_chat

logger = logging.getLogger("qolyx.api.routes.llm")

router = APIRouter(prefix="/llm", tags=["LLM Gateway"])

@router.get("/providers", response_model=List[LLMProviderResponse])
def list_providers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> List[LLMProviderResponse]:
    """Retrieve all configured LLM providers for the current user."""
    return db.query(LLMProvider).filter(LLMProvider.user_id == current_user.id).order_by(LLMProvider.priority.asc()).all()

@router.post("/providers", response_model=LLMProviderResponse)
def create_provider(
    payload: LLMProviderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> LLMProviderResponse:
    """Create a new LLM provider config, encrypting the API key at rest."""
    logger.info(f"Creating LLM provider '{payload.name}' for user {current_user.email}")

    encrypted_key = None
    if payload.api_key:
        encrypted_key = encrypt_config(payload.api_key, settings.SECRET_KEY.get_secret_value())

    new_provider = LLMProvider(
        id=uuid.uuid4(),
        user_id=current_user.id,
        name=payload.name,
        provider_type=payload.provider_type.upper(),
        base_url=payload.base_url,
        model_name=payload.model_name,
        encrypted_api_key=encrypted_key,
        is_active=payload.is_active,
        priority=payload.priority,
        created_at=datetime.now(timezone.utc)
    )

    db.add(new_provider)
    db.commit()
    db.refresh(new_provider)
    return new_provider

@router.put("/providers/{provider_id}", response_model=LLMProviderResponse)
def update_provider(
    provider_id: uuid.UUID,
    payload: LLMProviderRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
) -> LLMProviderResponse:
    """Update an existing LLM provider configuration."""
    logger.info(f"Updating LLM provider {provider_id} for user {current_user.email}")

    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_id,
        LLMProvider.user_id == current_user.id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM Provider not found or unauthorized."
        )

    provider.name = payload.name
    provider.provider_type = payload.provider_type.upper()
    provider.base_url = payload.base_url
    provider.model_name = payload.model_name
    provider.is_active = payload.is_active
    provider.priority = payload.priority

    if payload.api_key:
        # User specified a new key, encrypt it
        provider.encrypted_api_key = encrypt_config(payload.api_key, settings.SECRET_KEY.get_secret_value())

    db.commit()
    db.refresh(provider)
    return provider

@router.delete("/providers/{provider_id}")
def delete_provider(
    provider_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Delete an LLM provider configuration."""
    logger.info(f"Deleting LLM provider {provider_id} for user {current_user.email}")

    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_id,
        LLMProvider.user_id == current_user.id
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="LLM Provider not found or unauthorized."
        )

    db.delete(provider)
    db.commit()
    return {"message": "LLM Provider configuration deleted successfully."}

@router.post("/providers/test")
def test_provider_connection(
    payload: LLMProviderTestRequest,
    current_user: User = Depends(get_current_user)
):
    """Verify connectivity to an LLM provider before saving the configuration."""
    logger.info(f"Testing LLM connectivity: {payload.provider_type} -> {payload.model_name} at {payload.base_url}")

    # Build a temporary in-memory configuration object
    temp_provider = LLMProvider(
        name="Connectivity Test",
        provider_type=payload.provider_type.upper(),
        base_url=payload.base_url,
        model_name=payload.model_name,
        encrypted_api_key=None
    )

    if payload.api_key:
        temp_provider.encrypted_api_key = encrypt_config(payload.api_key, settings.SECRET_KEY.get_secret_value())

    try:
        test_prompt = "Hello. Respond with the single word 'OK'."
        response_text = execute_llm_chat(temp_provider, prompt=test_prompt)
        logger.info(f"Test LLM connection successful. Response: {response_text}")
        return {"success": True, "message": "Connection test successful.", "response_preview": response_text[:100]}
    except Exception as e:
        logger.warning(f"Connection test failed: {e}")
        return {"success": False, "message": str(e)}

@router.post("/chat")
def chat_gateway(
    provider_id: uuid.UUID,
    prompt: str,
    system_prompt: str = "",
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Execute completions through the gateway proxy for a saved provider."""
    provider = db.query(LLMProvider).filter(
        LLMProvider.id == provider_id,
        LLMProvider.user_id == current_user.id,
        LLMProvider.is_active == True
    ).first()

    if not provider:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Active LLM Provider not found or unauthorized."
        )

    try:
        response_text = execute_llm_chat(provider, prompt=prompt, system_prompt=system_prompt)
        return {"response": response_text}
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate completion: {e}"
        )
