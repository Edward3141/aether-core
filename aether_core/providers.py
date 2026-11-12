"""LiteLLM provider adapter. Created by Edward Tejada."""
from litellm import acompletion
from .config import MODEL, API_BASE, API_KEY

async def ask_model(system_prompt: str, user_prompt: str) -> str:
    kwargs = {"model": MODEL, "messages": [
        {"role": "system", "content": system_prompt[:8000]},
        {"role": "user", "content": user_prompt[:12000]},
    ]}
    if API_BASE:
        kwargs["api_base"] = API_BASE
    if API_KEY:
        kwargs["api_key"] = API_KEY
    response = await acompletion(**kwargs)
    content = response.choices[0].message.content
    if not isinstance(content, str):
        raise RuntimeError("The selected model returned no text response.")
    return content[:12000]
