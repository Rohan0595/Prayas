"""
LiteLLM-backed LLM client.
Supports Groq, Gemini, and any other LiteLLM-compatible provider.
Exports the same interface as the previous OpenRouter client so
chat.py and agent.py require zero logic changes.
"""
import asyncio
import litellm
from typing import AsyncIterator, List, Dict, Any, Optional
from app.core.config import settings

# Disable LiteLLM's verbose logging
litellm.set_verbose = False


class OpenRouterError(Exception):
    """Raised when the LLM call fails."""
    pass


class LiteLLMClient:
    """
    Thin async wrapper around LiteLLM.
    Provides the same interface the rest of the app expects:
      - chat_completion()        → non-streaming dict (OpenAI format)
      - stream_chat_completion() → async generator of text chunks
    """

    async def chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        tools: Optional[List[Dict]] = None,
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> Dict[str, Any]:
        """Non-streaming completion — used for tool/agent calls."""
        kwargs: Dict[str, Any] = dict(
            model=model,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=False,
        )
        if tools:
            kwargs["tools"] = tools
            kwargs["tool_choice"] = "auto"

        try:
            response = await litellm.acompletion(**kwargs)
            # Return as a plain dict so agent.py can index it the same way
            return response.model_dump()
        except litellm.exceptions.RateLimitError as e:
            raise OpenRouterError(f"Rate limited: {e}")
        except litellm.exceptions.AuthenticationError as e:
            raise OpenRouterError(f"Auth error: {e}")
        except Exception as e:
            raise OpenRouterError(str(e))

    async def stream_chat_completion(
        self,
        model: str,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 2048,
    ) -> AsyncIterator[str]:
        """
        Stream a chat completion.
        Yields plain text delta strings for the frontend to display.
        """
        try:
            response = await litellm.acompletion(
                model=model,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                stream=True,
            )
            async for chunk in response:
                delta = chunk.choices[0].delta
                content = getattr(delta, "content", None)
                if content:
                    yield content
        except litellm.exceptions.RateLimitError as e:
            raise OpenRouterError(f"Rate limited (429): {e}")
        except litellm.exceptions.AuthenticationError as e:
            raise OpenRouterError(f"Auth error: {e}")
        except Exception as e:
            raise OpenRouterError(str(e))


# Singleton — same name as before so no import changes needed elsewhere
openrouter_client = LiteLLMClient()
