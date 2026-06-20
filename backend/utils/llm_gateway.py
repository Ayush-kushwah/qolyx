import gc
import logging
import httpx
import openai
from typing import List, Dict, Any, Optional
from backend.modules.users.models import LLMProvider
from backend.modules.users.utils import decrypt_config
from backend.core.config import settings

logger = logging.getLogger("qolyx.utils.llm_gateway")

def execute_llm_chat(provider: LLMProvider, prompt: str, system_prompt: str = "") -> str:
    """Routes completion prompts to any configured model endpoint securely."""
    logger.info(f"Routing LLM completion request to provider: {provider.name} ({provider.provider_type}) using model: {provider.model_name}")

    # Decrypt Key in-memory
    api_key: Optional[str] = None
    if provider.encrypted_api_key:
        try:
            api_key = decrypt_config(provider.encrypted_api_key, settings.SECRET_KEY.get_secret_value())
        except Exception as e:
            logger.error(f"Failed to decrypt API key for provider {provider.name}: {e}")
            raise RuntimeError("Failed to decrypt model API key credentials.")

    try:
        if provider.provider_type == "ANTHROPIC":
            # Translate message schema and call Anthropic Messages HTTP REST API
            headers = {
                "x-api-key": api_key or "",
                "anthropic-version": "2023-06-01",
                "content-type": "application/json"
            }
            
            payload: Dict[str, Any] = {
                "model": provider.model_name,
                "max_tokens": 2048,
                "messages": [{"role": "user", "content": prompt}],
            }
            
            if system_prompt:
                payload["system"] = system_prompt
                
            url = provider.base_url or "https://api.anthropic.com/v1/messages"
            
            # Outbound request over HTTP
            with httpx.Client(timeout=30.0) as client:
                resp = client.post(url, headers=headers, json=payload)
                resp.raise_for_status()
                data = resp.json()
                result = data["content"][0]["text"]
                
        else:
            # Standard OpenAI-Compatible router (OpenAI, Ollama, Groq, vLLM, Custom)
            # Use decrypted api_key or default to a dummy string for Ollama/local
            client = openai.OpenAI(
                base_url=provider.base_url,
                api_key=api_key or "local-ollama"
            )
            
            messages: List[Dict[str, str]] = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})
            
            response = client.chat.completions.create(
                model=provider.model_name,
                messages=messages,
                temperature=0.2,
                timeout=30.0
            )
            result = response.choices[0].message.content or ""
            
        return result

    except Exception as exc:
        logger.error(f"LLM request failure on provider {provider.name}: {exc}", exc_info=True)
        raise RuntimeError(f"Model service completion failed: {exc}")
        
    finally:
        # Secure memory cleaning
        if api_key:
            # Overwrite reference string if mutable, then delete reference
            api_key = None
            del api_key
        gc.collect()
