"""LiteLLM provider adapter. Created by Edward Tejada."""
from litellm import acompletion

from .config import model_settings


async def ask_model(system_prompt: str, user_prompt: str, agent: str | None = None) -> str:
    """Call the configured model for an agent without exposing credentials."""
    settings = model_settings(agent)
    kwargs = {
        "model": settings.model,
        "messages": [
            {"role": "system", "content": system_prompt[:8000]},
            {"role": "user", "content": user_prompt[:12000]},
        ],
    }
    if settings.api_base:
        kwargs["api_base"] = settings.api_base
    if settings.api_key:
        kwargs["api_key"] = settings.api_key

    response = await acompletion(**kwargs)
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise TypeError("The selected model returned no text response.")
    return content[:12000]
