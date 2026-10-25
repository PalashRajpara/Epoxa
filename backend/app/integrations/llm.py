from typing import Optional, List, Dict, Any
from app.core.config import settings
from app.core.logging import logger
from app.core.exceptions import ProviderError

try:
    from groq import AsyncGroq
    GROQ_AVAILABLE = True
except ImportError:
    GROQ_AVAILABLE = False

try:
    from openai import AsyncOpenAI
    OPENAI_AVAILABLE = True
except ImportError:
    OPENAI_AVAILABLE = False

class LLMService:
    def __init__(self):
        self.groq_client: Optional[Any] = None
        self.openai_client: Optional[Any] = None

        if settings.GROQ_API_KEY and GROQ_AVAILABLE:
            self.groq_client = AsyncGroq(api_key=settings.GROQ_API_KEY)

        if settings.OPENAI_API_KEY and OPENAI_AVAILABLE:
            self.openai_client = AsyncOpenAI(api_key=settings.OPENAI_API_KEY)

    async def generate_response(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.1,
        tools: Optional[List[Dict[str, Any]]] = None
    ) -> Dict[str, Any]:
        """Executes LLM chat completion using Groq (or OpenAI fallback)."""
        # 1. Try Groq
        if self.groq_client:
            try:
                kwargs = {
                    "model": settings.DEFAULT_LLM_MODEL,
                    "messages": messages,
                    "temperature": temperature,
                }
                if tools:
                    kwargs["tools"] = tools
                    kwargs["tool_choice"] = "auto"

                response = await self.groq_client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message

                tool_calls = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        tool_calls.append({
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })

                return {
                    "content": message.content or "",
                    "tool_calls": tool_calls,
                    "finish_reason": choice.finish_reason
                }
            except Exception as e:
                logger.error("Groq inference error; checking fallbacks", error=str(e))

        # 2. Try OpenAI Fallback
        if self.openai_client:
            try:
                kwargs = {
                    "model": "gpt-4o-mini",
                    "messages": messages,
                    "temperature": temperature,
                }
                if tools:
                    kwargs["tools"] = tools

                response = await self.openai_client.chat.completions.create(**kwargs)
                choice = response.choices[0]
                message = choice.message
                tool_calls = []
                if message.tool_calls:
                    for tc in message.tool_calls:
                        tool_calls.append({
                            "id": tc.id,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments
                            }
                        })
                return {
                    "content": message.content or "",
                    "tool_calls": tool_calls,
                    "finish_reason": choice.finish_reason
                }
            except Exception as e:
                logger.error("OpenAI fallback failed", error=str(e))

        # 3. Deterministic Mock Response for testing
        last_user_msg = next((m["content"] for m in reversed(messages) if m["role"] == "user"), "")
        content = (
            f"Thank you for contacting Epoxa support. I heard: '{last_user_msg}'. "
            "How may I assist you with your order, product questions, or would you like to speak with a supervisor?"
        )
        return {
            "content": content,
            "tool_calls": [],
            "finish_reason": "stop"
        }

llm_service = LLMService()
